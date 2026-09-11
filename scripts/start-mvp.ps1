# Codex 2026-09-11: canonical startup and one avatar session.
[CmdletBinding()]
param([switch]$SkipAvatar, [ValidateRange(3, 180)][int]$StartupSeconds = 90)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'startup-common.ps1')
Initialize-AgentRuntime (Join-Path $PSScriptRoot '..')
$lock = $null
$launchedAvatar = $null
try {
    if (-not (Test-Path -LiteralPath $envPath)) { throw "Project .env not found: $envPath" }
    # Configuration errors still belong to the provider, not process liveness.
    # Preserve the existing key/endpoint guard; use the same env precedence as Core.
    $providerName = (Get-AgentSetting 'LLM_PROVIDER' 'glm').ToLowerInvariant()
    switch ($providerName) {
        'glm' {
            if ([string]::IsNullOrWhiteSpace((Get-AgentSetting 'GLM_API_KEY'))) { throw 'GLM_API_KEY is empty.' }
            if ((Get-AgentSetting 'GLM_BASE_URL') -notmatch '/api/coding/paas/v4/?$') {
                throw 'GLM_BASE_URL must use the Coding endpoint ending in /api/coding/paas/v4'
            }
        }
        'deepseek' {
            if ([string]::IsNullOrWhiteSpace((Get-AgentSetting 'DEEPSEEK_API_KEY'))) { throw 'DEEPSEEK_API_KEY is empty.' }
            if ([string]::IsNullOrWhiteSpace((Get-AgentSetting 'DEEPSEEK_BASE_URL'))) { throw 'DEEPSEEK_BASE_URL is empty.' }
        }
        'mock' { }
        default { throw "Unsupported LLM_PROVIDER: $providerName" }
    }
    Write-Host "[Anime Agent] Checking local services. Cold Core initialization can take up to ${StartupSeconds}s."
    $lock = Enter-AgentLock -TimeoutSeconds (2 * $StartupSeconds + 90)
    $health = Ensure-AgentCore -StartupSeconds $StartupSeconds
    Write-Host "[Anime Agent] Core is online on port $corePort."
    if ($SkipAvatar) {
        Write-Host '[Anime Agent] Core verified; avatar and session watchdog skipped.'
        return
    }
    $avatar = Get-ProjectAvatar
    if (-not $avatar) {
        $launchedAvatar = & (Join-Path $PSScriptRoot 'run-avatar-runtime.ps1') -LogDirectory $logRoot
    }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $ready = $false
    $readySamples = 0
    $coreMisses = 0
    while ($timer.Elapsed.TotalSeconds -lt 60) {
        if ($launchedAvatar -and $launchedAvatar.HasExited) { throw "Godot exited (code $($launchedAvatar.ExitCode)); check $logRoot" }
        $avatar = Get-ProjectAvatar
        if (-not $avatar -and -not $launchedAvatar) {
            $launchedAvatar = & (Join-Path $PSScriptRoot 'run-avatar-runtime.ps1') -LogDirectory $logRoot
        }
        $health = Get-AgentCoreHealth
        if ($health) { $coreMisses = 0 } else { $coreMisses++ }
        if ($coreMisses -ge 3) {
            # Core may crash while Godot is loading, before its session watcher exists.
            $health = Ensure-AgentCore -StartupSeconds $StartupSeconds
            $coreMisses = 0
        }
        if ($avatar -and $health -and $health.roles.avatar -gt 0) {
            $window = Get-Process -Id $avatar.ProcessId -ErrorAction SilentlyContinue
            if ($window -and $window.MainWindowHandle -ne 0 -and $window.Responding) { $readySamples++ }
            else { $readySamples = 0 }
        } else { $readySamples = 0 }
        if ($readySamples -ge 2) { $ready = $true; break }
        Start-Sleep -Milliseconds 400
    }
    if (-not $ready) { throw "Avatar window/bridge was not ready within 60 seconds. Check $logRoot" }
    $ackPath = Join-Path $logRoot ("watchdog-{0}-{1}.json" -f $runtimeKey, $avatar.ProcessId)
    $watchScript = Join-Path $PSScriptRoot 'core_watchdog.ps1'
    # Per-avatar supervisor mutex makes repeated calls harmless; ack proves that
    # it initialized, not merely that powershell.exe was created.
    $watchStamp = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + "-$PID"
    $watcher = Start-Process powershell.exe -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput (Join-Path $logRoot "watchdog-$watchStamp.stdout.log") `
      -RedirectStandardError (Join-Path $logRoot "watchdog-$watchStamp.stderr.log") -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $watchScript + '"'),
        '-AvatarId', $avatar.ProcessId, '-AvatarTicks', $avatar.CreationDate.Ticks
    )
    $ackReady = $false
    $timer.Restart()
    while ($timer.Elapsed.TotalSeconds -lt 15) {
        if (Test-Path -LiteralPath $ackPath) {
            try {
                $ack = Get-Content -LiteralPath $ackPath -Raw | ConvertFrom-Json
                $running = Get-AgentProcesses | Where-Object {
                    $_.ProcessId -eq $ack.pid -and $_.CreationDate.Ticks -eq $ack.createdTicks -and
                    $_.CommandLine -like ('*' + $watchScript + '*')
                }
                if ($running -and $ack.avatarTicks -eq $avatar.CreationDate.Ticks) { $ackReady = $true; break }
            } catch { }
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $ackReady) { throw "Session watchdog did not initialize; check $logRoot/core-watchdog.log" }
    Write-Host "[Anime Agent] Ready (Avatar PID $($avatar.ProcessId)). Close Godot to exit this session; use this same command to reopen."
} catch {
    # A failed launch must not leave a newly-created blank avatar/Core behind.
    if ($launchedAvatar -and -not $launchedAvatar.HasExited) {
        $null = $launchedAvatar.CloseMainWindow()
        if (-not $launchedAvatar.WaitForExit(3000)) { $launchedAvatar.Kill() }
    }
    if ($lock) {
        try { $null = Stop-AgentCoreAfterAvatarExit } catch { Write-Warning "Cleanup could not be verified: $_" }
    }
    throw
} finally { Exit-AgentLock $lock }
