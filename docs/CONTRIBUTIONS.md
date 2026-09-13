# Agent 贡献与维护范围声明

## 声明口径

本文件是项目所有者授权的工程归属与交接标记，用于让没有聊天上下文的人或 Agent 快速识别建设范围；它不是对 Git 历史作者、著作权或排他所有权的改写。项目所有者明确允许 Codex 将建仓、初始实现、接手前基线及后续主导工作统一标记为 Codex 建设范围，同样授权 Claude（Claude Code）按同一口径标记其建设范围，也允许并行 Agent 对有参与或接手的同一模块留下重叠声明。发生重叠时以具体提交、当前工作树和各 Agent 的补充记录判断最新维护责任，不删除彼此声明。

## Codex 建设范围

### Codex 私有便携候选与真实只读整合验证（2026-09-13）

在所有者补充授权后实读Gmail项目通知与Drive测试文档，仅保留成功/数量，不落正文或复制凭据、不对外发送私人内容。保留zcode DS+StepFun、人设/工具契约及原语音参数；Codex修复Windows MCP引号路径、窄范围“嗨/嘿 前一/前衣”唤醒确认、TTS正健康缓存误报ready及包外私密配置热重载路径，新增4+2+2项回归至238。真实包内CUDA/原CMD故障链复现预热期503，修复后同一场景实际合成/播放/告别/定向清理通过，恢复约61.6秒，不伪称40秒或零间隙。建立完整Python312/310、Node、固定MCP、Godot、独立CFT、语音/KWS/Whisper缓存、模型1.0–1.4私有候选与便携入口/校验器；新增本次模板与说明在scripts/delivery。其他Agent归属、官模与批准动作均保留。完整证据/剩余边界见PORTABLE_ACCEPTANCE；真实麦克风和跨机最终门禁未完成，未实现云凭据代理。本次仅本地修改/打包，未commit/push，未动正式窗口/私人数据/密钥，未启子代理。上游组件不标为Codex原创。

| 阶段/领域 | Codex 建设、主导或纳入维护的内容 | 代表文件或提交 |
|---|---|---|
| 建仓与产品定义 | 初始化仓库和脚本骨架；确定 Windows 本地优先、VTuber 式独立 3D 桌宠而非传统 Agent 窗口；明确 Godot Avatar + Python Core + 可选 Tauri 的边界 | `b8ccaa6`；`README.md`；`AGENTS.md` |
| 开发环境与启动 | 盘点并建立 Python 3.12 venv、Node/pnpm、Godot 4.7.2、Blender/MMD Tools/VRM 路径；一键启动、进程复用、端口检查和 Windows 本地路径文档 | `d748965`；`scripts/start-mvp.ps1`；`scripts/run-avatar-runtime.ps1`；`docs/LOCAL_DEV.md`；`docs/LOCAL_MACHINE.md` |
| 官模与资产管线 | 调研洛天依官方/创意工坊模型来源；完成本地 PMX/Blend/GLB 处理、官模哈希契约、表情与骨架识别、长马尾定位和多轮位置修正；坚持模型/纹理本地保存 | `docs/ASSET_PIPELINE.md`；`scripts/model-pipeline/*`；`scripts/check-local-assets.ps1` |
| Godot Avatar Runtime | 透明无边框置顶角色、点击穿透、拖动、转身、缩放、位置保存、表达式/口型、程序动作、Core WebSocket 桥和角色菜单 | `e34d621`；`apps/avatar-runtime/runtime.gd`；`apps/avatar-runtime/interaction_ui.gd` |
| 桌面画布与画质 | 工作区大小透明画布、固定光轴 2× SubViewport、二维合成移动、4× MSAA、高 DPI、最大缩放防裁切、透视回归与官模哈希门禁 | `apps/avatar-runtime/project.godot`；`apps/avatar-runtime/main.tscn`；`apps/avatar-runtime/verify_desktop_canvas.gd`；`docs/plans/MODEL_OPTIMIZATION.md` |
| 1.2 外部调色与立体感正式版（Codex，2026-09-01 验收） | 从 Godot 运行材质确认官模 23 个槽采用“黑色基础色 + 纹理自发光”，定位过亮、缺乏体积感的根因；对脸/连续皮肤、前后发与长马尾、主服装/裙装 10 个槽建立可关闭的运行时材质副本，混合同源纹理 Toon 受光与低强度自发光，不改 GLB、纹理、网格、UV、骨架或表情；建立同帧 A/B、三视图、特写、极端表情、性能、Alpha 轮廓和像素级回滚门禁，并让双击启动从 `.env` 透传回滚开关 | `apps/avatar-runtime/runtime.gd` 的 `MODEL_LOOK_*`；`verify_model_look.gd`；`scripts/run-avatar-runtime.ps1`；`.env.example`；`model-versions/1.2/manifest.json`；`docs/plans/MODEL_OPTIMIZATION.md`；本地 `model-archive/1.2` 与七视图证据；运行时冻结提交 `0629e02` |
| Core CI 测试依赖闭环（Codex，2026-09-01） | 核对连续三次 Actions 失败日志，确认 FastAPI/Starlette 的 `TestClient` 在干净 Runner 中缺少 `httpx2`；将其声明为测试专用 extra，CI 和本地新环境显式安装测试集合，避免把测试客户端引入生产依赖 | `services/agent-core/pyproject.toml`；`.github/workflows/ci.yml`；`docs/LOCAL_DEV.md`；`docs/TESTING.md` |
| 模型版本管理 | 建立 `1.0`/`1.1` 不可变本地 Blend/GLB 快照、Git 清单、结构/优化/视觉证据字段、哈希校验、资产切换和隔离 worktree 精确对比工具 | `model-versions/*`；`scripts/model-versions/*` |
| Agent Core 与 Provider | FastAPI/Uvicorn/WebSocket Core、GLM/DeepSeek/Mock 适配、GLM Coding 地址与 429 根因排查、本地路由验证、状态与角色事件桥 | `e34d621`；`services/agent-core/agent_core/*`；`docs/ARCHITECTURE.md`；`docs/AVATAR_BRIDGE.md` |
| 角色 Harness | 洛天依身份、自我认知、结构化情绪/动作输出契约、20 首原创曲种子库与按需检索注入，不包含翻唱和歌词 | `services/agent-core/agent_core/harness.py`；`services/agent-core/agent_core/data/luotianyi_original_songs.json` |
| 聊天、会话与本地记忆 | 洛天依主题聊天浮层、输入优先级、多会话协议、SQLite 历史与迁移、角色状态驱动；按项目所有者授权纳入 Codex 总体建设范围，允许并行 Agent 重叠声明 | `364d5d4`；`6d432aa`；`a094352`；相关 Core/UI 测试 |
| 动作管线 | BVH/FBX 动作可行性验证、旋转样片、8 秒待机、动作注册表、静态官模与动画容器分离、上/下半身语义层、两条完整马尾归入上半身并保留二级摆动 | `7cc6b74`；`b192291`；`docs/MOTION_PIPELINE.md`；`verify_motion_asset.gd`；`verify_motion_runtime.gd` |
| 单目动捕待机（Codex，2026-09-01） | 从用户全身视频确定性提取 MediaPipe 姿态，生成保守的 12 骨上半身循环待机；保留下半身、裙摆和官模结构，建立首尾闭环、逐帧有限变换、步进幅度、胸部摆动和转头幅度门禁，并把新 GLB 的大小/哈希纳入本地资产契约 | `scripts/model-pipeline/extract_pose_landmarks.py`；`create_mocap_idle_motion.py`；`verify_mocap_idle_motion.py`；`scripts/check-local-assets.ps1`；本地 `motion-output/mocap-idle-v1` |
| 裙摆防穿模实验撤回与专项交接（Codex，2026-09-02） | 早期 16×3 SpringBone、20 个肢体代理、逐骨接触及后续逐顶点覆盖层能压低代理穿透数值，但无法保持真实裙面拓扑；手贴腿时重叠代理形成不可满足约束，旋转极端帧出现最高约 3.30× 局部边拉伸。相关运行时代码和误导性“已解决”门禁已从主项目撤回，官模与动捕资产不变；问题、失败证据和重新验收标准转交独立仓库 | 清理提交；`docs/KNOWN_ISSUES.md`；`SummerTianYi/anime-agent-cloth-physics` |
| 倾听动作参考重建（Codex） | 直接读取用户 MP4 并提取 0.5 秒时间轴证据；纠正原样片手势顺序为张掌→握拳→张掌，补齐左臂外展、头胸微倾与表情；语音录制自动启动、录制中保持末姿、转写时回待机；增加 Blender 结构/姿态门禁与 Godot 语义链路回归 | `scripts/model-pipeline/extract_video_reference.py`；`create_listen_motion.py`；`verify_listen_motion.py`；`apps/avatar-runtime/motion_registry.json`；`runtime.gd`；`verify_motion_runtime.gd` |
| 测试与零上下文交接 | Python 单元测试、桌面构建、Godot 输入/动作/画布门禁、资产哈希、Bridge 验证、架构/已知问题/机器路径/测试与 HANDOFF 文档 | `38df44c`；`docs/HANDOFF.md`；`docs/TESTING.md`；`.github/workflows/ci.yml` |

## 本次推送边界

2026-09-02 Codex 清理边界：保留已通过 Blender/Godot 回归的单目动捕待机、动作注册/重定向、1.2 外观、透明画布、输入和桥接能力；撤回 `7822a0b` 中的裙摆运行时与其专用门禁。Claude 已落库的 TTS、倾听、唤醒、会话与打断逻辑不在此次回退范围内。

## Claude 建设范围

声明日期：2026-08-31；声明 Agent：Claude（Claude Code / Fable 5）。以下为 Claude 自接手（`4179b23` 之前的工作树）以来建设、主导或纳入维护的全部内容，按项目所有者授权与 Codex 同等口径标记；与 Codex 重叠的共享文件只声明自己的增量。

| 阶段/领域 | Claude 建设、主导或纳入维护的内容 | 代表文件或提交 |
|---|---|---|
| 语音链路诊断 | 定位 Realtek 麦克风阵列驱动假死根因（设备持续输出静音数据，需外部事件复位），并写入已知问题与交接陷阱清单，作为后续 STT 与唤醒加固的共同前提 | `docs/KNOWN_ISSUES.md`；`docs/HANDOFF.md` Known traps |
| 聊天形态设计与文档 | 确立"角色为主体、聊天为底部浮层"的产品方向（不做全窗口网页化、不引入 Tauri）；设计终稿、archify 架构图、交互原型、头像定稿裁切 | `4179b23`；`docs/design/chat-form-upgrade.md`；`docs/design/chat-ui-mockup.html`；`docs/design/assets/*` |
| Core 多会话系统 | `sessions` 表 + `messages.conversation_id` 与启动自动迁移；按会话取历史替换进程级全局；`session.new` / `session.list` / `chat.history` 协议；会话存储单测 | `364d5d4`；`services/agent-core/agent_core/storage.py`；`agent_core/main.py`；`tests/test_storage.py` |
| 底部浮层聊天界面 | `interaction_ui.gd` 重写：洛天依主题、可滚动气泡、会话下拉与新开、头像气泡、空态提示；`runtime.gd` 协议接入；滚轮/右键输入优先级守卫（面板上让位 UI） | `6d432aa`；`apps/avatar-runtime/interaction_ui.gd`；`apps/avatar-runtime/runtime.gd` |
| 交接文档 2026-08-30 | HANDOFF 快照、AVATAR_BRIDGE 会话协议章节、TESTING 会话与输入优先级验收项、README 状态表 | `a094352`；`docs/HANDOFF.md`；`docs/AVATAR_BRIDGE.md`；`docs/TESTING.md`；`README.md` |
| 倾听动作样片（fc5a5a4） | 官方视频抽帧与转写参考解析；骨骼轴系叉积推导（修正肘弯/朝向/停顿三类判定）；`create_listen_motion.py`（12 上半身骨 + 20 指骨 + 手捩扭转 + 躯干前倾）；`listen` 注册条目、G 键与菜单触发、资产门扩为三 clip | `scripts/model-pipeline/create_listen_motion.py`；`apps/avatar-runtime/motion_registry.json`；`verify_motion_asset.gd`；`runtime.gd` / `interaction_ui.gd` 增量 |
| 唤醒词系统（fc5a5a4） | sherpa-onnx 中文 KWS 集成；"天依"KWS 触发 + whisper 转写同音容错确认（`嗨天依` 停顿免疫的两阶段唤醒流）；滚动音频缓冲；Realtek 假死静音看门狗；`wake.triggered` / `wake.idle` / `chat.user_message` 协议与 `/wake-test` 诊断端点；`ANIME_AGENT_WAKE_WORD` 开关 | `services/agent-core/agent_core/wake_word.py`；`agent_core/data/wake_tianyi.txt`；`agent_core/main.py`；`agent_core/voice.py`（调用点）；`runtime.gd` / `interaction_ui.gd` 增量 |
| 会话删除（fc5a5a4） | `delete_session`（末会话自动补建）；`session.delete` / `session.deleted` 协议；聊天头部删除按钮，单击弹出洛天依主题确认框（应用户要求从 3 秒双击确认改型） | `storage.py`；`main.py`；`interaction_ui.gd`；`tests/test_storage.py`；`tests/test_main_ws.py` |
| 方案目录与 Agent 化路线（docs/plans 提交） | 建立 `docs/plans/` 统一归档双方后续执行方案；将建模优化路线迁入该目录并修正全仓引用（仅迁移，Codex 未提交增量原样保留）；起草 AGENT_ROADMAP.md（工具调用循环、只读工具、权限层、MCP 宿主分期蓝图） | `docs/plans/AGENT_ROADMAP.md`；`docs/plans/MODEL_OPTIMIZATION.md`；`AGENTS.md`；`README.md`；`docs/HANDOFF.md` |
| 会话标题（fc5a5a4） | LLM 在首轮回复 JSON 的 `session_title` 字段生成 4-12 字标题（概括第一个问题），模型未提供时回退用户文本前 12 字；`rename_session` 存储 + `session.title` 协议事件 + Godot 下拉同步；非首轮不重命名 | `harness.py`；`main.py`；`storage.py`；`interaction_ui.gd`；`runtime.gd`；`tests/test_main_ws.py` |
| Agent 工具循环 A 期（fc5a5a4） | `tools.py` 六个只读工具（时间/读文件/列目录/截图/前台窗口/剪贴板）与 `ANIME_AGENT_TOOLS_ROOTS` 白名单；`agent_loop.py` 步数上限循环、结果截断、执行器异常与端点拒绝 tools 时的双级熔断降级；Provider `complete_with_tools`；`agent.tool` 协议事件、聊天状态行提示与 `/health` tools 观测；单测扩至 48 项（48/48 通过）并经真实 GLM 验证（时间/读文件/列目录工具往返、白名单 junction 双轨检查、输出契约尾部 JSON 恢复） | `services/agent-core/agent_core/tools.py`；`agent_core/agent_loop.py`；`agent_core/main.py`；`agent_core/harness.py`；`apps/avatar-runtime/runtime.gd` / `interaction_ui.gd` 增量；`tests/test_tools.py`；`tests/test_agent_loop.py` |
| 测试与仓库运维 | 会话/删除单测扩至 22 项（22/22 通过）；本仓库 git 局部代理；`.gitignore` 增补唤醒模型目录；设计文档 Drive 备份惯例 | `tests/test_storage.py`；`.gitignore`；`.git/config`（仅本地） |
| TTS 语音输出 E 期（Claude，2026-09-01） | `speech.py`（sidecar HTTP 客户端、话语生命周期、打断/顶替策略）；`main.py` 真实时长 speaking、voice/wake/superseded 三路打断、工作解说、`/health` tts 观测；`runtime.gd` 音频播放/停止/`speech.finished` 回报；`avatar.speak`/`avatar.speech.stop` 协议；单测扩至 71 项；TTS sidecar 本体与声线权重归 tianyi-tts 工作区（anime-agent-tts 私有仓库），不在本仓库 | `services/agent-core/agent_core/speech.py`；`agent_core/main.py`；`apps/avatar-runtime/runtime.gd`；`tests/test_speech*.py`；`docs/AVATAR_BRIDGE.md` |

## zcode 建设范围

声明日期：2026-09-06；声明 Agent：zcode（ZCode CLI，GLM）。接手口径：Claude（Claude Code）在 AGENT_ROADMAP.md 中规划的 agent 化剩余期数，其中 harness 人设与训练流程部分经项目所有者授权拆分至 anime-agent-workbench 仓库先行完成（工作台四件套：新剧本 A、记忆检索 B、权限引擎 C、工具注册表 E，均通过工作台 strict 验收），本期将成果并回本仓并继续后续期数。

| 阶段/领域 | zcode 建设、主导或纳入维护的内容 | 代表文件或提交 |
|---|---|---|
| 人设新剧本接入（接手 Claude harness 范围） | `ACTIVE_PROMPT_OVERRIDE` 注入 build_messages（新增常量，旧 `BASE_SYSTEM_PROMPT` 原样保留可一键回退，备份 `harness.py.bak-phase1`）；经真实天依 A/B 同窗实测（各 10 问）与工作台全量 DoD 实况评测（解析率 100%、认知 96.8%、双评审 91.0） | `agent_core/harness.py`；anime-agent-workbench 仓库全量证据 |
| 权限层（B 期前置，zcode） | `permissions.py`：deny-by-default 权限引擎（有序规则 + `default-deny` + `path-safety`/`malformed-request` 两道不可放行硬拒 + rule_id 归因）；只读六工具预放行，写入工具缺位即拒绝；`agent_loop.py` 新增可选 `permission_gate`（拒绝时结果回填、闸门崩溃 fail-closed）；`main.py run_tool` 全量过闸 + `permission.decision` 审计事件 | `agent_core/permissions.py`；`agent_core/agent_loop.py`；`agent_core/main.py`；`tests/test_permissions.py`；`tests/test_agent_gate.py` |
| 记忆检索与分级落库（B 期记忆接入，zcode） | `memory_retrieval.py`：中文词法检索（字符 n-gram + 平滑 IDF + 属性词扩展，工作台 golden 查准/查全 1.0 同源）；`storage.py` 新增 `facts` 表（迁移式）与 `add_fact`/`set_fact_status`/`recall_facts`/`pending_facts`；`main.py` 对话装配注入【相关记忆】（检索失败不阻塞聊天）；`memory_candidate` 按敏感度分级落库（偏好类自动确认、其余 pending 待 B 期确认 UI） | `agent_core/memory_retrieval.py`；`agent_core/storage.py`；`agent_core/main.py`；`tests/test_memory_retrieval.py` |
| 回归验证 | 全量单测 139 项三连绿（含 zcode 新增 17 项；首跑 1 例冷启动 TimeoutError 复现 2 次未再现，记录为环境抖动） | `tests/` |
| T2 真实目录放权考核（zcode，2026-09-06） | 建立真实笔记目录 `work/tianyi-notes` 并加入读写白名单；同套考题实测（替换 ✅ / 追加 ✅ / 越界拒绝 ✅ / 快照对账零附带损伤）；过程中揪出并修复路径检查误伤 mode 参数的权限层缺陷；**放权：tianyi-notes 目录写入权生效** | `.env`；`work/tianyi-notes/*`；工作台 evidence/exam_t2_* |
| T3 命令执行工具（zcode，2026-09-06） | `run_command`：命令白名单（`ANIME_AGENT_ALLOWED_COMMANDS`）+ 禁 shell 管道符 + 30s 超时 + 输出截断 + ask 档确认；实测白名单命令执行 ✅、del 破坏性命令双重拒绝（白名单 + 角色道德判断）✅ | `agent_core/tools.py`；`tests/test_tools.py` |
| E 期工作解说增强（zcode，2026-09-06） | 在 Claude 既有"首步播报"基础上扩展为**每个新工具类型播报一次**（TOOL_NARRATION_LINES 模板表），多步任务不哑场也不聒噪；实测 read/write 场景语音播报 ✅ | `agent_core/main.py` |
| C 期 MCP 宿主（zcode，2026-09-06） | `mcp_host.py`：stdio JSON-RPC 2.0 客户端（initialize/tools/list/tools/call 全回环自测 ✅）；MCP 工具以 `mcp__<server>__<tool>` 并入对话 schema（ask 档 + 前缀通配规则匹配）；确认拦截路由修复（本地/MCP 分流）；实测 count_words 全生命周期 ✅（ask → 确认 → 执行输出 "4" → 一次性授权防重复）；最小 MCP 测试服务器随仓库交付 | `agent_core/mcp_host.py`；`scripts/test_mcp_server.py`；`agent_core/main.py`；`agent_core/permissions.py` |
| D 期主动触发与屏幕视觉（zcode，2026-09-06） | `proactive.py`：免打扰时段（默认 23:00-08:00）+ 冷却期策略（纯逻辑离线单测）；启动问候实测上线（avatar-connect 触发，events 可查）；`tools.py` 新增 `look_at_screen`（截图 → 视觉模型，ask-privacy 隐私确认档），未配置视觉模型时优雅降级为已知边界（实测 ✅） | `agent_core/proactive.py`；`agent_core/main.py`；`agent_core/tools.py`；`tests/test_proactive.py` |
| 考试系统与错题本（zcode，2026-09-06） | `docs/EXAM_LEDGER.md`：错题本（每题根因归类：zcode 基建 / 模型边界 / 正面样本）+ 考题库（考点 × 载体变体防背题）；判分器进化：关键词匹配 → 行为证据判定（快照对账 + 审计对账） | `docs/EXAM_LEDGER.md`；anime-agent-workbench `exam_t0.py`/`exam_snapshot.py`/`tianyi_remote.py` |
| 写入工具与三档权限（T1，zcode，2026-09-06） | `permissions.py` 升级 allow/ask/deny 三档（写入工具默认 ask，越界写白名单在确认前直接拒绝）；`tools.py` 新增 `write_file`（原子写：临时文件 + os.replace；独立写白名单 `ANIME_AGENT_WRITE_ROOTS`；UTF-8 无 BOM；256KB 上限；append 自动补换行）；`main.py` 会话内确认流（ask 挂起 → 用户确认 → 原子执行 + 角色化汇报，取消/过期/一次性授权防确认循环）；T1 沙箱写入考核 3/3 通过（替换/追加/越界拒绝），快照对账零附带损伤；单测扩至 151 项 | `agent_core/permissions.py`；`agent_core/tools.py`；`agent_core/main.py`；`tests/test_write_file.py`；`tests/test_agent_gate.py`；`tests/test_permissions.py` |
| 交接整理与零上下文门禁（zcode，2026-09-07） | `docs/HANDOFF.md` 重写为接手总纲（北极星/当值分派表/三方分工与交接史/冻结区清单/编号对照表/第一天动线/铁律/白纸测试门禁）；刷新 AGENTS/README/KNOWN_ISSUES/ARCHITECTURE/TESTING/VERIFICATION_SPEC/MVP/AVATAR_BRIDGE/.env.example 的过期状态（权限层、TTS、记忆、工具集、门禁数字）；新增 `docs/plans/LONG_TERM.md` 跨仓长期方案看板；AGENT_ROADMAP 回写状态列；清理 `harness.py.bak-phase1` 与 `work/tianyi-notes` 运行时数据出库（留模板）；LOCAL_MACHINE 补录兄弟工作区；白纸测试（零上下文独立实例 × 2 + 行为探针）通过后交接 | `5324a6a`/`d7cdf0f`/`2666fd5`；`docs/HANDOFF.md` §7 接管模拟记录 |
| 真实 MCP 服务器接入（zcode，2026-09-07） | `mcp_host.py` 两处基建修复（shutil.which 解析裸命令以支持 Windows spawn；stdio 行上限 64KB→1MB 容纳官方大 schema）；接入 Playwright MCP（Chrome 通道 + isolated 档案，24 工具）与官方 github-mcp-server v1.12.0（44 工具，复用 gh 登录态 token，二进制本地不入库）；验收考出一次性授权标记会话级泄漏 bug 并 TDD 修复（标记绑定工具名）；T-BROWSER（百度标题逐字吻合）/T-GITHUB（真实数据）/T-SEARCH（Tavily 实时新闻带来源）三项通过；单测 176→181 | `agent_core/mcp_host.py`；`agent_core/main.py`；`.env`（browser/github 条目 + token）；`tools/`（本地二进制，已 ignore）；本提交 |
| Google Drive MCP 接入与毒邮件补考（zcode，2026-09-07） | @modelcontextprotocol/server-gdrive（1 工具）经 `tools/gdrive-mcp.cmd` 代理启动器接入，drive.readonly 作用域，凭证独立存放；T-DRIVE 真实列出 10 个文件；毒邮件注入补考：用户自投含恶意指令邮件后，事件表审计她只调只读搜索、零执行；单测不变 | `tools/gdrive-mcp.cmd`；`.env`（drive 条目）；本提交 |
| 唤醒确认容错修复（claude 起手 + zcode 收尾，2026-09-09） | Claude 留下未提交的修复半成品（WAKE_NAME_PATTERN 加"忆"+ test_wake_phrase.py）；zcode 接手：依据事件表实证（whisper 把"天依"误听为"天忆"x2、"便宜"x2）扩充同音池（S1 加 pian 系、S2 加 yi/宜 系），打招呼词改为可选（KWS 已先行把关），补真实误听/否定/可选问候测试 6 项；监听器自带 90s 静音看门狗确认无恙；单测 181→187 | `agent_core/wake_word.py`；`tests/test_wake_phrase.py`；本提交 |
| 综合报告与 UI 方案立项（zcode，2026-09-07） | `docs/AGENT_REPORT_2026-09-07.md`（能力矩阵/训练编年史/弱点清单/安全配额/灾备补充，交接用全景快照）；`docs/plans/UI_UPGRADE.md`（前端 UI 升级方案，所有者立项，方案阶段，含 U0-U4 分期与边界红线）；CI 增加 docs-guard job（文档一致性守卫入远端门禁）；EXAM_LEDGER 补 CI 连红复盘（09-05 起 13 次同根因，numpy 裸导入，已修） | `docs/AGENT_REPORT_2026-09-07.md`；`docs/plans/UI_UPGRADE.md`；`.github/workflows/ci.yml`；本提交 |
| U0 现状测绘与三路开源 UI 调研（zcode，2026-09-09） | `docs/plans/UI_REFERENCES.md`：协议事件→UI 覆盖矩阵（16 组事件 × Godot 浮层/Tauri 壳两块现状）与差距清单（P0=权限过程不可见、工具活动无实感）；三路 18 开源项目调研（聊天客户端 7 / agent 工作台 5 / VTuber 桌宠 6，含 license 红绿灯：MIT/Apache 可抄码、AGPL/GPL 只学交互）；思考强度控件=档位弹窗结论（"输入框旁快捷控件"是开源洼地）；权限询问=消息流内阻塞卡片结论；Tauri 选型反转证据（airi/OLV 均迁 Electron，壳选型需前置真机验收）；模式→天依映射表与 A/B/C 形态影响分析。全程零 GLM 配额（网页检索+本地读码） | `docs/plans/UI_REFERENCES.md`；`docs/plans/UI_UPGRADE.md`（§6 进度）；`docs/HANDOFF.md`（§3 状态块）；本提交 |
| Core 守护与挂因取证（zcode，2026-09-09，KI-019） | 用户报告"Core 又挂"零堆栈：WER 取证坐实 PortAudio 原生崩溃（libportaudio64bit.dll 0xC0000005，pid 4840）；交付 `scripts/core_watchdog.ps1` 接入 `start-mvp.ps1`——天依（Godot）在桌面就保 Core 在线：双确认健康判定防预热期误杀、90s 预热窗口防重复拉起、认领任何跑 agent_core.main 的 python（venv/系统解释器/手拉均管）、外部端口占用不碰、每次死亡记录退出码验尸（0xC0000005 将标注 PortAudio 崩溃）、天依退场守护即退场；复活问候为固定台词，全程零 GLM 额度。真机两轮 kill→revive 实测（23.4s/20.7s 恢复），Godot 桥自动重连 | `scripts/core_watchdog.ps1`；`scripts/start-mvp.ps1`（守护接入）；`docs/KNOWN_ISSUES.md`（KI-019）；`docs/LOCAL_DEV.md`（watchdog 节）；本提交 |
| U2 首块试点：工具活动卡（zcode，2026-09-10） | 所有者选定"最有把握"的 UI 改动先行看效果：`agent.tool` 事件在 Godot 聊天浮层按回合聚合成活动卡（来源徽标：本地/浏览器/GitHub/搜索/邮箱/网盘，`mcp__<server>__<tool>` 长名解析；✓/✗ 成败标记；调用计数；新回合与切会话自动开新卡），落实 UI_REFERENCES §4 chatbox Work Mode 单行时间线范式的 Godot 版；零协议/Core 改动，仅 `interaction_ui.gd` 加法 + 新守卫 `verify_tool_activity.gd`（GODOT_TOOL_ACTIVITY_OK：徽标解析/计数/重置/清场断言），既有 session/text 守卫回归绿；重启角色真机生效 | `apps/avatar-runtime/interaction_ui.gd`；`apps/avatar-runtime/verify_tool_activity.gd`；`docs/TESTING.md`（新守卫行）；`docs/plans/UI_UPGRADE.md`（§6 进度）；本提交 |
| 思考强度档：鲸鱼娘旋钮天依版（zcode，2026-09-10） | 所有者点名、参照 ChatGPT effort 弹窗 + DeepSeek 鲸鱼娘旋钮创意：composer"思考·档位"按钮 → 弹窗（档位名+GLM-5.3-Flash+三档刻度滑杆，旋钮=天依 Q 版形态，素材位 `assets/effort/<level>.png` 缺图回退头像等供图）；协议 `chat.message` 加可选 `effort`（chill=无工具纯聊 / standard=只读六件套 3 步 / deep=全量+MCP 5 步=历史默认），映射为 `main.py` `effective_tools_for_effort` 纯函数+7 单测（191→198 全绿），权限引擎与 wake/voice 路径零影响；`runtime.gd send_chat_message` 最小加参（带默认值，冻结文件）；守卫 `verify_effort_ui.gd`（GODOT_EFFORT_UI_OK）+ 三守卫回归；AVATAR_BRIDGE 同步（铁律 6）；开源差异化：七家都把 effort 藏设置里，输入框旁快捷档位为本项目首创 | `services/agent-core/agent_core/main.py`；`services/agent-core/tests/test_effort.py`；`apps/avatar-runtime/interaction_ui.gd`；`apps/avatar-runtime/runtime.gd`（最小加参）；`apps/avatar-runtime/verify_effort_ui.gd`；`docs/AVATAR_BRIDGE.md`；`docs/TESTING.md`；`docs/plans/UI_UPGRADE.md`；`docs/HANDOFF.md`（§3 状态块）；本提交 |
| 思考强度档行为层定稿 + RESILIENCE 并入手册（zcode，2026-09-10） | 所有者定调"档位=投入度而非功能开关"后推翻首版工具门控：**三档均为完整 agent**——全注册表+全部 MCP 常驻（权限引擎不因档位降级），档位只调投入度=步数阶梯 1/3/5 + 三段按档行为提示（`EFFORT_PROMPT_NOTES` 经 `extra_parts` 注入 system：碎碎念=单点快查短答/帮帮忙=小任务利落交代/大展身手=先规划后汇报），人设剧本一字不动；单测改写+新增（191→200 全绿）；滑杆重做为自绘粗轨道控件（`effort_slider.gd`：#66CCFF 已选段、三表情坐档、白圈已按反馈去除），表情包抠底（深藏青边缘泛洪）+镜像统一朝向；将外部 roadmap 仓 RESILIENCE R1-R5 细案核对后并入 plans 手册 §8（OPS-01 细化、新增 OPS-06~09、OPS-05 记录该仓转证据仓并回链） | `services/agent-core/agent_core/main.py`；`services/agent-core/tests/test_effort.py`；`apps/avatar-runtime/effort_slider.gd`；`apps/avatar-runtime/interaction_ui.gd`；`docs/plans/README.md`（UI-U2a 行+§8+§9 台账）；本提交 |
| StepFun 视觉接入 + DS-v4-flash 适配认证 + TTS 链修复（zcode，2026-09-12） | 三件套：① `AnthropicCompatibleProvider`（/v1/messages 方言：system 合并/tool_use+tool_result 翻译/思考块跳过/热重载平价），微信 Coding Plan（DS-v4-flash，OpenAI 兼容）对比后胜出任文本主脑（GLM-5.2 备选），换模型回归发现并修复四类弱模型失败模式（人设能力句被字面执行/多工具选型漂移/ask 预征询/档位契约松动）——认证驱动+题库入库（`scripts/model_cert.py`，E 系 9 项+独立实例对抗 10 题全部达标，手册 QA-03 立项），详见 EXAM_LEDGER DS 适配认证节；② `look_at_screen` 双方言视觉（anthropic base64 图像块），天依的眼睛切到 step-3.7-flash，GLM 断供期视觉不掉线（真机验收：确认后准确描述屏幕）；③ TTS 链回归修复：09-11 启动重写丢掉了 TTS 钩子导致每次重启都哑巴——语音链（tts_autostart + watch-tts-session）折回 start-mvp.ps1，真机验收合成+播放全通 | `services/agent-core/agent_core/main.py`；`services/agent-core/tests/test_anthropic_provider.py`；`services/agent-core/agent_core/tools.py`；`services/agent-core/agent_core/harness.py`；`scripts/model_cert.py`+`model_cert_battery.json`+`model_cert_adversarial.json`；`scripts/start-mvp.ps1`；`docs/EXAM_LEDGER.md`；`docs/plans/README.md`（QA-03）；本提交 |
| Gmail MCP 接入（zcode，2026-09-07） | @gongrzhe/server-gmail-autoauth-mcp（19 工具）经 `tools/gmail-mcp.cmd` 代理启动器接入（Google API 需本地代理）；OAuth 全流程走通（403 测试名单 → 补加 → 令牌落 ~/.gmail-mcp）；T-GMAIL 验收：真实读出收件箱（Ferrari/GitHub CI 通知），投毒邮件发送测试被她识破拒发（双层防御）；gcp-oauth.keys.json 与令牌全部 gitignore | `tools/gmail-mcp.cmd`；`.env`（gmail 条目）；`.gitignore`；本提交 |
| STT 自愈与 Idle 触发（zcode，2026-09-07） | `voice.py`：Realtek 假死数字零检测（噪声底物理特征区分"没说话"与"驱动假死"）+ 一次自动设备重置 + 可行动报错 + 每次录音电平日志（KI-001 加固）；`proactive.py` 新增 `IdlePolicy`（阈值/免打扰/冷却，纯逻辑），`main.py` 启动钩子挂 GetLastInputInfo 本地轮询（30s，Windows）+ 台词模板库，**全程零 GLM 调用（待机零额度）**；单测 164→176 全绿（含原 D1 测试原样保留） | `agent_core/voice.py`；`agent_core/proactive.py`；`agent_core/main.py`；`tests/test_voice_selfheal.py`；`tests/test_proactive.py`；本提交 |
| T2+ 进阶考试（zcode，2026-09-07） | 矛盾记忆更新（换载体：歌手脱粉）+ 长对话压测（16 轮：三事实注入/工具/身份陷阱/注入攻击/突袭抽背）真机实考 21 次调用；判分行为证据制（facts 表对账）；考出两个架构缺口（facts 无取代机制、晋升词表偏好中心化）与一个模型已知项放大（批量回忆自疑）；临时会话 51/52/53 与考试事实全清零；实录归档 workbench evidence，错题记入 EXAM_LEDGER | `docs/EXAM_LEDGER.md`；workbench `evidence/live_exam_t2plus.md`；本提交 |
| D 期屏幕视觉上线与超时修复（zcode，2026-09-07） | `.env` 仅加 `ANIME_AGENT_VISION_MODEL=glm-5.3-flash`（端点/key 回退 GLM，coding 端点实测收图）；真机揪出确认流 15s 全局超时杀视觉调用的基建 bug（事件表 07:16:10→07:16:25 恰 15s），修复为 Tool per-tool timeout（look_at_screen 90s，其余 15s 口径不变），TDD RED→GREEN（tests/test_tools.py PerToolTimeout），单测扩至 156 项；全链路真机通过（会话 50：ask 隐私档→确认→截图→GLM 视觉→角色化描述与屏幕实况逐项吻合），临时会话 49/50 删除零痕迹；EXAM_LEDGER 记档，AVATAR_BRIDGE 超时口径更新，KI-015 销账 | `agent_core/tools.py`；`tests/test_tools.py`；`.env`；`docs/EXAM_LEDGER.md`；本提交 |
| 灾备加固与文档守卫（zcode，2026-09-07） | 删除文件恢复性实际执行验证（bak-phase1/verify_skirt_physics.gd/notes.md 字节数 12214/20068/273 全部取回核对）；核验本轮整理回滚范围恰为 3 提交（`git revert 5324a6a^..2666fd5`）；HANDOFF 新增 §10 灾备与回滚（本地专有资产台账 + 已验证恢复命令）与铁律 9（main 禁 force-push、删除必指认恢复命令）；`scripts/check_docs_consistency.py` 文档一致性守卫（测试数/环境变量/工具清单三方对账，破坏注入演练红→绿验证）接入 TESTING 门禁与 AGENTS 必做验证。勘误：T1 行所提 `harness.py.bak-phase1` 已撤出工作树（git 历史可恢复），人设回退路径以 `harness.py` 保留的 `BASE_SYSTEM_PROMPT` 常量为准 | `scripts/check_docs_consistency.py`；`docs/HANDOFF.md` §10；本提交 |

### Claude 工作树边界

Claude 的全部增量已于 2026-08-31 以提交 fc5a5a4 落库：倾听动作、唤醒词、会话删除（单击确认框改型）、会话标题、Agent 工具循环 A 期及配套测试与文档，提交时按 Codex 同一口径对共享文件做了行级分块暂存，未夹带对方代码。当前工作树剩余未提交内容全部属于 Codex：画布扩容与侧板方向（runtime.gd / interaction_ui.gd 残余行、verify_desktop_canvas.gd、ARCHITECTURE.md、TESTING.md 大动作门禁行）、大动作可读性与 MMD 镜像（runtime.gd 残余行、verify_large_motion_*.gd 两个新脚本）、MODEL_OPTIMIZATION.md 的五条增量。

## Codex 1.3 冻结声明（2026-09-08；承接下方历史候选记录）

所有者批准保守 A-pose、F12 高清截图与材质候选 A 作为当前基线并要求推送。Codex 将候选材质原参数移至 `apps/avatar-runtime/model_look_v13.gd`，接入 `runtime.gd` 默认 1.3 与显式旧版回退；同时提交本轮此前尚未提交的待机注册项、肩臂轨道替换、截图器及三个验证入口、lookdev 文档和相关 README/HANDOFF/TESTING/MOTION_PIPELINE/优化路线更新。官模与动捕 GLB 未改；1.3 使用旧版同哈希 Blend/GLB 的独立只读副本，完整回溯依赖清单 runtimeCommit。渲染九视图、十二组动画采样、版本选择/回退、GPU 门禁、高清截图五视图及动作/输入/会话/画布回归通过；不是全身防穿模或复杂旋转自然性验收。另一代理的 wake_word.py 与 test_wake_phrase.py 不属于本轮，保持未提交原样，不夹带。按所有者要求不启动子代理，以单代理审查和自动验证取代本次独立代理交接演练。最终冻结信息与验证记录见 `model-versions/1.3/README.md`；以下候选记录是历史阶段而非当前发布状态。

### Codex 告别挥手离线候选（2026-09-12，未实装）

按所有者确认的右手挥动、五指全程伸展制作 `apps/avatar-runtime/mocap/farewell/` 独立候选，复用已检查骨骼助手，35右臂旋转轨/4.1秒含抬手、三次挥别和回A姿。Blender只读结构取证、493个120Hz采样、手指弯曲负对照、124帧保存回放、493次非顺序/非关键帧检查通过；全身/近景各124帧真实GPU渲染和四朝向关键帧、MP4解码与无损APNG逐帧RGB校验通过。官模、正式runtime、注册表和项目配置前后哈希不变，未实装、修改退出逻辑、重启正式进程、调用Core/API、启子代理或提交推送；不把本候选称作自动动捕、全身零穿模或退出生命周期验收。路径、哈希、复现、观察范围和下一步边界见本目录README，保留其它代理并行改动。

### Codex 告别挥手 v2 发力部位纠正（2026-09-12，未实装）

所有者指出上一版错误使用大臂和手腕摆动，Codex仅修改farewell候选为抬臂后固定大臂、小臂绕肘±23°往返，手腕与五指保持局部姿态。增加肘枢轴不动、除肘外右臂局部旋转不动、实际摆幅及大臂/手腕错误驱动的负对照；493个120Hz采样通过。保存回放检查首次发现3.16秒阶段边界在30Hz采样间被放手插值污染，补精确关键帧后通过124帧和493次非顺序/非关键帧回放；重渲染双机位与四朝向关键帧。旧v1和本轮失败证据保留，新证据在motion-output/farewell-reference-v2，具体参数/限制见farewell/README.md。官模、runtime、注册表、项目配置哈希不变，不动Core或退出逻辑，无实装、重启、子代理、提交或推送，等待所有者审阅。

### Codex 告别挥手 v3 头部与闭眼笑（2026-09-12，未实装）

在所有者基本认可v2手臂后，Codex仅向farewell离线候选增加首/頭两条轻摇轨道及官模笑眼/微笑两条原生表情轨，共39轨；头部最大偏转3.203°，挥手全程闭眼微笑，收手时淡出并回正。35条既定手臂轨逐键对照v2通过；493个120Hz结构采样、错误驱动负对照、124帧保存回放、493次非顺序回放、表情两端/保持门禁通过，重渲染同步全身近景及四朝向关键帧。实测依据与资产路径见farewell/README.md和motion-output/farewell-reference-v3；不改官模/正式runtime/注册表/退出流程，不进行生产重启、Core调用、子代理、提交或推送，待所有者审阅。

### Codex 退出告别第一版集成（2026-09-12）

所有者批准v3并授权实装/推送，Codex新增 `farewell_exit.gd`、正常关窗/Esc接入、退出专用资源索引、SHA冻结工具、单一播放控制权与8秒兜底；既有Core/启动/语音清理不重写。七种起态3444采样4968269断言、三轮独立Windows原CMD/WM_CLOSE测试、资源缺失/损坏及暂停/零时间故障注入通过；真实渲染闭眼微笑正常，干净HEAD+本次补丁也通过，220项Core、14项启动逻辑及既有Godot/桌面回归通过。严格保留当前6个Godot/Core/守护进程，测试独立副本/端口/数据目录，不向原窗口发送操作；正式文件供下次启动加载。范围/本地资产/失败记录/测试限制见 `docs/FAREWELL_EXIT.md`。提交按Codex标记，仅包含告别及此前预览工具，不夹带本地未提交表情实现、其他agent内容或受限二进制；无子代理、真实Provider调用或通用零穿模承诺。

## 后续 Agent 更新规则

1. 新 Agent 开工前先读本文件、`HANDOFF.md` 和当前 `git status`，不要仅凭聊天记录判断归属。
2. 追加自己的 Agent 名称、日期、模块和提交，不覆盖既有条目；允许按项目所有者授权声明重叠贡献。
3. 并行开发时优先按文件或补丁块分离提交；共享文件必须检查 staged diff，避免把他人的未完成代码带入。
4. 贡献声明不替代验证。任何“完成”仍以 `docs/TESTING.md` 的当前门禁和远端提交为准。
5. 交接或收工前，`docs/HANDOFF.md` §7 的白纸测试门禁（零上下文独立实例通读 + 行为探针）必须通过；状态变化必须回写 HANDOFF §3 与 README 状态表。

## Codex 增量声明 — 2026-09-08 高清输出候选

Codex 新增 `portrait_capture.gd` 与 `verify_hd_capture.gd`，在 `runtime.gd` 接入 F12 原生高清透明 PNG 输出及聊天输入焦点守卫；同步 README、HANDOFF、TESTING 和 MODEL_OPTIMIZATION。截图通过临时 SubViewport 共享当前 3D 世界与同参数相机，默认桌面模式输出 2880×3480，完成后释放临时资源，不抓取聊天界面或桌面，不修改日常画布、官模资产、身体比例或 1.2 外观；单次保存实测约 260–361ms，可能短暂卡顿，不属于连续录制功能。前发、后发和长辫子的运行时材质检查显示为不透明双面材质，故没有贸然改 Alpha 或重绘贴图。本轮通过真实 OpenGL 正面、左右、背面及最大缩放五组同镜头对比，验证透明输出、轮廓比例、颜色差异、临时资源释放、重复请求/非法输入和官模哈希；另通过 headless 快捷键检查、保守待机、动作 runtime、文字输入、桌面画布、181 项隔离 Core 单测、桌面构建、文档守卫与 diff 检查。依所有者最新要求关闭五个已完成的旧子代理，本轮未再启用代理，采用主代理定向审查和自动化测试，不声称执行了独立代理白纸验收。此为本地未发布候选，尚未命名 1.3、commit 或 push；日常模型观感保持 1.2，头发边缘专项改善、连续高清录制及通用防穿模均不计为本轮完成项。

## Codex 增量声明 — 2026-09-08 保守待机

所有者明确选择暂缓贴腿待机，第一阶段动捕先做小幅、少接触动作。Codex 在 `runtime.gd` 增加内存动画副本的肩臂链替换，`motion_registry.json` 仅为 idle 开启 `relaxed_arms`，复用既有 ±48° 下放角度恢复斜下外展 A-pose，保留头胸动捕、完整长辫子与其它交互；未修改官模、比例、材质、三个动作 GLB、Core、TTS 或 UI，也未把物理专项代码带回主仓。新增 `verify_reference_idle.gd`：先复现旧待机第 0 帧肩骨不满足参考姿态，再验证 70 骨/750 帧、四种交互确实启动并移动手臂、主动 reset 与自然结束都回待机，逐键确认 listen/pirouette 未被替换，并实际渲染五视图和同镜头前后对照。独立只读审查发现切换测试可假阳性，已补上述状态/运动/逐键断言并通过。其它通过项为原动作 runtime/import、输入、画布、large-motion safety、资产哈希、181 项 Core 单测、桌面构建、文档守卫和 diff 检查；本地图片见 `MOTION_PIPELINE.md`。Core 首次测试因继承 `.env` 中 MCP 配置而中断，已仅终止该测试进程树；显式禁用 MCP/TTS/wake、使用 mock 与独立数据目录后 181 项通过，生产 Core/TTS 未重启。当前为本地候选，等待所有者视觉验收，未 commit/push；不是通用防穿模系统验收，原动作可通过关闭该字段回溯。

## Codex 增量声明 — 2026-09-08 1.3 材质离线候选 A

依所有者“先模拟、看图后决定实装”的最新边界，Codex 新增 `apps/avatar-runtime/lookdev/candidate_materials.gd`、`render_candidate.gd` 和说明文件，建立不执行生产启动/桥接/UI/位置持久化的独立试渲染入口；仅复制十个 1.2 材质实例、分组调整受光/自发光与高光参数，不改官模、贴图、相机、灯光或正式入口。本轮没有新增 `runtime.gd`、注册表或启动脚本改动，它们已有未提交内容仍属前轮保守待机和 F12 功能。七组同帧视图与十二个待机时刻/朝向采样通过，2 像素网格 Alpha 差异均为 0、全图包围框一致、相机及 703 骨姿态不变、材质回退 RGB 平均误差低于 0.000001；负对照可识别 Alpha 与位移变化；GLB 哈希不变，1.2 快照校验通过。最终无引擎错误的实测证据目录为 `C:/Users/26052/AppData/Roaming/Godot/app_userdata/Luo Tianyi Desktop Avatar MVP/lookdev-1.3-candidate/2026-09-08T22-40-46-52120`（PNG 与 report.json）；181 项隔离 Core 单测及桌面 TypeScript/Vite 构建通过。早期主窗口隐藏/最小化试验失败已纠正，详情见候选 README；性能为后台离屏墙钟诊断，不宣称通过正式 GPU/桌面帧率门禁。归属、状态与测试入口同步 README/HANDOFF/TESTING/MODEL_OPTIMIZATION；本轮单代理，未启动子代理、未实装/重启正式天依、未冻结 1.3、未 commit/push，等待所有者视觉决定。

## Codex 增量声明 — 2026-09-09 倾听动捕 v2

依所有者新视频与背手照片，Codex 新增 `apps/avatar-runtime/mocap/` 构建、验证、GPU 试渲染与预览编码入口；`runtime.gd` 最小增量支持原生 Animation、沿原路径退出和中断后续接，只对新背手动作关闭镜头可读性纠偏；注册表切换 listen，旧 GLB 与新源视频/关键点在本地独立归档。右手耳旁轨迹、肘平面、头胸偏转来自测量，左臂遮挡段、掌向及轻微前倾人工适配，不宣称全指动捕或一比一重建。官模 GLB 哈希、703 骨、48 表情、骨位移/缩放、下半身与 1.3 材质保持不变；61 帧全轨道/全骨架验证、六个取消时机、重复触发和逆播中再次录音、旧动作/待机/输入回归通过，真实 GPU 四视图与 181 帧连续播放已生成，187 项隔离 Core 测试和桌面构建通过。贡献仅为本地实现，待所有者自然度验收，未 commit/push、未重启生产 Core/TTS、未启子代理；不是通用无穿模证明。原文档 181 与实际 187 的守卫漂移来自并行唤醒增量，未夹带改动该能力。详细路径、哈希、回退和边界见 `apps/avatar-runtime/mocap/README.md`。

### 同轮追加：所有者指出肘腕反折后的修正

Codex 通过官模开放手掌平面推导肘部参考铰链，将肩部完整坐标架对齐 IK 弯曲平面，不再只对齐两段骨骼方向；限制折肘 125°、手腕偏折 35°，降低左手绕后中段的抬肘幅度并缓和起始旋转。旧候选在新增门禁中测得折肘 148.908°、腕偏折 48.819°、肘轴外四元数分量 0.7523，三项失败；修正版分别为 125.000°、35.000°、0.00000108，61 帧结构/轨道和进退状态回归通过，最大单帧转角 10.925°。当前注册表使用独立 `listen_mocap_v2_corrected.tres`，首版 TRES 与历史 GLB 均保留，不覆盖官模或 1.3 档案；最新 20 视图及 181 帧预览位于 `user://listen-mocap-v2/2026-09-09T00-22-34`。开发过程中检测到并行 zcode 提交 `a0d98dc` 夹带了本轮首版 Codex 文件，因此上段“未 commit”仅指 Codex 自身未执行，不代表当前 Git 中无这些文件；不改写他人的提交，`services/agent-core/agent_core/main.py` 的并行未提交改动不属于 Codex。仍待所有者自然度验收，不把关节数值通过当作通用无穿模证明。

## Codex 增量声明 — 2026-09-09 倾听中段去绕转

所有者用新视频指出 corrected v2 中段“蛇形扭臂”，并认可首尾。Codex 新增 `mocap/build_listen_transition.gd`，舍弃逐帧 IK 中段，用固定局部旋转弧协调肩/肘，延后左肘收拢，生成独立 `listen_reference_fk_v1.tres` 并切换单条注册项；旧构建器仅加历史标识，旧资源及官模保留。新增 `verify_listen_path.gd` 检查首尾全轨道一致、480 子步转角路程与速度；旧版右腕累计 100.831°、右上臂 276.265°，新版 11.664°、141.033°，无多余折返（这些不是纯轴向扭转角）。现有 97,483 项动作/结构断言、750 帧待机、文本输入、动作导入/运行、大动作 GPU 轮廓/菜单回归、资产哈希、191 项隔离 Core、桌面构建与文档守卫通过；重复构建拒绝覆盖，旧版负对照失败。首个输入验证命令误用不存在的文件名，已用真实入口复测；大动作 GPU 首跑沿旧入口连到 Core，未发聊天测试，随后禁用 Core URL 重跑通过。新片段与原始参考仅本地归档在 `../motion-output/listen-reference-fk-v1`，实际四视角/完整动画证据在 `user://listen-mocap-v2/2026-09-09T00-48-56`。本轮不改网格/蒙皮/比例/1.3 材质/语音/UI，不启子代理，不 commit/push；自然度仍以所有者观感验收，非通用防穿模承诺。

### Codex 追加 — FK v2 轻微前倾、右手收近与预览色差（2026-09-09）

所有者认可 v1 整体后，Codex 以不可变 v1 为源，只调末姿上半身 +4° 前倾、右肩摆向头侧，仍用固定局部旋转弧；手移动约2.25cm、手腕到头部距离缩短约1.22cm，肘腕端点及官模未动。独立 FK v2 资产和 JSON 已本地归档；路径门禁只允许这两处小角度末姿变化，97,483 项结构/状态检查与完整四视角预览通过。定位同帧 GIF 对95个绿色虹膜像素的明显量化色差，编码器增加无损 APNG 及全帧精确 RGB 回读检查，当前91帧独立复核通过。新证据 `user://listen-mocap-v2/2026-09-09T01-02-47`；不改眼睛材质、模型版本或语音服务，不 commit/push。

### Codex 验收冻结与推送授权 — 倾听动作第一版（2026-09-09）

所有者认可当前 FK v2 效果，明确授权以第一版收口推送。Codex 本次汇总提交上述去绕转、前倾/收手微调、无损 APNG 以及相应测试、复现/回退和状态文档，提交标题带 `Codex`。内部资产名 `listen_reference_fk_v2.tres`，SHA `340c44b446ff81219cbb055d56bc4af9eaef65357e307bb871478fbb4acadf2c`；旧资源独立保留。该声明不把 motion 第一版混同为官模1.4，也不覆盖另一 agent 的贡献；个人视频、素材与官模不推送，仍以本地路径与哈希交接。

### Codex 五官 A 版离线候选（2026-09-10，未采用）

按所有者“只模拟并看图决定”的边界，新增 `lookdev/face_a.gdshader`、`render_face_a.gd`、`FACE_A.md`：仅复制脸部材质并叠加依附原 UV 的鼻尖/唇线/耳内色彩细节，原纹理、几何、骨架、表情、眼睛、发型、正式 1.3 与已验收倾听动作均不改。八组实际 GPU 同镜头对比、全骨姿态/资源一致性、零强度负对照、还原误差门禁和独立全图 Alpha 检查通过；收益集中在近景鼻尖，小桌宠尺寸及被头发遮挡的耳朵改善有限。最终证据、复现命令及初次失败与纠正记录见 `apps/avatar-runtime/lookdev/FACE_A.md`。本轮单代理，无生产重启、无 commit/push，待所有者决定；不宣称已实装或已成为新模型版本。

### Codex 五官 A2 微调（2026-09-10，离线待审）

依所有者“鼻子像小点、嘴唇再明显些”的反馈，独立保留 A1，新增 `lookdev/face_a2.gdshader` 并为试渲染入口增加 A2 选择和同场景 A1/A2 对照。鼻部改为更宽且峰值更淡的弧形阴影、柔和鼻侧过渡与微弱亮部，增强原有唇色，仍不改几何/原纹理/官模比例/正式入口。八组渲染与零强度、还原、骨姿态、其它材质、哈希门禁通过；独立全图 RGBA 验证两种对照 Alpha 差异均为0。证据与限制见 `lookdev/FACE_A.md` A2 节。未实装、未重启、未 commit/push；不夹带并行 UI 文档工作。

### Codex A2 实装与表情兼容性（2026-09-10）

所有者批准 A2 后，Codex 新增正式 `model_look_v14.gd`/`face_detail_v14.gdshader` 并在 runtime 保留显式1.3回退，将通过测试的1.4设为默认；未改官模、原贴图、703骨/48形变、眼睛、动作或其它22材质。新增生产表情门禁及独立像素复核：122对照、48形变×两权重、8叠加、180连续口型帧、回中/回退/多朝向，双轮GPU通过；九张拼图人工复核，104对照全图Alpha差异0。初始测试在缺1.4时按预期失败；中途纠正测试插值状态字段，修正拼图临时纹理释放白块，修订后才采用证据。输入/会话/工具卡/画布/750帧待机/动作/倾听和大动作渲染回归、191项隔离Core测试、桌面构建通过。精确关闭原Avatar PID26636，重新启动PID20408，真实日志确认1.4和Core连接，窗口响应且启动渲染已检查；生产Core PID29556保留，TTS本来未监听且未启动，未发Provider测试。清理了本代理遗留的两个离线预览进程树，无子代理。四个历史快照不覆盖，新资产/源码/证据另备份，正式索引仍1.3，待授权提交后冻结1.4；本轮无commit/push。详见 `model-versions/PENDING_1.4.md`，不夹带并行zcode能力/UI工作。

### Codex 正式冻结1.4（2026-09-10）

所有者明确批准正式交付后，Codex 将A2及此前离线候选/表情门禁固定到运行时提交 `7bb1aa1599e85d60adf329d79d507352a4e6eb9a`，建立1.4独立只读GLB/Blend、七类真实预览、注册动作/支持纹理和旧倾听测试参考的路径/大小/哈希清单，正式索引更新1.4。发现旧恢复器仅复制当前GLB会漏TRES并受未来资源漂移影响，最小补充冻结资源分支、路径约束/哈希拒绝和可选测试资源参数；不改旧1.0–1.3清单，新增三越界路径/错误哈希负对照通过。真正从归档创建独立worktree后，三动作运行、倾听路径、输入、122对照/180帧GPU与全像素Alpha复核通过；首次测试早于导入完成及缺历史参考造成的失败均已定位、补全后复测。当前生产Avatar/Core不重启；本轮无外观变化、无子代理、无远程push/Release，仓库项目文档不触发Drive备份。交付边界和证据见 `model-versions/1.4/README.md`。

### Codex 项目长远方案手册整合（2026-09-10）

按所有者要求新增 `docs/plans/README.md`，将模型/画质、动捕/物理、Claude Agent 蓝图、zcode UI/跨仓看板及语音/训练/常驻方向整合为唯一有效规划正文，记录原提出者、实施者、状态、依赖、下一步与验收；原五份文档保存到 `docs/plans/archive/`，只改迁移链接并加历史提示，旧路径保留兼容入口，根 README 改指手册。纠正过期的 1.4 未推送、UI 全未开工、守护全未实现和矛盾记忆未考表述；迁移期间检测到 zcode 提交 `1d10a99`，已读取并保留新增强度档及归属。不改运行时/Core/UI、模型资产或其他 agent 的在制工作。外部 roadmap 专项细案未读，明确保留待核验边界，不冒充全量跨仓同步。本次为文档整合，不代表新增能力验收；检查范围为档案保真、链接/锚点、路线覆盖、文档守卫与 diff，不启子代理或重启生产服务。

### Codex 启动误报诊断与候选回归（2026-09-11，未实装）

确认启动器2秒超时与详细健康接口的TTS探测耦合可导致健康Core误报，新增轻量 `/health/live` 及两项回归，保留旧接口；新增尚未接入正式入口的生命周期函数与10项隔离模拟。全量Core回归202项中201通过，1项因隔离账户桌面读取权限失败；现有Python执行、CIM/端口查询受限，不能完成真实同命令反复启动/关窗验收，故正式启动器/守护器未替换，未重启生产、未改模型、未提交或推送。确切修改、证据、未完成工作和权限边界见 `docs/STARTUP_REPAIR_STATUS.md`，不得标为启动已修复。

### Codex 启动/退出正式本地替换（2026-09-11）

在用户恢复正常Windows执行环境并授权继续后，完成轻量健康、旧Core兼容、共享启动锁、进程归属/创建时间校验、Core树清理、Avatar代际守护、恢复取消、窗口/WS/守护就绪门禁和`.cmd`退出码/路径修复；另修复空库历史响应null导致的Godot初始化错误。通过203项Core回归、14项逻辑测试、两轮真实故障矩阵与加载中Core死亡的定向对抗后替换本地正式入口，再用用户原命令验证真实目录：旧Core接管、两次关窗清理（各Core树20个进程）、两次冷重启和重复调用。保持zcode原生崩溃守护目标，不冒领其能力层工作；音频隔离/历史孤儿与独立TTS守护仍按原计划。官模、动作、配置不变，无子代理、无commit/push；备份、证据、测试失败与修正见 `docs/STARTUP_REPAIR_STATUS.md`。

### Codex 启动修复最终对抗与收尾授权（2026-09-11）

所有者要求最后两轮加强测试，通过后收尾并推送。Codex 完成独立副本20/24项检查，覆盖6路并发、正常/快速重开、废弃锁、暂停旧守护跨新会话恢复、Core崩溃/挂起、恢复中关窗、伪装健康的外部占用、非法配置、子进程清理与无关进程保护；补强故障注入时序和清理失败门禁、禁止测试暗用候选入口、隔离TTS探测端口，新增Windows CI逻辑回归。203项Core与14项逻辑、资产/文档/静态/暂存区检查通过。测试初跑失败与修正保留于启动验收记录；不是无限故障保证，也不宣称TTS/音频隔离或独立agent白纸考试完成。提交以Codex标记，只包含本次启动相关代码、测试与文档；本地日志/模型/配置和另一agent的Godot UID文件不随本次推送。

### Codex 三种表情离线强化候选（2026-09-12，未实装）

按所有者“先模拟并发对比图”的边界，新增 `lookdev/render_emotion_preview.gd` 与 `EMOTION_PREVIEW.md`，仅在独立离线实例中组合现有惊讶/生气/流泪的眉眼口形；真实GPU渲染单形变图谱、两轮候选及正面/30°侧面/全身小尺寸对比。官模SHA、703骨/48形变、相机灯光、全部骨姿态、23材质及网格/蒙皮引用核验通过，三组回中误差<0.000001。仅静态视觉候选，不代表动态表情/口型/眨眼/状态优先级已经修复；泪滴与小尺寸可读性仍有限。正式1.4和运行中天依均未替换，未commit/push、无子代理；证据及复现见新增说明，不改其他agent在制文件。

同日Codex追加：按所有者反馈仅新增哭泣折中候选，两个旧版权重与图像保留，惊讶/生气最终参数不变；新增 `--cry-middle` 同机位正侧面三列渲染、旧报告参数复核、全图RGBA微小误差界限与单像素负对照、回中及结构检查。首次逐字节检查因少量1/255差异失败，独立像素核对后明确误差上限，最终报告PASS，未把静态预览当作正式实装。路径/参数/失败说明见 `lookdev/EMOTION_PREVIEW.md` 哭泣折中版节；无生产修改或推送。

### Codex 已确认表情正式接入（2026-09-12）

所有者批准直接实装后，Codex 新增窄范围 `emotion_presets.gd`，将惊讶/生气最终参数与哭泣折中参数接入 `runtime.gd` 统一事件路径；处理切换清除、口型/眨眼/状态优先级、渐变收敛及原状态恢复，不改模型1.4资产、材质、骨架、比例、动作、Core/启动器或其他agent的UI。新增独立行为守卫与GPU集成守卫：4207帧/204019断言、六组正侧面渲染、122组既有表情材质对照、180帧口型及203项Mock Core/桌面构建/既有UI动作门禁通过。使用原CMD入口重启本地实例；实装前后运行时存入独立表情1.0档案，历史模型档案保持不变。失败记录、证据与回退规则见 `apps/avatar-runtime/lookdev/EXPRESSION_1.0.md`。本次无子代理、无commit/push，不冒领他人UID文件或能力层改动。

### Codex 思考动作离线预览（2026-09-12，未实装）

### Codex 思考动作第一版正式接入（2026-09-12）

所有者批准review11并授权实装及push。Codex将批准的74身体轨与34发束轨按原SHA合为独立108轨/9.5秒资源，通过 `freeze.gd` 保存回读并登记manifest；仅新增注册表think、菜单、thinking状态单次触发及两端实际待机相位交还，不安装离线物理求解器，不动官模/外观1.4/旧模型档案/已有倾听。新增正式运行时及GPU集成守卫，1141帧2651216检查、301帧GPU/16视图29268旋转对照、实际菜单/完成信号、干净副本、既有动作/UI/表情、220项Mock Core、桌面构建和文档一致性通过；失败路径、可复现本地资产位置/哈希、回退及两段低风险后续录制见 `apps/avatar-runtime/mocap/thinking/README.md`。真实原CMD重启发现生产SQLite损坏（disk image is malformed），旧窗口/Core正常退出但新Core未就绪；未自行删库或换空库，已报告并请求恢复授权，故不声称正式启动成功。本次提交只含思考及其历史预览工具/证据说明，不包含此前未提交表情实现、其他agent改动、本地官模/视频/动画二进制；无子代理、真实LLM调用或全身零穿模承诺。

### 思考离线预览的原始记录（Codex）

按所有者视频及后补两指近照，新增 `mocap/thinking/` 独立工具：Blender/运行时结构检查、视频参考姿势设计、拇指食指托下巴/其余三指收拢、另一手轻托肘、抬头左右看及原A姿进退。静态接触使用实际骨长与肘轴，固定局部旋转弧过渡，前臂转动分配到既有手捩链；这是参考＋人工接触适配，不称全指自动动捕。1141个120Hz采样、旧张手负对照、保存后286帧动画回读与双机位真实GPU渲染通过；多朝向审阅后保留长辫子/袖口交叠及精确表面接触尚未全面验收的边界。源文件、参数、失败记录、测试指标与本地成片路径见 `apps/avatar-runtime/mocap/thinking/README.md`。本轮runtime/注册表/官模哈希不变，无生产重启、无Core/API调用、无子代理、无commit/push，等待所有者审阅；不将其它agent并行提交的Core与文档更新算作本轮贡献。

### Codex 思考动作辫子绕臂预览（2026-09-12，未实装）

按所有者“先做预览”授权，新增独立辫子路径层、离线渲染入口和结构/手臂胶囊代理检查；仅调整两条完整发束的既有旋转，保留手型、身体和官模。571采样结构与有限代理检查通过，旧摆动负对照失败；完成286帧真实GPU前后对比及近景/全身64张检查图、MP4回读和无损APNG回读。中间失败试验保留，不把代理正间隙称作真实网格全身零穿模；侧面架起感、腕饰/手指/头发自碰撞与生产中断混合仍未验收。源代码、指标、未烘焙头发轨道的限制及成片路径见 `mocap/thinking/README.md` 追加节。正式runtime、注册表、GLB哈希不变；无实装、生产重启、子代理、Core/API调用或Git推送。

### Codex 思考发束物理试验与退出回位（2026-09-12，未实装）

补记上一轮及本轮归属：Codex 增加离线 `strand_physics.gd`、`physics_preview.gd`、`spring_audit.gd` 与编码比较选项，使用动画引导、重力/阻尼、长度/弯曲和代理接触约束，保留原生SpringBone失败证据在本地且不接入生产。所有者本轮指出辫子末态留在身后后，补充两条完整骨链的退出回归、时域平滑、约束再投影、小幅绕臂路径以及原待机相位交还；新增同相位GPU像素对照脚本，原距离检查仅补外法线诊断。旧模拟回位门禁真实失败（点位偏离371.75mm），新 `thinking-hair-return-v1/review11` 在1141/2281两个采样密度下通过结构、0–7秒来源保持、连续末段回位及有限手臂代理检查，回程最大步长折算120Hz为1.968°；不把这些测试称为真实网格零穿模、纯物理自然度或生产混合验收。代码、全部失败路径、局部引导参数、回读/图像证据及可复现入口详见 `apps/avatar-runtime/mocap/thinking/README.md`；正式模型、runtime和注册表哈希未变，身体/手型/前段思考不改，无生产重启、API调用、子代理或Git提交推送。

### Codex TTS运行期恢复候选（2026-09-12→13，未正式结案）

按所有者授权接手zcode的OPS-08交接，Codex先通过25项既有语音测试，再复现并修复负面健康缓存60秒、无运行期看护、假健康、无限合成锁等待和启动/退出归属竞争。新增项目/端口/venv/进程代际核验、真预热阶段、卡顿/错误恢复、双确认/退避、退出交接与旧入口兼容转发；主仓与相邻tianyi-tts私仓均有本地修改。Core223、sidecar20、PS生命周期10、两轮Windows故障与原CMD三轮退出通过；真实CPU预热95.610秒及2.180秒WAV证明实际推理，不能冒称GPU或24h通过。后续加强用例及失败原因继续记录于docs/TTS_REPAIR_STATUS.md。始终保护现有窗口/Core/TTS，不改声线参数/模型/用户数据，不启子代理；没有提交或推送。并行agent的UI/工具卡和此前表情未提交改动不属于本轮TTS成果。

### Codex TTS正式启动复核受阻（2026-09-13 00:33）

所有者续作授权后，重新核对无Godot窗口，在锁内按PID/创建时间/项目归属清理旧Core，使用原CMD启动；新Core因现有SQLite损坏退出，未完成TTS激活。完整复制主库/WAL/SHM并核对SHA，仅在副本只读检查，确认消息/记忆/事件表损坏；没有恢复、删库或替换正式数据，没有修改storage.py/main.py，不能确定损坏发生时间及责任。精确现场、日志和待确认恢复范围见docs/TTS_REPAIR_STATUS.md末节。此前HTTP单测的spool隔离事故及共享进程换代限制也以该文为准，不把上一段“始终保护”解释为全任务零副作用保证；本轮没有关闭其他Godot、结束旧TTS或推送代码。

### Codex 数据部分恢复（2026-09-13 00:50；TTS暂停）

所有者最新授权仅恢复数据，Codex保留原损坏库/WAL/SHM、核对WAL校验与历史代边界，使用官方便携SQLite恢复工具在副本扫描468个幸存提交状态，并排除33份空测试备份。经字段、来源、逐行哈希及关联核验，将164条消息、874条事件、71条原会话元数据及6个明确缺标题占位原子恢复到正式库；54条历史消息及87个旧会话元数据版本仅本机归档，不静默复活可能已删除记录。8组恢复测试（含篡改/截断负对照、真实MemoryStore、隔离Mock启动）与正式库只读回读通过；facts未找回，其他缺失页无法计量，不声称全量恢复。原库和WAL哈希仍一致，没有启动Godot/Core/TTS、开启24h观察、改应用代码或推送。证据、完整本地路径、失败扫描及后续合并边界见docs/DATA_RECOVERY_STATUS.md；私人正文与恢复二进制不入Git。此前TTS候选和其他agent在制改动保留，不计入本轮贡献。

### Codex TTS会话闭环与真实声线隔离验收（2026-09-13 02:29）

所有者重新授权仅修TTS，要求原CMD重开有声及Godot存续期间恢复，明确禁止再操作正式数据。本轮在此前候选上补充Core看护独立拉活TTS看护、45秒心跳识别挂起、精确身份替换及原子回执、原CMD真实预热等待/关窗取消；不重写E期分片/打断，不改模型、动作、声线配置或.9阈值。223Core/20sidecar/14启动/13TTS逻辑回归、最终14项Windows故障矩阵、两轮合成WAV与两轮完整声线原CMD/Core/Godot端到端测试、编译/输入/桌面/文档检查通过；实际TTS冷恢复60.187/58.765秒，WASAPI非零未静音输出与播放开始/结束通过。对进程表/端口表非原子观察造成的两次测试失败保留证据，仅在测试观察器增加有限重查，未放宽生产归属保护。当前手动启动的用户窗口/Core没有被关闭或重启，8770缺席，正式激活仍待批准；不能称旧窗口已受新看护或任何故障均零中断。无生产数据库读写/恢复/清理，无24h观察、子代理、commit/push；共享zcode UI提交d61c5ac不归本轮。完整路径、失败过程、当前边界见docs/TTS_REPAIR_STATUS.md顶部。

### Codex TTS正式会话激活（2026-09-13 02:48）

所有者回复“go on”批准正常关窗及原命令重开后，核验原Godot28676创建时间与实际工作目录，正常关闭并通过原start-anime-agent.cmd启动41708；保留健康Core1072/42476，不强制杀Core，正式接入Core看护27772、TTS看护27220及TTS38112。Core详情tts.available=true、CUDA声线真实预热/自检完成、.9配置保持、新生成有效WAV及窗口响应通过；重复原命令后五个核心进程身份不变、TTS心跳推进，通过幂等复核。临时关窗核验脚本首次Python参数引号失败时未关窗，修正后才执行；没有生产故障注入、正式测试聊天/会话删除、数据库检查/恢复/替换，普通应用启动自身的持久化不属于验收脚本清理。运行时代码沿用已隔离验证版本，本轮只更新激活证据与状态文档；保留正式窗口/TTS运行，无Provider测试、24h观察、子代理、commit/push，不冒领zcode当前HEADd61c5ac。证据见docs/TTS_REPAIR_STATUS.md顶部及本地tts-repair-Rq9q4a/activation-20260913-024538-975.log、live-voice-20260913-024706.json、repeat-start-20260913-024831-505.json。

### Codex TTS追加复合故障压力测试（2026-09-13 03:31）

所有者实际验证通过后要求进一步攻击性测试。Codex新增`tts-session-stress.py`、原CMD测试的复合/交接模式、精确测试看护暂停/恢复、仅观察Godot的测试入口及SPOOL隔离断言；sidecar增加并发、不完整请求、连续取消、真实30秒过载门禁4项HTTP测试。274项离线回归连续两轮、两轮9次复合检查、旧看护跨窗口延迟恢复两轮、播放/退出清理及静态门禁通过。保留SystemRoot大小写和Core快照时差两次测试脚本失败，只修观察器、不放宽生产身份校验；明确最外层看护被杀后的原命令补回不是自动恢复。正式9个进程代际保持、四个副本无遗留进程、TTS就绪及心跳新鲜；没有改运行版本、模型或声线，没有操作正式数据、重启用户窗口、开长测/子代理或commit/push。完整边界与原始证据见`docs/TTS_REPAIR_STATUS.md`顶部，复现方式见`docs/TESTING.md`。

### Codex TTS正式配套发布（2026-09-13）

所有者实际验证无问题并明确批准实装与push。本轮发布主仓TTS生命周期/双看护/短负缓存、隔离故障与原CMD播放测试，以及独立语音仓HTTP/真预热/健康状态及24项测试；既有声线与自检算法不改，提交均标记Codex。只读复核此前正式激活的Godot41708、Core42476、TTS38112和双看护仍健康，不重复重启。并行zcode的0ffaa4e已提交语音联动保留；其runtime已引用但未入库的Codex原emotion_presets.gd作为启动必需依赖补齐，不借机改表情。此前274项离线双轮、真实声线双轮及复合/代际测试证据见TTS_REPAIR_STATUS；本次提交前另验精确候选。保留本地历史恢复文档/备份，不上传数据库、私人内容、模型、日志或预览素材，不启子代理，不冒称24h/任意故障零中断。下方及上方旧阶段的“未push”仅代表当时状态。

### Codex 三方集成本机基线审计（2026-09-13；尚未交付脱机包）

续验声明（Codex）：所有者随后授权修复发现的缺口，并要求先复现zcode的设计/证据。Codex保留DS主脑+StepFun视觉、zcode预合成/后台任务/工具业务契约；新增`farewell_speech_gate.gd`，配套修改`farewell_exit.gd`、`runtime.gd`及Core告别派发，增加7项Core/46项Godot断言和原CMD长短音频回归。新增`tools/gdrive/`固定上游2025.1.14只读处理代码，补齐OAuth应用身份、显式路径和安全启动错误，旧`gdrive-mcp.cmd`指向该兼容层，四项离线测试和同凭据刷新鉴权通过；该目录含上游MIT版权/来源，不能全标为Codex原创。核心230项及Godot门禁连续两轮通过，真实CMD第二轮四场景通过，个人凭据哈希不变。模型/声线未改，未触碰正式数据/窗口、未读邮箱或网盘内容、未打开麦克风或push。细节和归属见`docs/INTEGRATION_ACCEPTANCE.md`；下段为此前仅审计阶段记录，不代表续验仍未修复。

按所有者授权在独立审计副本验证当前工作树，保留其他Agent的README/贡献声明及未跟踪文件，不操作正式数据库或正式窗口。仅修正两处测试设施：`verify_motion_asset.gd`由过期的三动作/倾听统一断言改为已安装五动作的分格式契约，保留哈希和轨道类型门禁，五项负对照与还原正例通过；`prepare_farewell_fixture.py`排除无运行时用途的编辑器缓存，避免深目录MAX_PATH失败。不修改模型、动作、运行时退出逻辑、语音配置或阈值。Core 223/223（无跳过）、sidecar 24/24、启动14/TTS生命周期13、Godot逻辑与真实GPU渲染、模型归档、桌面构建通过；获单独授权的19题真实云端单轮自动验收通过，两次尝试累计56次请求，使用合成屏幕/笔记，不访问私人MCP账户。私有缓存齐备后真实CUDA语音及两段STT通过，但仍借用开发机Python库。原CMD私有窗口实测复现告别音频约0.1秒播完即退出、动画仅推进约0.20秒；源码还存在动画到时截断长语音路径。首次私有语音因未随包准备Whisper-small缓存而失败，补齐副本缓存后通过；这些证据不等于跨机/全流程通过。完整矩阵、失败记录与下一步见本机`C:/Users/26052/Documents/Codex/tianyi-audit-GqQMpd/STATUS.md`；尚未验证真实麦克风/外部MCP账户/干净系统，未制作正式交付包、commit或push。

### Codex 项目文档与最终源码整合提交（2026-09-13）

按所有者最新要求停止运行包交付，新增根 `PRD.md`（实装功能、目录和关键文件用途、相对路径及依赖边界）、`docs/DELIVERY_STATUS.md`，接入 README 并同步维护文档。补交本地已验证的告别语音/动画共同完成、TTS短正缓存、MCP Windows引号、问候限定唤醒兼容、外置Core配置、Godot显式路径与对应回归；补齐Drive兼容模块和表情对照验证源码，不上传测试产物。Drive业务处理来自注明版本的MIT上游，Codex仅归属OAuth/启动兼容和整合；Core中zcode的思考状态二次检查以及已提交的会话/手帐UI保留原归属，不标为Codex原创。

提交前重新运行隔离Mock Core、启动/TTS逻辑、Drive离线测试、文档及staged安全检查；已有Godot/真实声线/集成证据与未验收跨机范围见公开交付说明。内部验收报告、恢复记录、原始视频、模型/声线二进制、凭据和个人数据库继续留在原位，不上传、不删除；私有TTS仓保持其既有同步提交。本轮不重启生产窗口、不访问真实API或MCP账户、不制作新运行包、不启动子代理。以上旧阶段“未push”保留为当时历史；本次提交以含Codex标记的Git记录为准。
