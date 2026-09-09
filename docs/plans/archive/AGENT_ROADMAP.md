> 历史快照：Codex 于 2026-09-10 整合前保留。以下状态仅代表原文时点，当前有效方案统一见 [项目长远方案手册](../README.md)。原作者与历史结论保留；仅修正迁移后的相对链接。

# 天依 Agent 化路线

声明：本方案由 Claude（Claude Code / Fable 5）起草于 2026-08-31，归入 `docs/plans/` 目录；同目录 [MODEL_OPTIMIZATION.md](MODEL_OPTIMIZATION.md) 是 Codex 负责的建模优化方向，[LONG_TERM.md](LONG_TERM.md) 是后续建立的跨仓长期方案看板。

**执行状态（2026-09-07，zcode 回写）：本蓝图已基本执行完毕**——A/B/E/C 期完成，D 期收官（视觉+主动触发全线：问候+Idle 上线），键鼠按设计缓行。逐期凭证与"蓝图期号 ↔ workbench 任务包 ↔ 考试编号"对照见 [`HANDOFF.md`](../../HANDOFF.md) §4；全期考核复盘见 [`../TEST_REPORT_2026-09-06.md`](../../TEST_REPORT_2026-09-06.md)。本文保留原始蓝图、约束与验收口径。

## 约束与基线

- 角色优先：一切 agent 能力必须经 Core 的角色 Harness 收口输出；Godot 只做演出层与确认 UI，不直接执行系统操作。
- 本地优先：工具执行、MCP server、桌面控制全部在本地进程内完成，不引入云端 agent 托管服务，桌面数据不出机器。
- 权限先行：只读工具先行；任何写入型或外部作用工具合入前，确认 UI 与审计日志必须已验收。
- 不破坏既有基线：聊天、会话、唤醒词、STT、动作与画布门禁保持通过；GLM 配额受限时用 Mock/DeepSeek 验证回路，不阻塞开发。
- 有限循环：agent 循环必须带最大步数、单工具超时与失败兜底，超限时给出角色化收尾而不是卡死。

## 当前基线

| 组件 | 现状 | 在 agent 化中的位置 |
|---|---|---|
| 聊天循环 | `chat.message` → Provider 单发 → `chat.response` | 已改造为工具调用循环的宿主（A 期） |
| 角色 Harness | 严格 JSON 契约（reply/emotion/gesture）与安全兜底 | 循环每一轮的提示约束与最终收口契约；2026-09-05 起启用训练版新剧本 |
| 唤醒词 | "天依" KWS + whisper 两阶段确认，绝对优先 | agent 的免持语音入口 |
| 会话与事件 | SQLite sessions/messages/events（+ facts） | 工具调用审计落在 events 表 |
| 语音 | faster-whisper STT 已通；TTS sidecar 已上线（GPT-SoVITS 真实声线） | 工作解说（E 期）已落地；Realtek 假死自愈待加固 |

## 后续方向与优先级（附执行状态）

| 优先级 | 方向 | 方案 | 预期收益 | 风险与验收 | 状态（2026-09-07） |
|---|---|---|---|---|---|
| P0 | 工具调用循环（A 期·大脑） | Provider 请求加入 tools，解析 tool_calls；Core 新增循环执行器（执行→结果回填→再调用），带步数上限；过程以 working 状态与中间解说事件广播 | 从一问一答升级为能多步做事 | Mock Provider 离线单测覆盖循环分支；真实 Provider 手动验收 | ✅ Claude 实现（`fc5a5a4`） |
| P0 | 只读工具集 | get_time、screenshot、read_file、list_dir、active_window、clipboard_read，统一 schema 注册表 | 零风险打通全链路 | 全部只读、路径白名单、注册表单测 | ✅ Claude 实现；zcode T0 考试 6/6 |
| P0 | 权限层（B 期前置） | `permission.request` 协议事件；Godot 确认卡片做角色化确认；allowlist/ask/deny 三档策略；每次决策落审计 | 高危能力的闸门，也是角色演出机会 | 拒绝路径有测试；确认不阻塞其余事件流 | ✅ zcode：三档引擎 + 会话内文字确认流（未做 Godot 确认卡片）+ `permission.decision` 审计 |
| P1 | 写入型工具（B 期·双手） | write_file、open_app、run_command（约束与配额）、键鼠控制（确认后单步执行） | 真正接管电脑 | 权限层未验收不合入；键鼠默认 ask | ⚠️ write_file（T1 放权）/run_command（T3）已上线；open_app 未做；键鼠缓行 |
| P1 | MCP 宿主（C 期·生态） | Core 以 stdio 拉起并管理 MCP server，list_tools 合并进统一注册表 | 社区工具即插即用 | 先接 filesystem 一个 server 验证；进程生命周期与工具名冲突策略另定 | ✅ 收官（2026-09-07）：stdio 宿主 + 真实服务器上线——Playwright 浏览器（24）+ 官方 GitHub（44）+ Tavily 搜索（5）+ Gmail（19）+ Drive（1） |
| P1 | TTS 工作解说（E 期·声线） | 与 GPT-SoVITS 声线项目会合，中间步骤语音播报 | 灵魂层：干活时开口说话 | 依赖声线素材到位；打断策略单独验收 | ✅ Claude sidecar 链路 + zcode 每工具类型播报；声线资产归 anime-agent-tts 仓 |
| P2 | 屏幕视觉（D 期·感官） | 截图送多模态 Provider 或本地 VLM（8GB VRAM 约束内选型） | 看得见屏幕才能操作 GUI | 本地 VLM 选型另行验证；多模态调用计费另计 | ✅ 2026-09-07 上线：GLM-5.3-Flash 原生多模态（coding 端点实测收图），隐私 ask 档全链路真机通过；本地 VLM 仅作隐私/断网备胎（LONG_TERM） |
| P2 | 主动触发（D 期） | 启动/空闲触发 + IGNORE + 免打扰时段（承接 HANDOFF 既有条目） | 有"活着"的感觉 | 去抖与静音时段生效，防骚扰 | ✅ 收官（2026-09-07）：启动问候 + Idle 触发全部上线（本地轮询+台词库，待机零 GLM 调用） |

## 明确不采用

| 操作 | 原因 |
|---|---|
| Godot 侧直接执行系统命令或键鼠控制 | 系统操作必须收口在 Core；Godot 只负责演出、确认 UI 与事件呈现 |
| 无确认的静默写入、删除或网络外发 | 高危动作一律 ask 或拒绝；审计先行，拒绝可回放 |
| 引入云端 agent 托管（Computer Use 云服务等） | 与本地优先和隐私边界冲突 |
| 在角色 Harness 之外开"裸 LLM"旁路执行通道 | 绕开人设契约与权限层，属架构回归 |
| 语音唤醒直接触发高危工具 | 唤醒只负责开启对话；高危确认必须经文本/UI 双通道 |

## 每期验收门禁

| 门禁 | 通过条件 |
|---|---|
| 单元测试 | 循环执行器、工具注册表、权限策略决策表有单测；Mock Provider 全离线可跑 |
| 协议回归 | 既有 chat/session/wake/voice 事件全部保持；新增事件写入 `docs/AVATAR_BRIDGE.md` |
| 权限审计 | 每次 ask/deny/allow 在 events 表可查；拒绝路径可回放 |
| 有限循环 | 步数上限与单工具超时生效，超限有角色化收尾台词 |
| 手动验收 | 每期给出 3 个可复现场景（如"现在几点""看看屏幕上是什么""把这段话追加到文件里"） |
| 能力放权（2026-09-06 起新增） | 高危能力先在 anime-agent-workbench 沙箱通过对应考试（T 系编号见 HANDOFF §4），经所有者授权后才接入真实权限 |

## 风险与已知难点

- GLM function calling 稳定性弱于 Claude：schema 严格化、解析失败重试、最终兜底为"不调用工具直接回答"。
- 工具结果膨胀上下文：循环执行器内做结果截断与摘要，不把原始输出全量回填。
- 键鼠控制是最高危面：权限层验收前不合入任何键鼠工具代码。
- 唤醒词与 agent 能力叠加放大误触后果：两阶段确认已前置缓解，另要求高危确认走文本/UI 双通道。

## 与其他方向的关系

- [MODEL_OPTIMIZATION.md](MODEL_OPTIMIZATION.md)（Codex，建模优化）：无直接依赖；其"表情与口型细化""马尾/衣摆二级运动"条目会反哺 agent 演出层。
- TTS 声线项目（anime-agent-tts 私仓，GPT-SoVITS v2Pro）：E 期依赖已落地；后续声线迭代见 [LONG_TERM.md](LONG_TERM.md)。
- `docs/HANDOFF.md` 中 P2"Permission layer and tools"已由本方案执行完毕；P0"Startup and Idle triggers"对应 D 期，已收官（启动问候 + Idle 触发均已上线）。
