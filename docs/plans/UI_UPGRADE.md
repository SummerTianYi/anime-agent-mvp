# 前端 UI 升级方案（UI Upgrade Roadmap）

声明：zcode 起草于 2026-09-07，经项目所有者立项。**当前执行状态：方案阶段，未开工。** 接手 agent 按本文开工前，先读 [`HANDOFF.md`](../HANDOFF.md) 总纲（§6 铁律）与本文件 §5 边界。

## 1. 为什么要升级

产品现状：Agent 大脑层已完成 M2（有手有眼的联网 agent，103 个工具）并大半完成 M3，但交互界面仍是 MVP 时代的 Godot 底部聊天浮层——**能力与外壳严重不匹配**。她现在能联网搜索、读邮件、操作浏览器，但用户没有一个像样的界面去观察和指挥这一切。Agent 线开发告一段落（见 [`AGENT_REPORT_2026-09-07.md`](../AGENT_REPORT_2026-09-07.md)），UI 是下一主战场。

## 2. 现状盘点（接手 agent 先摸一遍）

| 现有件 | 现状 | 问题 |
|---|---|---|
| `apps/avatar-runtime/interaction_ui.gd` | 角色点击菜单 + 底部半透明聊天浮层（气泡滚动、会话下拉/新建/删除、语音键、确认框） | 单列气泡流；无 Markdown/富文本；无工具活动可视化；面板尺寸固定 |
| `runtime.gd` | WebSocket 桥、状态机映射、口型/动作驱动 | 聊天 UI 与 3D 运行时耦合在同一 Godot 工程 |
| `apps/desktop/`（Tauri+React） | 已有可连 Core 的调试壳（`chat.message` 通了） | 长期闲置，只有基础聊天 |
| 协议层 `AVATAR_BRIDGE.md` | 事件契约完整（chat/session/voice/agent.tool/avatar.speak/permission 决策审计在 events 表） | `permission.decision`、`agent.tools`、MCP 活动没有前端呈现；确认流目前靠聊天文字（"回复确认"） |

## 3. 设计方向（与所有者对齐过的原则）

- **角色优先不变**：桌面 3D 角色是主体验，UI 是她的"工具面板"，绝不能退化成又一个聊天窗口应用（AGENTS.md 红线）。
- **三块信息流**：① 对话流（含富文本：代码块/列表/链接）；② **能力活动流**（她在用什么工具、权限裁决、MCP 调用——数据现成，events 表和 `agent.tool`/`agent.tools` 事件都在，只缺呈现）；③ 确认中心（把聊天文字确认升级为可点击的权限卡片，保留聊天文字确认作后备通道）。
- **形态待定**（接手后与所有者第一件事就是定这个）：A. 强化现有 Godot 浮层（延续性强、Godot UI 能力有限）；B. Tauri 壳转正（Web 技术栈 UI 自由度高、与 Godot 角色并排双进程）；C. Godot 内嵌 WebView 混合。**倾向 B**，因为 `apps/desktop/` 骨架和协议都在，且 Godot 侧只保留角色演出更符合"演出层/大脑层"分工。
- **美 学**：洛天依主题（天依蓝 #66CCFF）、半透明、贴边、可收起；与角色状态机联动（thinking 时 UI 呈"正在想"微动效）。

## 4. 分期建议

| 期 | 内容 | 验收口径 |
|---|---|---|
| U0 现状测绘 | 通读 interaction_ui.gd/runtime.gd/AVATAR_BRIDGE，列出协议事件→UI 现状映射表；与所有者定形态（A/B/C） | 测绘表 + 形态决策记录进本文件 |
| U1 对话体验 | 富文本渲染、多行输入、会话管理优化、历史分页 | 现有全部协议事件回归通过；单问单答/打断/会话切换不回退 |
| U2 能力可视化 | 工具活动流（agent.tool/agent.tools 事件实时呈现）、MCP 调用徽标、权限审计页（读 events 表或新事件） | 她每次用工具，UI 有对应可见反馈；验收对照 events 表 |
| U3 确认中心 | ask 类操作弹出角色化权限卡片（图标+风险等级+允许/拒绝按钮），落 `permission.request` 协议（AGENT_ROADMAP B 期遗留的"Godot 确认卡片"正式补课）；聊天文字确认保留 | 权限卡片全链路测试；拒绝路径有测试；协议变更同步 AVATAR_BRIDGE + 测试（铁律 6） |
| U4 打磨 | 主题、动效、多显示器、开机常驻形态配合（将来接自启） | 手动验收 3 场景 |

## 5. 边界与红线（接手 agent 必读）

1. **不动 Core 协议语义**：UI 只消费/新增展示层事件；改协议必须同步 AVATAR_BRIDGE.md + 测试（HANDOFF 铁律 6）。
2. **不绕权限层**：确认卡片只是把"聊天回复确认"图形化，裁决仍在 `permissions.py`，审计仍落 events 表。
3. **Godot 角色工程谨慎动**：`runtime.gd` 是 Codex 的冻结区（模型 1.2/画布/动作层），UI 工作尽量隔离在 `interaction_ui.gd` 或 Tauri 壳；确需动共享文件按 CONTRIBUTIONS 规矩分块提交。
4. **真实机验收走 VERIFICATION_SPEC**：UI 改动同样八条铁律（用户可见字段显式断言）。
5. 每期收工：HANDOFF §3 状态回写 + 本文件进度标注 + CONTRIBUTIONS 归属行。

## 6. U0 执行进度

- **2026-09-09：U0 测绘与开源调研完成（zcode，零 GLM 配额）**，产出并入 [`UI_REFERENCES.md`](UI_REFERENCES.md)：协议事件→UI 覆盖矩阵与差距清单（其 §2，确认两处 P0 缺口：权限过程不可见、工具活动无实感）；三路开源调研 18 项目（其 §3-5：聊天客户端 7 / agent 工作台 5 / VTuber 桌宠 6）；模式→天依映射表（§6）；A/B/C 形态影响分析（§7，注意其中"Tauri 选型反转证据"）。
- **2026-09-10：U2 首块试点上线（zcode，所有者选定"最有把握"先行）**：工具活动卡落入 Godot 浮层——`agent.tool` 事件按回合聚合成气泡流内卡片（本地/MCP 服务器徽标 + ✓/✗ + 计数），零协议/Core 改动，守卫 `verify_tool_activity.gd`（`GODOT_TOOL_ACTIVITY_OK`）入 TESTING 门禁。这是 §3"三块信息流"之能力活动流的最小实现；chatbox Work Mode 范式的 Godot 版。
- **形态决策 A/B/C 仍待所有者拍板**——拍板后把决策记录回填到本文 §3"形态待定"处，U1 才开工。
