# Avatar Runtime

这是独立于 Tauri/React 聊天壳的 Godot 3D 角色运行时。它负责模型渲染、镜头、角色菜单、聊天浮层、输入和基础动作，后续由 Agent Core 通过本地 WebSocket 驱动。

## 运行

在仓库根目录执行：

```powershell
pnpm avatar:dev
```

也可以直接运行 `scripts/run-avatar-runtime.ps1`。脚本会查找本机 Godot 4、验证本地 GLB 是否存在，并打开一个透明、无边框、置顶的 560x760 桌面角色窗口。Core 地址默认是 `ws://127.0.0.1:8765/ws`，可通过 `AGENT_CORE_WS_URL` 覆盖；资产路径、哈希和处理流程见 [`assets/README.md`](assets/README.md) 与 [`docs/ASSET_PIPELINE.md`](../../docs/ASSET_PIPELINE.md)。

## 当前交互

- 鼠标左键单击人物：打开“聊天 / 互动”菜单
- 鼠标左键拖拽人物：移动桌面角色窗口，松开后自动保存位置（移动超过阈值后识别为拖拽）
- 鼠标右键拖拽：连续转身，支持查看背面
- 鼠标滚轮：缩放
- `F1`：显示或隐藏调试状态
- `A` / `D` 或左右方向键：左右转身 30°
- `R`：回到正面
- `N`：点头
- `W`：挥手
- `Space`：打招呼（点头 + 挥手）
- `B`：眨眼
- `S`：微笑
- `O`：惊讶
- `X`：生气
- `L`：右眼单眨
- `T`：眼泪
- `Esc`：退出

聊天浮层支持文本输入；语音按钮为按住录音、松开转写，转写结果会先回填输入框，确认后再发送。

运行时会自动连接 `ws://127.0.0.1:8765/ws`，断线后每 2 秒重连。Agent Core 的 `thinking / speaking / idle / working / error` 状态会驱动基础表情与说话口型；`avatar.command` 事件会交给 `handle_agent_event()` 执行。完整协议见 [Avatar Bridge](../../docs/AVATAR_BRIDGE.md)。

## 资产说明

洛天依模型是第三方本地素材，仓库没有足以确认再分发权利的授权证据，因此二进制模型与纹理被 `.gitignore` 排除；只有 `assets/README.md` 会提交。新环境需要由使用者自行取得并放置经过处理的本地模型资产。

当前模型源文件没有内置动作片段，因此 MVP 使用程序化骨骼动作。两条从颈侧出发的长辫子由 `MaWei_R_0_1` / `MaWei_L_0_1` 控制，运行时已调整为沿胸前两侧自然下垂，并保留原有曲度与轻微摆动；后脑勺发束不参与这项修正。模型内置的 48 个形变键已接入眨眼、单眼、微笑、惊讶、生气、眼泪和元音口型。
