# Codex 2026-09-11: shared, project-scoped startup/lifecycle primitives.
# Dot-source only. No process is started or stopped while loading this file.
Add-Type -AssemblyName System.Net.Http

function Get-AgentSetting {
    param([string]$Name, [string]$DefaultValue = "")
    # Match python-dotenv: the inherited process environment takes precedence.
    $inherited = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ($null -ne $inherited) { return $inherited }
    if (-not (Test-Path -LiteralPath $envPath)) { return $DefaultValue }
    $pattern = '^\s*' + [regex]::Escape($Name) + '\s*=\s*(.*)$'
    $line = Get-Content -LiteralPath $envPath | Where-Object { $_ -match $pattern } | Select-Object -Last 1
    if ($null -eq $line) { return $DefaultValue }
    return ([regex]::Match($line, $pattern).Groups[1].Value.Trim()).Trim('"').Trim("'")
}

function Initialize-AgentRuntime {
    param([string]$Root)
    $script:repoRoot = (Resolve-Path -LiteralPath $Root).Path
    $script:coreRoot = Join-Path $repoRoot 'services\agent-core'
    $script:pythonPath = Join-Path $coreRoot '.venv\Scripts\python.exe'
    $script:envPath = Join-Path $repoRoot '.env'
    $script:avatarRoot = Join-Path $repoRoot 'apps\avatar-runtime'
    $script:logRoot = Join-Path $env:LOCALAPPDATA 'AnimeAgent\logs'
    $portText = Get-AgentSetting 'AGENT_CORE_PORT' '8765'
    $script:corePort = 0
    if (-not [int]::TryParse($portText, [ref]$script:corePort) -or $corePort -lt 1 -or $corePort -gt 65535) {
        throw 'AGENT_CORE_PORT must be an integer between 1 and 65535.'
    }
    $script:healthBase = "http://127.0.0.1:$corePort"
    $env:AGENT_CORE_WS_URL = "ws://127.0.0.1:$corePort/ws"
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($repoRoot.ToLowerInvariant() + ":$corePort")
        $script:runtimeKey = ([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-', '').Substring(0, 24)
    } finally { $hasher.Dispose() }
}

function Enter-AgentLock {
    param([string]$Suffix = 'startup', [int]$TimeoutSeconds = 180)
    $mutex = New-Object Threading.Mutex($false, "Local\AnimeAgent-$runtimeKey-$Suffix")
    $acquired = $false
    try {
        try { $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds($TimeoutSeconds)) }
        catch [Threading.AbandonedMutexException] { $acquired = $true }
        if (-not $acquired) { throw 'Another Anime Agent lifecycle operation is still running; no duplicate instance was started.' }
        return $mutex
    } catch { $mutex.Dispose(); throw }
}

function Exit-AgentLock {
    param($Mutex)
    if ($null -ne $Mutex) { $Mutex.ReleaseMutex(); $Mutex.Dispose() }
}

function Invoke-AgentHealthRequest {
    param([string]$Uri, [int]$TimeoutSeconds)
    $handler = New-Object Net.Http.HttpClientHandler
    $handler.UseProxy = $false
    $client = New-Object Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
    $response = $null
    try {
        $response = $client.GetAsync($Uri).GetAwaiter().GetResult()
        if ([int]$response.StatusCode -eq 404) { return [pscustomobject]@{ Missing = $true; Payload = $null } }
        if (-not $response.IsSuccessStatusCode) { return $null }
        $payload = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
        if ($payload.status -ne 'ok' -or $payload.service -ne 'anime-agent-core') { return $null }
        return [pscustomobject]@{ Missing = $false; Payload = $payload }
    } catch { return $null }
    finally {
        if ($null -ne $response) { $response.Dispose() }
        $client.Dispose(); $handler.Dispose()
    }
}

function Get-AgentCoreHealth {
    param([int]$ExpectedPid = 0)
    $result = Invoke-AgentHealthRequest "$healthBase/health/live" 2
    # Compatibility for an already-running pre-fix Core. Do NOT fall back on
    # timeout/500: only 404 proves it does not implement the cheap endpoint.
    if ($result -and $result.Missing) { $result = Invoke-AgentHealthRequest "$healthBase/health" 6 }
    if (-not $result -or -not $result.Payload) { return $null }
    if ($ExpectedPid -and $result.Payload.pid -and [int]$result.Payload.pid -ne $ExpectedPid) { return $null }
    return $result.Payload
}

function Get-AgentProcesses {
    # A permissions failure is NOT an empty process list. Fail safely.
    return @(Get-CimInstance Win32_Process -ErrorAction Stop)
}

function Test-ProjectCoreProcess {
    param($Process, [array]$Processes)
    if (-not $Process -or $Process.Name -notlike 'python*') { return $false }
    if ($Process.CommandLine -notmatch '(?:^|\s)-m\s+agent_core\.main(?:\s|$)') { return $false }
    if ($Process.ExecutablePath -eq $pythonPath) { return $true }
    # Windows venv python is a redirector; its worker uses the base interpreter.
    $parent = $Processes | Where-Object { $_.ProcessId -eq $Process.ParentProcessId } | Select-Object -First 1
    return ($null -ne $parent -and $parent.ExecutablePath -eq $pythonPath -and
        $parent.CommandLine -match '(?:^|\s)-m\s+agent_core\.main(?:\s|$)' -and
        $parent.CreationDate -le $Process.CreationDate)
}

function Get-AgentCoreState {
    $processes = Get-AgentProcesses
    $owned = @($processes | Where-Object { Test-ProjectCoreProcess $_ $processes })
    $listeners = @(Get-NetTCPConnection -ErrorAction Stop | Where-Object {
        $_.LocalPort -eq $corePort -and $_.State -eq 'Listen'
    })
    foreach ($listener in $listeners) {
        if ($listener.OwningProcess -notin $owned.ProcessId) {
            throw "Port $corePort belongs to an unverified/foreign process (PID $($listener.OwningProcess)). It was NOT stopped."
        }
    }
    $listenerPid = 0
    if ($listeners.Count) { $listenerPid = [int]$listeners[0].OwningProcess }
    return [pscustomobject]@{ Processes = $owned; ListenerPid = $listenerPid }
}

function Stop-ProjectCoreProcesses {
    param([array]$Processes)
    # Snapshot identity (PID + creation time + executable/parent) before each
    # stop. Never kill by image name, port alone, or a stale PID file.
    foreach ($candidate in ($Processes | Sort-Object CreationDate -Descending)) {
        $current = Get-AgentProcesses
        $same = $current | Where-Object {
            $_.ProcessId -eq $candidate.ProcessId -and $_.CreationDate -eq $candidate.CreationDate
        } | Select-Object -First 1
        if ($same -and (Test-ProjectCoreProcess $same $current)) {
            Stop-AgentProcessTree $same.ProcessId
        }
    }
}

function Stop-AgentProcessTree {
    param([int]$ProcessId)
    # The caller has just verified this exact project's root and creation time.
    # /T also ends its MCP/stdio descendants; never use image-name-wide kills.
    try { $null = & "$env:SystemRoot\System32\taskkill.exe" /PID $ProcessId /T /F 2>&1 }
    catch {
        if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) { throw }
        return # It exited between identity validation and taskkill.
    }
    if ($LASTEXITCODE -ne 0 -and (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
        throw "Could not stop verified project process tree PID $ProcessId."
    }
}

function Start-AgentCoreProcess {
    if (-not (Test-Path -LiteralPath $pythonPath)) { throw "Core Python was not found: $pythonPath" }
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + "-$PID"
    $script:lastCoreErrorLog = Join-Path $logRoot "core-$stamp.stderr.log"
    return Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'agent_core.main') `
        -WorkingDirectory $coreRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logRoot "core-$stamp.stdout.log") `
        -RedirectStandardError $lastCoreErrorLog
}

function Ensure-AgentCore {
    param([int]$StartupSeconds = 90, [int]$ConfirmFailures = 3, [scriptblock]$ContinueWhile)
    # Caller must hold the shared startup mutex, including the watchdog.
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $started = $null
    $recovered = $false
    $misses = 0
    while ($watch.Elapsed.TotalSeconds -lt (2 * $StartupSeconds + 10)) {
        if ($ContinueWhile -and -not (& $ContinueWhile)) { throw 'Avatar exited during Core recovery.' }
        $state = Get-AgentCoreState
        if ($state.ListenerPid) {
            $health = Get-AgentCoreHealth $state.ListenerPid
            if ($health) { return $health }
        }
        if ($started -and $started.HasExited) {
            throw "Core exited during startup (exit $($started.ExitCode)). Check $lastCoreErrorLog"
        }
        if (-not $state.Processes.Count) {
            if ($started) { throw "Core disappeared during startup. Check $lastCoreErrorLog" }
            $started = Start-AgentCoreProcess
            $misses = 0
        } else {
            $misses++
            $newest = $state.Processes | Sort-Object CreationDate -Descending | Select-Object -First 1
            $age = ((Get-Date) - $newest.CreationDate).TotalSeconds
            if ($age -ge $StartupSeconds -and $misses -ge $ConfirmFailures) {
                if ($started -or $recovered) {
                    # Bound the failure: do not leave another hung test/startup Core.
                    Stop-ProjectCoreProcesses $state.Processes
                    throw "Core did not become live within ${StartupSeconds}s. Check $lastCoreErrorLog"
                }
                Write-Host '[Anime Agent] Confirmed stale project Core; recovering it.'
                Stop-ProjectCoreProcesses $state.Processes
                $recovered = $true
            }
        }
        Start-Sleep -Milliseconds 500
    }
    throw 'Core startup deadline exceeded; no additional instance was started.'
}

function Get-ProjectAvatar {
    $normalizedRoot = $avatarRoot.Replace('/', '\')
    return Get-AgentProcesses | Where-Object {
        $_.Name -like 'Godot*' -and $_.CommandLine.Replace('/', '\') -match
            ('(?i)--path\s+"?' + [regex]::Escape($normalizedRoot) + '(?:"|\s|$)')
    } | Select-Object -First 1
}

function Stop-AgentCoreAfterAvatarExit {
    # Under the SAME mutex as startup: a rapid close/reopen cannot have its
    # new Core killed by the previous avatar's watcher.
    if (Get-ProjectAvatar) { return $false }
    $state = Get-AgentCoreState
    Stop-ProjectCoreProcesses $state.Processes
    return $true
}
