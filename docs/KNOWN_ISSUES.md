# Known issues and deferred work

| ID | Severity | Current behavior | Required outcome |
|---|---|---|---|
| KI-001 | P0 | STT sometimes reports no valid audio or no clear speech | Add device diagnostics, minimum duration/level feedback and repeatable Mandarin acceptance tests |
| KI-002 | P0 | One-click startup is a developer launcher, not Windows login autostart | Add install/uninstall commands, duplicate prevention, log paths and restart-safe supervision |
| KI-003 | P0 | Startup and Idle events are absent | Add Windows event source, debounce/quiet hours and explicit `IGNORE` result |
| KI-004 | P0 | Motion registry, semantic upper/lower masks and authored idle/pirouette are verified, but thinking/speaking/greeting remain procedural and transitions use simple cross-fades | Complete the small character motion set, then evaluate AnimationTree/state blending and test front/back views, foot contact and hair/body clipping per clip |
| KI-005 | P1 | Both long pigtail chains are fully skinned and classified as upper body, with subtle procedural secondary sway but no collision-aware spring physics | Tune spring-bone/collision behavior after thinking/speaking clips; preserve `MaWei_R_0_1`/`MaWei_L_0_1` and the full 17-bone chains, without changing rear hair |
| KI-006 | P1 | `memory_candidate` is only stored as a pending event | Design review/promotion/deletion and selective prompt injection before claiming long-term memory |
| KI-007 | P1 | Core returns complete responses only | Add streaming/cancellation only if it measurably improves the character experience |
| KI-008 | P1 | Godot and Tauri have separate handwritten event clients | Add protocol versioning/shared schema before broadening the event surface |
| KI-009 | P1 | Python dependencies have ranges but no resolved lock | Add a Windows-tested lock strategy without broad upgrades |
| KI-010 | P1 | Minimal Windows CI covers Core tests and desktop build, but Godot model tests remain local because the asset is excluded | Keep CI green and document local Godot evidence for Avatar changes |
| KI-011 | P2 | TTS is absent | Select a voice path only after STT is stable and licensing/latency are understood |
| KI-012 | P2 | Permission layer, tools and Spark Adapter are placeholders | Keep destructive/external actions disabled until explicit confirmation and audit contracts exist |
| KI-013 | Policy | Repository has no explicit source license and model redistribution rights are unresolved | Do not invent a license or upload model assets; owner must make the legal/publishing decision |
| KI-014 | P0 | Static hand-to-thigh poses and larger full-body motions can visibly penetrate or unnaturally deform the skirt; the former Godot spring/panel/vertex-overlay experiment was removed because overlapping hand/thigh proxies produced mathematically incompatible constraints and local mesh tearing | Solve in the dedicated `SummerTianYi/anime-agent-cloth-physics` repository with a clean cloth architecture; acceptance must cover idle, wave, greet, pirouette, listen, mocap and action transitions without per-action exceptions |

Resolved pitfalls that should remain regression-tested include the Godot input focus guard, localhost proxy bypass in health/bridge checks, GLM Coding endpoint selection, provider-aware startup validation, static song data tracking, configurable Core WebSocket URL, foot-ground correction during BVH retarget, and animation-only rebinding that preserves the accepted Godot materials. Skirt contact is explicitly not resolved.
