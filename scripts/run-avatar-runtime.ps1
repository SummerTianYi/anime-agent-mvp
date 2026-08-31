$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$projectPath = Join-Path $repoRoot "apps\avatar-runtime"
$modelPath = Join-Path $projectPath "assets\luotianyi_v4.glb"
$envPath = Join-Path $repoRoot ".env"

function Get-LocalEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $envPath)) {
        return ""
    }
    $pattern = "^\s*" + [regex]::Escape($Name) + "\s*=\s*(.*)$"
    $line = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match $pattern } |
        Select-Object -Last 1
    if (-not $line) {
        return ""
    }
    $value = [regex]::Match($line, $pattern).Groups[1].Value.Trim()
    return $value.Trim('"').Trim("'")
}

if (-not (Test-Path -LiteralPath $modelPath)) {
    throw "Local avatar model asset not found: $modelPath"
}

if ([string]::IsNullOrWhiteSpace($env:AGENT_CORE_WS_URL)) {
    $corePort = "8765"
    if (Test-Path -LiteralPath $envPath) {
        $portLine = Get-Content -LiteralPath $envPath |
            Where-Object { $_ -match '^\s*AGENT_CORE_PORT\s*=\s*(\d+)\s*$' } |
            Select-Object -Last 1
        if ($portLine -and $portLine -match '^\s*AGENT_CORE_PORT\s*=\s*(\d+)\s*$') {
            $corePort = $Matches[1]
        }
    }
    $env:AGENT_CORE_WS_URL = "ws://127.0.0.1:$corePort/ws"
}

if ([string]::IsNullOrWhiteSpace($env:ANIME_AGENT_MODEL_LOOK)) {
    $configuredModelLook = Get-LocalEnvValue -Name "ANIME_AGENT_MODEL_LOOK"
    if (-not [string]::IsNullOrWhiteSpace($configuredModelLook)) {
        $env:ANIME_AGENT_MODEL_LOOK = $configuredModelLook
    }
}

$godotCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Godot\Godot_v4.7.2-stable_win64.exe"),
    "D:\steam\steamapps\common\Godot\Godot_v4.7.2-stable_win64.exe",
    (Join-Path $repoRoot "..\tools\godot-4.7.2\Godot_v4.7.2-stable_win64.exe")
)
$godotPath = $godotCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $godotPath) {
    throw "Godot 4 was not found. Install Godot 4 or update the candidate paths in this script."
}

$godotArguments = @(
    "--display-driver", "windows",
    "--path", $projectPath,
    "--script", "res://launcher.gd",
    "--position", "80,80",
    "--resolution", "560x760"
)

Start-Process -FilePath $godotPath -ArgumentList $godotArguments -WindowStyle Normal | Out-Null
