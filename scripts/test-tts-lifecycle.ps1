# Codex: pure boundary tests. NO production processes/ports are touched.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'startup-common.ps1')
. (Join-Path $PSScriptRoot 'tts-lifecycle.ps1')
$script:ttsRoot='C:\fixture\tts'; $script:ttsPython='C:\fixture\tts\venv\Scripts\python.exe'
$script:ttsServer='C:\fixture\tts\scripts\tts_server.py'; $script:ttsPort=18870
$passed=0
function Assert($Value,$Message) {if (-not $Value) {throw $Message}}
function Case($Name,[scriptblock]$Body) {& $Body; $script:passed++; Write-Host "PASS $Name"}
function Proc([int]$Id=40001,[int]$Age=300) {
    [pscustomobject]@{ProcessId=$Id;ParentProcessId=0;Name='python.exe';ExecutablePath=$ttsPython;
    CommandLine=('"'+$ttsPython+'" -u "'+$ttsServer+'" --port '+$ttsPort);CreationDate=(Get-Date).AddSeconds(-$Age)}
}
function Get-AgentProcesses {return $script:processes}
function Get-NetTCPConnection {param($ErrorAction) return $script:listeners}
function Stop-AgentProcessTree($ProcessId) {$script:stopped+=@($ProcessId)}
function Write-TtsLog($Event,$Details) {}
Case 'exact venv/script/port ownership including redirected worker' {
    $p=Proc; $worker=Proc 40002 290; $worker.ParentProcessId=$p.ProcessId; $worker.ExecutablePath='C:\base\python.exe'
    Assert (Test-TtsProcess $p @($p)) 'parent rejected'
    Assert (Test-TtsProcess $worker @($p,$worker)) 'worker rejected'
    $p.ExecutablePath='C:\foreign\python.exe'
    Assert (-not (Test-TtsProcess $worker @($p,$worker))) 'foreign interpreter accepted'
}
Case 'same venv other script and other port rejected' {
    $p=Proc; $p.CommandLine=$p.CommandLine.Replace('tts_server.py','tts_server.py.fake')
    Assert (-not (Test-TtsProcess $p @($p))) 'suffix accepted'
    $p=Proc; $p.CommandLine=$p.CommandLine.Replace('18870','8770')
    Assert (-not (Test-TtsProcess $p @($p))) 'wrong port accepted'
}
Case 'healthy ready/busy is never restarted at any age' {
    foreach ($age in @(1,179,180,999999)) {Assert ((Get-TtsDecision @{ok=$true;phase='synthesizing';service='tianyi-tts';protocol=1} $age 100) -eq 'ready') 'busy killed'}
}
Case 'owned legacy healthy sidecar upgrades after two samples' {
    Assert ((Get-TtsDecision @{ok=$true} 999 1) -eq 'upgrade-confirm') 'legacy killed at first probe'
    Assert ((Get-TtsDecision @{ok=$true} 999 2) -eq 'restart') 'legacy never upgraded'
}
Case 'loading and missing health use full warmup grace' {
    Assert ((Get-TtsDecision @{ok=$false;phase='warming'} 179 20) -eq 'warming') 'warmup killed'
    Assert ((Get-TtsDecision $null 179 20) -eq 'warming') 'cold startup killed'
}
Case 'failure/stall needs two samples and expired warmup recovers' {
    Assert ((Get-TtsDecision $null 10 1 -WasReady) -eq 'confirm') 'single transient killed'
    Assert ((Get-TtsDecision $null 10 2 -WasReady) -eq 'restart') 'ready server got cold grace'
    foreach ($phase in @('failed','stalled')) {
        Assert ((Get-TtsDecision @{ok=$false;phase=$phase} 20 1) -eq 'confirm') 'single miss killed'
        Assert ((Get-TtsDecision @{ok=$false;phase=$phase} 20 2) -eq 'restart') 'failure not recovered'
    }
    Assert ((Get-TtsDecision $null 181 2) -eq 'restart') 'expired not recovered'
}
Case 'foreign occupied port fails safely, no kills' {
    $script:processes=@(Proc); $script:listeners=@([pscustomobject]@{State='Listen';LocalPort=$ttsPort;OwningProcess=50000})
    $script:stopped=@(); $caught=$false
    try {$null=Get-TtsState} catch {$caught=$_.Exception.Message.Contains('NOT touched')}
    Assert ($caught -and $stopped.Count -eq 0) 'foreign process affected'
}
Case 'reused PID is not stopped' {
    $before=Proc; $script:processes=@(Proc 40001 0); $script:stopped=@()
    Stop-OwnedTts @($before)
    Assert ($stopped.Count -eq 0) 'reused PID stopped'
}
Case 'only exact owned process snapshot stopped' {
    $p=Proc; $script:processes=@($p); $script:stopped=@()
    Stop-OwnedTts @($p)
    Assert ($stopped.Count -eq 1 -and $stopped[0] -eq $p.ProcessId) 'wrong stop target'
}
Case 'persistent failure backs off instead of unlimited rapid spawning' {
    $expected=@(2,4,8,16,120,120)
    for ($i=1;$i -le 6;$i++) {Assert ((Get-TtsRetryDelay $i) -eq $expected[$i-1]) 'retry budget mismatch'}
}
Case 'readiness waits for ready, never merely a listening socket' {
    function Get-ProjectAvatar {return [pscustomobject]@{ProcessId=60001;CreationDate=[datetime]'2026-09-13'}}
    function Get-TtsState {return [pscustomobject]@{ListenerPid=40001}}
    function Get-TtsHealth($ExpectedPid) {return @{ok=$true;service='tianyi-tts';protocol=1;phase='ready'}}
    Assert (Wait-AgentTtsReady (Get-ProjectAvatar) -TimeoutSeconds 1) 'ready rejected'
    function Get-TtsHealth($ExpectedPid) {return @{ok=$false;service='tianyi-tts';protocol=1;phase='warming'}}
    Assert (-not (Wait-AgentTtsReady (Get-ProjectAvatar) -TimeoutSeconds 1)) 'warming called ready'
}
Case 'voice wait cancels when avatar generation changes' {
    $expected=[pscustomobject]@{ProcessId=60001;CreationDate=[datetime]'2026-09-13'}
    function Get-ProjectAvatar {return [pscustomobject]@{ProcessId=60001;CreationDate=[datetime]'2026-09-14'}}
    Assert (-not (Wait-AgentTtsReady $expected -TimeoutSeconds 1)) 'stale avatar accepted'
}
Case 'supervisor heartbeat cannot claim a hung watcher is alive' {
    $now=[DateTime]::UtcNow.Ticks
    Assert (Test-TtsWatchHeartbeat @{heartbeatTicks=$now} $now) 'fresh heartbeat rejected'
    Assert (-not (Test-TtsWatchHeartbeat @{heartbeatTicks=$now-[TimeSpan]::FromSeconds(46).Ticks} $now)) 'hung watcher accepted'
    Assert (-not (Test-TtsWatchHeartbeat @{} $now)) 'legacy ack accepted as heartbeat'
}
Write-Host "TTS_LIFECYCLE_UNIT_PASS cases=$passed"
