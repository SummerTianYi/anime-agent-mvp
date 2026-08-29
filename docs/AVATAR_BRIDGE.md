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
