# Known issues and deferred work

状态口径：以 [`HANDOFF.md`](HANDOFF.md) §3 为准。已解决的问题移入文末"已解决台账"，不做静默删除。

## 未决

| ID | Severity | Current behavior | Required outcome |
|---|---|---|---|
| KI-001 | P0 | STT sometimes reports no valid audio or no clear speech | Add device diagnostics, minimum duration/level feedback and repeatable Mandarin acceptance tests |
| KI-002 | P0 | One-click startup is a developer launcher, not Windows login autostart | Add install/uninstall commands, duplicate prevention, log paths and restart-safe supervision |
| KI-003 | P0 | Idle trigger and a general Windows event source are absent (startup greeting already shipped with quiet hours + cooldown) | Idle events reach Core, may yield a useful action or explicit `IGNORE`, obeying debounce/quiet hours |
| KI-004 | P0 | Motion registry, semantic upper/lower masks and authored idle/pirouette are verified, but thinking/speaking/greeting remain procedural and transitions use simple cross-fades | Complete the small character motion set, then evaluate AnimationTree/state blending and test front/back views, foot contact and hair/body clipping per clip |
| KI-005 | P1 | Both long pigtail chains are fully skinned and classified as upper body, with subtle procedural secondary sway but no collision-aware spring physics | Tune spring-bone/collision behavior after thinking/speaking clips; preserve `MaWei_R_0_1`/`MaWei_L_0_1` and the full 17-bone chains, without changing rear hair |
| KI-007 | P1 | Core returns complete responses only | Add streaming/cancellation only if it measurably improves the character experience |
| KI-008 | P1 | Godot and Tauri have separate handwritten event clients | Add protocol versioning/shared schema before broadening the event surface |
| KI-009 | P1 | Python dependencies have ranges but no resolved lock | Add a Windows-tested lock strategy without broad upgrades |
| KI-010 | P1 | Minimal Windows CI covers Core tests and desktop build, but Godot model tests remain local because the asset is excluded | Keep CI green and document local Godot evidence for Avatar changes |
| KI-013 | Policy | Repository has no explicit source license and model redistribution rights are unresolved | Do not invent a license or upload model assets; owner must make the legal/publishing decision |
| KI-014 | P0 | Static hand-to-thigh poses and larger full-body motions can visibly penetrate or unnaturally deform the skirt; the former Godot spring/panel/vertex-overlay experiment was removed because overlapping hand/thigh proxies produced mathematically incompatible constraints and local mesh tearing | Solve in the dedicated `SummerTianYi/anime-agent-cloth-physics` repository with a clean cloth architecture; acceptance must cover idle, wave, greet, pirouette, listen, mocap and action transitions without per-action exceptions |
| KI-015 | P2 | `look_at_screen` pipeline is ready but no vision model is configured, so it always degrades to a stated boundary | Configure `ANIME_AGENT_VISION_*` (local VLM or multimodal provider within 8GB VRAM budget); acceptance = real screen description with privacy ask-gate |
| KI-016 | P2 | Non-preference `memory_candidate` rows are stored pending but have no review/edit UI | Review/promote/delete surface for pending facts before claiming mature long-term memory |
| KI-017 | P2 | Sandbox exams (T0-T3, C, D) are one-shot scripts in `anime-agent-workbench`, not an automated regression suite | Convert the exam bank into a re-runnable regression pipeline so capability changes can be re-certified cheaply |
| KI-018 | P2 | MCP host is verified against the bundled minimal test server only | Integrate and accept one real third-party MCP server (process lifecycle, tool-name conflicts, error surfaces) |

## 已解决台账（保留防回归意识）

| ID | 原问题 | 解决凭证 |
|---|---|---|
| KI-006（2026-09-06） | `memory_candidate` 仅存为挂起事件 | facts 表迁移 + 分级落库（偏好自动确认）+ `memory_retrieval` 词法注入；剩余审阅 UI 拆为 KI-016 |
| KI-011（2026-09-01/06） | TTS 缺失 | Claude E 期 sidecar 客户端 + 真实声线上线；工作解说由 zcode 扩展为每工具类型播报 |
| KI-012（2026-09-06） | 权限层/工具为占位符 | allow/ask/deny 引擎 + write_file/run_command/look_at_screen + MCP 宿主（T0-T3/C/D 考试凭证）；剩余仅 Spark Adapter |

Resolved pitfalls that should remain regression-tested include the Godot input focus guard, localhost proxy bypass in health/bridge checks, GLM Coding endpoint selection, provider-aware startup validation, static song data tracking, configurable Core WebSocket URL, foot-ground correction during BVH retarget, and animation-only rebinding that preserves the accepted Godot materials. Skirt contact is explicitly not resolved.
