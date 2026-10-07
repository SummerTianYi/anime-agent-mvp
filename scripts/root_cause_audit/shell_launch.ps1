# Codex diagnostic launcher: broker an existing executable through Explorer.
# No UI automation, authentication, settings or process termination.
param([Parameter(Mandatory=$true)][string]$Executable,
      [Parameter(Mandatory=$true)][string]$Arguments,
      [Parameter(Mandatory=$true)][string]$WorkingDirectory)
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject Shell.Application
$shell.ShellExecute($Executable, $Arguments, $WorkingDirectory, 'open', 0)
