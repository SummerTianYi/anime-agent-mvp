# Current development machine locator

This repository is intentionally local-first. The table records project-related artifacts that cannot or should not be uploaded; paths are evidence for Agents working on this same machine, not portable defaults and not redistribution authorization. Verify each path with `Test-Path -LiteralPath` before use, never print `.env` values or download cookies, and use repository-relative/configurable paths in committed code.

| Artifact | Current local path | Policy or purpose |
|---|---|---|
| Repository | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp` | Git working tree |
| Runtime GLB | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\apps\avatar-runtime\assets\luotianyi_v4.glb` | Ignored; required by Godot; 128,621,144 bytes; SHA-256 `DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A` |
| Exported VRM | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\luotianyi_v4_preview.vrm` | Ignored external artifact; byte-identical to runtime GLB |
| Source PMX | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\luotianyi_v4_source\luotianyi_v4_ver2.0.pmx` | Third-party source; do not upload |
| Source archive | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\洛天依V4公式服ver2.0.zip` | Third-party source; do not upload |
| Imported Blend | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\luotianyi_v4_imported.blend` | Intermediate; SHA-256 `1036D8FB521AFB1388B8177E8EC4A1391120441323DC994277DAABF710C28CCD` |
| Prepared Blend | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\luotianyi_v4_prepared.blend` | Intermediate; SHA-256 `886B61339707C289157F7D762A9B44DF26E9CFDFA92BD1D5AC518D7116B7672D` |
| Godot executable | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\tools\godot-4.7.2\Godot_v4.7.2-stable_win64.exe` | Local tool; launcher also checks LocalAppData and Steam |
| Blender executable | `D:\steam\steamapps\common\Blender\blender.exe` | Blender 5.2.1 LTS |
| MMD Tools | `C:\Users\26052\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\blender_org\mmd_tools` | Version 4.5.13 |
| VRM add-on | `C:\Users\26052\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\blender_org\vrm` | Version 4.5.0 |
| Local secrets | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\.env` | Ignored; GLM configured, DeepSeek Key currently empty; never display or commit |
| SQLite | `C:\Users\26052\AppData\Local\AnimeAgent\data\anime-agent.sqlite3` | User conversation/event state; never upload |
| Core logs | `C:\Users\26052\AppData\Local\AnimeAgent\logs` | Local diagnostics; never upload by default |
| Download diagnostics | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\bowlroll-*` | May contain Cookie/header material; do not read, print or upload unless explicitly authorized for acquisition debugging |

The old Blender helper scripts beside the repository used personal absolute paths; parameterized copies are versioned under `scripts/model-pipeline/`, so future work should use those copies and leave the external originals untouched.
