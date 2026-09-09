[CmdletBinding()]
param(
    [switch]$SkipAvatar
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Net.Http

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$coreRoot = Join-Path $repoRoot "services\agent-core"
$pythonPath = Join-Path $coreRoot ".venv\Scripts\python.exe"
$envPath = Join-Path $repoRoot ".env"
$avatarLauncher = Join-Path $PSScriptRoot "run-avatar-runtime.ps1"
$avatarRoot = Join-Path $repoRoot "apps\avatar-runtime"
$logRoot = Join-Path $env:LOCALAPPDATA "AnimeAgent\logs"

function Get-LocalEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path -LiteralPath $envPath)) {
        return $DefaultValue
    }

    $pattern = "^\s*" + [regex]::Escape($Name) + "\s*=\s*(.*)$"
    $line = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match $pattern } |
        Select-Object -Last 1
    if (-not $line) {
        return $DefaultValue
    }

    $value = [regex]::Match($line, $pattern).Groups[1].Value.Trim()
    return $value.Trim('"').Trim("'")
}

function Test-AgentCoreHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Uri
    )

    $handler = New-Object System.Net.Http.HttpClientHandler
    $handler.UseProxy = $false
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(2)
    try {
        $response = $client.GetAsync($Uri).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            return $false
        }
        $content = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $payload = $content | ConvertFrom-Json
        return $payload.status -eq "ok" -and $payload.service -eq "anime-agent-core"
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
        $handler.Dispose()
    }
}

function Get-AvatarProcess {
    $escapedRoot = [regex]::Escape($avatarRoot)
    return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "Godot*" -and
            $_.CommandLine -match $escapedRoot
        } |
        Select-Object -First 1
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Agent Core Python environment was not found: $pythonPath"
}
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Project .env file was not found: $envPath"
}

$providerName = (Get-LocalEnvValue -Name "LLM_PROVIDER" -DefaultValue "glm").ToLowerInvariant()
switch ($providerName) {
    "glm" {
        $apiKey = Get-LocalEnvValue -Name "GLM_API_KEY"
        if ([string]::IsNullOrWhiteSpace($apiKey)) {
            throw "GLM_API_KEY is empty in $envPath"
        }
        $baseUrl = Get-LocalEnvValue -Name "GLM_BASE_URL"
        if ($baseUrl -notmatch "/api/coding/paas/v4/?$") {
            throw "GLM_BASE_URL must use the Coding endpoint ending in /api/coding/paas/v4"
        }
    }
    "deepseek" {
        $apiKey = Get-LocalEnvValue -Name "DEEPSEEK_API_KEY"
        if ([string]::IsNullOrWhiteSpace($apiKey)) {
            throw "DEEPSEEK_API_KEY is empty in $envPath"
        }
        $baseUrl = Get-LocalEnvValue -Name "DEEPSEEK_BASE_URL"
        if ([string]::IsNullOrWhiteSpace($baseUrl)) {
            throw "DEEPSEEK_BASE_URL is empty in $envPath"
        }
    }
    "mock" { }
    default {
        throw "Unsupported LLM_PROVIDER in ${envPath}: $providerName"
    }
}

$portText = Get-LocalEnvValue -Name "AGENT_CORE_PORT" -DefaultValue "8765"
$corePort = 0
if (-not [int]::TryParse($portText, [ref]$corePort) -or $corePort -lt 1 -or $corePort -gt 65535) {
    throw "AGENT_CORE_PORT is invalid: $portText"
}

$healthUri = "http://127.0.0.1:$corePort/health"
$env:AGENT_CORE_WS_URL = "ws://127.0.0.1:$corePort/ws"
$coreStarted = $false

if (Test-AgentCoreHealth -Uri $healthUri) {
    Write-Host "[Anime Agent] Core is already online on port $corePort."
}
else {
    $listener = Get-NetTCPConnection -LocalPort $corePort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        $ownerName = if ($owner) { $owner.ProcessName } else { "unknown" }
        throw "Port $corePort is occupied by PID $($listener.OwningProcess) ($ownerName), but it is not a healthy Anime Agent Core."
    }

    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    $stdoutLog = Join-Path $logRoot "core.stdout.log"
    $stderrLog = Join-Path $logRoot "core.stderr.log"
    $coreProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("-m", "agent_core.main") `
        -WorkingDirectory $coreRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
    $coreStarted = $true

    $healthy = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($coreProcess.HasExited) {
            throw "Agent Core exited during startup. Check $stderrLog"
        }
        if (Test-AgentCoreHealth -Uri $healthUri) {
            $healthy = $true
            break
        }
    }

    if (-not $healthy) {
        Stop-Process -Id $coreProcess.Id -Force -ErrorAction SilentlyContinue
        throw "Agent Core did not become healthy within 15 seconds. Check $stderrLog"
    }
    Write-Host "[Anime Agent] Core started in the background (PID $($coreProcess.Id))."
}

# Core keepalive watchdog (KI-019): PortAudio native crashes / reboots kill Core
# silently while the avatar keeps retrying the bridge forever. While Tianyi is
# on the desktop, the watchdog revives Core and records exit-code forensics.
# The script holds a mutex, so a duplicate spawn here is a harmless no-op.
$watchdogScript = Join-Path $PSScriptRoot "core_watchdog.ps1"
if (Test-Path -LiteralPath $watchdogScript) {
    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $watchdogScript) `
        -WindowStyle Hidden | Out-Null
    Write-Host "[Anime Agent] Core watchdog is on duty (revives Core while the avatar is on the desktop)."
}

if ($SkipAvatar) {
    Write-Host "[Anime Agent] Core verification completed; avatar launch skipped."
    exit 0
}

$avatarProcess = Get-AvatarProcess
if ($avatarProcess) {
    Write-Host "[Anime Agent] Avatar is already running (PID $($avatarProcess.ProcessId))."
}
else {
    if (-not (Test-Path -LiteralPath $avatarLauncher)) {
        throw "Avatar launcher was not found: $avatarLauncher"
    }

    & $avatarLauncher
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        $avatarProcess = Get-AvatarProcess
        if ($avatarProcess) {
            break
        }
    }
    if (-not $avatarProcess) {
        throw "Godot avatar did not start within 10 seconds."
    }
    Write-Host "[Anime Agent] Avatar started (PID $($avatarProcess.ProcessId))."
}

Write-Host "[Anime Agent] Ready. You can close this launcher window."
