# Codex: TTS session supervision; never owns Core or unrelated python processes.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][int]$AvatarId,
      [Parameter(Mandatory=$true)][long]$AvatarTicks,
      [ValidateRange(0.2,60)][double]$PollSeconds=3,
      [ValidateRange(2,600)][int]$WarmupSeconds=180)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'startup-common.ps1')
. (Join-Path $PSScriptRoot 'tts-lifecycle.ps1')
Initialize-AgentRuntime (Join-Path $PSScriptRoot '..')
if (-not (Initialize-AgentTts)) { exit 0 }
$mutex = New-Object Threading.Mutex($false, "Local\AnimeAgent-TTS-$ttsKey")
$ownedLock = $false
$avatarHandle = $null
$ackPath = Join-Path $logRoot "tts-watch-$runtimeKey-$AvatarId.json"
function Write-Heartbeat {
    # Readers must never see half-written JSON during a concurrent startup.
    $ack.heartbeatTicks=[DateTime]::UtcNow.Ticks
    $temporary="$ackPath.$PID.tmp"
    [IO.File]::WriteAllText($temporary, ($ack | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    if ([IO.File]::Exists($ackPath)) { [IO.File]::Replace($temporary,$ackPath,[Management.Automation.Language.NullString]::Value) }
    else { [IO.File]::Move($temporary,$ackPath) }
}
try {
    try { $ownedLock = $mutex.WaitOne(12000) }
    catch [Threading.AbandonedMutexException] { $ownedLock = $true }
    if (-not $ownedLock) { Write-TtsLog 'duplicate-supervisor'; exit 0 }
    $avatar = Get-ProjectAvatar
    if (-not $avatar -or $avatar.ProcessId -ne $AvatarId -or $avatar.CreationDate.Ticks -ne $AvatarTicks) {
        Write-TtsLog 'obsolete-session'; exit 0
    }
    $avatarHandle = Get-Process -Id $AvatarId
    $null = $avatarHandle.Handle
    $self = Get-AgentProcesses | Where-Object ProcessId -eq $PID
    $ack=@{pid=$PID; createdTicks=$self.CreationDate.Ticks; avatarTicks=$AvatarTicks; heartbeatTicks=[DateTime]::UtcNow.Ticks}
    Write-Heartbeat
    Write-TtsLog 'supervisor-start' @{avatar=$AvatarId; avatarTicks=$AvatarTicks}
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $nextPoll=0.0; $retryAt=0.0; $misses=0; $restarts=0; $goodSince=-1.0
    $previous=''; $started=$null; $wasReady=$false
    while (-not $avatarHandle.HasExited) {
        if ($clock.Elapsed.TotalSeconds -ge $nextPoll) {
            try {
                $state = Get-TtsState
                $health = if ($state.ListenerPid) {Get-TtsHealth $state.ListenerPid} else {$null}
                $age = if ($state.Processes.Count) {((Get-Date)-($state.Processes | Sort-Object CreationDate | Select-Object -First 1).CreationDate).TotalSeconds} else {0}
                $misses++
                $decision = if (-not $state.Processes.Count) {'start'} else {Get-TtsDecision $health $age $misses $WarmupSeconds -WasReady:$wasReady}
                if ($decision -eq 'ready') {
                    $wasReady=$true
                    $misses=0
                    if ($goodSince -lt 0) {$goodSince=$clock.Elapsed.TotalSeconds}
                    if ($clock.Elapsed.TotalSeconds-$goodSince -ge 60) {$restarts=0}
                } else {$goodSince=-1.0}
                if ($decision -ne $previous) {
                    Write-TtsLog $decision @{listener=$state.ListenerPid; phase=$health.phase; misses=$misses}
                    $previous=$decision
                }
                if ($decision -in @('start','restart') -and $clock.Elapsed.TotalSeconds -ge $retryAt) {
                    if ($avatarHandle.HasExited) {break}
                    if ($started -and $started.HasExited) {Write-TtsLog 'child-exited' @{pid=$started.Id; code=$started.ExitCode}}
                    if ($decision -eq 'restart') {Stop-OwnedTts $state.Processes}
                    $state = Get-TtsState
                    if (-not $avatarHandle.HasExited -and -not $state.Processes.Count) {
                        $started = Start-OwnedTts
                        $null = $started.Handle
                        $wasReady=$false
                        $restarts++
                        $delay = Get-TtsRetryDelay $restarts
                        $retryAt=$clock.Elapsed.TotalSeconds+$delay
                        $misses=0
                        Write-TtsLog 'retry-budget' @{attempt=$restarts; delaySeconds=$delay}
                    }
                }
            } catch {
                Write-TtsLog 'deferred' @{reason=$_.Exception.Message}
                $misses=0
            }
            $nextPoll=$clock.Elapsed.TotalSeconds+$PollSeconds
            Write-Heartbeat
        }
        Start-Sleep -Milliseconds 200
    }
    # Serialize the last-avatar check and cleanup against canonical startup.
    # Startup releases its mutex before waiting for the TTS acknowledgement.
    $exitLock = Enter-AgentLock
    try {
        if (-not (Get-ProjectAvatar)) {
            $state=Get-TtsState
            Stop-OwnedTts $state.Processes
            Write-TtsLog 'session-closed' @{remainingOwned=(Get-TtsState).Processes.Count}
        } else {Write-TtsLog 'handover-to-new-avatar'}
    } finally { Exit-AgentLock $exitLock }
} catch {Write-TtsLog 'supervisor-error' @{reason=$_.Exception.Message}; throw}
finally {
    if ($avatarHandle) {$avatarHandle.Dispose()}
    if ($ownedLock) {
        if (Test-Path -LiteralPath $ackPath) {Remove-Item -LiteralPath $ackPath -Force}
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
