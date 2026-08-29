[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$modelPath = Join-Path $repoRoot "apps\avatar-runtime\assets\luotianyi_v4.glb"
$expectedSize = 128621144
$expectedSha256 = "DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A"

if (-not (Test-Path -LiteralPath $modelPath)) {
    throw "Local avatar model is missing: $modelPath"
}

$model = Get-Item -LiteralPath $modelPath
if ($model.Length -ne $expectedSize) {
    throw "Avatar model size mismatch. Expected $expectedSize bytes, got $($model.Length)."
}

$actualSha256 = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
if ($actualSha256 -ne $expectedSha256) {
    throw "Avatar model SHA-256 mismatch. Expected $expectedSha256, got $actualSha256."
}

Write-Host "[Anime Agent] Local avatar asset verified."
Write-Host "Path: $modelPath"
Write-Host "Bytes: $($model.Length)"
Write-Host "SHA-256: $actualSha256"
