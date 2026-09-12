# Codex: process fault injection is forbidden without a disposable marker.
param([string]$Action='inspect',[int]$TargetId=0,[long]$TargetTicks=0)
$ErrorActionPreference='Stop'
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '..\.tts-test-fixture'))) {throw 'Not a TTS test fixture'}
. (Join-Path $PSScriptRoot 'startup-common.ps1')
. (Join-Path $PSScriptRoot 'tts-lifecycle.ps1')
Initialize-AgentRuntime (Join-Path $PSScriptRoot '..')
$null=Initialize-AgentTts
if ($Action -in @('stop-watch','suspend-watch','resume-watch')) {
    $watchPath=Join-Path $PSScriptRoot 'watch-tts-session.ps1'
    $target=@(Get-AgentProcesses | Where-Object { $_.ProcessId -eq $TargetId -and $_.CreationDate.Ticks -eq $TargetTicks -and $_.Name -like 'powershell*' -and $_.CommandLine.Replace('/','\').Contains($watchPath) })
    if ($target.Count -ne 1) {throw 'Isolated TTS watcher identity mismatch'}
    if ($Action -in @('suspend-watch','resume-watch')) {
        Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class TtsFault { [DllImport("ntdll.dll")] public static extern int NtSuspendProcess(IntPtr h); [DllImport("ntdll.dll")] public static extern int NtResumeProcess(IntPtr h); }'
        $process=Get-Process -Id $TargetId
        try {
            $status=if ($Action -eq 'suspend-watch') {[TtsFault]::NtSuspendProcess($process.Handle)} else {[TtsFault]::NtResumeProcess($process.Handle)}
            if ($status -ne 0) {throw 'Could not pause/resume isolated watcher'}
        } finally { $process.Dispose() }
    } else { Stop-Process -Id $TargetId -Force }
    return
}
$state=Get-TtsState
if ($Action -eq 'stop') {
    $target=@($state.Processes | Where-Object { $_.ProcessId -eq $TargetId -and $_.CreationDate.Ticks -eq $TargetTicks })
    if ($target.Count -ne 1) {throw 'Test process identity mismatch'}
    Stop-OwnedTts $target
    return
}
$avatar=Get-ProjectAvatar
$watchPath=Join-Path $PSScriptRoot 'watch-tts-session.ps1'
$watchers=@(Get-AgentProcesses | Where-Object { $_.Name -like 'powershell*' -and $_.CommandLine.Replace('/','\').Contains($watchPath) })
@{tts=@($state.Processes | Select-Object ProcessId,ParentProcessId,@{n='Ticks';e={$_.CreationDate.Ticks}});
listener=$state.ListenerPid; avatar=$avatar.ProcessId; avatarTicks=$avatar.CreationDate.Ticks;
watchers=@($watchers | Select-Object ProcessId,@{n='Ticks';e={$_.CreationDate.Ticks}})} | ConvertTo-Json -Depth 4 -Compress
