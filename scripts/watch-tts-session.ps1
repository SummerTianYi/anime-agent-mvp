$ErrorActionPreference = "SilentlyContinue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$avatarRoot = Join-Path $repoRoot "apps\avatar-runtime"
$ttsPort = 8770
$appearTimeoutSec = 180
$logFile = Join-Path $env:LOCALAPPDATA "AnimeAgent\logs\tts-watch.log"

function Write-WatchLog {
    param([string]$Message)
    New-Item -ItemType Directory -Path (Split-Path $logFile) -Force | Out-Null
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message" | Out-File -FilePath $logFile -Append -Encoding utf8
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

function Stop-TtsSidecar {
    $conn = Get-NetTCPConnection -LocalPort $ttsPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-WatchLog "sidecar (pid $($conn.OwningProcess)) stopped; VRAM freed"
    }
    else {
        Write-WatchLog "no sidecar listener on port $ttsPort; nothing to stop"
    }
}

# Phase 1: wait for her window to appear (start failures still reclaim VRAM).
Write-WatchLog "watcher started; waiting for avatar (up to ${appearTimeoutSec}s)"
$appeared = $false
for ($i = 0; $i -lt ($appearTimeoutSec / 5); $i++) {
    $avatar = Get-AvatarProcess
    if ($avatar) { $appeared = $true; break }
    Start-Sleep -Seconds 5
}
if (-not $appeared) {
    Write-WatchLog "avatar never appeared; stopping sidecar"
    Stop-TtsSidecar
    exit 0
}
Write-WatchLog "avatar detected (pid $($avatar.ProcessId)); holding sidecar"

# Phase 2: hold the voice ready for as long as she is on screen.
while (Get-AvatarProcess) {
    Start-Sleep -Seconds 5
}

# Phase 3: she closed. Free the VRAM.
Write-WatchLog "avatar closed; stopping sidecar"
Stop-TtsSidecar
