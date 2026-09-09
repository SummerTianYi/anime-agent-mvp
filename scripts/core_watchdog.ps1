# Core keepalive watchdog.
#
# Why: Core dies silently when PortAudio (libportaudio64bit.dll) takes a native
# access violation inside the wake-word microphone stream — Python cannot catch
# it and leaves no traceback (see docs/KNOWN_ISSUES.md KI-019). Reboots and
# hibernation have the same net effect: Godot keeps retrying the bridge forever
# while nothing listens on the Core port.
#
# Contract: while the Godot avatar is on the desktop, keep Agent Core online.
#   - Polls the local /health endpoint only (zero GLM calls; the startup
#     greeting on revive is a fixed template line, see agent_core/main.py).
#   - Two consecutive failed health polls before any action (Core warmup and
#     busy turns can make one probe time out — never kill on a single miss).
#   - Manages ANY python process running agent_core.main on the port (venv or
#     system interpreter, started by start-mvp.ps1 or by hand); foreign port
#     occupants are left alone.
#   - A core spawned by this watchdog gets a 90s warmup window before the next
#     decision, so slow imports never trigger duplicate spawns.
#   - Records every death it witnesses with the process exit code, so the next
#     "she hung" leaves a forensic trail instead of silence.
#   - Exits when the avatar is gone (watchdog must outlive nothing).
#
# Manual run: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\core_watchdog.ps1

[CmdletBinding()]
param(
    [int]$PollSeconds = 10,
    [int]$StartTimeoutSeconds = 45,
    [int]$StartupGraceSeconds = 180,
    [int]$WarmupSeconds = 90
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$coreRoot = Join-Path $repoRoot "services\agent-core"
$pythonPath = Join-Path $coreRoot ".venv\Scripts\python.exe"
$envPath = Join-Path $repoRoot ".env"
$avatarRoot = Join-Path $repoRoot "apps\avatar-runtime"
$logRoot = Join-Path $env:LOCALAPPDATA "AnimeAgent\logs"

$mutex = New-Object System.Threading.Mutex($false, "AnimeAgentCoreWatchdog")
if (-not $mutex.WaitOne(0)) {
    exit 0
}

function Get-LocalEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path -LiteralPath $envPath)) {
        return $DefaultValue
    }

    $pattern = "^\s*" + [regex]::Escape($Name) + "\s*=\s*(.*)$"
    $line = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match $pattern } |
        Select-Object -Last 1
    if (-not $line) {
        return $DefaultValue
    }

    $value = [regex]::Match($line, $pattern).Groups[1].Value.Trim()
    return $value.Trim('"').Trim("'")
}

function Test-AgentCoreHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Uri
    )

    $handler = New-Object System.Net.Http.HttpClientHandler
    $handler.UseProxy = $false
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(2)
    try {
        $response = $client.GetAsync($Uri).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            return $false
        }
        $content = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $payload = $content | ConvertFrom-Json
        return $payload.status -eq "ok" -and $payload.service -eq "anime-agent-core"
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
        $handler.Dispose()
    }
}

function Get-AvatarProcess {
    $escapedRoot = [regex]::Escape($avatarRoot)
    return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "Godot*" -and
            $_.CommandLine -match $escapedRoot
        } |
        Select-Object -First 1
}

# Returns the port occupant when it is a python running agent_core.main
# (interpreter-agnostic: venv, system python, watchdog- or hand-started).
function Get-CorePortOwner {
    param([int]$Port)

    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $listener) {
        return $null
    }

    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
    if (-not $proc -or $proc.Name -notlike "python*") {
        return "foreign"
    }
    if ("$($proc.CommandLine)" -notmatch "agent_core") {
        return "foreign"
    }
    return $proc
}

function Format-ExitCode {
    param($Code)
    if ($null -eq $Code) { return "unknown" }
    return "0x{0:X8}" -f ($Code -band 0xFFFFFFFF)
}

function Write-WatchdogLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $watchdogLog -Value $line
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Agent Core Python environment was not found: $pythonPath"
}

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$watchdogLog = Join-Path $logRoot "core-watchdog.log"
$stdoutLog = Join-Path $logRoot "core.stdout.log"
$stderrLog = Join-Path $logRoot "core.stderr.log"

$portText = Get-LocalEnvValue -Name "AGENT_CORE_PORT" -DefaultValue "8765"
$corePort = 0
if (-not [int]::TryParse($portText, [ref]$corePort) -or $corePort -lt 1 -or $corePort -gt 65535) {
    $corePort = 8765
}
$healthUri = "http://127.0.0.1:$corePort/health"
$env:AGENT_CORE_WS_URL = "ws://127.0.0.1:$corePort/ws"

Write-WatchdogLog "watchdog started (pid $PID, poll ${PollSeconds}s, port $corePort)"

$lastCore = $null
$lastStartAt = Get-Date "2000-01-01"
$deadStrikes = 0
$avatarSeen = $false
$absentPolls = 0

while ($true) {
    $avatar = Get-AvatarProcess
    if ($avatar) {
        $avatarSeen = $true
        $absentPolls = 0
    }
    else {
        $absentPolls += 1
        if ($avatarSeen -and $absentPolls -ge 2) {
            Write-WatchdogLog "avatar no longer on the desktop (confirmed twice); watchdog exits"
            break
        }
        if (-not $avatarSeen -and ($absentPolls * $PollSeconds) -ge $StartupGraceSeconds) {
            Write-WatchdogLog "avatar never appeared within ${StartupGraceSeconds}s; watchdog exits"
            break
        }
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    if (Test-AgentCoreHealth -Uri $healthUri) {
        $deadStrikes = 0
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    # A core we spawned recently is still warming up (heavy imports take tens
    # of seconds); never judge it dead during that window.
    if ($lastCore -and -not $lastCore.HasExited -and ((Get-Date) - $lastStartAt).TotalSeconds -lt $WarmupSeconds) {
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    $deadStrikes += 1
    if ($deadStrikes -lt 2) {
        Write-WatchdogLog "health check failed once; confirming on next poll"
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    $owner = Get-CorePortOwner -Port $corePort
    if ($owner -eq "foreign") {
        Write-WatchdogLog "port $corePort held by a foreign process; standing by"
        $deadStrikes = 0
        Start-Sleep -Seconds $PollSeconds
        continue
    }
    if ($owner) {
        Write-WatchdogLog "unhealthy core (pid $($owner.ProcessId)) still holds port $corePort after confirmation; stopping it"
        Stop-Process -Id $owner.ProcessId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }

    if ($lastCore -and $lastCore.HasExited) {
        $codeText = Format-ExitCode $lastCore.ExitCode
        $hint = "see core.stderr.log"
        if ($lastCore.ExitCode -eq -1073741819) { $hint = "native access violation (PortAudio-style crash)" }
        elseif ($codeText -eq "0x00000000") { $hint = "clean exit" }
        Write-WatchdogLog "core death witnessed: pid $($lastCore.Id) exit=$codeText ($hint)"
    }

    $started = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("-m", "agent_core.main") `
        -WorkingDirectory $coreRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
    $lastCore = $started
    $lastStartAt = Get-Date
    $deadStrikes = 0

    $healthy = $false
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $StartTimeoutSeconds) {
        Start-Sleep -Milliseconds 500
        if ($started.HasExited) { break }
        if (Test-AgentCoreHealth -Uri $healthUri) {
            $healthy = $true
            break
        }
    }

    if ($healthy) {
        Write-WatchdogLog ("core revived: pid {0} healthy in {1:N1}s" -f $started.Id, $stopwatch.Elapsed.TotalSeconds)
    }
    elseif ($started.HasExited) {
        Write-WatchdogLog "core failed during startup: pid $($started.Id) exit=$(Format-ExitCode $started.ExitCode); backing off 20s"
        Start-Sleep -Seconds 20
    }
    else {
        Write-WatchdogLog "core pid $($started.Id) warming up past ${StartTimeoutSeconds}s but still running; keep watching"
    }

    Start-Sleep -Seconds $PollSeconds
}
