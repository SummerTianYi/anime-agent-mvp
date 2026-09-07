# MVP 方案

> 实现快照（2026-09-07）：M1 桌面角色闭环与 M2 agent 能力层（权限/工具/写入/命令/MCP/解说/主动问候/TTS）均已上线并经考试验收；Windows 登录自启、进程守护、Idle Trigger、稳定 STT 验收未完成。后续 Agent 必须以 [`HANDOFF.md`](HANDOFF.md)（接手总纲）的状态与铁律为准，本文件保留产品范围和验收目标。

## 1. 目标

做出一个真正能“住在电脑里”的二次元 Agent，而不是需要用户每次手动打开 Codex/Claude 的聊天工具。

第一版只验证四件事：

1. **开机即在线**：Windows 登录后后台 Agent 与桌面角色自动启动。
2. **能聊**：支持文字聊天，默认走 GLM 5.3 Flash，也可切换 DeepSeek。
3. **能主动触发**：至少支持 Startup 与 Idle 两类本地事件。
4. **有本地内核**：由本地 Agent Core 负责聊天、语音、事件和记忆；Spark 先不纳入基础闭环。

## 2. 非目标

MVP 暂不做：TTS 双向语音、复杂 Live2D 动作、手机遥控、跨设备同步、全自动电脑控制、多 Agent 协作、插件市场、云端 24/7 部署、Spark Skills。

## 3. 系统架构

```text
Windows Login
    │
    ├── Avatar Runtime (Godot)
    │      └── 3D 角色 / 菜单 / 聊天气泡 / 动作表情
    │
    ├── Desktop Shell (Tauri)
    │      └── 托盘 / 设置 / 进程守护（隐藏运行）
    │
    └── Agent Core (本地后台进程)
           ├── Router
           ├── Event Engine
           ├── Memory (SQLite)
           ├── Permission Layer
           ├── GLM / DeepSeek Provider Adapter
           └── Speech-to-Text Adapter
```

### 为什么保留本地 Agent Core

本地 Core 负责模型调用、语音转写、开机自启、鼠标/键盘空闲检测、桌面通信、SQLite 和权限控制。它不依赖 Codex、Claude、CC Switch 或 Spark 进程，Provider 只通过配置切换。

## 4. MVP 功能范围

### P0：必须完成

- Windows 登录自启
- 后台 Agent Core 常驻
- 桌面二次元角色窗口
- 文字聊天
- GLM 5.3 Flash API 接入
- DeepSeek Provider 切换
- 语音转文字（按住说话，松开转写）
- `idle / thinking / speaking / working / error` 五种角色状态
- Startup Trigger
- Idle Trigger
- SQLite 保存最近对话、事件、任务状态
- 本地日志
- API Key 只从环境变量或本地 secrets 配置读取，不提交 Git

### P1：MVP 验证后加入

- TTS 语音回复
- Spark Adapter
- 1 个可重复 Skill，例如“总结指定文件夹中的文档”
- 简单 Schedule
- 本地文件只读能力
- 操作确认弹窗

### P2：后续版本

- 更高质量的语音 STT/TTS
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
3. Avatar Runtime 自动出现。
4. Core 发出 `SYSTEM_START`。
5. Core 判断是否需要主动说话。
6. 若没有有价值信息，保持安静；不要为了“主动”而主动。

### 场景 B：一般聊天

```text
用户输入
→ Agent Core Router
→ GLM 5.3 Flash / DeepSeek
→ 回复文本
→ Avatar Runtime 展示并驱动表情/动作
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
- 删除类操作：默认禁用，至今不存在。执行外部命令、修改文件自 2026-09-06 起由三档权限引擎收口：写入/命令走 ask 确认、路径越界硬拒、决策全审计。

## 8. 开发阶段

| Milestone | 当前状态 |
|---|---|
| 0 — Skeleton | 已完成 |
| 1 — Avatar Interaction & Chat | 基础闭环已完成；稳定 STT 待验收 |
| 2 — Always On | 未完成，当前只有开发机一键启动 |
| 3 — Proactive | 部分（启动问候已上线，含免打扰时段与冷却；Idle Trigger 未做） |
| 4 — Spark Spike | 暂缓，不阻塞本地闭环 |

### Milestone 0 — Skeleton

- 初始化 monorepo
- Tauri Desktop 空窗口
- Python Agent Core `/health`
- WebSocket 打通

验收：桌面壳能够显示 Core `online`。

### Milestone 1 — Avatar Interaction & Chat

- 输入框与气泡
- 角色点击菜单
- 互动动作菜单
- GLM Provider
- 语音转文字
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
- 用户能发送文本并得到 GLM 回复。
- 角色状态能随请求变化。
- Startup / Idle 至少两种事件被正确捕获。
- Agent 可选择不打扰用户。
- 对话和事件可在重启后恢复。
- GLM API Key 不进入 Git 历史。
- 角色点击后可使用聊天和互动菜单。
- 语音可以转成可编辑文本并发送。

## 10. 成本

本地 MVP 本身可以基本零新增基础设施成本。主要变量成本是 GLM/DeepSeek API；本地语音识别主要成本是模型存储和设备算力。未来增加 TTS、云端常驻、商用模型素材时再单独评估。
