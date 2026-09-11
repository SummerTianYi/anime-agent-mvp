param([ValidateSet('inspect','close','crash','suspend','resume','cleanup','watch-crash','watch-suspend','watch-resume','hold-lock')][string]$Action = 'inspect')
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '..\.startup-test-fixture'))) {
    throw 'Fault injection is allowed only in the isolated startup fixture.'
}
. (Join-Path $PSScriptRoot 'startup-common.ps1')
Initialize-AgentRuntime (Join-Path $PSScriptRoot '..')
if ($Action -eq 'hold-lock') {
    $held = Enter-AgentLock
    try {
        Set-Content -LiteralPath (Join-Path $repoRoot 'lock-held.txt') -Value $PID
        Start-Sleep -Seconds 90
    } finally { Exit-AgentLock $held }
    return
}
if ($Action -eq 'close') {
    $avatar = Get-ProjectAvatar
    if ($avatar) { $null = (Get-Process -Id $avatar.ProcessId).CloseMainWindow() }
    return
}
if ($Action -eq 'cleanup') {
    $avatar = Get-ProjectAvatar
    if ($avatar) {
        $p=Get-Process -Id $avatar.ProcessId
        $null=$p.CloseMainWindow()
        if (-not $p.WaitForExit(3000)) { $p.Kill() }
    }
}
$state = Get-AgentCoreState
if ($Action -eq 'crash' -or $Action -eq 'cleanup') {
    Stop-ProjectCoreProcesses $state.Processes
    return
}
if ($Action -in @('suspend','resume','watch-suspend','watch-resume')) {
    $targets = @($state.ListenerPid)
    if ($Action.StartsWith('watch-')) {
        $targets = @(Get-AgentProcesses | Where-Object {
            $_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*'+$repoRoot+'\scripts\core_watchdog.ps1*')
        } | ForEach-Object { $_.ProcessId })
    } elseif (-not $state.ListenerPid) { throw 'no test Core to suspend' }
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class ProcessPause {
 [DllImport("kernel32.dll")] public static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
 [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
 [DllImport("ntdll.dll")] public static extern int NtSuspendProcess(IntPtr h);
 [DllImport("ntdll.dll")] public static extern int NtResumeProcess(IntPtr h);
}
'@
    foreach ($target in $targets) {
    $h = [ProcessPause]::OpenProcess(0x0800, $false, $target)
    if ($h -eq [IntPtr]::Zero) { throw 'Cannot suspend test process' }
    try {
        if ($Action -in @('suspend','watch-suspend')) { $status=[ProcessPause]::NtSuspendProcess($h) }
        else { $status=[ProcessPause]::NtResumeProcess($h) }
        if ($status -ne 0) { throw "Pause/resume status $status" }
    } finally { $null=[ProcessPause]::CloseHandle($h) }
    }
    return
}
$avatar=Get-ProjectAvatar
$window=$null
if ($avatar) { $window=Get-Process -Id $avatar.ProcessId }
$all=Get-AgentProcesses
$watchers=@($all | Where-Object {
    $_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*'+$repoRoot+'\scripts\core_watchdog.ps1*')
})
if ($Action -eq 'watch-crash') {
    foreach ($w in $watchers) { Stop-Process -Id $w.ProcessId -Force -ErrorAction Stop }
    return
}
@{ cores=@($state.Processes | ForEach-Object { $_.ProcessId }); listener=$state.ListenerPid; avatar=$avatar.ProcessId;
   window=$(if ($window) { $window.MainWindowHandle.ToInt64() } else { 0 });
   visible=($window -and $window.MainWindowHandle -ne 0); responding=($window -and $window.Responding);
   watchers=@($watchers | ForEach-Object { $_.ProcessId }) } | ConvertTo-Json -Compress
