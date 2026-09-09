# Codex: read-only negative controls for immutable support-resource restoration.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "model-version-common.ps1")
$repoRoot = Get-ModelVersionRepoRoot
foreach ($bad in @("../outside", "C:/outside", "../../secrets")) {
    $rejected = $false
    try { Resolve-ModelResourcePath -Root $repoRoot -RelativePath $bad | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw "Traversal accepted: $bad" }
}
$path = Resolve-ModelResourcePath -Root $repoRoot -RelativePath "apps/avatar-runtime/runtime.gd"
$length = (Get-Item $path).Length
$hash = (Get-FileHash $path -Algorithm SHA256).Hash
Assert-FileContract -Path $path -ExpectedBytes $length -ExpectedSha256 $hash | Out-Null
$rejected = $false
try { Assert-FileContract -Path $path -ExpectedBytes $length -ExpectedSha256 ("0" * 64) | Out-Null } catch { $rejected = $true }
if (-not $rejected) { throw "Corrupted resource accepted" }
foreach ($file in Get-ChildItem $PSScriptRoot -Filter *.ps1) {
    $tokens = $null
    $parseErrors = $null
    [Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count) { throw "PowerShell parse failed: $($file.Name): $parseErrors" }
}
Write-Host "MODEL_RESOURCE_CONTRACT_OK traversal=3 corrupt_hash=1"
