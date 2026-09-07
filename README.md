# Anime Agent MVP

这是一个 Windows 本地优先的 3D 二次元桌面角色 MVP，产品形态是类似 VTuber 的独立桌面角色，而不是 Codex、Claude 或传统聊天窗口的复制品。当前角色由 Godot 渲染，点击角色可打开"聊天 / 互动"菜单，文字或语音输入由本地 Python Agent Core 处理，默认调用 GLM 5.3 Flash，回复中的情绪和动作元数据会驱动模型表情与骨骼动作；Codex、Claude、zcode 等 Agent 只用于开发，不是生产运行时依赖。

## 当前结论

| 范围 | 状态 | 说明 |
|---|---|---|
| 3D 桌面角色 | 已完成基础闭环 | 默认使用当前屏幕工作区大小的透明穿透画布；角色在固定光轴的 2× SubViewport 中渲染，再作为二维透明层拖动，避免离轴"压扁"和旧 560×760 窗口裁切；支持转身、缩放、位置保存与 `compact` 回退模式 |
| 角色菜单 | 已完成 | 点击角色打开聊天或互动菜单 |
| 聊天界面 | 已完成并真实验证 | 底部半透明浮层，洛天依主题、气泡可滚动，支持新开/切换/删除会话与历史回载 |
| 文字聊天 | 已完成并真实验证 | 多会话；Godot → WebSocket → Core → GLM 5.3 Flash → Godot |
| 角色 Harness | 已完成两轮 | 洛天依身份、自我认知、结构化回复、表情与动作映射；2026-09-05 注入训练版新剧本（旧剧本保留可回退） |
| 歌曲知识 | 已完成种子库 | 20 首原创曲，本地检索后按需注入，不包含翻唱和歌词 |
| 表情与动作 | 已完成动作注册表与首个待机 | 48 个形变槽；12.47 秒单目动捕待机（idle_mocap_v1）自动循环，旋转样片可按 `P` 打断并在结束后自动回待机，详见 [`docs/MOTION_PIPELINE.md`](docs/MOTION_PIPELINE.md) |
| 本地记忆 | 已完成 agent 化 | SQLite 按会话保存消息 + facts 事实表；`memory_candidate` 按敏感度分级落库，词法检索注入聊天上下文 |
| 语音转文字 | 管线可用，驱动假死自愈待加固 | sounddevice + faster-whisper；已定位 Realtek 麦克风阵列驱动假死根因（设备持续输出静音数据，需外部事件复位），`voice.py` 自愈加固未做 |
| TTS 语音输出 | 已完成 | GPT-SoVITS sidecar（真实声线）、分片合成、三路打断、工作解说；sidecar 缺席时自动回退文字 |
| Agent 能力层 | 已完成（考试授权制） | allow/ask/deny 权限引擎、只读工具六件套、write_file 原子写（T1 考试 3/3）、真实目录放权（T2 3/3）、run_command 白名单（T3）、MCP 宿主（C 考试）、每工具类型工作解说、主动问候（免打扰+冷却）；详见 [`docs/TEST_REPORT_2026-09-06.md`](docs/TEST_REPORT_2026-09-06.md) |
| 一键启动 | 已完成开发机版本 | 根目录双击 `start-anime-agent.cmd`，Core 隐藏运行、Avatar 独立出现 |
| Windows 登录自启、守护 | 未完成 | 尚未做安装器、登录任务和崩溃恢复（M3 主战场） |
| Idle 触发、键鼠控制、Spark | 未完成 | Idle 属 D 期剩余；键鼠按蓝图缓行需先设考试；Spark 暂缓 |

## 零上下文接手

新 Agent 不应根据旧聊天记录猜测项目状态。**先读 [`docs/HANDOFF.md`](docs/HANDOFF.md)（接手总纲：最终目标、三方分工与交接史、当前真实状态/冻结区清单、编号对照表、铁律与白纸测试门禁）**，再读 [`AGENTS.md`](AGENTS.md) 与 [`docs/CONTRIBUTIONS.md`](docs/CONTRIBUTIONS.md)（归属声明），然后按任务查阅 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)、[`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md)、[`docs/ASSET_PIPELINE.md`](docs/ASSET_PIPELINE.md)、[`docs/MOTION_PIPELINE.md`](docs/MOTION_PIPELINE.md)、[`docs/plans/`](docs/plans/)（AGENT_ROADMAP 已加状态列；MODEL_OPTIMIZATION 为官模优化路线；LONG_TERM 为跨仓长期方案）、[`model-versions/README.md`](model-versions/README.md)、[`docs/TESTING.md`](docs/TESTING.md)、[`docs/VERIFICATION_SPEC.md`](docs/VERIFICATION_SPEC.md) 与 [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md)。当前机器的受限模型、工具和兄弟工作区位置集中记录在 [`docs/LOCAL_MACHINE.md`](docs/LOCAL_MACHINE.md)，其中不包含密钥、Cookie 或用户对话。

## 一键启动

首次准备请复制 `.env.example` 为 `.env` 并填写所选 Provider 的 Key，然后在仓库根目录双击 `start-anime-agent.cmd`，或执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-mvp.ps1`。启动器不依赖 pnpm，但依赖已安装的 `services/agent-core/.venv`、Godot 4.7.2 和本地模型 `apps/avatar-runtime/assets/luotianyi_v4.glb`；完整安装和验证命令见 [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md)。

## 技术栈

| 层 | 技术 |
|---|---|
| Avatar Runtime | Godot 4.7.2 + GDScript + GLB |
| Agent Core | Python 3.12 + FastAPI + Uvicorn + WebSocket |
| LLM | GLM 5.3 Flash Coding API；DeepSeek 可切换；Mock 可离线调试 |
| Harness | 角色系统提示词 + JSON 输出契约 + 本地原创曲检索 + 记忆注入 |
| Agent 能力 | 工具循环 + allow/ask/deny 权限引擎 + MCP stdio 宿主 + 主动触发 |
| Voice | sounddevice + faster-whisper（STT）；GPT-SoVITS sidecar（TTS） |
| Persistence | SQLite WAL，默认 `%LOCALAPPDATA%\AnimeAgent\data` |
| Optional Desktop Shell | Tauri 2 + React 19 + TypeScript 5.9 + Vite 7 |
| Model Pipeline | Blender 5.2.1 LTS + MMD Tools 4.5.13 + VRM 4.5.0 |

## 仓库边界

`.env`、API Key、SQLite、日志、用户记忆、模型、纹理、PMX/VRM/Blend、中间渲染、依赖目录和下载凭据均不得进入 Git。洛天依运行模型因文件大小和再分发授权边界只保存在本地；仓库提供确定的路径、哈希、处理脚本和检查方法，使同一开发机上的其他 Agent 能直接继续，同时避免把受限资产写入公开历史。
