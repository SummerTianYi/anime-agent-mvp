Set-StrictMode -Version Latest

$script:ModelVersionScriptsRoot = $PSScriptRoot

function Get-ModelVersionRepoRoot {
    return (Resolve-Path (Join-Path $script:ModelVersionScriptsRoot "..\..")).Path
}

function Get-ModelVersionArchiveRoot {
    param([string]$ArchiveRoot)

    if (-not [string]::IsNullOrWhiteSpace($ArchiveRoot)) {
        return [IO.Path]::GetFullPath($ArchiveRoot)
    }
    $repoRoot = Get-ModelVersionRepoRoot
    return [IO.Path]::GetFullPath((Join-Path (Split-Path $repoRoot -Parent) "model-archive"))
}

function Read-ModelVersionIndex {
    $repoRoot = Get-ModelVersionRepoRoot
    $indexPath = Join-Path $repoRoot "model-versions\index.json"
    if (-not (Test-Path -LiteralPath $indexPath)) {
        throw "Model version index is missing: $indexPath"
    }
    return Get-Content -Raw -Encoding UTF8 -LiteralPath $indexPath | ConvertFrom-Json
}

function Read-ModelVersionManifest {
    param([Parameter(Mandatory = $true)][string]$Version)

    if ($Version -notmatch '^\d+\.\d+$') {
        throw "Invalid model version '$Version'. Expected a number such as 1.0 or 1.2."
    }
    $repoRoot = Get-ModelVersionRepoRoot
    $manifestPath = Join-Path $repoRoot "model-versions\$Version\manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw "Unknown model version '$Version': $manifestPath"
    }
    $manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
    if ([string]$manifest.version -ne $Version) {
        throw "Manifest version mismatch in $manifestPath"
    }
    return $manifest
}

function Get-ArchivedArtifactPath {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Artifact,
        [string]$ArchiveRoot
    )

    $resolvedArchiveRoot = Get-ModelVersionArchiveRoot -ArchiveRoot $ArchiveRoot
    return Join-Path $resolvedArchiveRoot (Join-Path ([string]$Manifest.artifacts.archiveDirectory) ([string]$Artifact.file))
}

function Assert-FileContract {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][long]$ExpectedBytes,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256,
        [string]$Label = "artifact"
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label is missing: $Path"
    }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -ne $ExpectedBytes) {
        throw "$Label size mismatch at $Path. Expected $ExpectedBytes bytes, got $($item.Length)."
    }
    $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
    if ($actualSha256 -ne $ExpectedSha256.ToUpperInvariant()) {
        throw "$Label SHA-256 mismatch at $Path. Expected $ExpectedSha256, got $actualSha256."
    }
    return $actualSha256
}

function Copy-VerifiedArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][long]$ExpectedBytes,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256
    )

    Assert-FileContract -Path $Source -ExpectedBytes $ExpectedBytes -ExpectedSha256 $ExpectedSha256 -Label "source artifact" | Out-Null
    $destinationDirectory = Split-Path $Destination -Parent
    if (-not (Test-Path -LiteralPath $destinationDirectory)) {
        New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    }
    $temporaryPath = "$Destination.model-version-switching"
    if (Test-Path -LiteralPath $temporaryPath) {
        throw "A previous incomplete switch must be inspected first: $temporaryPath"
    }
    Copy-Item -LiteralPath $Source -Destination $temporaryPath
    try {
        Set-ItemProperty -LiteralPath $temporaryPath -Name IsReadOnly -Value $false
        Assert-FileContract -Path $temporaryPath -ExpectedBytes $ExpectedBytes -ExpectedSha256 $ExpectedSha256 -Label "temporary artifact" | Out-Null
        if (Test-Path -LiteralPath $Destination) {
            Set-ItemProperty -LiteralPath $Destination -Name IsReadOnly -Value $false
        }
        Move-Item -LiteralPath $temporaryPath -Destination $Destination -Force
        Assert-FileContract -Path $Destination -ExpectedBytes $ExpectedBytes -ExpectedSha256 $ExpectedSha256 -Label "activated artifact" | Out-Null
    } catch {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
        throw
    }
}

function Write-ModelVersionJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$Value
    )

    $directory = Split-Path $Path -Parent
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $json = $Value | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($Path, "$json`n", [Text.UTF8Encoding]::new($false))
}
