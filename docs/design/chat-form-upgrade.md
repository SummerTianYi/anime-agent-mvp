# 聊天形态升级设计稿

状态：方案已确认，Core 侧已落地（存储 + 协议），Godot 侧待实施
范围：Godot 端聊天界面重做 + Core 会话管理 + 桥接协议扩展
配套：架构图 [chat-form-upgrade.html](chat-form-upgrade.html) · 交互原型 [chat-ui-mockup.html](chat-ui-mockup.html)

## 问题

- 全部对话挤在一个 520×310 的面板里，超过 6 条就看不全，无法回看。
- 没有"会话"概念：重启后只能回载最近 20 条，不能新开对话，也不能切回旧对话。
- 面板位置糊在角色正脸，打开聊天就看不见洛天依了。
- 界面是默认 Godot 控件灰，没有任何洛天依视觉元素。

## 方案总览

原则：**角色是主体，聊天是附属浮层**。不做窗口扩展、不引入 Tauri。

聊天面板改为窗口底部的半透明浮层，只盖住下半身，脸和上身永远可见。窗口尺寸（560×760、无边框、置顶、透明）全部不动。

```text
┌────────────────────────────┐
│      洛天依（3D 舞台）        │
│      脸和上身完全可见         │
│                            │
├────────────────────────────┤
│ ♪洛天依  [会话▾]    [＋新对话] │
│ ┌────────────────────────┐ │
│ │ 气泡 · 可滚动 300px      │ │
│ │ 天依左：浅色气泡+头像圆    │ │
│ │ 用户右：天依蓝气泡        │ │
│ └────────────────────────┘ │
│ [输入框……] [按住语音] [发送] │
└────────────────────────────┘
```

浮层结构（自上而下）：

- 标题栏：小圆头像 + "洛天依" 签名、会话下拉、＋新对话按钮。
- 气泡区：高约 300px 可滚动；天依消息左侧浅灰白气泡（灰发色）带头像圆，用户消息右侧天依蓝气泡；自动滚底，用户上翻时不打断。
- 输入行：输入框 + 按住语音 + 发送，行为与现在一致（语音转写回填输入框，人工确认发送）。

## 洛天依主题

官方人设考据：天依蓝 #66CCFF 主色，灰发绿瞳，蓝白旗袍，碧玉发饰，中国结腰坠。

| Token | 值 | 用途 |
|---|---|---|
| 主色 | `#66CCFF` | 用户气泡底、会话高亮、发送键、焦点描边 |
| 面板底 | `rgba(10, 16, 28, 0.92)` | 深海军蓝浮层，毛玻璃质感 |
| 天依气泡 | `#F2F5FA` 底 + `#2A3140` 字 | 灰白发色的浅色气泡 |
| 碧玉点缀 | `#7FD4A8` | 用户头像描边、状态色 |
| 文字 | `#E8ECF4` / 次要 `#8A93A8` | |
| 圆角 | 14px 气泡 / 16px 面板 | |

头像：`docs/design/assets/luotianyi-avatar-original.jpg` 为源图，定稿裁切（920px 窗口、脸偏左、含全部头发）缩至 256px，用于消息头像圆、标题栏签名、空会话占位三处。音符符号只保留在"按住语音"等功能语义位置。

## Core 与协议改造（已实现，19 项单测通过）

存储（storage.py）：

- 新增 `sessions` 表（id / title / created_at / updated_at）；`messages` 加 `conversation_id` 列，启动迁移把存量消息归入"初始会话"，全新库自动建"新对话"默认会话。
- 新方法：`create_session / list_sessions / latest_session_id / get_session / load_history`；`add_message` 返回会话 id，"新对话"收到首条用户消息时自动用前 12 字改名。
- 会话历史改为按请求从库里取（替换进程内全局），切换会话上下文天然隔离。

协议（main.py）：

| 事件 | 方向 | 说明 |
|---|---|---|
| `session.new` | 客户端→Core | 建新会话，Core 广播 `session.switched(conversationId, title)` |
| `session.list.request` | 客户端→Core | 单播 `session.list.response`（conversationId / title / updatedAt） |
| `chat.history.request` | 客户端→Core | 带 `conversationId`，单播 `chat.history.response`（role / text / createdAt） |
| `chat.message` | 增字段 | 可选 `conversationId`，缺省落最近活跃会话；`chat.response` 同样携带 |

已用独立实例（mock provider、隔离数据目录）在线验证：建会话、按会话路由、历史回载、列表排序、跨会话隔离全部通过。

## Godot 侧实施清单（下一步）

1. `interaction_ui.gd`：聊天面板重做为底部浮层（标题栏 / 气泡区 / 输入行），新会话与切换控件。
2. `runtime.gd`：接入 `session.switched / session.list.response / chat.history.response`，发送侧携带 conversationId。
3. 头像图复制进 `apps/avatar-runtime/assets/`，气泡与标题栏使用。
4. 主题色集中定义（天依蓝 / 碧玉 / 深蓝面板）。
5. 文档同步（AVATAR_BRIDGE.md、TESTING.md 验收项）+ 真机验收（含重启后历史回载）。

## 本版不做

Markdown/代码块渲染、会话重命名与删除、无限历史翻页（先回载最近 50 条）、Tauri 壳、会话置顶。
