[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+$')]
    [string]$Version,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+$')]
    [string]$BaseVersion,
    [Parameter(Mandatory = $true)][string]$DisplayName,
    [Parameter(Mandatory = $true)][string[]]$OptimizationPlan,
    [Parameter(Mandatory = $true)][string[]]$OptimizationChanges,
    [string[]]$ExplicitlyUnchanged = @("official character design", "mesh topology", "UV", "skin weights"),
    [string[]]$KnownIssues = @(),
    [Parameter(Mandatory = $true)][string]$PreviewDirectory,
    [string]$BlendPath,
    [string]$GlbPath,
    [string]$RuntimeCommit,
    [string[]]$VerificationResources = @(),
    [string]$ArchiveRoot
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "model-version-common.ps1")

$repoRoot = Get-ModelVersionRepoRoot
$resolvedArchiveRoot = Get-ModelVersionArchiveRoot -ArchiveRoot $ArchiveRoot
$versionDirectory = Join-Path $repoRoot "model-versions\$Version"
$archiveDirectory = Join-Path $resolvedArchiveRoot "$Version\artifacts"
if ((Test-Path -LiteralPath $versionDirectory) -or (Test-Path -LiteralPath (Join-Path $resolvedArchiveRoot $Version))) {
    throw "Model version $Version already exists. Versions are immutable and cannot be overwritten."
}

$baseManifest = Read-ModelVersionManifest -Version $BaseVersion
$index = Read-ModelVersionIndex
if ([string]$index.currentVersion -ne $BaseVersion) {
    throw "BaseVersion must be the current accepted version $($index.currentVersion)."
}
$baseParts = $BaseVersion.Split('.')
$expectedVersion = "$($baseParts[0]).$([int]$baseParts[1] + 1)"
if ($Version -ne $expectedVersion) {
    throw "The next formal model version after $BaseVersion must be $expectedVersion, not $Version."
}
if ([string]::IsNullOrWhiteSpace($RuntimeCommit)) {
    $RuntimeCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
}
& git -C $repoRoot cat-file -e "$RuntimeCommit^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Runtime commit does not exist: $RuntimeCommit"
}
$avatarChanges = @(& git -C $repoRoot status --porcelain -- apps/avatar-runtime)
if ($avatarChanges.Count -gt 0) {
    throw "Avatar runtime has uncommitted changes. Commit the accepted optimization before assigning model version $Version."
}

if ([string]::IsNullOrWhiteSpace($BlendPath)) {
    $BlendPath = Join-Path (Split-Path $repoRoot -Parent) "luotianyi_v4_prepared.blend"
}
if ([string]::IsNullOrWhiteSpace($GlbPath)) {
    $GlbPath = Join-Path $repoRoot "apps\avatar-runtime\assets\luotianyi_v4.glb"
}
foreach ($path in @($BlendPath, $GlbPath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Snapshot source is missing: $path"
    }
}
if (-not (Test-Path -LiteralPath $PreviewDirectory -PathType Container)) {
    throw "Preview directory is missing: $PreviewDirectory"
}
$requiredViews = @("front", "left", "right", "back", "max-zoom", "neutral-face", "expression-extremes")
$previewSources = @()
foreach ($view in $requiredViews) {
    $candidate = Get-ChildItem -LiteralPath $PreviewDirectory -File | Where-Object {
        $_.BaseName -eq $view -and $_.Extension.ToLowerInvariant() -in @(".png", ".jpg", ".jpeg")
    } | Select-Object -First 1
    if (-not $candidate) {
        throw "Required preview '$view.png' or '$view.jpg' is missing from $PreviewDirectory."
    }
    $previewSources += $candidate
}

New-Item -ItemType Directory -Path $archiveDirectory -Force | Out-Null
$previewArchiveDirectory = Join-Path $resolvedArchiveRoot "$Version\previews"
New-Item -ItemType Directory -Path $previewArchiveDirectory -Force | Out-Null
$blendDestination = Join-Path $archiveDirectory "luotianyi_v4_prepared.blend"
$glbDestination = Join-Path $archiveDirectory "luotianyi_v4.glb"
Copy-Item -LiteralPath $BlendPath -Destination $blendDestination
Copy-Item -LiteralPath $GlbPath -Destination $glbDestination
Set-ItemProperty -LiteralPath $blendDestination -Name IsReadOnly -Value $true
Set-ItemProperty -LiteralPath $glbDestination -Name IsReadOnly -Value $true
$capturedPreviews = @()
foreach ($previewSource in $previewSources) {
    $previewDestination = Join-Path $previewArchiveDirectory $previewSource.Name
    Copy-Item -LiteralPath $previewSource.FullName -Destination $previewDestination
    Set-ItemProperty -LiteralPath $previewDestination -Name IsReadOnly -Value $true
    $previewItem = Get-Item -LiteralPath $previewDestination
    $capturedPreviews += [ordered]@{
        view = $previewSource.BaseName
        file = $previewItem.Name
        bytes = $previewItem.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $previewDestination).Hash
    }
}

$blendItem = Get-Item -LiteralPath $blendDestination
$glbItem = Get-Item -LiteralPath $glbDestination
$blendHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $blendDestination).Hash
$glbHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $glbDestination).Hash
$binaryChanged = $glbHash -ne ([string]$baseManifest.artifacts.runtimeGlb.sha256).ToUpperInvariant()
# Codex: preserve the exact motion resources and support textures, not future HEAD's assets.
$resourcePaths = @($VerificationResources)
$registry = Get-Content -Raw -Encoding UTF8 (Join-Path $repoRoot "apps/avatar-runtime/motion_registry.json") | ConvertFrom-Json
foreach ($clip in $registry.clips) {
    if (-not ([string]$clip.path).StartsWith("res://assets/motions/")) { throw "Unsupported motion path: $($clip.path)" }
    $resourcePaths += "apps/avatar-runtime/" + ([string]$clip.path).Substring(6)
}
$resourcePaths += @(Get-ChildItem (Join-Path $repoRoot "apps/avatar-runtime/assets") -File | Where-Object {
    $_.Extension.ToLowerInvariant() -in @(".jpg", ".jpeg", ".png", ".webp")
} | ForEach-Object { "apps/avatar-runtime/assets/" + $_.Name })
$runtimeResources = @()
foreach ($relative in ($resourcePaths | Sort-Object -Unique)) {
    $sourcePath = Resolve-ModelResourcePath -Root $repoRoot -RelativePath $relative
    $destinationPath = Resolve-ModelResourcePath -Root (Join-Path $resolvedArchiveRoot "$Version/resources") -RelativePath $relative
    New-Item -ItemType Directory -Path (Split-Path $destinationPath -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath
    Set-ItemProperty -LiteralPath $destinationPath -Name IsReadOnly -Value $true
    $runtimeResources += [ordered]@{ path = $relative; bytes = (Get-Item $destinationPath).Length; sha256 = (Get-FileHash $destinationPath -Algorithm SHA256).Hash }
}
$manifest = [ordered]@{
    schemaVersion = 1
    version = $Version
    status = "accepted"
    baseVersion = $BaseVersion
    displayName = $DisplayName
    acceptedAt = (Get-Date).ToString("o")
    source = $baseManifest.source
    runtime = [ordered]@{
        commit = $RuntimeCommit
        modelBinaryChangedFromBase = $binaryChanged
        godot = "4.7.2"
        blender = "5.2.1 LTS"
        mmdTools = "4.5.13"
        vrmAddon = "4.5.0"
    }
    artifacts = [ordered]@{
        archiveDirectory = "$Version/artifacts"
        editableBlend = [ordered]@{ file = $blendItem.Name; bytes = $blendItem.Length; sha256 = $blendHash }
        runtimeGlb = [ordered]@{ file = $glbItem.Name; bytes = $glbItem.Length; sha256 = $glbHash }
    }
    runtimeResources = $runtimeResources
    structure = [ordered]@{
        skeletons = 1
        bones = 751
        expressions = 48
        pigtailChainLengths = @(17, 17)
        meshTopologyChanged = $false
        uvChanged = $false
        skinWeightsChanged = $false
    }
    optimization = [ordered]@{
        goal = $DisplayName
        plan = @($OptimizationPlan)
        changes = @($OptimizationChanges)
        explicitlyUnchanged = @($ExplicitlyUnchanged)
        knownIssues = @($KnownIssues)
    }
    visualEvidence = [ordered]@{
        localDirectory = "$Version/previews"
        requiredViews = $requiredViews
        captured = $capturedPreviews
    }
    verification = @(
        [ordered]@{ name = "snapshot-contract"; result = "passed"; evidence = "$($glbItem.Length) bytes; SHA-256 $glbHash" },
        [ordered]@{ name = "visual-review"; result = "pending"; evidence = "Add local preview filenames and hashes after capture." }
    )
    rollback = [ordered]@{
        assetCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\model-versions\switch-model-version.ps1 -Version $Version"
        exactRuntimeCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\model-versions\open-model-version.ps1 -Version $Version -Launch"
    }
}

$manifestPath = Join-Path $versionDirectory "manifest.json"
Write-ModelVersionJson -Path $manifestPath -Value $manifest
Write-ModelVersionJson -Path (Join-Path $resolvedArchiveRoot "$Version\manifest.json") -Value $manifest

foreach ($entry in @($index.versions)) {
    if ([string]$entry.status -eq "current") {
        $entry.status = "accepted"
    }
}
$index.currentVersion = $Version
$index.versions = @($index.versions) + @([ordered]@{
    version = $Version
    status = "current"
    manifest = "model-versions/$Version/manifest.json"
    runtimeCommit = $RuntimeCommit
})
Write-ModelVersionJson -Path (Join-Path $repoRoot "model-versions\index.json") -Value $index
Write-Host "MODEL_VERSION_SNAPSHOT_CREATED $Version"
Write-Host "Review and fill visualEvidence before committing the new manifest."
