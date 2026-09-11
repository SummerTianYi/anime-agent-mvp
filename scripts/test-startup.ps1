# Codex: deterministic lifecycle/fault tests. NO real processes are stopped.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'startup-common.ps1')
Initialize-AgentRuntime (Join-Path $PSScriptRoot '..')
$passed = 0
function Assert-True($Value, $Message) { if (-not $Value) { throw $Message } }
function Test-Case($Name, [scriptblock]$Body) {
    & $Body
    $script:passed++
    Write-Host "PASS $Name"
}
function New-TestCore([int]$Id = 41001, [int]$AgeSeconds = 120) {
    return [pscustomobject]@{
        ProcessId = $Id; ParentProcessId = 0; Name = 'python.exe'
        ExecutablePath = $pythonPath; CommandLine = 'python.exe -m agent_core.main'
        CreationDate = (Get-Date).AddSeconds(-$AgeSeconds)
    }
}
function Reset-TestState {
    $script:fakeProcesses = @()
    $script:fakeListeners = @()
    $script:stopped = @()
    $script:spawned = 0
    $script:responses = [Collections.Queue]::new()
    $script:requests = @()
    $script:exitOnStart = $false
}
# Replace OS boundaries in this test process only; production has no test mode.
function Get-CimInstance { param($ClassName, $ErrorAction) return $script:fakeProcesses }
function Get-NetTCPConnection { param($ErrorAction) return $script:fakeListeners }
function Stop-AgentProcessTree {
    param($ProcessId)
    $Id = $ProcessId
    $script:stopped += $Id
    $script:fakeProcesses = @($script:fakeProcesses | Where-Object { $_.ProcessId -ne $Id })
    $script:fakeListeners = @($script:fakeListeners | Where-Object { $_.OwningProcess -ne $Id })
}
function Start-Sleep { param($Milliseconds, $Seconds) }
function Invoke-AgentHealthRequest {
    param($Uri, $TimeoutSeconds)
    $script:requests += [pscustomobject]@{ Uri = $Uri; Timeout = $TimeoutSeconds }
    if ($script:responses.Count) { return $script:responses.Dequeue() }
    return [pscustomobject]@{ Missing = $false; Payload = [pscustomobject]@{
        status = 'ok'; service = 'anime-agent-core'; pid = 41001
    } }
}
function Start-AgentCoreProcess {
    $script:spawned++
    $script:fakeProcesses = @(New-TestCore 41001 0)
    $script:fakeListeners = @([pscustomobject]@{ LocalPort = $corePort; State = 'Listen'; OwningProcess = 41001 })
    return [pscustomobject]@{ Id = 41001; HasExited = $script:exitOnStart; ExitCode = 17 }
}
Reset-TestState
Test-Case 'venv parent and redirected worker identity; reject another project' {
    $parent = New-TestCore
    $worker = New-TestCore 41002 110
    $worker.ExecutablePath = 'C:\Python312\python.exe'
    $worker.ParentProcessId = 41001
    Assert-True (Test-ProjectCoreProcess $worker @($parent, $worker)) 'worker not recognized'
    $parent.ExecutablePath = 'C:\another-project\.venv\Scripts\python.exe'
    Assert-True (-not (Test-ProjectCoreProcess $worker @($parent, $worker))) 'foreign project accepted'
    $worker.CommandLine = 'python.exe -m agent_core.main_fake'
    Assert-True (-not (Test-ProjectCoreProcess $worker @($worker))) 'nonexact module accepted'
}
Test-Case 'fast live endpoint; no dependency health fallback' {
    Reset-TestState
    $null = Get-AgentCoreHealth 41001
    Assert-True ($requests.Count -eq 1 -and $requests[0].Uri.EndsWith('/health/live')) 'not fast endpoint'
}
Test-Case 'old Core gets six-second health budget only after live returns 404' {
    Reset-TestState
    $responses.Enqueue([pscustomobject]@{ Missing = $true; Payload = $null })
    Assert-True ($null -ne (Get-AgentCoreHealth 41001)) 'legacy health failed'
    Assert-True ($requests.Count -eq 2 -and $requests[1].Timeout -eq 6) 'legacy budget not extended'
}
Test-Case 'timeout is not mistaken for legacy endpoint; reject PID mismatch' {
    Reset-TestState
    $responses.Enqueue($null)
    Assert-True ($null -eq (Get-AgentCoreHealth 41001)) 'timeout accepted'
    Assert-True ($requests.Count -eq 1) 'timeout used dependency fallback'
    Assert-True ($null -eq (Get-AgentCoreHealth 99999)) 'wrong process health accepted'
}
Test-Case 'foreign port owner is preserved, including healthy-looking impostor' {
    Reset-TestState
    $script:fakeListeners = @([pscustomobject]@{ LocalPort = $corePort; State = 'Listen'; OwningProcess = 99999 })
    $caught = $false
    try { $null = Ensure-AgentCore } catch { $caught = $_.ToString().Contains('NOT stopped') }
    Assert-True ($caught -and $stopped.Count -eq 0 -and $spawned -eq 0) 'foreign owner touched'
}
Test-Case 'cold start and duplicate launch reuse one healthy Core' {
    Reset-TestState
    $null = Ensure-AgentCore
    $null = Ensure-AgentCore
    Assert-True ($spawned -eq 1 -and $stopped.Count -eq 0) 'duplicate launch'
}
Test-Case 'two transient failures do not kill a warming Core' {
    Reset-TestState
    $null = Start-AgentCoreProcess
    $responses.Enqueue($null); $responses.Enqueue($null)
    $null = Ensure-AgentCore
    Assert-True ($spawned -eq 1 -and $stopped.Count -eq 0) 'warm Core was killed'
}
Test-Case 'stale own Core is recovered only after three failures' {
    Reset-TestState
    $null = Start-AgentCoreProcess
    $fakeProcesses[0].CreationDate = (Get-Date).AddMinutes(-5)
    $responses.Enqueue($null); $responses.Enqueue($null); $responses.Enqueue($null)
    $null = Ensure-AgentCore
    Assert-True ($spawned -eq 2 -and $stopped.Count -eq 1 -and $requests.Count -eq 4) 'bad recovery'
}
Test-Case 'PID reuse is not killed' {
    Reset-TestState
    $original = New-TestCore
    $script:fakeProcesses = @(New-TestCore 41001 0)
    Stop-ProjectCoreProcesses @($original)
    Assert-True ($stopped.Count -eq 0) 'reused PID killed'
}
Test-Case 'avatar close cleans Core; rapid reopen prevents previous watcher cleanup' {
    Reset-TestState
    $null = Start-AgentCoreProcess
    $avatar = [pscustomobject]@{ Name = 'Godot.exe'; ProcessId = 42001
        CommandLine = 'godot.exe --path "' + $avatarRoot + '" --script res://launcher.gd' }
    $script:fakeProcesses += $avatar
    Assert-True (-not (Stop-AgentCoreAfterAvatarExit)) 'live avatar was cleaned'
    Assert-True ($stopped.Count -eq 0) 'new session Core stopped'
    $script:fakeProcesses = @($fakeProcesses | Where-Object { $_.ProcessId -ne 42001 })
    Assert-True (Stop-AgentCoreAfterAvatarExit) 'closed avatar not cleaned'
    Assert-True ($stopped.Count -eq 1) 'Core residual remains'
}
Test-Case 'process inventory permission failure never becomes a cold start' {
    Reset-TestState
    function Get-CimInstance { throw 'injected access denied' }
    $caught = $false
    try { $null = Ensure-AgentCore } catch { $caught = $_.ToString().Contains('injected access denied') }
    Assert-True ($caught -and $spawned -eq 0 -and $stopped.Count -eq 0) 'permissions failed open'
}
Test-Case 'failed new Core reports exit instead of retrying forever' {
    Reset-TestState
    $script:exitOnStart = $true
    $responses.Enqueue($null)
    $caught = $false
    try { $null = Ensure-AgentCore } catch { $caught = $_.ToString().Contains('exited during startup') }
    Assert-True ($caught -and $spawned -eq 1) 'startup crash not bounded'
}
Test-Case 'inherited port matches Core environment precedence' {
    $before = $env:AGENT_CORE_PORT
    try {
        $env:AGENT_CORE_PORT = '12345'
        Assert-True ((Get-AgentSetting 'AGENT_CORE_PORT') -eq '12345') 'environment not respected'
    } finally { $env:AGENT_CORE_PORT = $before }
}
Test-Case 'closing avatar cancels ongoing watchdog recovery' {
    Reset-TestState
    $caught = $false
    try { $null = Ensure-AgentCore -ContinueWhile { return $false } }
    catch { $caught = $_.ToString().Contains('Avatar exited during Core recovery') }
    Assert-True ($caught -and $spawned -eq 0) 'recovery continued without avatar'
}
Write-Host "STARTUP_SIMULATION_OK cases=$passed (OS process boundaries mocked; not a real desktop acceptance)"
