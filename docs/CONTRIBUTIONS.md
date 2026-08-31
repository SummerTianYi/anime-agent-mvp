# Agent 贡献与维护范围声明

## 声明口径

本文件是项目所有者授权的工程归属与交接标记，用于让没有聊天上下文的人或 Agent 快速识别建设范围；它不是对 Git 历史作者、著作权或排他所有权的改写。项目所有者明确允许 Codex 将建仓、初始实现、接手前基线及后续主导工作统一标记为 Codex 建设范围，同样授权 Claude（Claude Code）按同一口径标记其建设范围，也允许并行 Agent 对有参与或接手的同一模块留下重叠声明。发生重叠时以具体提交、当前工作树和各 Agent 的补充记录判断最新维护责任，不删除彼此声明。

## Codex 建设范围

| 阶段/领域 | Codex 建设、主导或纳入维护的内容 | 代表文件或提交 |
|---|---|---|
| 建仓与产品定义 | 初始化仓库和脚本骨架；确定 Windows 本地优先、VTuber 式独立 3D 桌宠而非传统 Agent 窗口；明确 Godot Avatar + Python Core + 可选 Tauri 的边界 | `b8ccaa6`；`README.md`；`AGENTS.md` |
| 开发环境与启动 | 盘点并建立 Python 3.12 venv、Node/pnpm、Godot 4.7.2、Blender/MMD Tools/VRM 路径；一键启动、进程复用、端口检查和 Windows 本地路径文档 | `d748965`；`scripts/start-mvp.ps1`；`scripts/run-avatar-runtime.ps1`；`docs/LOCAL_DEV.md`；`docs/LOCAL_MACHINE.md` |
| 官模与资产管线 | 调研洛天依官方/创意工坊模型来源；完成本地 PMX/Blend/GLB 处理、官模哈希契约、表情与骨架识别、长马尾定位和多轮位置修正；坚持模型/纹理本地保存 | `docs/ASSET_PIPELINE.md`；`scripts/model-pipeline/*`；`scripts/check-local-assets.ps1` |
| Godot Avatar Runtime | 透明无边框置顶角色、点击穿透、拖动、转身、缩放、位置保存、表达式/口型、程序动作、Core WebSocket 桥和角色菜单 | `e34d621`；`apps/avatar-runtime/runtime.gd`；`apps/avatar-runtime/interaction_ui.gd` |
| 桌面画布与画质 | 工作区大小透明画布、固定光轴 2× SubViewport、二维合成移动、4× MSAA、高 DPI、最大缩放防裁切、透视回归与官模哈希门禁 | `apps/avatar-runtime/project.godot`；`apps/avatar-runtime/main.tscn`；`apps/avatar-runtime/verify_desktop_canvas.gd`；`docs/plans/MODEL_OPTIMIZATION.md` |
| 模型版本管理 | 建立 `1.0`/`1.1` 不可变本地 Blend/GLB 快照、Git 清单、结构/优化/视觉证据字段、哈希校验、资产切换和隔离 worktree 精确对比工具 | `model-versions/*`；`scripts/model-versions/*` |
| Agent Core 与 Provider | FastAPI/Uvicorn/WebSocket Core、GLM/DeepSeek/Mock 适配、GLM Coding 地址与 429 根因排查、本地路由验证、状态与角色事件桥 | `e34d621`；`services/agent-core/agent_core/*`；`docs/ARCHITECTURE.md`；`docs/AVATAR_BRIDGE.md` |
| 角色 Harness | 洛天依身份、自我认知、结构化情绪/动作输出契约、20 首原创曲种子库与按需检索注入，不包含翻唱和歌词 | `services/agent-core/agent_core/harness.py`；`services/agent-core/agent_core/data/luotianyi_original_songs.json` |
| 聊天、会话与本地记忆 | 洛天依主题聊天浮层、输入优先级、多会话协议、SQLite 历史与迁移、角色状态驱动；按项目所有者授权纳入 Codex 总体建设范围，允许并行 Agent 重叠声明 | `364d5d4`；`6d432aa`；`a094352`；相关 Core/UI 测试 |
| 动作管线 | BVH/FBX 动作可行性验证、旋转样片、8 秒待机、动作注册表、静态官模与动画容器分离、上/下半身语义层、两条完整马尾归入上半身并保留二级摆动 | `7cc6b74`；`b192291`；`docs/MOTION_PIPELINE.md`；`verify_motion_asset.gd`；`verify_motion_runtime.gd` |
| 测试与零上下文交接 | Python 单元测试、桌面构建、Godot 输入/动作/画布门禁、资产哈希、Bridge 验证、架构/已知问题/机器路径/测试与 HANDOFF 文档 | `38df44c`；`docs/HANDOFF.md`；`docs/TESTING.md`；`.github/workflows/ci.yml` |

## 本次推送边界

本次 Codex 提交包含语义动作层与马尾验证、透明桌面画布、固定光轴 SubViewport、画质/防裁切优化、相关回归测试、优化路线及本贡献声明。提交时明确排除另一位并行 Agent 尚未提交的倾听动作增量、唤醒词/Core 增量及其 `.gitignore` 调整；这些文件继续留在本地工作树，由对应 Agent 自行验证、标记和提交。`runtime.gd` 与 `interaction_ui.gd` 同时包含双方未提交行时，Codex 只分块暂存自己的行，不把对方增量夹带进本次提交。

## Claude 建设范围

声明日期：2026-08-31；声明 Agent：Claude（Claude Code / Fable 5）。以下为 Claude 自接手（`4179b23` 之前的工作树）以来建设、主导或纳入维护的全部内容，按项目所有者授权与 Codex 同等口径标记；与 Codex 重叠的共享文件只声明自己的增量。

| 阶段/领域 | Claude 建设、主导或纳入维护的内容 | 代表文件或提交 |
|---|---|---|
| 语音链路诊断 | 定位 Realtek 麦克风阵列驱动假死根因（设备持续输出静音数据，需外部事件复位），并写入已知问题与交接陷阱清单，作为后续 STT 与唤醒加固的共同前提 | `docs/KNOWN_ISSUES.md`；`docs/HANDOFF.md` Known traps |
| 聊天形态设计与文档 | 确立"角色为主体、聊天为底部浮层"的产品方向（不做全窗口网页化、不引入 Tauri）；设计终稿、archify 架构图、交互原型、头像定稿裁切 | `4179b23`；`docs/design/chat-form-upgrade.md`；`docs/design/chat-ui-mockup.html`；`docs/design/assets/*` |
| Core 多会话系统 | `sessions` 表 + `messages.conversation_id` 与启动自动迁移；按会话取历史替换进程级全局；`session.new` / `session.list` / `chat.history` 协议；会话存储单测 | `364d5d4`；`services/agent-core/agent_core/storage.py`；`agent_core/main.py`；`tests/test_storage.py` |
| 底部浮层聊天界面 | `interaction_ui.gd` 重写：洛天依主题、可滚动气泡、会话下拉与新开、头像气泡、空态提示；`runtime.gd` 协议接入；滚轮/右键输入优先级守卫（面板上让位 UI） | `6d432aa`；`apps/avatar-runtime/interaction_ui.gd`；`apps/avatar-runtime/runtime.gd` |
| 交接文档 2026-08-30 | HANDOFF 快照、AVATAR_BRIDGE 会话协议章节、TESTING 会话与输入优先级验收项、README 状态表 | `a094352`；`docs/HANDOFF.md`；`docs/AVATAR_BRIDGE.md`；`docs/TESTING.md`；`README.md` |
| 倾听动作样片（当前工作树） | 官方视频抽帧与转写参考解析；骨骼轴系叉积推导（修正肘弯/朝向/停顿三类判定）；`create_listen_motion.py`（12 上半身骨 + 20 指骨 + 手捩扭转 + 躯干前倾）；`listen` 注册条目、G 键与菜单触发、资产门扩为三 clip | `scripts/model-pipeline/create_listen_motion.py`；`apps/avatar-runtime/motion_registry.json`；`verify_motion_asset.gd`；`runtime.gd` / `interaction_ui.gd` 增量 |
| 唤醒词系统（当前工作树） | sherpa-onnx 中文 KWS 集成；"天依"KWS 触发 + whisper 转写同音容错确认（`嗨天依` 停顿免疫的两阶段唤醒流）；滚动音频缓冲；Realtek 假死静音看门狗；`wake.triggered` / `wake.idle` / `chat.user_message` 协议与 `/wake-test` 诊断端点；`ANIME_AGENT_WAKE_WORD` 开关 | `services/agent-core/agent_core/wake_word.py`；`agent_core/data/wake_tianyi.txt`；`agent_core/main.py`；`agent_core/voice.py`（调用点）；`runtime.gd` / `interaction_ui.gd` 增量 |
| 会话删除（当前工作树） | `delete_session`（末会话自动补建）；`session.delete` / `session.deleted` 协议；聊天头部删除按钮，单击弹出洛天依主题确认框（应用户要求从 3 秒双击确认改型） | `storage.py`；`main.py`；`interaction_ui.gd`；`tests/test_storage.py`；`tests/test_main_ws.py` |
| 方案目录与 Agent 化路线（docs/plans 提交） | 建立 `docs/plans/` 统一归档双方后续执行方案；将建模优化路线迁入该目录并修正全仓引用（仅迁移，Codex 未提交增量原样保留）；起草 AGENT_ROADMAP.md（工具调用循环、只读工具、权限层、MCP 宿主分期蓝图） | `docs/plans/AGENT_ROADMAP.md`；`docs/plans/MODEL_OPTIMIZATION.md`；`AGENTS.md`；`README.md`；`docs/HANDOFF.md` |
| 会话标题（当前工作树） | LLM 在首轮回复 JSON 的 `session_title` 字段生成 4-12 字标题（概括第一个问题），模型未提供时回退用户文本前 12 字；`rename_session` 存储 + `session.title` 协议事件 + Godot 下拉同步；非首轮不重命名 | `harness.py`；`main.py`；`storage.py`；`interaction_ui.gd`；`runtime.gd`；`tests/test_main_ws.py` |
| Agent 工具循环 A 期（当前工作树） | `tools.py` 六个只读工具（时间/读文件/列目录/截图/前台窗口/剪贴板）与 `ANIME_AGENT_TOOLS_ROOTS` 白名单；`agent_loop.py` 步数上限循环、结果截断、执行器异常与端点拒绝 tools 时的双级熔断降级；Provider `complete_with_tools`；`agent.tool` 协议事件、聊天状态行提示与 `/health` tools 观测；单测扩至 48 项（48/48 通过）并经真实 GLM 验证（时间/读文件/列目录工具往返、白名单 junction 双轨检查、输出契约尾部 JSON 恢复） | `services/agent-core/agent_core/tools.py`；`agent_core/agent_loop.py`；`agent_core/main.py`；`agent_core/harness.py`；`apps/avatar-runtime/runtime.gd` / `interaction_ui.gd` 增量；`tests/test_tools.py`；`tests/test_agent_loop.py` |
| 测试与仓库运维 | 会话/删除单测扩至 22 项（22/22 通过）；本仓库 git 局部代理；`.gitignore` 增补唤醒模型目录；设计文档 Drive 备份惯例 | `tests/test_storage.py`；`.gitignore`；`.git/config`（仅本地） |

### Claude 工作树边界

Claude 当前未提交的增量为：倾听动作（`create_listen_motion.py`、`motion_registry.json`、`verify_motion_asset.gd`、runtime/UI 触发行）、唤醒词（`wake_word.py`、`wake_tianyi.txt`、`main.py`、`voice.py`、`.gitignore`）、会话删除（`storage.py`、`main.py`、`test_storage.py`、runtime/UI 删除行）。`runtime.gd` 与 `interaction_ui.gd` 同时包含 Codex 的画布增量与 Claude 的唤醒/删除增量，提交时按 Codex 同一口径分块暂存自己的行，不夹带对方代码。倾听动作与唤醒词已分别通过离线管线验证与 `/wake-test` 活体链路验证，等待项目所有者真人语音验收后提交。Agent 工具循环（`tools.py`、`agent_loop.py`、main/harness 接线、Godot 状态行增量与配套测试）同样留在工作树，已通过离线单测与 Godot 无头门禁（当前全套 58/58，含 WS 会话全链路模拟测试），待项目所有者验收后一并提交。

## 后续 Agent 更新规则

1. 新 Agent 开工前先读本文件、`HANDOFF.md` 和当前 `git status`，不要仅凭聊天记录判断归属。
2. 追加自己的 Agent 名称、日期、模块和提交，不覆盖既有条目；允许按项目所有者授权声明重叠贡献。
3. 并行开发时优先按文件或补丁块分离提交；共享文件必须检查 staged diff，避免把他人的未完成代码带入。
4. 贡献声明不替代验证。任何“完成”仍以 `docs/TESTING.md` 的当前门禁和远端提交为准。
