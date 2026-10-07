# Codex: local diagnostic shortcut launched by the existing Explorer broker.
# The helper only hashes DB paths; it never opens SQLite for writes.
param([string]$PythonW,[string]$AuditRoot)
$ErrorActionPreference='Stop'
$shortcutPath=Join-Path $env:TEMP ('tianyi-audit-identity-'+[Guid]::NewGuid().ToString()+'.lnk')
$link=(New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
$link.TargetPath=$PythonW
$link.Arguments='"'+(Join-Path $AuditRoot 'scripts/root_cause_audit/identity_probe.py')+'" --output "'+(Join-Path $AuditRoot 'docs/assessments/root-cause-audit/evidence/explorer-identity.json')+'"'
$link.WorkingDirectory=$AuditRoot
$link.WindowStyle=7
$link.Save()
Start-Process explorer.exe -WindowStyle Hidden -ArgumentList ('"'+$shortcutPath+'"')
Write-Output ('Diagnostic shortcut: '+$shortcutPath)
