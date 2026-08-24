# Anime Agent MVP

一个 **Windows 本地优先、开机即在线** 的二次元桌面 Agent MVP。

## 核心定位

- **Codex**：主要开发工具，不作为最终运行时载体。
- **Spark**：目标 Agent 内核 / 长任务与 Skills 编排层；通过适配器接入，避免项目与单一平台强绑定。
- **Gemini Flash API**：日常聊天、意图判断、简单推理等高频任务接口。
- **本地后台服务**：负责开机自启、事件监听、记忆、权限与桌面壳通信，保证无需手动打开 Codex 即可运行。

## MVP 一句话目标

> Windows 登录后，二次元角色自动出现；后台 Agent 已经在线；用户可直接文字交互；Agent 可调用 Gemini 处理一般任务，并对开机/空闲等本地事件做有限主动响应。

详细方案见 [`docs/MVP.md`](docs/MVP.md)。

## 建议技术栈

- Desktop：Tauri + React + TypeScript
- Agent Core：Python 3.12 + FastAPI/WebSocket
- Memory：SQLite
- LLM：Gemini Flash API
- Agent Kernel：Spark Adapter（先验证可用接入路径）
- Packaging：Windows 安装包 + 登录自启

## 初始目录

```text
anime-agent-mvp/
├─ apps/desktop/          # 二次元桌面壳
├─ services/agent-core/   # 本地常驻 Agent 服务
├─ packages/shared/       # 公共类型/协议
├─ config/                # 本地配置模板
├─ scripts/               # 安装、自启、开发脚本
├─ docs/MVP.md            # MVP 方案
└─ AGENTS.md              # Codex 开发约束
```

## 当前状态

- [x] MVP 方案
- [x] 初始架构决策
- [ ] Spark 接入可行性验证
- [ ] Desktop Shell
- [ ] Agent Core
- [ ] Gemini API
- [ ] 开机自启
- [ ] Idle Trigger
- [ ] MVP 联调
