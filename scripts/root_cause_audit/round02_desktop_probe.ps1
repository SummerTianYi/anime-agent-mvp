# Audit-only namespace probe via the already-running desktop Explorer.
param([Parameter(Mandatory=$true)][string]$PythonW,
      [Parameter(Mandatory=$true)][string]$AuditRoot,
      [Parameter(Mandatory=$true)][string]$PrivateOutput)
$ErrorActionPreference='Stop'
$probe=Join-Path $AuditRoot 'scripts/root_cause_audit/round02_identity.py'
if (-not (Test-Path -LiteralPath $probe)) { throw 'Probe missing' }
if (Test-Path -LiteralPath $PrivateOutput) { throw 'Output already exists' }
$shortcutPath=Join-Path (Split-Path -Parent $PrivateOutput) ('identity-'+[Guid]::NewGuid().ToString()+'.lnk')
$link=(New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
$link.TargetPath=$PythonW
$link.Arguments='"'+$probe+'" --require-unpackaged --output-dir "'+$PrivateOutput+'"'
$link.WorkingDirectory=$AuditRoot
$link.WindowStyle=7
$link.Save()
Start-Process explorer.exe -WindowStyle Hidden -ArgumentList ('"'+$shortcutPath+'"')
Write-Output ('Audit identity shortcut: '+$shortcutPath)
