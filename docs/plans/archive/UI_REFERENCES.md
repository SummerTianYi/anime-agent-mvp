> 历史快照：Codex 于 2026-09-10 整合前保留。以下状态仅代表原文时点，当前有效方案统一见 [项目长远方案手册](../README.md)。原作者与历史结论保留；仅修正迁移后的相对链接。

# 前端 UI 参考调研与 U0 现状测绘（UI References & Survey）

声明：zcode 起草于 2026-09-08 至 09-09，服务 [`UI_UPGRADE.md`](UI_UPGRADE.md) 的 U0 期（现状测绘 + 形态决策输入）。**本文为零 GLM 配额产出**（网页检索 + 本地读码，未消耗天依 key）。形态决策 A/B/C 仍待所有者拍板，本文只提供决策输入，不做决定。接手 agent 动 UI 前先读 [`HANDOFF.md`](../../HANDOFF.md) 总纲与 [`UI_UPGRADE.md`](UI_UPGRADE.md) §5 边界红线。

## 1. TL;DR（给赶时间的决策者）

- 三路调研共 18 个开源项目：通用聊天客户端 7 家、agent 工作台 5 家、VTuber/桌宠 6 家（报告见 §3/§4/§5）。
- **"输入框旁的思考强度快捷控件"是开源圈的普遍洼地**：7 家聊天客户端全都把 reasoning effort 藏在设置深处，"放进 composer 旁"在每家都是未实现的 Feature Request。ChatGPT 官方做了（本调研的触发截图），开源没人做好——我们直接做对就是差异化亮点。
- **思考强度控件选"档位弹窗"不选裸滑杆**：档位（关闭/快速/标准/深度）是开源验证过的主流形态；token 预算滑杆在开源里基本没落地过，且宠物面板空间小。
- **思维链折叠的收敛共识**：默认收起 + 思考中动效 + 完成后显示耗时 + 最小展示时长防闪烁 + 用户手动展开后不被自动覆盖。桌宠形态的加分改造：把"转圈"换成洛天依的思考小动作。
- **工具活动流最佳范本是 chatbox Work Mode**：单行时间线（工具名·摘要·耗时，默认收起，点击展开参数）+ 高危操作审批卡 + 步数熔断——与我们 `agent.tool` 事件和 U2/U3 规划几乎一一对应。
- **权限询问的正确形态是"消息流内的阻塞卡片"而非弹窗**（CopilotKit `renderAndWait` / Chainlit 内联按钮 / OpenHands 把"等待确认"当一等状态），协议侧只需新增 `permission.request`/`permission.resolve` 一对事件。
- **桌宠态没有一家用完整聊天气泡流**：主流是混合式——日常用"可拖拽可隐藏的极简悬浮胶囊"（字幕+输入+状态+打断四合一，Open-LLM-VTuber 范本），看历史才展开完整面板。我们现有底部浮层应向"胶囊+面板"双态演进。
- **license 红绿灯**：放心抄码=LibreChat(MIT)/Jan(Apache)/NextChat(MIT)/lobe-ui(MIT系)/assistant-ui(MIT)/OpenHands(MIT)/桌宠四家(MIT)；只学交互别抄码=cherry-studio(AGPL)/chatbox(GPL)；注意品牌条款=open-webui(BSD+branding)。
- **对 A/B/C 形态的影响**：B 方案"壳承载 Web UI + Godot 只管演出"的架构被桌宠圈强验证（Open-LLM-VTuber 三形态共享上下文），但**壳选型出现反转证据**——airi 从 Tauri 迁回 Electron、OLV 从 PyWebView 迁到 Electron，透明置顶穿透窗在 Electron 生态最省心。B 不锁定 Tauri，需加"桌宠窗特性逐项真机验收"前置风险项。详见 §7，**拍板权在所有者**。

## 2. U0 现状测绘：协议事件 → UI 覆盖矩阵

本地读码对象：[`AVATAR_BRIDGE.md`](../../AVATAR_BRIDGE.md)（协议契约）、`apps/avatar-runtime/interaction_ui.gd`（Godot 浮层，808 行）、`apps/avatar-runtime/runtime.gd`（WebSocket 桥，1871 行）、`apps/desktop/src/App.tsx`（Tauri 壳，322 行）。

### 2.1 覆盖矩阵

| 协议事件 | 载荷要点 | Godot 浮层 | Tauri 壳 | 差距归属 |
|---|---|---|---|---|
| `client.hello` / `core.status` / `client.ready` | 握手与在线状态 | ✅（runtime.gd，自动重连 2s） | ✅（连接 chip + 3s 重连） | 基线 |
| `agent.state` | idle/thinking/speaking/working/error | ✅ 轻表情映射 + 口型 | ✅ 中文状态卡 + 状态点 | U1 把"思考中"做成角色微动效 |
| `chat.message` / `chat.response` | 文本 + conversationId | ✅ 纯文本气泡 | ✅ 纯文本气泡 | U1 富文本/Markdown |
| `chat.history.request/response` | 最近 50 条 | ✅ 切会话拉取 | ❌ | U1 |
| `session.new/switched/title/list/delete/deleted` | 会话全生命周期 | ✅ 下拉 + 删除确认框 | ❌ 完全没有 | U1 |
| `agent.tool` | tool/ok/summary/request_id | ⚠️ 仅一行"已使用工具：…"，MCP 长名（`mcp__server__tool`）不解析 | ❌ | **U2 工具活动流（P0 缺口）** |
| `permission.decision` | allow/ask/deny + rule_id | ❌ 只落 events 表，UI 不可见 | ❌ | **U3 确认中心（P0 缺口）** |
| ask 确认流 | 600s 超时，文字往返 | ⚠️ 纯聊天文字确认，无图形卡片 | ❌ | U3 需新协议事件 `permission.request` |
| `avatar.speak` | 分片 partIndex/partCount + audioPath | ✅ 播放 + 口型 | ❌ | U1/U4 字幕化 |
| `avatar.speech.stop` | reason=voice/wake/superseded | ✅ 停播 | ❌ | U1 |
| `speech.finished` | interrupted 回报 | ✅ | —（avatar 侧职责） | 基线 |
| `voice.*`（voice.start 等） | 语音输入状态 | ✅ 按住说话键 | ❌ | U1 |
| `avatar.interaction` / `ui.menu.toggle` | 角色点击菜单 | ✅ Godot 承载 | ⚠️ 未注册 `ui` 角色接管 | U4 |
| `avatar.command`（avatar.wave） | 白名单动作命令 | ✅ | ❌ | U4 |
| `proactive.idle` / `proactive.skipped` | Idle 触发决策 | ❌ 只落 events 表 | ❌ | U2/U4 |
| `agent.tools.unsupported` | 端点降级记录 | ❌ 不可见 | ❌ | U2 |

### 2.2 差距清单（按严重度）

- **P0｜权限过程不可见**：她每次写文件/执行命令/调 MCP 都在 ask 档，但用户只能靠聊天文字往返感知，600 秒超时静默丢弃。数据全在 events 表，缺的是 `permission.request` 展示事件 + 图形卡片（U3，参照 §4 审批卡范本）。
- **P0｜工具活动无实感**：`working` 状态没有内容——她在搜网页/读邮件/操作 GitHub 时 UI 层面一片安静，只有一行"已使用工具：…"。`agent.tool` 事件现成，只缺呈现（U2）。
- **P1｜无富文本**：代码块/列表/链接全部裸文本（U1）。
- **P1｜Tauri 壳落后一代**：322 行的壳连会话管理都没有，若形态 B 转正，U1 的第一步是"补课"（补齐 Godot 浮层已有能力）再"超课"（富文本+活动流）。
- **P2**：`avatar.speak` 分片字幕、Idle 主动问候的可见提示、token 用量显示（协议当前无用量字段，需 Core 侧补充，参照路①各家 reasoning tokens 展示）。

## 3. 路①调研：通用聊天客户端（7 家）

方法与全景：GitHub/官方文档/changelog/issue 交叉验证（2026-09-08）。

### 3.1 项目卡片

| 项目 | 栈 / License | 思考强度控件 | 思维链展示 | 亮点与借鉴 |
|---|---|---|---|---|
| [open-webui](https://github.com/open-webui/open-webui) | SvelteKit 纯 Web / BSD-3 + **品牌条款**（2025-04 起，借鉴模式 OK、抄码注意） | 档位（low/medium/high），藏于三层设置（管理员→模型→会话）；社区抱怨不直观，"输入框旁 Think 按钮"是未实现 FR（#11006/#16806），甚至有第三方注入脚本 | `<think>` 标签自动折叠为"Thinking"块，流式实时归拢 | "管理员→模型→会话"三层参数继承；会话级工具开关（扳手图标，v0.6.31 原生 MCP）；多模型同轮对比 |
| [lobe-chat](https://github.com/lobehub/lobehub) | Next.js+React / **Community License**（Apache 基础+附加条款；组件库 lobe-ui 为 MIT 系可整用） | 有，但在模型/会话设置里；"放进 composer 旁"是高赞 FR（#18038/#7469） | **lobe-ui Thinking 组件是开源最佳**：`collapsed` 默认收起 + 思考中光标/呼吸动画 + "Thought for X seconds" + reasoning tokens 用量 | ModelSelectPopover（搜索+按 provider 分组+能力图标）；MCP Marketplace；话题分组/消息分支 |
| [cherry-studio](https://github.com/CherryHQ/cherry-studio) | **Electron**+React+antd / **AGPL-3.0**（只学交互别抄码） | 档位（关闭/低/中/高），"关闭"=不传参曾致困惑（#9013）；Gemini thinkingBudget 滑杆仍是 FR（#5013） | `ThinkingBlock`（v2 路径实证）；**最小展示时长防闪烁**逻辑与工具块共享 | 同为桌面客户端最贴近我们场景；@ 提及多模型对比；透明窗口主题 |
| [LibreChat](https://github.com/danny-avila/LibreChat) | React+Node 纯 Web / **MIT**（维护者承诺不改，**七家最放心**） | 档位下拉**最全**：none/minimal/low/medium/high/xhigh；支持 URL query 传参 | ThinkBlock "Thought for X seconds"；**v0.8.8 Agent activity view**：推理与工具调用分组展示 | 对话树分支+Fork；token usage 面板；Agent Builder/Marketplace/Skills |
| [NextChat](https://github.com/ChatGPTNextWeb/NextChat) | Next.js+**Tauri（约 5MB 安装包）** / MIT | 无（#6032 开放中） | 基础流式思考文本 | **Tauri 轻量打包实证**；"Mask=人设+参数+会话配置"模板抽象适合做天依的性格预设 |
| [chatbox](https://github.com/chatboxai/chatbox) | **Electron**+React / **GPLv3**（只学交互别抄码） | 无专门控件（#2335 开放中） | **Work Mode 时间线是桌面 agent 交互最佳范本**：思考+工具调用实时时间线，默认收起为一行"工具名·摘要·耗时"，点击展开参数 JSON；结束后"Worked for…"可整体折叠 | **审批卡**（命令步骤变黄自动展开 Approve/Deny）；连续 25 步强制暂停；Chat/Work 智能切换建议卡 |
| [jan](https://github.com/janhq/jan) | **Tauri**+React（已弃 Electron）/ **Apache 2.0** | 无；传统参数滑杆 | thinking 块折叠（深度一般） | **Tauri 底座+扩展化架构实证**；MCP Servers 设置页；100% 离线主张 |

### 3.2 跨项目收敛结论

1. **思考强度控件三种主流形态**：① 档位选择（下拉/分段）是主流，但家家藏在设置里；② ChatGPT 式"输入框旁弹窗"**7 家全没做好**，相关诉求全是开放 FR——体验洼地，即我们的机会；③ token 预算滑杆开源基本没落地（Gemini 官方除外）。
2. **思维链折叠共识**：默认收起 + 思考中动效 + 耗时显示 + 防闪烁最小展示时长（cherry 独有细节，值得抄）。
3. **模型选择器共识**：popover + 搜索 + 按服务商分组 + 能力图标（lobe-ui 最佳）。我们单模型，可转化为"模式选择器"（见 §6）。
4. **MCP UI 共识**：设置页管理服务器 + 会话内快捷开关 + 市场化发现 + 高危审批卡。

## 4. 路②调研：agent 工作台（5 家）

方法说明：GitHub 网页不稳，主体信息来自各官方文档域（docs.openhands.dev / docs.cline.bot / assistant-ui.com / docs.chainlit.io；docs.copilotkit.ai 不可达，经搜索摘要+GitHub API 交叉核实）。

### 4.1 项目卡片

| 项目 | 栈 / License | agent 状态可视化 | 工具调用卡片 | 权限询问 UX | 思考/计量 | 借鉴建议 |
|---|---|---|---|---|---|---|
| [OpenHands](https://github.com/All-Hands-AI/OpenHands)（87k★） | TS 前端 + Python AgentServer / **MIT** | **"等待确认"是一等状态**（`WAITING_FOR_CONFIRMATION`），typed 事件流同步 | ActionEvent 渲染卡片 | **最完整**：策略对象 `AlwaysConfirm / ConfirmRisky(阈值) / NeverConfirm` + SecurityAnalyzer 风险四级（LOW/MEDIUM/HIGH/UNKNOWN，UNKNOWN 默认确认）；**拒因文字回灌 agent** 换安全方案；中断/超时默认拒绝 | 结构化 Metrics：cost + token（含 reasoning_tokens）分账聚合 | allow/ask/deny 映射为策略对象+风险徽标+拒因回灌——最成熟可抄的权限模型 |
| [Cline](https://github.com/cline/cline)（67.7k★） | VS Code 扩展（TS）/ **Apache-2.0** | Plan/Act 双模式（只读讨论 vs 动手），上下文延续 | 命令自带 `requires_approval` 标志 | **粒度最细**：按操作类别（读文件/写文件/命令/浏览器/MCP）独立开关 + **两段式解锁**；YOLO 一键放行；**等待审批/超 30s 发 OS 级通知** | Plan 模式=显式思考阶段 | 类别开关矩阵 + "等待审批→OS 通知"桌面提醒链路（桌宠场景极相关） |
| [CopilotKit](https://github.com/CopilotKit/CopilotKit)（37.3k★） | React 组件栈，AG-UI 协议 / **MIT** | —（文档域不可达） | Generative UI：动作可带 render 函数在消息流内生成 UI | **`renderAndWait` 抽象**：agent 暂停→消息流内渲染自定义 UI→用户完成→agent 恢复 | 未核实 | 抄 `renderAndWait` 一个抽象就够：权限询问=消息流里会阻塞的组件，与我们的确认流天然同构 |
| [assistant-ui](https://github.com/assistant-ui/assistant-ui)（12.1k★） | React，shadcn 风格分发 / **MIT** | ThinkingIndicator | **四态状态机**：running/complete/error/cancelled（取消态罕见）；未识别工具 `ToolFallback` 兜底；`ExternalStoreRuntime` 可接外部事件流 | Interactables（可交互工具） | **reasoning 契约做得最细**：流式自动展开/流毕收起 + **用户手动切换后优先** + 标签挂"(12s)"耗时 + 步骤时间线面板 | 直接抄 reasoning 折叠契约 + ToolCall 四态 |
| [Chainlit](https://github.com/Chainlit/chainlit)（12.4k★） | Python + 内置 Web（Socket.IO）/ **Apache-2.0** | **旁侧 TaskList 面板**：一句话整体状态 + READY/RUNNING/DONE/FAILED 四态；Step 嵌套折叠组 | Step（type/input/output）折叠组 + `config.ui.cot` 三档噪音开关（全显/隐藏/只看工具调用） | **消息内联按钮**（✅ Continue / ❌ Cancel）+ **timeout 默认 90 秒**，超时返回 None（=超时默认拒绝的现成参数化） | 无独立 reasoning 组件 | 两个低成本高收益件：旁侧 TaskList + 内联按钮询问卡 |

### 4.2 跨项目总结：「桌宠+权限引擎」最值得抄的 3 个模式

1. **权限 = 策略对象 + 风险四级 + 类别矩阵**（OpenHands + Cline）：我们已有 allow/ask/deny 引擎与 rule_id 审计，补课方向是——待确认动作带风险徽标（LOW/MEDIUM/HIGH/UNKNOWN，UNKNOWN 默认确认）、拒因附一句文字回灌 agent、超时/中断一律默认拒绝（我们已是 600s 超时丢弃，语义一致）、OS 级通知兜底（她待机时权限请求不该被淹没）。
2. **权限询问 = 消息流内的阻塞卡片，不是弹窗**（CopilotKit `renderAndWait` + Chainlit `AskActionMessage`）：卡片带 ✅/❌ 内联按钮，agent 状态停在"等待确认"（对应我们 ask 挂起态）；90s 量级超时参数化。**协议侧只需新增 `permission.request` / `permission.resolve` 一对事件**，聊天文字确认保留为后备通道（铁律：裁决在 `permissions.py` 不动）。
3. **步骤折叠组 + 侧栏任务面板双视图 + 四态工具卡**（Chainlit + assistant-ui）：MCP 调用渲染为可折叠卡片（running/complete/error/cancelled，含"取消"态——我们的一次性授权过期/超时正好映射），全局配"只看工具调用"噪音开关；思考折叠照 assistant-ui 契约（流式自动展开/流毕收起/手动切换优先/标签挂秒数）。

## 5. 路③调研：VTuber / 桌宠（6 家）

方法说明：GitHub 主站不稳，经官方文档域（docs.llmvtuber.com）、GitHub API 与搜索摘要交叉验证。

### 5.1 项目卡片

| 项目 | 栈 / License | 窗口形态 | 聊天/字幕 | 状态与情绪 | 借鉴建议 |
|---|---|---|---|---|---|
| [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) | Python 后端 + Vue3 Web/Electron 前端 / **MIT** | **本次核实最充分**：Web/窗口/桌宠三模式；桌宠态=置顶+透明+**非交互区点击穿透**+拖拽+缩放（可开关）；三模式**共享完整上下文**（设置/历史/WS 状态/记忆），托盘或右键菜单无缝切换不丢状态 | **极简悬浮胶囊**：输入框+字幕独立可拖拽、可隐藏；胶囊内置 AI 状态 + 麦克风开关 + **打断按钮**（barge-in 显式 UI 入口） | 状态指示与输入控件合并在同一悬浮条；表情切换承担大部分状态表达 | **最完整范本**：一套 Web UI 三形态 + 可拖拽可隐藏胶囊；壳演进史=PyWebView→Electron |
| [moeru-ai/airi](https://github.com/moeru-ai/airi)（约 22k★） | monorepo 多端 / **MIT** | `stage-web`（浏览器）/`stage-tamagotchi`（桌宠）/`stage-pocket`（移动）共享 `stage-ui` 组件包 | provider 卡片式设置面板 | 实时语音+打断 | 学"一套 UI 组件层+每端薄壳"结构；**关键前车之鉴：桌面端 2025-10 从 Tauri 迁移到 Electron** |
| [pixiv/ChatVRM](https://github.com/pixiv/ChatVRM)（已停维护） | Next.js+three.js / MIT | 无桌宠，全屏角色+页面内聊天区 | 气泡式对话记录 | **情绪标签内联于 LLM 文本输出**（[joy] 类）映射 VRM 表情——最简情绪协议 | 只借情绪标签协议与"角色全屏+对话区侧置"基线 |
| [semperai/amica](https://github.com/semperai/amica) | Next.js+Electron / MIT | 桌面版窗口细节未核实 | 设置以抽屉面板挂同一页面 | LLM 驱动表情、视线跟随镜头 | 借"抽屉式设置"与视线跟随这类低成本生命感细节 |
| [OpenBMB/MiniCPM-Desk-Pet](https://github.com/OpenBMB/MiniCPM-Desk-Pet)（2026 新） | 本地优先，MiniCPM5 | 未核实 | 未核实 | **"桌宠旁观 agent 工作"的被动陪伴交互**（观察你用 Cursor/Claude Code） | 方向与我们最接近的新一代标杆，关注其陪伴式交互 |
| [DyberPet](https://github.com/ChaozhongLiu/DyberPet) | Python/PyQt | 拖拽/贴边/下落物理是强项 | LLM 部分较弱 | 任务/动画状态机（idle 生态成熟） | 借桌宠"物理感与 idle 生态"，不借 LLM UI |

### 5.2 跨项目总结

1. **桌宠态没有一家用完整聊天气泡流**：主流是**混合式**——桌宠态用"可拖拽、可隐藏、可缩放的极简悬浮胶囊"（字幕+输入+状态+打断四合一，OLV 范本），要看历史时才展开/切换为完整面板。我们现有"底部半透明聊天浮层"介于两者之间，U1 起应向"胶囊（日常）+ 面板（深度用）"双态演进。
2. **状态反馈共识**：状态指示与输入控件合并在同一悬浮条（聆听/说话+麦克风+打断按钮），表情切换本身承担大部分状态表达——不单独做呼吸灯组件。
3. **情绪协议共识**：LLM 文本流内联情绪标签（ChatVRM 式）或结构化输出，经用户可配的映射表驱动表情。我们已有 `agent.state` 五态与 48 表情槽，缺的是"回复→表情"的情绪映射层（Godot 侧或协议侧，归属 U4 演出联动）。
4. **对 B 方案的可行性证据（含反转）**：OLV 证明"壳承载同一套 Web UI、多形态共享上下文"是成熟架构，桌宠三件套（置顶/透明/穿透）在 Web 层 UI 完全可实现；**但两个头部项目最终都选了 Electron**（OLV 从 PyWebView 迁出、airi 从 Tauri 迁出）——透明置顶穿透在 Electron 有现成一致的开关，Tauri 技术上具备同能力（transparent/always_on_top/set_ignore_cursor_events）但属少数派路线。**结论：B 方案不锁定 Tauri，壳选型需带"桌宠窗特性逐项真机验收"前置风险项，Electron 为备选。**

## 6. 模式目录 → 天依映射表

| UI 模式 | 开源参照 | 天依落点 | 归属期 |
|---|---|---|---|
| 思考强度控件 | LibreChat 档位全集 + ChatGPT 式弹窗（开源无人做好） | 输入框角"脑形"图标档位弹窗：**安静陪聊 / 标准 / 深度工作** 三档起步。映射到 Core 侧：工具循环步数上限、MCP 工具是否参与本轮、（若 Core 后续暴露 GLM thinking 参数则透传）——UI 只发参数，裁决在 Core | U1 末期/U2 |
| 思维链折叠 | assistant-ui Reasoning 契约 + lobe-ui Thinking 组件 + cherry 防闪烁 | 默认收起、流到才自动展开、流毕收回；**用户手动切换后不再被自动覆盖**；标签挂"想了 X 秒"；思考中状态气泡换成天依待机小动作（桌宠独有的加分项，替代千篇一律的转圈） | U1/U2 |
| 工具活动流 | chatbox Work Mode 时间线 + assistant-ui ToolCall 四态 | `agent.tool` 事件 → 单行卡片（工具名·ok·耗时），MCP 前缀 `mcp__server__tool` 解析成"服务器·工具"双徽标；默认收起、点击展开 summary；状态机含 **error 与 cancelled 态**（超时/过期授权有处安放）；全局配"只看工具调用"噪音开关 | U2 |
| 权限审批卡 | chatbox 审批卡 + CopilotKit `renderAndWait` + Chainlit 内联按钮/90s 超时 + OpenHands 风险四级 | U3 核心：**不做弹窗，做消息流内的阻塞卡片**——新协议事件 `permission.request`（工具名+风险档 LOW/MED/HIGH/UNKNOWN+参数摘要）→ 内联 ✅/❌ 卡（另设"本会话记住"），"等待确认"作为一等状态呈现；超时默认拒绝；可选 OS 通知兜底；裁决仍在 `permissions.py`，审计仍落 events 表；聊天文字确认保留为后备通道 | U3 |
| 模式选择器 | lobe-ui ModelSelectPopover 降维 | 我们单模型，无需模型选择器；转化为"模式选择"（闲聊/工作）或直接并入思考强度档位，避免两个控件做同一件事 | U2 可选 |
| 说话字幕 | Open-LLM-VTuber 悬浮胶囊（可拖拽/可隐藏，内置状态+麦克风+打断按钮） | `avatar.speak` 已有分片协议（partIndex/partCount），UI 侧做成"日常胶囊、深度面板"双态：胶囊常驻可拖拽显示当句字幕与状态，面板承载完整历史 | U1/U4 |
| 情绪→表情映射 | ChatVRM 内联情绪标签 + OLV/amica 可配映射表 | 我们有 `agent.state` 五态 + 48 表情槽，缺"回复情绪→表情"映射层（协议或 Godot 侧加一层，不动官模形态键基值） | U4 演出联动 |
| 记忆审阅 | （assistant-ui 侧栏组件线索；专属 UI 无现成范本） | KI-016 pending 记忆审阅 UI，建议与 U2 活动流同期（同属"看她在想什么"信息架构） | UI 期后段 |

## 7. 形态决策 A/B/C 影响分析（拍板权在所有者）

| 维度 | A. 强化 Godot 浮层 | B. 独立壳承载 Web UI（Tauri 或 Electron） | C. Godot 内嵌 WebView |
|---|---|---|---|
| 富文本/Markdown | Godot RichTextLabel 生态弱，代码块高亮等要自造轮子 | Web 生态全家桶（react-markdown/shiki 现成） | 可用 Web 生态，但两头受气 |
| 桌宠窗口形态（透明/穿透/贴边） | 已验证（现有画布） | **架构被验证、壳选型有分歧行情**：OLV 三形态共享上下文成熟可用；但 airi 弃 Tauri 转 Electron、OLV 弃 PyWebView 转 Electron——Tauri 技术可行（transparent/always_on_top/set_ignore_cursor_events）属少数派路线，Electron 是行业收敛点 | 未验证，风险最高 |
| 与角色状态机联动 | 同进程最紧密 | 跨进程走既有 WebSocket 协议（`agent.state` 等事件已齐） | 耦合最古怪 |
| 工程隔离（铁律 3） | 挤进 `interaction_ui.gd`（已 808 行）或新 gd 文件 | Godot 侧只留演出层，UI 独立演进，最符合"演出层/大脑层"分工 | 修改面最大 |
| 长期成本 | 天花板最低 | `apps/desktop/` 骨架+协议已通，增量最小 | 维护两套窗口逻辑 |

**调研后的证据倾向**：B 的"壳承载 Web UI"架构被桌宠圈强验证，但**壳选型（原倾向 Tauri）出现反转证据**——两个头部桌宠项目都退到 Electron，透明置顶穿透窗在 Electron 上是现成一致的开关，Tauri 需把"桌宠窗特性（透明/置顶/穿透/拖拽/多屏）逐项真机验收"列为前置风险项；若验收顺利 Tauri 的体积与内存优势仍值得拿，不顺则 Electron 兜底。A 的 Markdown 生态成本依旧最高。**决策留给所有者；无论选哪个壳，§6 映射表的交互设计结论全部不受影响。**

## 8. 合规与来源

- 抄码安全区：LibreChat（MIT）、Jan（Apache-2.0）、NextChat（MIT）、lobe-ui 组件库（MIT 系）、OpenHands（MIT）、CopilotKit（MIT）、assistant-ui（MIT）、Open-LLM-VTuber/airi/ChatVRM/amica（均 MIT；Live2D/VRM 模型资产另有授权需单独注意）。
- 只学交互不抄码：cherry-studio（AGPL-3.0）、chatbox（GPLv3）；Cline/Chainlit（Apache-2.0，保留 NOTICE 即可）。
- 品牌条款注意：open-webui（BSD-3 + branding，2025-04 起）。
- 路①来源：各家官方 docs/changelog/releases/LICENSE 与编号 issue（#18038/#11006/#9013/#6032/#2335 等），检索日 2026-09-08。
- 路②来源：docs.openhands.dev（Security/Confirmation、Metrics）、docs.cline.bot（auto-approve、plan-and-act）、assistant-ui.com（tool-ui、reasoning）、docs.chainlit.io（step、AskActionMessage、TaskList）；CopilotKit 文档域不可达，经搜索摘要+GitHub API 核实。
- 路③来源：docs.llmvtuber.com（窗口与桌宠模式、Electron 子页）、airi 仓库与 devlog（2025-10-20 Electron migration）、pixiv.github.io/ChatVRM、各仓库 README；MiniCPM-Desk-Pet/DyberPet 为线索级（UI 细节未核实）。
