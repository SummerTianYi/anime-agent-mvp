# Local avatar asset contract

This directory intentionally keeps the licensed or third-party character asset outside Git. On the current development machine the runtime asset is `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\apps\avatar-runtime\assets\luotianyi_v4.glb`; it must be named `luotianyi_v4.glb`, is 128,621,144 bytes, and has SHA-256 `DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A`. The file is byte-identical to the locally exported `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\luotianyi_v4_preview.vrm`. Neither file nor its textures may be committed until redistribution rights are explicitly confirmed.

| Runtime expectation | Value |
|---|---|
| Scene path | `res://assets/luotianyi_v4.glb` |
| Skeletons | 1 |
| Cached action bones | 8 |
| Pigtail roots | `MaWei_R_0_1`, `MaWei_L_0_1` |
| Expression slots | 48 |
| Godot | 4.7.2 stable, GL Compatibility renderer |

Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-local-assets.ps1` from the repository root before starting the avatar. A different machine must obtain the source model independently and follow `docs/ASSET_PIPELINE.md`; code-only Core and Tauri work can continue without this asset, but Godot scene loading cannot.
