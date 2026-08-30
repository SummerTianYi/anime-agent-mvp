[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+$')]
    [string]$Version,
    [string]$ArchiveRoot,
    [string]$WorktreeRoot,
    [switch]$Launch,
    [switch]$SkipMotions
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "model-version-common.ps1")

$repoRoot = Get-ModelVersionRepoRoot
$manifest = Read-ModelVersionManifest -Version $Version
$commit = [string]$manifest.runtime.commit
& git -C $repoRoot cat-file -e "$commit^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Runtime commit is unavailable locally: $commit"
}

if ([string]::IsNullOrWhiteSpace($WorktreeRoot)) {
    $WorktreeRoot = Join-Path (Split-Path $repoRoot -Parent) "model-worktrees"
}
$worktreePath = Join-Path ([IO.Path]::GetFullPath($WorktreeRoot)) $Version
if (Test-Path -LiteralPath $worktreePath) {
    $existingCommit = (& git -C $worktreePath rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or $existingCommit.Trim() -ne $commit) {
        throw "Existing worktree path does not match model version $Version and will not be overwritten: $worktreePath"
    }
} else {
    New-Item -ItemType Directory -Path (Split-Path $worktreePath -Parent) -Force | Out-Null
    & git -C $repoRoot worktree add --detach $worktreePath $commit
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create isolated worktree for model version $Version."
    }
}

$artifact = $manifest.artifacts.runtimeGlb
$sourcePath = Get-ArchivedArtifactPath -Manifest $manifest -Artifact $artifact -ArchiveRoot $ArchiveRoot
$targetPath = Join-Path $worktreePath "apps\avatar-runtime\assets\luotianyi_v4.glb"
$targetMatches = $false
if (Test-Path -LiteralPath $targetPath) {
    $targetItem = Get-Item -LiteralPath $targetPath
    if ($targetItem.Length -eq [long]$artifact.bytes) {
        $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetPath).Hash
        $targetMatches = $targetHash -eq ([string]$artifact.sha256).ToUpperInvariant()
    }
}
if (-not $targetMatches) {
    Copy-VerifiedArtifact -Source $sourcePath -Destination $targetPath -ExpectedBytes ([long]$artifact.bytes) -ExpectedSha256 ([string]$artifact.sha256)
}

if (-not $SkipMotions) {
    $currentMotionDirectory = Join-Path $repoRoot "apps\avatar-runtime\assets\motions"
    $targetMotionDirectory = Join-Path $worktreePath "apps\avatar-runtime\assets\motions"
    if (Test-Path -LiteralPath $currentMotionDirectory) {
        New-Item -ItemType Directory -Path $targetMotionDirectory -Force | Out-Null
        Get-ChildItem -LiteralPath $currentMotionDirectory -Filter "*.glb" -File | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $targetMotionDirectory $_.Name) -Force
        }
    }
}

$supportAssetChanged = $false
$currentAssetDirectory = Join-Path $repoRoot "apps\avatar-runtime\assets"
$targetAssetDirectory = Join-Path $worktreePath "apps\avatar-runtime\assets"
Get-ChildItem -LiteralPath $currentAssetDirectory -File | Where-Object { $_.Extension.ToLowerInvariant() -in @(".jpg", ".jpeg", ".png", ".webp") } | ForEach-Object {
    $supportTarget = Join-Path $targetAssetDirectory $_.Name
    $copySupportAsset = -not (Test-Path -LiteralPath $supportTarget)
    if (-not $copySupportAsset) {
        $copySupportAsset = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $supportTarget).Hash
    }
    if ($copySupportAsset) {
        Copy-Item -LiteralPath $_.FullName -Destination $supportTarget -Force
        $supportAssetChanged = $true
    }
}

$projectPath = Join-Path $worktreePath "apps\avatar-runtime"
$godotCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Godot\Godot_v4.7.2-stable_win64_console.exe"),
    "D:\steam\steamapps\common\Godot\Godot_v4.7.2-stable_win64_console.exe",
    (Join-Path (Split-Path $repoRoot -Parent) "tools\godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe")
)
$godotConsolePath = $godotCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$needsImport = (-not $targetMatches) -or $supportAssetChanged -or (-not (Test-Path -LiteralPath (Join-Path $projectPath ".godot\imported")))
if ($needsImport) {
    if (-not $godotConsolePath) {
        throw "Godot 4.7.2 is required to initialize the isolated model worktree."
    }
    & $godotConsolePath --headless --editor --path $projectPath --import --quit
    if ($LASTEXITCODE -ne 0) {
        throw "Godot import initialization failed for model version $Version."
    }
}

Write-Host "MODEL_VERSION_WORKTREE_READY $Version"
Write-Host "Path: $worktreePath"
Write-Host "Commit: $commit"
if ($Launch) {
    if (-not $godotConsolePath) {
        throw "Godot 4.7.2 is required to launch model version $Version."
    }
    $godotGuiPath = $godotConsolePath -replace '_console\.exe$', '.exe'
    if (-not (Test-Path -LiteralPath $godotGuiPath)) {
        $godotGuiPath = $godotConsolePath
    }
    $godotArguments = @("--display-driver", "windows", "--path", $projectPath, "--script", "res://launcher.gd", "--position", "80,80", "--resolution", "560x760")
    Start-Process -FilePath $godotGuiPath -ArgumentList $godotArguments -WorkingDirectory $worktreePath -WindowStyle Normal | Out-Null
    Write-Host "MODEL_VERSION_LAUNCHED $Version"
}
