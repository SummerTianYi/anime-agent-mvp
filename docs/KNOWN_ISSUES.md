# Known issues and deferred work

状态口径：以 [`HANDOFF.md`](HANDOFF.md) §3 为准。已解决的问题移入文末"已解决台账"，不做静默删除。

## 未决

| ID | Severity | Current behavior | Required outcome |
|---|---|---|---|
| KI-001 | P1 | STT wedge self-heal shipped 2026-09-07 (digital-zero detection, one automatic device reopen, actionable error, per-recording level logging); the Realtek wedge's real-world recurrence still needs one confirmed natural occurrence to prove the recovery path end to end | Repeatable Mandarin acceptance + one real wedge survived by the self-heal |
| KI-002 | P0 | One-click startup is a developer launcher, not Windows login autostart | Add install/uninstall commands, duplicate prevention, log paths and restart-safe supervision |
| KI-004 | P0 | Motion registry, semantic upper/lower masks and authored idle/pirouette are verified, but thinking/speaking/greeting remain procedural and transitions use simple cross-fades | Complete the small character motion set, then evaluate AnimationTree/state blending and test front/back views, foot contact and hair/body clipping per clip |
| KI-005 | P1 | Both long pigtail chains are fully skinned and classified as upper body, with subtle procedural secondary sway but no collision-aware spring physics | Tune spring-bone/collision behavior after thinking/speaking clips; preserve `MaWei_R_0_1`/`MaWei_L_0_1` and the full 17-bone chains, without changing rear hair |
| KI-007 | P1 | Core returns complete responses only | Add streaming/cancellation only if it measurably improves the character experience |
| KI-008 | P1 | Godot and Tauri have separate handwritten event clients | Add protocol versioning/shared schema before broadening the event surface |
| KI-009 | P1 | Python dependencies have ranges but no resolved lock | Add a Windows-tested lock strategy without broad upgrades |
| KI-010 | P1 | Minimal Windows CI covers Core tests and desktop build, but Godot model tests remain local because the asset is excluded | Keep CI green and document local Godot evidence for Avatar changes |
| KI-013 | Policy | Repository has no explicit source license and model redistribution rights are unresolved | Do not invent a license or upload model assets; owner must make the legal/publishing decision |
| KI-014 | P0 | Static hand-to-thigh poses and larger full-body motions can visibly penetrate or unnaturally deform the skirt; the former Godot spring/panel/vertex-overlay experiment was removed because overlapping hand/thigh proxies produced mathematically incompatible constraints and local mesh tearing | Solve in the dedicated `SummerTianYi/anime-agent-cloth-physics` repository with a clean cloth architecture; acceptance must cover idle, wave, greet, pirouette, listen, mocap and action transitions without per-action exceptions |
| KI-016 | P2 | Non-preference pending facts are now injected tagged （待确认） (sensitive ones stay hidden), and explicit "记住" promotes to confirmed, but there is no review/edit/duplicate-merge UI | Review/promote/delete surface for pending facts before claiming mature long-term memory |
| KI-017 | P2 | Sandbox exams (T0-T3, C, D) are one-shot scripts in `anime-agent-workbench`, not an automated regression suite | Convert the exam bank into a re-runnable regression pipeline so capability changes can be re-certified cheaply |
| KI-019 | P0 | Core dies silently when PortAudio (`libportaudio64bit.dll`) faults natively inside the persistent wake-word mic stream — WER APPCRASH `0xC0000005` on pid 4840 at 2026-09-09 22:40 (no Python traceback possible); reboots/hibernation produce the same "avatar alive, Core gone" state. Mitigated 2026-09-09: `scripts/core_watchdog.ps1` (auto-started by `start-mvp.ps1`) revives Core while the avatar is on the desktop — two-strike health confirm, 90s warmup guard, manages any python running `agent_core.main`, zero GLM calls (revival greeting is a fixed template line) — and logs exit-code forensics to `%LOCALAPPDATA%\AnimeAgent\logs\core-watchdog.log`; live-tested kill→revive twice (23.4s / 20.7s to healthy) | Catch the actual crash trigger via the watchdog's exit-code history; structural fix = move the audio listener into an isolated child process so a native fault kills only the listener, not Core |

## 已解决台账（保留防回归意识）

| ID | 原问题 | 解决凭证 |
|---|---|---|
| KI-006（2026-09-06） | `memory_candidate` 仅存为挂起事件 | facts 表迁移 + 分级落库（偏好自动确认）+ `memory_retrieval` 词法注入；剩余审阅 UI 拆为 KI-016 |
| KI-011（2026-09-01/06） | TTS 缺失 | Claude E 期 sidecar 客户端 + 真实声线上线；工作解说由 zcode 扩展为每工具类型播报 |
| KI-012（2026-09-06） | 权限层/工具为占位符 | allow/ask/deny 引擎 + write_file/run_command/look_at_screen + MCP 宿主（T0-T3/C/D 考试凭证）；剩余仅 Spark Adapter |
| KI-018（2026-09-07） | MCP 宿主仅验证过随仓测试 server | 五台真实服务器接入并验收（Playwright 浏览器 24 / GitHub 44 / Tavily 5 / Gmail 19 / Drive 1），进程生命周期、大 schema（行上限 1MB）、Windows spawn、工具名绑定授权均经真机考验 |
| KI-003（2026-09-07） | Idle 触发缺失 | GetLastInputInfo 本地轮询（30s）+ IdlePolicy（阈值/免打扰/冷却，纯逻辑离线测试）+ 本地台词库；全程零 GLM 调用（待机零额度门禁） |
| KI-015（2026-09-07） | 视觉模型未配置 | GLM-5.3-Flash 原生多模态，coding 端点实测收图；`.env` 仅需 `ANIME_AGENT_VISION_MODEL`；隐私 ask 档全链路真机通过（附带修复确认流 15s 超时 bug） |

Resolved pitfalls that should remain regression-tested include the Godot input focus guard, localhost proxy bypass in health/bridge checks, GLM Coding endpoint selection, provider-aware startup validation, static song data tracking, configurable Core WebSocket URL, foot-ground correction during BVH retarget, and animation-only rebinding that preserves the accepted Godot materials. Skirt contact is explicitly not resolved.
