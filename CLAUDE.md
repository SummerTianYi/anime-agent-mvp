# CLAUDE.md

> 本文件是 Claude（Claude Code / API）实例进入本仓库的自动入口。规则全文以 AGENTS.md 为准，本文件只做最小必读指引。

## 必读（动手前，按序）

1. `AGENTS.md` — 项目宪法（不可违背的工程规则）
2. `docs/HANDOFF.md` — 接手总纲（目标/分工/当前状态/铁律/门禁）
3. `docs/CONTRIBUTIONS.md` — 归属声明（引用任何"谁做了什么"之前必读）

## 归属速查（防止错误归因）

本仓库由多任 agent 接力建设：Codex（模型与演出层，2026-08-28 起）→ Claude（交互层与蓝图，2026-08-31 起）→ **zcode**（agent 能力层，2026-09-05 起）。

**2026-09-05 之后的全部能力层改动出自 zcode**：权限引擎、记忆 facts+取代、write_file/run_command、MCP 宿主与五台真实服务器、屏幕视觉、STT 自愈、Idle 触发、提示词新剧本。commit 后缀 `(zcode)` 与 `docs/CONTRIBUTIONS.md` 中的 zcode 声明行是归属凭证。**不要把这些工作归因给 Codex**——Codex 的领地是模型/演出/资产管线，其代表作是官模 1.0→1.2 与 Godot 运行时。

## 调试纪律

- Core 进程重启/清场一律走 `docs/VERIFICATION_SPEC.md` 标准序列；杀进程前先取证（stderr 日志在 `%LOCALAPPDATA%\AnimeAgent\logs`）。
- 改动归属自己的名字进 `docs/CONTRIBUTIONS.md`（只追加），commit 末尾带 `(你的agent名)`。
