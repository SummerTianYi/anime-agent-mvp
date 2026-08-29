# Known issues and deferred work

| ID | Severity | Current behavior | Required outcome |
|---|---|---|---|
| KI-001 | P0 | STT sometimes reports no valid audio or no clear speech | Add device diagnostics, minimum duration/level feedback and repeatable Mandarin acceptance tests |
| KI-002 | P0 | One-click startup is a developer launcher, not Windows login autostart | Add install/uninstall commands, duplicate prevention, log paths and restart-safe supervision |
| KI-003 | P0 | Startup and Idle events are absent | Add Windows event source, debounce/quiet hours and explicit `IGNORE` result |
| KI-004 | P1 | Model action poses are procedural and visually rough | Tune or replace actions one by one; test front/back views and hair/body clipping |
| KI-005 | P1 | Long pigtail offsets are runtime bone rotations without collision physics | Preserve `MaWei_R_0_1`/`MaWei_L_0_1` distinction and validate natural front drape before changing rear hair |
| KI-006 | P1 | `memory_candidate` is only stored as a pending event | Design review/promotion/deletion and selective prompt injection before claiming long-term memory |
| KI-007 | P1 | Core returns complete responses only | Add streaming/cancellation only if it measurably improves the character experience |
| KI-008 | P1 | Godot and Tauri have separate handwritten event clients | Add protocol versioning/shared schema before broadening the event surface |
| KI-009 | P1 | Python dependencies have ranges but no resolved lock | Add a Windows-tested lock strategy without broad upgrades |
| KI-010 | P1 | Minimal Windows CI covers Core tests and desktop build, but Godot model tests remain local because the asset is excluded | Keep CI green and document local Godot evidence for Avatar changes |
| KI-011 | P2 | TTS is absent | Select a voice path only after STT is stable and licensing/latency are understood |
| KI-012 | P2 | Permission layer, tools and Spark Adapter are placeholders | Keep destructive/external actions disabled until explicit confirmation and audit contracts exist |
| KI-013 | Policy | Repository has no explicit source license and model redistribution rights are unresolved | Do not invent a license or upload model assets; owner must make the legal/publishing decision |

Resolved pitfalls that should remain regression-tested include the Godot input focus guard, localhost proxy bypass in health/bridge checks, GLM Coding endpoint selection, provider-aware startup validation, static song data tracking and configurable Core WebSocket URL.
