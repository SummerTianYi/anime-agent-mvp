[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+$')]
    [string]$Version,
    [string]$ArchiveRoot
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "model-version-common.ps1")

$repoRoot = Get-ModelVersionRepoRoot
$resolvedArchiveRoot = Get-ModelVersionArchiveRoot -ArchiveRoot $ArchiveRoot
$manifest = Read-ModelVersionManifest -Version $Version
$artifact = $manifest.artifacts.runtimeGlb
$sourcePath = Get-ArchivedArtifactPath -Manifest $manifest -Artifact $artifact -ArchiveRoot $resolvedArchiveRoot
$runtimePath = Join-Path $repoRoot "apps\avatar-runtime\assets\luotianyi_v4.glb"
Assert-FileContract -Path $sourcePath -ExpectedBytes ([long]$artifact.bytes) -ExpectedSha256 ([string]$artifact.sha256) -Label "$Version runtime GLB" | Out-Null

$currentSha256 = $null
if (Test-Path -LiteralPath $runtimePath) {
    $currentSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $runtimePath).Hash
    $knownHashes = @()
    foreach ($entry in @(Read-ModelVersionIndex).versions) {
        $knownManifest = Read-ModelVersionManifest -Version ([string]$entry.version)
        $knownHashes += ([string]$knownManifest.artifacts.runtimeGlb.sha256).ToUpperInvariant()
    }
    if ($knownHashes -notcontains $currentSha256) {
        $recoveryDirectory = Join-Path $resolvedArchiveRoot (Join-Path "_recovery" (Get-Date -Format "yyyyMMdd-HHmmss"))
        New-Item -ItemType Directory -Path $recoveryDirectory -Force | Out-Null
        $recoveryPath = Join-Path $recoveryDirectory "luotianyi_v4.glb"
        Copy-Item -LiteralPath $runtimePath -Destination $recoveryPath
        Write-Warning "Unknown current runtime model was preserved before switching: $recoveryPath"
    }
}

if ($currentSha256 -ne ([string]$artifact.sha256).ToUpperInvariant()) {
    Copy-VerifiedArtifact -Source $sourcePath -Destination $runtimePath -ExpectedBytes ([long]$artifact.bytes) -ExpectedSha256 ([string]$artifact.sha256)
}

$activeState = [ordered]@{
    version = $Version
    activatedAt = (Get-Date).ToString("o")
    runtimeCommit = [string]$manifest.runtime.commit
    runtimeGlbSha256 = [string]$artifact.sha256
    note = "Asset-only activation; use open-model-version.ps1 for an exact runtime comparison."
}
Write-ModelVersionJson -Path (Join-Path $resolvedArchiveRoot "active-version.json") -Value $activeState
Write-Host "MODEL_VERSION_ACTIVE $Version"
Write-Host "Runtime GLB: $runtimePath"
Write-Host "For exact visuals: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\model-versions\open-model-version.ps1 -Version $Version -Launch"
