# Codex: compatibility entry only. All startup/voice ownership is canonical.
[CmdletBinding()]
param([switch]$SkipAvatar, [ValidateRange(3,180)][int]$StartupSeconds=90)
& (Join-Path $PSScriptRoot 'start-mvp.ps1') @PSBoundParameters
