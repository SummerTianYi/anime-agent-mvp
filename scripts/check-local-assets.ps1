[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$modelPath = Join-Path $repoRoot "apps\avatar-runtime\assets\luotianyi_v4.glb"
$expectedSize = 128621144
$expectedSha256 = "DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A"
$motionContracts = @(
    @{
        Name = "Idle"
        Path = Join-Path $repoRoot "apps\avatar-runtime\assets\motions\luotianyi_idle.glb"
        Size = 23057704
        Sha256 = "33E3FE13721F0D01929C6CB4AF22A408C3485F20512066975ED102DC693CC21B"
    },
    @{
        Name = "Pirouette"
        Path = Join-Path $repoRoot "apps\avatar-runtime\assets\motions\luotianyi_pirouette.glb"
        Size = 23114580
        Sha256 = "1FEFBF0667711845E4FC6E0574D57D74C8982E15AA76A2A25BB9192BE1FAA284"
    }
)

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

foreach ($contract in $motionContracts) {
    if (-not (Test-Path -LiteralPath $contract.Path)) {
        Write-Host "[Anime Agent] Optional $($contract.Name) motion is absent."
        continue
    }
    $motion = Get-Item -LiteralPath $contract.Path
    if ($motion.Length -ne $contract.Size) {
        throw "$($contract.Name) motion size mismatch. Expected $($contract.Size) bytes, got $($motion.Length)."
    }
    $actualMotionSha256 = (Get-FileHash -LiteralPath $contract.Path -Algorithm SHA256).Hash
    if ($actualMotionSha256 -ne $contract.Sha256) {
        throw "$($contract.Name) motion SHA-256 mismatch. Expected $($contract.Sha256), got $actualMotionSha256."
    }
    Write-Host "[Anime Agent] Optional $($contract.Name) motion verified."
    Write-Host "Motion path: $($contract.Path)"
    Write-Host "Motion bytes: $($motion.Length)"
    Write-Host "Motion SHA-256: $actualMotionSha256"
}
