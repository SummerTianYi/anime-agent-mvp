# Codex: session lifecycle/recovery; preserves zcode's Core crash watchdog.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][int]$AvatarId,
      [Parameter(Mandatory=$true)][long]$AvatarTicks,
      [ValidateRange(1,60)][int]$PollSeconds = 10)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'startup-common.ps1')
. (Join-Path $PSScriptRoot 'tts-lifecycle.ps1')
Initialize-AgentRuntime (Join-Path $PSScriptRoot '..')
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$watchdogLog = Join-Path $logRoot 'core-watchdog.log'
$ackPath = Join-Path $logRoot ("watchdog-{0}-{1}.json" -f $runtimeKey, $AvatarId)
function Write-WatchdogLog($Message) {
    Add-Content -LiteralPath $watchdogLog -Value ("[{0}] pid={1} {2}" -f (Get-Date -Format 's'), $PID, $Message)
}
$singleton = $null
$avatarHandle = $null
try {
    try { $singleton = Enter-AgentLock -Suffix "watch-$AvatarId-$AvatarTicks" -TimeoutSeconds 0 }
    catch { return } # Existing supervisor owns this exact avatar generation.
    $tracked = Get-ProjectAvatar
    if (-not $tracked -or $tracked.ProcessId -ne $AvatarId -or $tracked.CreationDate.Ticks -ne $AvatarTicks) {
        throw 'Avatar generation changed before supervisor initialization.'
    }
    $avatarHandle = Get-Process -Id $AvatarId -ErrorAction Stop
    $self = Get-AgentProcesses | Where-Object { $_.ProcessId -eq $PID }
    @{pid=$PID; createdTicks=$self.CreationDate.Ticks; avatarTicks=$AvatarTicks} |
        ConvertTo-Json | Set-Content -LiteralPath $ackPath -Encoding UTF8
    Write-WatchdogLog "started for avatar=$AvatarId"
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $strikes = 0
    while ($true) {
        # Hold the process handle: cheap exit detection, immune to PID reuse.
        if ($avatarHandle.HasExited) {
            $lock = Enter-AgentLock
            try {
                $cleaned = Stop-AgentCoreAfterAvatarExit
                Write-WatchdogLog "avatar exited; cleaned=$cleaned (false means a newer avatar is active)"
            } finally { Exit-AgentLock $lock }
            break
        }
        if ($timer.Elapsed.TotalSeconds -ge $PollSeconds) {
            $timer.Restart()
            # Codex: a dead TTS supervisor must not leave a living avatar mute.
            # Separate from Core health, outside the startup mutex: TTS exit
            # cleanup takes that mutex while holding its own session mutex.
            try { $null = Start-AgentTtsWatch $tracked }
            catch { Write-WatchdogLog "TTS supervisor recovery deferred: $_" }
            if (Get-AgentCoreHealth) { $strikes = 0 }
            else { $strikes++ }
            if ($strikes -ge 2) {
                $lock = $null
                try {
                    $lock = Enter-AgentLock -TimeoutSeconds 2
                    $stillHere = Get-ProjectAvatar
                    if ($stillHere -and $stillHere.ProcessId -eq $AvatarId -and $stillHere.CreationDate.Ticks -eq $AvatarTicks) {
                        Write-WatchdogLog 'recovery-start'
                        $health = Ensure-AgentCore -ContinueWhile {
                            $active = Get-ProjectAvatar
                            return ($active -and $active.ProcessId -eq $AvatarId -and $active.CreationDate.Ticks -eq $AvatarTicks)
                        }
                        Write-WatchdogLog "core recovered pid=$($health.pid)"
                    }
                } catch { Write-WatchdogLog "recovery deferred/failed: $_" }
                finally { Exit-AgentLock $lock }
                $strikes = 0
            }
        }
        Start-Sleep -Milliseconds 500
    }
} catch { Write-WatchdogLog "supervisor failed: $_"; throw }
finally {
    if ($avatarHandle) { $avatarHandle.Dispose() }
    if ($singleton) {
        if (Test-Path -LiteralPath $ackPath) { Remove-Item -LiteralPath $ackPath -Force }
        Exit-AgentLock $singleton
    }
}
