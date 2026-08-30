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
| CMU motion source | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\motion-sources\cmu\pirouette.bvh` | Local test source; 763,933 bytes; SHA-256 `BED46806D1C1E03D5165F9BFECADFF0A57409522D5D3096B863484B5AEF15EAA` |
| Retargeted motion Blend | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\motion-output\cmu-pirouette\luotianyi_pirouette.blend` | Ignored intermediate; 48,077,682 bytes; SHA-256 `084DCC4EDD67AFEC4E014035B22237089EA35BEDC2B0544775AD7C80DCC325E3` |
| Runtime motion GLB | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\apps\avatar-runtime\assets\motions\luotianyi_pirouette.glb` | Ignored animation container; 23,114,580 bytes; SHA-256 `1FEFBF0667711845E4FC6E0574D57D74C8982E15AA76A2A25BB9192BE1FAA284` |
| Idle motion Blend | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\motion-output\idle\luotianyi_idle.blend` | Ignored intermediate; 47,613,755 bytes; SHA-256 `3482B6E084FEE018793B8F5EA109618439CF48F67B32540CEC1FE6B4A12C8040` |
| Idle runtime GLB | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\apps\avatar-runtime\assets\motions\luotianyi_idle.glb` | Ignored animation container; 23,057,704 bytes; SHA-256 `33E3FE13721F0D01929C6CB4AF22A408C3485F20512066975ED102DC693CC21B` |
| Godot executable | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\tools\godot-4.7.2\Godot_v4.7.2-stable_win64.exe` | Local tool; launcher also checks LocalAppData and Steam |
| Blender executable | `D:\steam\steamapps\common\Blender\blender.exe` | Blender 5.2.1 LTS |
| MMD Tools | `C:\Users\26052\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\blender_org\mmd_tools` | Version 4.5.13 |
| VRM add-on | `C:\Users\26052\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\blender_org\vrm` | Version 4.5.0 |
| Video reference decoder | Not installed in PATH or the Agent Core venv (`ffmpeg`, `ffprobe`, OpenCV, ImageIO and MoviePy absent) | Users may provide the original video; install/use a local decoder to extract frames automatically rather than asking them to split it manually |
| Local secrets | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\.env` | Ignored; GLM configured, DeepSeek Key currently empty; never display or commit |
| SQLite | `C:\Users\26052\AppData\Local\AnimeAgent\data\anime-agent.sqlite3` | User conversation/event state; never upload |
| Core logs | `C:\Users\26052\AppData\Local\AnimeAgent\logs` | Local diagnostics; never upload by default |
| Download diagnostics | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\bowlroll-*` | May contain Cookie/header material; do not read, print or upload unless explicitly authorized for acquisition debugging |

The old Blender helper scripts beside the repository used personal absolute paths; parameterized copies are versioned under `scripts/model-pipeline/`, so future work should use those copies and leave the external originals untouched. Motion build details, controls and current limitations are in `docs/MOTION_PIPELINE.md`.
