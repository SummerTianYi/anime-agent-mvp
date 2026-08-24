# MVP 方案

## 1. 目标

做出一个真正能“住在电脑里”的二次元 Agent，而不是需要用户每次手动打开 Codex/Claude 的聊天工具。

第一版只验证四件事：

1. **开机即在线**：Windows 登录后后台 Agent 与桌面角色自动启动。
2. **能聊**：支持文字聊天，普通任务走 Gemini Flash API。
3. **能主动触发**：至少支持 Startup 与 Idle 两类本地事件。
4. **有 Agent 内核**：优先接 Spark 承担 Skills / 长任务 / 调度；同时保留 Adapter 层，避免 Spark 接口限制阻塞整个 MVP。

## 2. 非目标

MVP 暂不做：完整语音对话、复杂 Live2D 动作、手机遥控、跨设备同步、全自动电脑控制、多 Agent 协作、插件市场、云端 24/7 部署。

## 3. 系统架构

```text
Windows Login
    │
    ├── Desktop Shell (Tauri + React)
    │      └── Avatar / Chat / 状态展示
    │
    └── Agent Core (本地后台进程)
           ├── Router
           ├── Event Engine
           ├── Memory (SQLite)
           ├── Permission Layer
           ├── Gemini Adapter
           └── Spark Adapter
                  └── Skills / 长任务 / 调度（以实际可用接口为准）
```

### 为什么保留本地 Agent Core

即使 Spark 是目标内核，本地 Core 仍然必须存在，因为开机自启、鼠标/键盘空闲检测、桌面 UI 通信、SQLite、权限控制都属于本机职责。Spark 负责“思考与任务编排”，本地 Core 负责“让它活在这台电脑上”。

## 4. MVP 功能范围

### P0：必须完成

- Windows 登录自启
- 后台 Agent Core 常驻
- 桌面二次元角色窗口
- 文字聊天
- Gemini Flash API 接入
- `idle / thinking / speaking / working / error` 五种角色状态
- Startup Trigger
- Idle Trigger
- SQLite 保存最近对话、事件、任务状态
- 本地日志
- API Key 只从环境变量或本地 secrets 配置读取，不提交 Git

### P1：MVP 验证后加入

- Spark Adapter
- 1 个可重复 Skill，例如“总结指定文件夹中的文档”
- 简单 Schedule
- 本地文件只读能力
- 操作确认弹窗

### P2：后续版本

- 语音 STT/TTS
- Live2D 完整模型与动作
- Computer Use
- Codex Runtime Adapter
- Claude Adapter
- 云端/常开设备节点
- 跨设备记忆同步

## 5. 关键交互

### 场景 A：开机

1. Windows 登录。
2. Agent Core 自动启动。
3. Desktop Shell 自动出现。
4. Core 发出 `SYSTEM_START`。
5. Gemini 判断是否需要主动说话。
6. 若没有有价值信息，保持安静；不要为了“主动”而主动。

### 场景 B：一般聊天

```text
用户输入
→ Agent Core Router
→ Gemini Flash
→ 回复文本
→ Desktop Shell 展示
```

### 场景 C：长期任务

```text
用户任务
→ Router 判断为 long-running / skill task
→ Spark Adapter
→ Spark/Skill 执行
→ Core 接收状态
→ Avatar 切换 working
→ 完成后通知用户
```

## 6. Spark 接入必须先做的技术验证

Spark 是目标内核，但 MVP 不应假设一个尚未确认存在的“第三方 Spark Runtime API”。开发第一阶段必须完成 Spike：

- 是否存在可供本地桌面应用稳定调用的官方接口；
- 是否可创建/触发 Task、Skill、Schedule；
- 是否能获得任务状态与最终结果；
- 是否支持本地 App 所需鉴权模式；
- 若只能由 Spark 调 MCP，而不能由桌面 App 调 Spark，则把 Spark 降为可选能力，本地 Core 继续承担基础调度。

**验收原则：Spark 接口问题不能阻塞桌面 Agent 基础闭环。**

## 7. 权限设计

MVP 默认保守：

- 聊天、读取状态：自动。
- 读取用户明确授权目录：自动。
- 修改文件：弹窗确认。
- 删除文件、执行外部命令、发送消息：MVP 默认禁用。

## 8. 开发阶段

### Milestone 0 — Skeleton

- 初始化 monorepo
- Tauri Desktop 空窗口
- Python Agent Core `/health`
- WebSocket 打通

验收：桌面壳能够显示 Core `online`。

### Milestone 1 — Chat

- 输入框与气泡
- Gemini Adapter
- 五种角色状态

验收：用户无需打开 Codex，可直接与桌面角色聊天。

### Milestone 2 — Always On

- Agent Core 随登录启动
- Desktop 随登录启动
- 崩溃恢复与日志

验收：重启 Windows 后不手动打开任何开发工具，角色自动上线。

### Milestone 3 — Proactive

- Startup Trigger
- Idle Trigger
- 防打扰规则

验收：系统事件能触发 Agent 判断，并允许返回 `IGNORE`。

### Milestone 4 — Spark Spike

- 完成官方接入验证
- 建立 `SparkAdapter` 接口
- 若可用，接通一个 Skill；若不可用，记录阻塞原因并使用 Local Scheduler fallback

验收：架构不因 Spark 当前接口形态而推倒重来。

## 9. MVP 验收标准

满足以下条件即可认为 MVP 成功：

- 重启电脑后无需手动启动 Codex 或终端。
- 桌面角色自动出现并显示 Online。
- 用户能发送文本并得到 Gemini 回复。
- 角色状态能随请求变化。
- Startup / Idle 至少两种事件被正确捕获。
- Agent 可选择不打扰用户。
- 对话和事件可在重启后恢复。
- Gemini API Key 不进入 Git 历史。
- Spark 已完成“可接/不可接”的明确技术结论，并有 Adapter 隔离。

## 10. 成本

本地 MVP 本身可以基本零新增基础设施成本。主要变量成本是 Gemini API；Codex 用现有订阅进行开发。未来增加云端常驻、商用 Live2D 素材、云端语音等时再单独评估。
