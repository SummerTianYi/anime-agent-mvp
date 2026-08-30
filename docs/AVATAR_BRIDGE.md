# Avatar Bridge

Godot 角色运行时通过本地 WebSocket 连接 Agent Core，默认地址是 `ws://127.0.0.1:8765/ws`，可用进程环境变量 `AGENT_CORE_WS_URL` 覆盖；`start-mvp.ps1` 会根据 `.env` 中的 `AGENT_CORE_PORT` 自动设置该地址。连接断开后每 2 秒自动重试，不依赖 React/Tauri 窗口。

## 连接握手

Avatar 连接后发送：

```json
{"type":"client.hello","role":"avatar"}
```

Core 返回 `core.status` 和 `client.ready`。

## Agent 状态

Core 只向 `avatar` 和 `ui` 角色发送状态事件：

```json
{"type":"agent.state","state":"thinking"}
```

当前支持 `idle`、`thinking`、`speaking`、`working`、`error`。Godot 目前只做轻量映射：思考/工作使用轻表情，说话时循环元音口型，空闲恢复自然，错误显示困惑表情。

## 角色点击与菜单

角色点击后，Avatar 可以发送：

```json
{
  "type":"avatar.interaction",
  "event":"avatar.clicked",
  "payload":{"x":240,"y":360}
}
```

Core 会把它定向路由为 `ui.menu.toggle`。角色内置菜单目前直接由 Godot 承载；未来 Tauri UI 注册为 `ui` 角色后可接管该事件。Core 不会把完整聊天内容广播给不需要的客户端。

## 会话与历史

聊天以会话为单位持久化（SQLite `sessions` 表，`messages.conversation_id` 关联）。Core 不维护进程内对话状态，每条消息按会话即时落库，上下文按会话从库中取最近 20 条。

新建会话：Avatar 发送 `session.new`，Core 建库并广播：

```json
{"type":"session.new"}
{"type":"session.switched","conversationId":2,"title":"新对话"}
```

“新对话”收到首条用户消息时，Core 自动用前 12 个字改名。

请求会话列表：Avatar 发送 `session.list.request`，Core 单播返回（按最近活跃倒序）：

```json
{"type":"session.list.request"}
{"type":"session.list.response","sessions":[{"conversationId":1,"title":"初始会话","updatedAt":"2026-08-30 02:10:00.000"}]}
```

请求某个会话的历史：Avatar 发送 `chat.history.request`（`conversationId` 缺省取最近活跃会话），Core 单播返回最近 50 条：

```json
{"type":"chat.history.request","conversationId":1}
{"type":"chat.history.response","conversationId":1,"messages":[{"role":"user","text":"你好","createdAt":"2026-08-30 02:10:00"}]}
```

`chat.message` 可携带可选 `conversationId` 指定落库会话，缺省落最近活跃会话；`chat.response` 原样携带 `conversationId`。客户端切换会话时自行清空气泡并按需拉取历史。

## Avatar 命令

任何已连接的本地客户端都可以向 Core 发送：

```json
{
  "type":"avatar.command",
  "event":"avatar.wave",
  "payload":{}
}
```

Core 验证命令白名单后定向发送给 Avatar。支持的命令由 `AVATAR_EVENTS` 和 Godot 的 `handle_agent_event()` 共同定义。

## 验证

先启动 Agent Core，然后在仓库根目录执行；脚本会自行创建临时的 `avatar` 与 `ui` WebSocket 角色，因此真实 Avatar Runtime 可以不启动：

```powershell
.\services\agent-core\.venv\Scripts\python.exe .\scripts\verify-avatar-bridge.py
```

通过时会输出 `"bridge": "ok"`，并确认状态路由、菜单事件、聊天响应和 `avatar.wave` 命令。该脚本会触发一次聊天请求；若当前 Core 配置了真实 Provider，就会产生真实 API 调用，纯本地验证请先显式使用 Mock。
