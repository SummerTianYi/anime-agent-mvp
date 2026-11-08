# Read only public health metadata and the launch identity, never chat data.
$ErrorActionPreference = 'Stop'
$live = Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:8765/health/live' -TimeoutSec 4
$h = Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 5
$p = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $live.pid)
$parent = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $p.ParentProcessId)
$avatar = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'Godot%'" | Where-Object { $_.CommandLine -match 'avatar-runtime' })
function Describe($proc) {
    if (!$proc) { return $null }
    [ordered]@{
        pid=$proc.ProcessId; parent=$proc.ParentProcessId; created_utc=$proc.CreationDate.ToUniversalTime().ToString('o')
        executable=[IO.Path]::GetFileName($proc.ExecutablePath)
        production_tree_in_command_or_exe=([string]$proc.CommandLine + [string]$proc.ExecutablePath) -match '2026-08-28[\\/].*?work[\\/]anime-agent-mvp[\\/]'
        candidate_tree_in_command_or_exe=([string]$proc.CommandLine + [string]$proc.ExecutablePath) -match 'tianyi-companion-v12'
        agent_core_entry=[string]$proc.CommandLine -match 'agent_core[.:]main'
        hot_reload_flag=[string]$proc.CommandLine -match '--reload\b'
    }
}
[ordered]@{checked_utc=[datetime]::UtcNow.ToString('o'); service=$live.service; core=(Describe $p); parent=(Describe $parent)
    avatars=@($avatar | ForEach-Object {Describe $_}); attached_avatars=$h.roles.avatar
    reported_provider=$h.llm.provider; reported_runtime=$h.llm.runtime; reported_model=$h.llm.model
    configured=$h.llm.configured; tools=$h.tools; period='read-only health sample, no formal chat'
} | ConvertTo-Json -Depth 5
