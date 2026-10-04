# Codex: explicitly authorized, project-scoped normal-close activation.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Production, [ValidateSet('prepare','activate','rollback')][string]$Phase='prepare', [string]$Backup, [string]$ExpectedManifest)
$ErrorActionPreference='Stop'
$source=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$target=(Resolve-Path -LiteralPath $Production).Path
function Get-FileHash([string]$Path) {
    $stream=[IO.File]::OpenRead($Path)
    $hash=[Security.Cryptography.SHA256]::Create()
    try {return [pscustomobject]@{Hash=([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','')}}
    finally {$stream.Dispose();$hash.Dispose()}
}
function ShaText([string]$Path) {
    $text=(Get-Content -LiteralPath $Path -Raw -Encoding UTF8).Replace("`r`n","`n")
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($text)))).Replace('-','').ToLowerInvariant() }
    finally {$hash.Dispose()}
}
function TargetPath([string]$Relative) {
    $path=[IO.Path]::GetFullPath((Join-Path $target $Relative))
    if (-not $path.StartsWith($target+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Path escaped production checkout'}
    return $path
}
if ($Phase -eq 'prepare') {
    if ($ExpectedManifest) {
        $active=Get-Content -LiteralPath $ExpectedManifest -Raw -Encoding UTF8 | ConvertFrom-Json
        if(-not $active.files_match -or -not $active.file_hashes){throw 'Expected activation manifest is not verified'}
        foreach($entry in $active.file_hashes.PSObject.Properties){
            if((Get-FileHash (TargetPath $entry.Name)).Hash.ToLowerInvariant() -ne $entry.Value.deployed){throw "Production changed after activation: $($entry.Name). No overwrite."}
        }
    } else {
    $base=Get-Content (Join-Path $source 'docs/assessments/harness-v0/evidence/baseline/manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach($entry in $base.files.PSObject.Properties) {
        if ((ShaText (TargetPath $entry.Name)) -ne $entry.Value) {throw "Production source changed since baseline: $($entry.Name). No overwrite."}
    }
    & git -C $target diff --exit-code --quiet -- apps/avatar-runtime/runtime.gd apps/avatar-runtime/interaction_ui.gd
    if ($LASTEXITCODE -ne 0) {throw 'Production avatar has unreviewed changes'}
    }
    $Backup=Join-Path $env:LOCALAPPDATA ('AnimeAgent/harness-backups/v1-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $Backup | Out-Null
    $files=@()
    foreach($file in Get-ChildItem (Join-Path $source 'services/agent-core/agent_core') -Filter '*.py') {
        $relative='services/agent-core/agent_core/'+$file.Name
        $old=TargetPath $relative
        if ((Test-Path -LiteralPath $old) -and (Get-FileHash $old).Hash -eq (Get-FileHash $file.FullName).Hash) {continue}
        $files+=$relative
    }
    $files+=@('apps/avatar-runtime/runtime.gd','apps/avatar-runtime/interaction_ui.gd')
    $entries=@()
    foreach($relative in @($files)+@('.env')) {
        $old=TargetPath $relative
        $save=Join-Path $Backup $relative
        $exists=Test-Path -LiteralPath $old
        if($exists){New-Item -ItemType Directory -Path (Split-Path $save) -Force | Out-Null; Copy-Item -LiteralPath $old -Destination $save}
        $entries+=@{path=$relative;existed=$exists;before_sha= $(if($exists){(Get-FileHash $old).Hash}else{$null});
                    candidate_sha=$(if($relative -ne '.env'){(Get-FileHash (Join-Path $source $relative)).Hash}else{$null})}
    }
    @{source=$source;production=$target;entries=$entries;created=(Get-Date).ToString('o')} | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath (Join-Path $Backup 'manifest.json') -Encoding UTF8
    Write-Output ("BACKUP="+$Backup)
    return
}
$state=Get-Content -LiteralPath (Join-Path $Backup 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($state.production -ne $target -or $state.source -ne $source) {throw 'Backup identity mismatch'}
. (Join-Path $target 'scripts/startup-common.ps1')
Initialize-AgentRuntime $target
if($Phase -eq 'activate'){
    foreach($entry in $state.entries | Where-Object {$_.path -ne '.env'}){
        $old=TargetPath $entry.path
        if($entry.existed -and (Get-FileHash $old).Hash -ne $entry.before_sha){throw "Production changed after backup: $($entry.path)"}
        if((Get-FileHash (Join-Path $source $entry.path)).Hash -ne $entry.candidate_sha){throw "Candidate changed after backup: $($entry.path)"}
    }
}
$avatar=Get-ProjectAvatar
if($avatar){
    $window=Get-Process -Id $avatar.ProcessId -ErrorAction Stop
    if(-not $window.CloseMainWindow()){throw 'Normal close request was not accepted; no force kill or install'}
    if(-not $window.WaitForExit(30000)){throw 'Normal farewell exit did not finish; no force kill or install'}
    Write-Output 'Normal avatar farewell exit completed.'
}
$timer=[Diagnostics.Stopwatch]::StartNew()
while(Get-AgentCoreHealth){
    if($timer.Elapsed.TotalSeconds -gt 45){throw 'Core supervisor did not finish normal cleanup; no install'}
    Start-Sleep -Milliseconds 500
}
foreach($entry in $state.entries){
    if($Phase -eq 'activate' -and $entry.path -ne '.env'){
        Copy-Item -LiteralPath (Join-Path $source $entry.path) -Destination (TargetPath $entry.path)
    }elseif($Phase -eq 'rollback' -and $entry.existed){
        Copy-Item -LiteralPath (Join-Path $Backup $entry.path) -Destination (TargetPath $entry.path)
    }
}
Write-Output 'Starting through the unchanged official CMD entry.'
& (Join-Path $target 'start-anime-agent.cmd')
if($LASTEXITCODE -ne 0){throw 'Official startup failed; use rollback with the same backup'}
$active=@{}
foreach($entry in $state.entries|Where-Object{$_.path -ne '.env'}){
    $active[$entry.path]=(Get-FileHash (TargetPath $entry.path)).Hash
}
@{phase=$Phase;activated=(Get-Date).ToString('o');files=$active} | ConvertTo-Json -Depth 8 |
 Set-Content -LiteralPath (Join-Path $Backup ($Phase+'-result.json')) -Encoding UTF8
Write-Output ("ACTIVATION_COMPLETE "+$Phase)
