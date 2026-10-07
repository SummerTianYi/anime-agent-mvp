# Codex: authorized existing formal entry, brokered by desktop Explorer.
# Caller must normally close the current Godot and verify its exit first.
param([Parameter(Mandatory=$true)][string]$Production)
$ErrorActionPreference='Stop'
$entry=Join-Path (Resolve-Path -LiteralPath $Production).Path 'start-anime-agent.cmd'
if (-not (Test-Path -LiteralPath $entry)) { throw 'Formal entry absent' }
$shortcutPath=Join-Path $env:TEMP ('tianyi-audit-formal-'+[Guid]::NewGuid().ToString()+'.lnk')
$link=(New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
$link.TargetPath=Join-Path $env:WINDIR 'System32/WindowsPowerShell/v1.0/powershell.exe'
$link.Arguments='-NoProfile -WindowStyle Hidden -Command "& '''+$entry+'''"'
$link.WorkingDirectory=$Production
$link.WindowStyle=7
$link.Save()
Start-Process explorer.exe -WindowStyle Hidden -ArgumentList ('"'+$shortcutPath+'"')
Write-Output ('Formal-entry shortcut: '+$shortcutPath)
