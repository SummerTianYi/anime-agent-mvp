$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$workRoot = Split-Path $repoRoot -Parent
$ttsBat = Join-Path $workRoot "tianyi-tts\scripts\tts_autostart.bat"
$watcher = Join-Path $PSScriptRoot "watch-tts-session.ps1"
$startMvp = Join-Path $PSScriptRoot "start-mvp.ps1"

function Get-PortFromEnv {
    $envPath = Join-Path $repoRoot ".env"
    if (-not (Test-Path -LiteralPath $envPath)) { return 8765 }
    $line = Get-Content -LiteralPath $envPath |
        Where-Object { $_ -match '^\s*AGENT_CORE_PORT\s*=\s*(\d+)\s*$' } |
        Select-Object -Last 1
    if ($line) { return [int]$Matches[1] }
    return 8765
}

# 0) Kill stale watchers from previous sessions first: an old watcher that
#    sees its avatar vanish must never murder the NEW session's sidecar.
Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'watch-tts-session\.ps1' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# 1) TTS sidecar: hidden, detached, guarded (no-op if already on 8770)
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $ttsBat -WindowStyle Hidden

# 2) Session watcher (detached): frees the sidecar's VRAM when her window closes.
Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $watcher
) -WindowStyle Hidden

# 3) Core + avatar: detached hidden run of the existing launcher.
Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $startMvp
) -WindowStyle Hidden

# 4) Poll and report; this wrapper exits as soon as the session is confirmed up.
$corePort = Get-PortFromEnv
$healthUri = "http://127.0.0.1:$corePort/health"
$coreOk = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $h = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2
        if ($h.status -eq "ok" -and $h.service -eq "anime-agent-core") { $coreOk = $true; break }
    }
    catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $coreOk) {
    throw "Agent Core did not come online within 30s. Check $env:LOCALAPPDATA\AnimeAgent\logs."
}

$avatarOk = $false
for ($i = 0; $i -lt 40; $i++) {
    $escapedRoot = [regex]::Escape((Join-Path $repoRoot "apps\avatar-runtime"))
    $avatar = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "Godot*" -and $_.CommandLine -match $escapedRoot } |
        Select-Object -First 1
    if ($avatar) { $avatarOk = $true; break }
    Start-Sleep -Milliseconds 500
}

if ($avatarOk) {
    Write-Host "[Tianyi] Core online, avatar on screen, voice warming up (~1 min)."
    Write-Host "[Tianyi] Chat works right away; voice joins when the sidecar is hot."
    Write-Host "[Tianyi] Closing her window will free the voice VRAM automatically."
}
else {
    throw "Core is online but the avatar window did not appear within 20s."
}
