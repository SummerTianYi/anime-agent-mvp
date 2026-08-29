$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$coreRoot = Join-Path $repoRoot "services\agent-core"
$pythonPath = Join-Path $coreRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Agent Core virtual environment not found: $pythonPath"
}

Set-Location -LiteralPath $coreRoot
& $pythonPath -m agent_core.main
