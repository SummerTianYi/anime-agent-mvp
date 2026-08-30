[CmdletBinding()]
param(
    [ValidatePattern('^\d+\.\d+$')]
    [string]$Version,
    [string]$ArchiveRoot
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "model-version-common.ps1")

$repoRoot = Get-ModelVersionRepoRoot
$index = Read-ModelVersionIndex
$versions = @($index.versions)
if (-not [string]::IsNullOrWhiteSpace($Version)) {
    $versions = @($versions | Where-Object { [string]$_.version -eq $Version })
    if ($versions.Count -ne 1) {
        throw "Version '$Version' is absent from model-versions/index.json."
    }
}

foreach ($entry in $versions) {
    $manifest = Read-ModelVersionManifest -Version ([string]$entry.version)
    if ([string]$manifest.status -ne "accepted") {
        throw "Formal model version $($entry.version) must have immutable accepted status."
    }
    if ([string]$manifest.runtime.commit -ne [string]$entry.runtimeCommit) {
        throw "Runtime commit mismatch for model version $($entry.version)."
    }
    & git -C $repoRoot cat-file -e "$($manifest.runtime.commit)^{commit}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime commit for model version $($entry.version) does not exist locally: $($manifest.runtime.commit)"
    }

    foreach ($artifactName in @("editableBlend", "runtimeGlb")) {
        $artifact = $manifest.artifacts.$artifactName
        $artifactPath = Get-ArchivedArtifactPath -Manifest $manifest -Artifact $artifact -ArchiveRoot $ArchiveRoot
        Assert-FileContract -Path $artifactPath -ExpectedBytes ([long]$artifact.bytes) -ExpectedSha256 ([string]$artifact.sha256) -Label "$($entry.version) $artifactName" | Out-Null
    }
    Write-Host "MODEL_VERSION_OK $($entry.version) commit=$($manifest.runtime.commit)"
}

$currentEntries = @($index.versions | Where-Object { [string]$_.version -eq [string]$index.currentVersion })
if ($currentEntries.Count -ne 1) {
    throw "currentVersion must reference exactly one registered model version."
}

Write-Host "MODEL_VERSION_REGISTRY_OK count=$($versions.Count) current=$($index.currentVersion)"
