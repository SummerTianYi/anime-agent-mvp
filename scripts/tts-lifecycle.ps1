# Codex: TTS-only lifecycle helpers; dot-source has no process side effects.
function Initialize-AgentTts {
    $enabled = (Get-AgentSetting 'ANIME_AGENT_TTS' '0').ToLowerInvariant() -notin @('0','false','off','')
    if (-not $enabled) { return $false }
    $uri = $null
    if (-not [uri]::TryCreate((Get-AgentSetting 'TTS_SERVICE_URL' 'http://127.0.0.1:8770'), [UriKind]::Absolute, [ref]$uri)) { throw 'Invalid TTS_SERVICE_URL' }
    # Custom/remote TTS is never owned or restarted by this local supervisor.
    if ($uri.Scheme -ne 'http' -or $uri.Host -ne '127.0.0.1' -or $uri.AbsolutePath -ne '/' -or $uri.UserInfo -or $uri.Query -or $uri.Fragment) { return $false }
    $script:ttsPort = $uri.Port
    if ($ttsPort -eq $corePort) { throw 'TTS and Core must not share a port' }
    $root = Get-AgentSetting 'TTS_WORKSPACE' (Join-Path (Split-Path $repoRoot -Parent) 'tianyi-tts')
    if (-not (Test-Path -LiteralPath $root)) { return $false }
    $script:ttsRoot = (Resolve-Path -LiteralPath $root).Path
    $script:ttsPython = Join-Path $ttsRoot 'venv\Scripts\python.exe'
    $script:ttsServer = Join-Path $ttsRoot 'scripts\tts_server.py'
    if (-not (Test-Path -LiteralPath $ttsPython) -or -not (Test-Path -LiteralPath $ttsServer)) { return $false }
    $script:ttsHealthUri = "http://127.0.0.1:$ttsPort/health"
    $script:ttsLog = Join-Path $logRoot 'tts-watch.log'
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    $hash = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($ttsRoot.ToLowerInvariant() + ":$ttsPort")
        $script:ttsKey = ([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-','').Substring(0,24)
    } finally { $hash.Dispose() }
    return $true
}

function Write-TtsLog([string]$Event, $Details = @{}) {
    @{time=(Get-Date -Format 'o'); agent='Codex'; event=$Event; watcher=$PID; port=$ttsPort; detail=$Details} |
        ConvertTo-Json -Compress -Depth 4 | Add-Content -LiteralPath $ttsLog -Encoding UTF8
}

function Test-TtsProcess($Process, [array]$Processes) {
    if (-not $Process -or $Process.Name -notlike 'python*' -or -not $Process.CommandLine) { return $false }
    $cmd = $Process.CommandLine.Replace('/','\')
    $scriptToken = '(?:"' + [regex]::Escape($ttsServer) + '"|' + [regex]::Escape($ttsServer) + '|scripts\\tts_server\.py)'
    if ($cmd -notmatch ('(?i)(?:^|\s)' + $scriptToken + '(?:\s|$)')) { return $false }
    $portMatch = [regex]::Match($cmd, '(?:^|\s)--port(?:=|\s+)(\d+)(?:\s|$)')
    if ($portMatch.Success) { if ([int]$portMatch.Groups[1].Value -ne $ttsPort) { return $false } }
    elseif ($ttsPort -ne 8770) { return $false }
    if ($Process.ExecutablePath -eq $ttsPython) { return $true }
    $parent = $Processes | Where-Object { $_.ProcessId -eq $Process.ParentProcessId } | Select-Object -First 1
    return ($parent -and $parent.ExecutablePath -eq $ttsPython -and
        $parent.CreationDate -le $Process.CreationDate -and (Test-TtsProcess $parent @()))
}

function Get-TtsState {
    $all = Get-AgentProcesses
    $owned = @($all | Where-Object { Test-TtsProcess $_ $all })
    $listeners = @(Get-NetTCPConnection -ErrorAction Stop | Where-Object { $_.State -eq 'Listen' -and $_.LocalPort -eq $ttsPort })
    foreach ($listener in $listeners) {
        if ($listener.OwningProcess -notin $owned.ProcessId) { throw "Foreign/unverified TTS port owner $($listener.OwningProcess); NOT touched" }
    }
    return [pscustomobject]@{Processes=$owned; ListenerPid=$(if ($listeners.Count) {[int]$listeners[0].OwningProcess} else {0})}
}

function Get-TtsHealth([int]$ExpectedPid) {
    $handler = New-Object Net.Http.HttpClientHandler
    $handler.UseProxy = $false
    $client = New-Object Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(2)
    $response = $null
    try {
        $response = $client.GetAsync($ttsHealthUri).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) { return $null }
        $h = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
        if ($h.ok -isnot [bool] -or ($h.pid -and $h.pid -ne $ExpectedPid)) { return $null }
        return $h
    } catch { return $null }
    finally { if ($response) {$response.Dispose()}; $client.Dispose(); $handler.Dispose() }
}

function Get-TtsDecision($Health, [double]$Age, [int]$Misses, [int]$WarmupSeconds = 180, [switch]$WasReady) {
    # An already-running legacy sidecar has no stall telemetry. On the NEXT
    # owned avatar startup only, replace it once so the fixed code is loaded.
    if ($Health -and $Health.ok -eq $true -and ($Health.service -ne 'tianyi-tts' -or $Health.protocol -ne 1)) {
        if ($Misses -ge 2) { return 'restart' }
        return 'upgrade-confirm'
    }
    if ($Health -and $Health.ok -eq $true) { return 'ready' }
    if ($Health -and $Health.phase -in @('failed','stalled')) {
        if ($Misses -ge 2) { return 'restart' }
        return 'confirm'
    }
    if (-not $WasReady -and $Age -lt $WarmupSeconds) { return 'warming' }
    if ($Misses -ge 2) { return 'restart' }
    return 'confirm'
}

function Stop-OwnedTts([array]$Processes) {
    foreach ($candidate in ($Processes | Sort-Object CreationDate -Descending)) {
        $all = Get-AgentProcesses
        $same = $all | Where-Object { $_.ProcessId -eq $candidate.ProcessId -and $_.CreationDate -eq $candidate.CreationDate } | Select-Object -First 1
        if ($same -and (Test-TtsProcess $same $all)) {
            Stop-AgentProcessTree $same.ProcessId
            Write-TtsLog 'stopped-owned-process' @{pid=$same.ProcessId; ticks=$same.CreationDate.Ticks}
        }
    }
}

function Get-TtsRetryDelay([int]$Attempts) {
    if ($Attempts -ge 5) { return 120 }
    return [Math]::Pow(2,[Math]::Max(1,$Attempts))
}

function Start-OwnedTts {
    $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + "-$PID"
    $process = Start-Process -FilePath $ttsPython -WorkingDirectory $ttsRoot -WindowStyle Hidden -PassThru `
        -ArgumentList @('-u', ('"' + $ttsServer + '"'), '--port', $ttsPort) `
        -RedirectStandardOutput (Join-Path $logRoot "tts-$stamp.stdout.log") `
        -RedirectStandardError (Join-Path $logRoot "tts-$stamp.stderr.log")
    Write-TtsLog 'spawn' @{pid=$process.Id; stdout="tts-$stamp.stdout.log"; stderr="tts-$stamp.stderr.log"}
    return $process
}

function Test-TtsWatchHeartbeat($Ack, [long]$NowTicks=[DateTime]::UtcNow.Ticks) {
    if (-not $Ack.heartbeatTicks) { return $false }
    $age=[TimeSpan]::FromTicks($NowTicks-[long]$Ack.heartbeatTicks).TotalSeconds
    return ($age -ge -5 -and $age -le 45)
}

function Start-AgentTtsWatch($Avatar) {
    if (-not (Initialize-AgentTts)) { return $false }
    # Never resurrect voice for an obsolete/closed avatar, including a late
    # call from its Core supervisor during close/reopen.
    $active = Get-ProjectAvatar
    if (-not $active -or $active.ProcessId -ne $Avatar.ProcessId -or $active.CreationDate -ne $Avatar.CreationDate) { return $false }
    $watchScript = Join-Path $PSScriptRoot 'watch-tts-session.ps1'
    $ackPath = Join-Path $logRoot "tts-watch-$runtimeKey-$($Avatar.ProcessId).json"
    # Only exact same-project legacy watcher, never every watch-tts process.
    $pathPattern = '(?i)-File\s+"?' + [regex]::Escape($watchScript) + '(?:"|\s|$)'
    foreach ($old in (Get-AgentProcesses | Where-Object { $_.Name -like 'powershell*' -and $_.CommandLine -and $_.CommandLine.Replace('/','\') -match $pathPattern -and $_.CommandLine -notmatch '-AvatarId\s' })) {
        $current = Get-AgentProcesses | Where-Object { $_.ProcessId -eq $old.ProcessId -and $_.CreationDate -eq $old.CreationDate }
        if ($current) { Stop-Process -Id $old.ProcessId -Force; Write-TtsLog 'retired-own-legacy-watcher' @{pid=$old.ProcessId} }
    }
    if (Test-Path -LiteralPath $ackPath) {
        try {
            $ack = Get-Content -LiteralPath $ackPath -Raw | ConvertFrom-Json
            $running = Get-AgentProcesses | Where-Object { $_.ProcessId -eq $ack.pid -and $_.CreationDate.Ticks -eq $ack.createdTicks -and $_.CommandLine -and $_.CommandLine.Replace('/','\') -match $pathPattern }
            if ($running -and $ack.avatarTicks -eq $Avatar.CreationDate.Ticks) {
                if (Test-TtsWatchHeartbeat $ack) { return $true }
                # Re-read before retiring a frozen watcher; only its exact
                # process generation, never Core/TTS or a newer session.
                $fresh=Get-Content -LiteralPath $ackPath -Raw | ConvertFrom-Json
                if (Test-TtsWatchHeartbeat $fresh) { return $true }
                $same=Get-AgentProcesses | Where-Object { $_.ProcessId -eq $ack.pid -and $_.CreationDate.Ticks -eq $ack.createdTicks -and $_.CommandLine -and $_.CommandLine.Replace('/','\') -match $pathPattern }
                if ($same -and $fresh.pid -eq $ack.pid -and $fresh.createdTicks -eq $ack.createdTicks) {
                    Stop-Process -Id $same.ProcessId -Force
                    Write-TtsLog 'retired-stalled-supervisor' @{pid=$same.ProcessId}
                }
            }
        } catch { }
    }
    $watcher = Start-Process powershell.exe -WindowStyle Hidden -PassThru -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$watchScript+'"'),
        '-AvatarId',$Avatar.ProcessId,'-AvatarTicks',$Avatar.CreationDate.Ticks)
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt 15) {
        if (Test-Path -LiteralPath $ackPath) {
            try {
                $ack = Get-Content -LiteralPath $ackPath -Raw | ConvertFrom-Json
                $running = Get-AgentProcesses | Where-Object { $_.ProcessId -eq $ack.pid -and $_.CreationDate.Ticks -eq $ack.createdTicks -and $_.CommandLine -and $_.CommandLine.Replace('/','\') -match $pathPattern }
                if ($running -and $ack.avatarTicks -eq $Avatar.CreationDate.Ticks -and (Test-TtsWatchHeartbeat $ack)) {
                    Write-Host '[Anime Agent] TTS supervisor ready; voice model warms independently.'
                    return $true
                }
            } catch { } # acknowledgement can be in the middle of an atomic session transition
        }
        if ($watcher.HasExited) { throw 'TTS supervisor exited before acknowledgement' }
        Start-Sleep -Milliseconds 200
    }
    throw 'TTS supervisor acknowledgement timed out; inspect tts-watch.log'
}

function Wait-AgentTtsReady($Avatar, [ValidateRange(1,600)][int]$TimeoutSeconds=180) {
    # Only observation, never owns/terminates a process. A port/ack alone does
    # not prove model readiness. Cancellation preserves close-during-warmup.
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        $active=Get-ProjectAvatar
        if (-not $active -or $active.ProcessId -ne $Avatar.ProcessId -or $active.CreationDate -ne $Avatar.CreationDate) { return $false }
        try {
            $state=Get-TtsState
            $health=if ($state.ListenerPid) {Get-TtsHealth $state.ListenerPid} else {$null}
            if ($health -and $health.ok -eq $true -and $health.service -eq 'tianyi-tts' -and $health.protocol -eq 1) { return $true }
        } catch { Write-TtsLog 'readiness-wait' @{reason=$_.Exception.Message} }
        Start-Sleep -Milliseconds 500
    }
    return $false
}
