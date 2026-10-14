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

### Codex 视觉 API 配置更新与激活阻塞（2026-10-02）

按所有者授权核实 Qwen3.8-Flash 支持图像输入，在被 Git 忽略的本机 `.env` 更新视觉模型、Token Plan Anthropic 端点及密钥，并更换 DeepSeek 密钥；保留 DS 模型及端点、既有视觉序列化/解析实现和隐私确认门禁。密钥不入库、不回显。6 项视觉协议及 10 项 Provider 回归通过；真实 DS 连通检查返回 CONNECTION_OK（约 1.62 秒），Qwen 识别内存生成的文字/颜色/形状测试图返回 HTTP 200、模型 qwen3.8-flash，内容正确（约 3.28 秒）；其结果交给 DS 后摘要正确（约 1.98 秒）。隔离测试只使用临时数据目录，不读取个人聊天或真实桌面。

为加载新配置正常关闭原 Godot，确认会话看护清理旧 Core 后调用原 `start-anime-agent.cmd`；Core 在 MemoryStore 初始化读取 sessions 时报告 `database disk image is malformed`，未重新上线。随后仅以 SQLite 只读/immutable 模式核查正式库，sessions/messages 读取失败，quick_check 报告损坏页；只读检查前后 SHA-256 一致，但不能据此确定损坏发生时间或原因。未删除、重建、替换或恢复正式库，未使用空白数据库绕过故障。API 配置及独立连通验证完成，正式运行激活被数据库问题阻塞，不宣称整体交付完成；数据库恢复需另行确认范围。未改模型、动作、TTS 实现，未 commit/push。

### Codex 本地语音恢复、当前证据数据库恢复与激活（2026-10-02）

所有者随后授权恢复/修复并强化故障验收，明确选择仅恢复当前库可证实记录、备份独有记录另存恢复档案、不混入当前历史。Codex在原始冷快照上解析并校验记录，拒绝结构完整但表语义错位的候选；最终独立候选的完整性、关联、逐表摘要及MemoryStore迁移读写通过后，原子替换当前库并保留原损坏库与全部原始快照。恢复210条消息及14条记忆；备份独有896条消息仅留私人档案，不宣称损坏零页的历史全部找回。恢复材料和个人数据只留本地。

本轮代码归属：主仓 `voice.py` 离线缓存加载；`speech.py` 可重试错误分类、有界待播恢复、分段取消及预取失败时保留打断；`main.py` 移除负健康直接丢回复路径、恢复/失败提示、待播状态与新录音状态归属；`startup-common.ps1` 空CommandLine保护与进程/端口快照不一致的有界重取。新增专用回归、测试探针PID代际标识及观察器空值保护。兄弟语音仓仅 `voice_selfcheck.py` 的Whisper GPU/CPU加载与离线回归变更。保留Claude/zcode的原语音管线、权限、人设、工具和会话看护架构，不冒领其既有成果；不改声线权重、自检算法/.9阈值、模型、表情或动作。

证据：Core252、sidecar26、启动18、TTS生命周期13全部通过；独立Windows服务故障矩阵14项通过；真实CUDA声线/Godot实际音频输出两轮（恢复53.157/51.562秒）；最终原CMD组合测试覆盖并发启动、冻结看护+sidecar死亡、Core/TTS双故障、外看护终止后原CMD补回、额外三次sidecar终止、旧看护跨快速重开恢复，整体PASS且每轮恢复有实际播放。保留失败与修正记录，不改断言掩盖失败。DS/Qwen各一次独立云端复核联通，桌面构建、Godot输入、资产SHA、文档及diff检查通过。

23:49原CMD正式激活健康，真实声线ready、唤醒监听running且未暂停；物理人声交互仍待所有者反馈，不以合成输入替代。测试产物只保留小型证据，移除本轮明确标记的重复运行副本，未清理原项目/训练/历史数据。完整当前状态见 `TTS_REPAIR_STATUS.md`，本机证据在 `runtime-repair-20261002-tnykvY`。本轮未commit/push、未启子代理、未开24h观察，不承诺断电/驱动/网络等任意故障下零中断。

### Codex 公共语音播放闭环（2026-10-03）

保留Claude/zcode已有四场景及双看护。Codex新增 `playbackId` 分片回执、去重补发/明确失败重合成、失败不能消耗主动冷却、稳定告别WAV缓存与Godot预解码；更新WS契约及对应回归，不改模型/动作/声线参数/正式历史。新增Core21项（总273）通过，Godot播放器16及退出46断言通过；合成WAV9项与真实天依声线10项闭环验证覆盖四场景、坏音频、预热、丢回执、WS重连与Core离线告别；真实音频总线非静音且有输出。正式激活及组合进程故障的最终状态见 `TTS_REPAIR_STATUS.md` 最新节；本轮未commit/push，不将测试日志/私人数据上传。

### Codex 语音闭环验收后配套发布（2026-10-03）

所有者已明确确认真实倾听和语音回复正常，并授权本次GitHub同步。Codex仅汇总上面2026-10-02与2026-10-03的语音/启动恢复源码、回归测试和公开文档，主仓与原有anime-agent-tts语音仓分别以`fix(Codex)`提交；不是重写或重新归属Claude/zcode的原能力。提交前核对精确暂存集合、秘密/大文件边界及隔离源码回归，远端结果以两个main分支记录为准。保留现有天依窗口、私人数据/恢复材料、训练与模型资源，不带入历史运行包/日志/无关未跟踪工作；不启动子代理或再次生产故障注入。之前各条未推送描述均为当时历史。

### Codex 五仓实装依赖审计与现用声线备份补齐（2026-10-04）

所有者要求核对MVP、Workbench、TTS、Roadmap与Cloth Physics，并明确选择“保留分仓，补齐声线；官模/动作暂留本地”。Codex比对五仓远端、工作树及正式启动引用，确认MVP为产品主仓、TTS为独立运行配套，其他三仓分别是已并入能力的开发沙箱、规划证据及未实装物理实验。新增`docs/REPOSITORY_MAP.md`并回链README/HANDOFF/长期方案手册/交付范围；没有把实验或旧vendor快照覆盖到正式源码。

发现配置使用的SoVITS e5与原私仓e20不同，按授权在TTS私仓新增e5的LFS快照；GPT e15哈希一致，复用旧备份。新增私仓只读资产清单/校验器、恢复说明和12项合成小文件回归，38项TTS测试通过；实际备份及安装权重、配置、三条参考音频和既有上游补丁校验通过。训练成果保留所有者归属，Claude/zcode既有实现保留原归属。本轮只新增备份与验证文档/工具，不修改当前语音参数、源权重、模型、动作、私人历史或运行进程；不新建仓、不改可见性、不清理其他工作树。提交以Codex标记，远端提交与LFS实体需发布后另行核对，不将本次盘点称为跨机脱机验收。

发布核对：TTS私仓main已到`3814b4c9d32bb17c3638cf851e5649d9c7d17fa7`；使用空的独立LFS缓存从GitHub重新下载e5与GPT e15，真实对象SHA均与安装文件匹配。主仓文档一致性通过、官模SHA保持冻结值；后续主仓记录以本条所在Codex提交为准。仅移除本轮远端下载核验临时副本，不碰原声线/训练资源或旧未提交实验。

### Codex Agent能力全景评测与决策报告（2026-10-04）

所有者要求综合定位Agent核心能力，并将完整Markdown记录推送MVP供后续训练决策。Codex固定b0c2d34源码、现用Deepseek-v4-flash主脑及Qwen3.8-Flash视觉，在独立配置/SQLite/读写目录中调用原聊天处理、Harness、权限与工具循环，完成56个真实模型场景、84轮对话（153次模型HTTP）、36项定向工程探针；原Core273项回归通过。另核对五类真实MCP冷启动，以及GitHub公共README、官方文档搜索、Drive唯一无命中标记查询。报告保留首轮失败、复测、实际产物/回执及未验证范围；没有用模型口述完成替代文件或状态对账。

新增`docs/AGENT_CAPABILITY_ASSESSMENT_2026-10-04_CODEX.md`，更新README/HANDOFF入口及当前可靠性声明；发现授权误判、待办覆盖/伪成功回执、物理路径边界、结果裁剪/资源丢失、记忆召回及连接器问题，均仍待修。本轮不修改运行源码、提示词、正式数据、角色资产或语音，不将审计归为重写Claude/zcode能力。真实窗口/人声不在本次评测，8765只读健康探测当时不可达；不声称生产端到端通过。连接器仅回收本轮明确归属的子进程树；Gmail上游启动时自动复制现有OAuth应用配置的副作用与哈希验证局限在报告中如实披露。秘密、数据库、真实个人资料和本地原始日志不入库；测试合成记录以脱敏Markdown交付，提交标记Codex。

### Codex 非Agent综合评估与DS连接诊断（2026-10-04）

按所有者新增要求，补充模型/表情、动捕/衣发物理、STT/TTS四场景、UI、启动看护、数据恢复与分发边界的综合报告`docs/NON_AGENT_SYSTEM_ASSESSMENT_2026-10-04_CODEX.md`，同步README/HANDOFF入口。逐项区分本次实测、源码核对、历史验收及未完成项；原Claude/zcode的实现与所有者训练成果保留归属，不把报告工作标成新增功能。

本次只读核对现有Core/Godot/TTS与唤醒状态、运行Provider配置、官模和原动作、1.0–1.4全部归档、资源负对照以及私有声线5项资产/配置/补丁/安装权重；启动18项和TTS生命周期13项逻辑通过。复用当天相同源码的Core273回归，不重跑私人云端题库。4次独立DS短请求覆盖代理/直连及普通/工具schema，全为HTTP200；所有者随后确认未重启的原窗口现在能正常回复。截图历史传输原因仍未精确还原，明确不宣称已根治、不擅改Key/超时/代理或重装TTS。AppData只读事件检查发现Codex包LocalCache路径视图与当前证据边界，未将旧事件作为当日错误、未恢复/删除/迁移数据库。

本轮无生产故障注入、关窗重启、邮件发送、原始资料上传或子代理；只推送上述公开文档并带Codex提交标记。秘密、私人日志/历史、模型/动作和声线二进制不进入此次主仓暂存。报告发布不是跨机脱机验收或通用防穿模完成。

### Codex Harness V0 candidate：统一契约、评测校准与部分双模型基线（2026-10-04）

按所有者作为Manager的新任务，建立独立分支`codex/harness-v0-20261004`。读取HANDOFF/AGENTS、既有model_cert与当天两份评估；保留d3ed主工作树的DS/GLM未提交增量，不覆盖生产。只新增评测源码/文档：共享基础能力与角色合同、完整未激活提示词候选、26题固定夹具、确认消息精确关联、产物/回执判卷、隔离Core和受控stdio MCP、请求预算与可离线重判证据。`scripts/model_cert.py --harness-v0`复用入口，旧默认生产耦合CLI禁用。既有Claude/zcode核心实现不改、不改归属；Codex本次归属评测与合同候选。

冻结前25项校准通过；计划26题×2模型×3重复，实际每模型开始4题10次，共66次HTTP，因共享微信网关429停止后续题。Deepseek-v4-flash为5通过/0部分/4失败/69阻塞，GLM-5.2为6通过/0部分/3失败/69阻塞；每模型68个阻塞槽根本未运行，不能称全量基线完成。另8项零HTTP机制探针对已知正/负结果匹配，分列于真实模型成绩之外。拒绝后写入在两模型均3/3复现；候选提示词未用于测试，权限/上下文运行修复仅作为V1建议。

交付入口`docs/assessments/harness-v0/REPORT.md`与`SPEC.md`，从长期方案手册回链；全部输入/状态/数据库证据为合成数据，个人资料、凭据、真实邮箱/远端业务资源不进入测试。未连接生产Core、未动Godot/语音/模型，未启动子代理。脱敏后重判与HTTP账本核对、源码未变/文档/提交安全检查见候选包；独立白纸agent门禁未执行，停在Manager验收点。仅授权推独立分支，不合并main、不部署；远端是否成功以此次实际Git核对为准。

### Codex Harness V0 网关复测与138槽补测（2026-10-04）

按Manager“先把网关测试完成”的续作指令，保留原候选c310a67、原用例/判卷器/源码overlay/当前提示词。新增独立串行补测调度、每次网络计数与401/403/429停止门、原BLOCKED槽续测、错误元数据留存及离线审计，原评测文件未改。范围仅评测代码和公开合成证据，未改Claude/zcode运行代码或归属。

双模型探针通过；本次23题×每模型3重复=138次实际任务运行、500次任务HTTP，另2次探针，0次429；GLM有3次45秒超时。两批累计568/900次，26题每模型均有三次逻辑样本，保留旧429尝试后各79次实际任务尝试：DS43通过/3部分/32失败/1阻塞，GLM49/2/24/4。机械判卷不作模型排名：M05虚假完成漏判及M01/R01等价表达误判独立列入REVIEW，原分不覆盖。R03更正为本用例实测只注入1/5事实，3是代码上限。

调度器6项离线校验、原156行和新138行重判、198个原包文件逐字节保留、HTTP账本与精确关联、6个秘密值比对脱敏通过；干净Git导出、文档门禁及源码未变检查见`docs/assessments/harness-v0/batches/gateway-resume-01/delivery-checks.json`。入口仍为主REPORT/SPEC，补测目录含预登记、版本hash、逐例证据、全文复核及V1最小建议。无生产Core连接、真实邮件发送、远端业务写入、Godot/语音变动或新提示词激活；未新开子代理。仅交并推独立分支candidate，评测语义修订、超时缺项及V1实施仍由Manager决定，不合并main、不部署。

## Codex — 2026-10-04 Harness V1 candidate

按Manager本轮授权实现共享动作账本、精确参数版本确认、拒绝/改参/取消、多个待办、持久真实回执和崩溃未知态；补全工具结果续取、MCP resource正文、任务预算与记忆召回，共享天依音乐人格。并实现手动录音/本地简体回填/代际取消、600秒同闲置段一次提醒、三档投入预算；不改模型动作资产和TTS实现。保留既有zcode能力归属，本次不是重做其整套Agent。复用当前本地DS/GLM连接修复及V0源码overlay，完整V0用例/证据只读。所有实测、未完成与激活状态见 `docs/assessments/harness-v1/REPORT.md`，不以本声明宣称正式验收或远端业务测试通过。独立分支交付，不合并main。

Codex补测追加：repair-01暴露“写成：不要执行样本”被误当取消的回归。修正共享授权文本边界（引号/代码和显式正文不当指令，肯定授权仍须完整原文匹配），保留失败成绩；四个新增反例中三个修前失败，修后全套359项通过，待双模型定向复测。共享JSON恢复和后续闲置/正文修复为自审，不混同早先独立审查。按所有者最新要求将现场免打扰改为01:00–07:00，零模型请求的时段边界校验通过。

冻结后第二个独立实例复核授权文本边界，发现英语撇号、内容话题标签、空白否定和额外正文引用四类反例。Codex主执行者复现3项排队取消副作用反例并修复，修前55项中6失败、修后整套362项通过；详见Harness V1的REVIEW-FOLLOWUP。独立发现与主执行者修补/复测分开归属，不将其写为独立实例已经复测。

## Codex — 2026-10-07 全能力根因审查候选

只新增审计取证/离线反事实/覆盖脚本与文档，不修改既有Claude/zcode/Codex业务实现及正式提示词。锁定所有者桌面，经正常输入、原生确认、显示和播报链执行合成文件、邮件、Issue、记忆、Drive与DS/GLM对照。54次可关联模型HTTP（DS49/GLM5），一次明确批准的真实测试发信和一次审计Issue创建；Drive由Codex准备私有合成夹具，天依本机OAuth阻塞与资源桥缺口分列。模型对照完成后原入口恢复DS，配置与私有备份相同，历史不清理，官模/动作/声线不变。

登记256项覆盖（72有分层实证含失败、47阻塞、127未验证、10未启用/未实现），不是全能力通过。既有362项隔离回归通过、288条旧V1原判重放不改成绩；Sagan独立新上下文反例、主执行者复现与审计夹具修正分别记录。根因/证据界限、TTS高置信编码机制、数据身份风险及下一轮Manager裁决见 `docs/assessments/root-cause-audit/REPORT.md`。仅推审计独立分支，不合并main，不修业务，不宣称正式验收。

## Codex — 2026-10-08 第二轮根因审计部分交付

依据所有者授权，在837318335307c85bb288265d0b80b4c7256d46f0另建审计分支；仅增加round-02审计材料、合成夹具和可关闭取证/反事实脚本。前台Godot正常输入和原生确认、真人录音/600秒听感、DS三档与GLM同题、原始响应/票据/解析/记忆/GBK异常取证分层登记。独立新上下文审查和主执行复现分列，不归属为Claude/zcode产品重写。按用户最后10分钟收尾要求交付部分成果，259项未全面闭合，不实施业务修复、不改正式提示词、不合并main。原配置及诊断入口逐字节恢复；最终桌面/API/对象状态见round-02/REPORT.md与STATE.md。只推独立分支，私有历史、数据库、认证、推理正文与资产不入库。


## Codex — 2026-10-12 根因审计收口方案

依据93aedbeb07bd65e84cd0851498c46561de3643f8复核任务/回执与Godot消费源码及已脱敏原始链，形成五组集中修复方案、验收合同和独立反例处置。原259清单与成绩不改，未实施业务或正式提示词修改。本轮模型/TTS/STT/业务测试调用均0；局部反事实脚本未执行，当前部署/数据身份未核验。详见closure/REPORT.md及STATE.md。此为供Manager审查的方案，不是现场或实现验收。

## Codex — 2026-10-12 首批根因修复候选

依据所有者首批实施授权，从b2d871316b35287f17b0771dcd02212b4be2bb72另建实现分支。复用既有ActionLedger，修复无待办确认/继续、执行后异常回执交付、MCP业务/空/unknown与method合同、物理路径判断；配套TTS安全日志和确定性编码/瞬态恢复分类独立提交fb681d0a93bd6bd3d8b2785924dbaf264810dc5e。Core387项、TTS43项隔离回归及两位独立新上下文反例复核通过，不冒领原授权/声线/播放系统实现。

生产未提交工作/配置/历史未改，私有代码配置已备份；普通/UNC数据库身份不一致，SQLite操作在连接前停止。桌面控制执行器故障，未新开验收Godot、未调用真实模型/声线或外部业务；本轮不是桌面验收通过。A4自由文本及剩余范围明确保留。详见root-cause-repair/batch-01/REPORT.md和STATE.md；旧审计成绩、证据不修改。

## Codex — 2026-10-12 首批修复桌面续作

所有者重启客户端后恢复桌面执行器，通过正式入口新开唯一Godot，使用获准独立持久测试目录；普通/UNC身份与事务快照核实一致。真实DS短聊、原生文件确认、Gmail空结果/业务错误、历史列表重开及窗口重启留证；所有者明确确认声音清楚。GLM同类代表验收及后续状态以batch-01/REPORT.md为准，不把CLI独立核验计为天依执行。

现场发现旧待办覆盖普通答复、成功卡吞掉读回；修正当轮交付归属并保留实际分页。独立反例又补取消等待时假成功、尾页丢失；现场否定取消误撤销修复经双重否定/独立拒绝反例收窄。最终Core395项、TTS既有43项、独立交付7/7及确认20分类+3状态通过；没有更改正式人格/系统提示词或重造ActionLedger。真实证据、准备故障、失败和未完成边界分别记录，A4自由正文仍未闭环；生产原数据库/源码/配置和用户历史不覆盖，不合并main。

2026-10-12 20:27收尾增量：双模型文件/只读原文/Gmail空与失败均经Godot完成；GLM真实写入后补答超时仍交付成功，DS真实Issue读取后超时也交付。DS issue_write update经原生确认实际更新专用Issue标题并完整播报；GLM假待办和无票据拦截保留失败。正式重启历史及最后会话重开有证据；最终44次模型传输、62条持久消息、11动作、无待办。唯一Godot21368保留，Deepseek配置逐字节恢复，生产174+19源码及配置hash不变。TTS最终本地记录提交ea5c4abf04518c684a3da5c56994ff8f6f927d49；主仓真实结果见batch-01/REPORT.md、STATE.md及desktop-final/deployment-final.json。首批部分通过，A4未闭环；不push、不合并main。


## Codex — 2026-10-12 首批修复后台收敛

从d0ff796及TTS ea5c4ab另建独立工作区；所有者授权两私仓候选分支推送，基线已由GitHub连接器回读。独立反例复现分页ref坏类型/ALLOW异常只留AgentStep而丢任务回执；最小类型校验与unknown持久交付修复经修前失败/修后4项及Core399全套验证。另15用例100断言独立复验、TTS43复核。固定双模型18案例26传输，GLM两次假待办和一次超时保留，A4未关闭，未声明整批通过。取证runner隔离/推理字段投影问题经独立审查修正；原始证据不覆盖。没有操作Godot、连接在用Core/TTS、访问生产聊天记忆数据库或真实外部业务写入；未改人格、声线、配置或合并main。最终边界与可读证据见batch-01/FOLLOWUP.md。


## Codex — 2026-10-13 A4 控制链小试验（未通过集成）

沿463cbdd候选分支接手，新增任务决策/交付合同、一次有界纠正、引用归属与参数校验、预算非空失败交付及真实文件回执内容展示。保留原ActionLedger/权限/工具/存储/TTS；不冒领其实现。Core399基线与最终418项通过，首轮双模型10例6通过，保留失败且不补样。23为请求入口计数，首轮重定向分发不可追溯，不能宣称严格底层调用量已验收。

独立上下文 a4_independent 负责反例脚本和业务审查：初轮14例7失败、最终4失败，冻结源码hash绑定；三个HIGH语义绕过仍开放。a4_python_review 负责Python/运行器反例审查：异常/耗尽、计数、判卷和推理投影经定向修复，公开证据及10库历史只读重开核验一致；两审查脚本互审，主执行者整合。未操作当前桌面进程，未部署/合并main。所有者授权仅推送私有候选分支，最终停在Manager验收。真实结果与复现入口见root-cause-repair/a4-pilot/REPORT.md；不把单测全绿称为A4完成。

收尾偏差：主执行者运行文档一致性检查遗漏显式隔离环境，动态discovery导入Core会初始化默认MemoryStore；不能证明默认数据库未被触及，实际影响未核验。已向用户说明并停止此类检查，未继续读取或自行还原默认库；此项单独交Manager验收，见报告execution-deviation.json。该失误不改变隔离模型/回归证据，但不能宣称本轮生产数据边界全部得到证明。

## Codex — 2026-10-13 检查入口隔离前置修正

check_docs_consistency 自行建立临时数据/合成配置，在独立子进程动态导入前核验；配置或路径异常提前退出，审计守卫阻止非隔离数据库、私人.env、越界写入及外部I/O。三项测试含五种错误上下文的合成哨兵、真实导入与公开入口通过，Python独立差异审查无阻断问题。证据：a4-pilot/evidence/pending-isolation.json。此项独立提交，不改变业务源码；保留上次影响未知记录，本轮不检查或恢复生产库。

## Codex — 2026-10-14 已有待办跨轮状态交付（窄范围通过）

沿8ae77011接手，先以独立提交e8c2e385修正文档检查隔离入口，再修main/task_status明确进度查询：按当前会话完整账本逐任务交付，保留普通聊天、票据、参数版本及操作预算，确认/取消/改参仍走已有机制。原跨轮反例先复现失败再通过；最终Core431隔离回归通过，新增13项定向回归。没有改ActionLedger/权限/工具/存储/TTS的原实现，不冒领既有能力。

pending_product_review独立上下文先提出并复现不同问法、问候回退、带空格文件及复合撤权时序反例，主执行者定向修正，保留所有首次失败；最终13例37检查通过并绑定业务hash。pending_isolation_review做Python/隔离及审查脚本互审，发现并验证修复运行器根绑定与异常假PASS，最终小差异无阻断。零真实模型/外部业务调用，不操作Godot/Core/TTS服务，不读或恢复生产库；上次数据库影响未知记录保留。报告a4-pilot/PENDING_STATUS.md只判本项通过，A4其他语义漏洞仍开放，候选分支推送后停在Manager验收，不部署或合并main。

## Codex — 2026-10-14 文件任务跨模型交付（部分验收）

沿509e69b9接手，只改main及新增file_task窄文件写后读义务；沿用原工具/ActionLedger/权限/存储/Provider及跨轮状态，不冒领其实现。自然语言原任务与正常确认继续实际read_file，宿主用真实完整正文交付；字面正文错误先纠正，未读/失败/unknown明确未完成。新增20项入口回归，最终Core451通过。统一file_models入口按Provider配置切换，真实模型不预填意图、工具或结果；独立持久库、共用30次HTTP封顶、脱敏证据及历史重开检查保留。

file_flow_independent独立上下文先复现问法、正常解释、分页、取消改参及跨轮正文约束反例，主执行者定向修正，最终24项通过。file_python_review独立Python/运行器审查纠正空读取判卷、核验硬预算及隔离、非文件编辑负对照，最终14项通过；所有首次失败保留，两结论绑定最终业务hash。真实模型共9次任务运行、30HTTP，最终同源六例真提案/正确写入全部通过，DS3例和GLM2例完整交付，GLM末例额度耗尽未读回，不能声称六例全过；历史中间DS成功另列。报告a4-pilot/FILE_TASK.md。

未打开或恢复生产库，旧数据库影响未知记录保留；只读取获准模型连接字段，不改当前Godot/Core/TTS、TTS源码或部署合并main。私有候选分支授权推送，停在Manager验收，剩余为GLM第三例完整验收及原A4范围外开放项。

## Codex — 2026-10-14 GLM 第三文件样例补验（通过）

业务冻结87ca474，仅给file_models增加显式关联原30次账本的补验预算入口和一次性领取登记；不改业务/提示词/schema/每任务预算/原12判据。一次全新GLM-5.2 variant3任务完成真提案、正常确认写入、实际read_file与完整交付，新增4HTTP索引31–34、累计34/38；未使用剩余额度。原72材料及旧30账本字节不变，原5/6历史保留，本次1/1另列。

file_supplement_review独立Python复核先指出换账本重复领取的静态边界，主执行者补一次性登记；35项预算/隔离离线检查与9项新增证据/只读重开核验通过，首个夹具NameError另列非产品失败。file_supplement_evidence独立代码审查核验runner小差异、审查脚本和最终live证据、原始归一化messages及业务冻结一致性，无阻断。本轮复用未变化业务的451回归与原对抗，不重跑DS/六例/451。报告FILE_TASK_SUPPLEMENT.md；生产库/当前Godot/Core/TTS不动，不部署或合并main，候选推送后停在Manager验收，仅文件流程具备收尾条件，A4其他项未关闭。

## Codex — 2026-10-14 Issue 仅改标题并重读核验（部分验收）

沿bc58e313接手，直接复用文件流程的任务推进、授权、确认、执行回执与单次纠正。改main/actions，新增verified_task薄分派和issue_task窄适配：目标/标题/字段范围约束、真实旧值基线、更新后的读取代次及字段快照核验，成功交付由宿主绑定真实写后读取。文件实现、权限、Provider、schema、存储、TTS不改；不复制控制循环，不冒领Claude/zcode既有机制。

先通过文件20项基线再复现旧Issue链失败。主执行13项、文件修后20项通过；首次全量失败保留，修正后485项通过，最后一行否定范围修正再跑原A4 19项、独立21项及scope3项。issue_independent独立上下文先提出并复现否定范围、带引号仓库及解释误激活等反例，最终21+3通过并绑定最终源码，原夹具错误另列。issue_python_review独立核对运行器/隔离/预算/失败分类，39项离线通过，两审查脚本互审；最终四例与账本只读44项通过，证据通过不等于任务通过。

后台合成MCP四次真实模型任务同源同schema同预算，首轮DS/GLM均通过后各扩样一次。DS1、GLM1、GLM2真提案/仅标题更新一次/实际新读/准确交付通过；DS2更新提案前45秒连接超时，实际只读一次、零更新、明确未完成，失败不重跑。共21/40HTTP，整体3/4部分完成，剩余阻塞为DS第二样本完整证据。报告a4-pilot/ISSUE_TASK.md。未接触生产库、当前Godot/Core/TTS或真实GitHub业务对象，旧A4及未知数据库影响记录保留；仅候选分支推送，未部署或合并main，停在Manager验收。

## Codex — 2026-10-14 DS 第二 Issue 样例补验（通过）

按所有者明确续作授权，冻结aebcd50d业务、运行器、提示词、schema及原13判据，沿原40次HTTP账本做一次全新空初态DS variant2。217文件冻结核验一致，原失败与四例本机报告不变；Deepseek-v4-flash经原聊天入口及正常确认完成正确提案、一次仅标题更新、真实后置读取和逐字交付，13/13通过。新增6HTTP编号22–27、累计27/40，剩余13未使用；原3/4记录不改，本次1/1单列。

本轮仅一次独立只读复核新增任务副作用、票据/任务/读取关联、新库重开和账本增量，复用原回归、对抗与交接结论，不重跑文件/GLM或旧成功例。进度列表既有“号/千克”格式化限制单列，业务不改。报告a4-pilot/ISSUE_TASK_SUPPLEMENT.md；只认证后台合成MCP窄流程具备Manager收尾条件，不证明连接稳定性或真实GitHub集成，不关闭其他A4项。生产库、当前Godot/Core/TTS和TTS版本未动，不部署或合并main。

## Codex — 2026-10-14 单收件人纯文本邮件（合成 Gmail 通过）

沿fb35fa14接手，复用既有verified_task、真实handle_chat、权限/确认、ActionLedger、unknown及交付补救；新增email_task窄适配、原生发送ID核验、默认MIME去重与旧票据哈希兼容。地址、主题、正文逐字核验，附加字段造票前拒绝；成功交付限定发送请求受理，不冒领Claude/zcode原机制。不复制聊天或授权循环、不按模型名称分支，不改main、agent_loop、harness、权限、存储、file_task或issue_task。

修前文件20项和Issue13项通过；邮件10方法中7失败，测试替身不足错误另存。首次模型版本Core510项全量通过。email_independent独立上下文先提出自然措辞、解释误激活、地址/正文改参等反例并修复，首次15项通过；email_runner_review独立指出schema冻结遗漏，补指纹后38项预算/隔离/验收对照通过。首个DS因改写正文失败，零票据/发送，2HTTP证据保留；仅加强逐字参数错误反馈，在原一次纠正内修复，25项定向与独立16项通过，当前共511个测试，没有冒称最终全量重跑。

最终同源DS/GLM各两例均12/12通过，原失败单列，阶段15/40 HTTP。DS最终首例实际重复提出相同send_email，账本复用回执，合成服务只受理一封；每例独立核对邮件参数/原生ID、重复确认及历史/账本/邮箱重开。EMAIL_TASK.md记录完整来源、证据和剩余边界。未发送真实邮件、未访问生产历史或改变当前Godot/Core/TTS，旧数据库影响未知和其他A4项保留。仅候选分支提交推送，停在Manager验收，不部署或合并main。

收尾补充：运行器最终只读证据55/55通过，确认DS与GLM的重复提案均未重复派发。两位零上下文白纸检查对干净e32e57c各完成8问，指出最终全量缺口后，主执行者在源码冻结下补跑511/511完整Core回归，零失败/错误/跳过/模型请求。旧510与全部失败保留；剩余Idle/UI等历史文档漂移登记为范围外，不扩展业务修改。


## Codex — 2026-10-14 基础流程交界收口（局部通过，整体冻结阻断）

沿601b81e8接手，在既有handle_chat/verified_task/权限/ActionLedger/回执链上验证文件→Issue→邮件、两会话待办及Provider替换。只修文件任务无关业务写入造票，以及明确继续既有任务时状态/预算和假完成交付缺口；保留只读ASK、聊天/解释/澄清与原工具合同。首次9项1失败、补充10项1失败及独立措辞/只读回归反例保留。最终新增10项、独立6项和受影响旧148项通过；复用原511全量证据，当前发现527，未重跑全量或旧模型样例。

closure_independent进行一次差异及新增证据复核，反例修正后回验；最终16个持久合成库只读重开核对，零真实模型/业务调用。BASELINE_CLOSURE.md分列已关闭子集、A4/C1数据及生产阻断和未实现扩展。通用自由正文假完成仍HIGH，因此不能宣布基础内核整体冻结通过。未操作生产库/私人配置/当前Godot/Core/TTS，不部署或合并main；按本轮明确授权仅候选分支提交推送，停在Manager验收。


## Codex — 2026-10-14 通用回复发布前核对试点（未采用）

沿6a1d523接手，新增general_reply_check一次tool-free提取与宿主证据核验；file_models仅新增reply场景及语义用例适配，复用原Provider/隔离/HTTP账本。未改main/task_delivery/harness/权限/ActionLedger/存储及文件Issue邮件适配，既有流程与交界保持。原两条A4失败由旧trace复用，初始7例及独立4例/模型固定；首DS2次程序/判卷偏离保留，实际源码修正后验证，不刷失败。

general_independent同一上下文独立准备未见语义样例、复现重复键和正常get_time举证、以及退场HTTP线程/锁竞态，主执行修正，最终独立14项通过；主执行5项通过，旧运行器38项通过。真实总24/40次HTTP，原score不可代表对象完整性；独立人工严格DS9/11、GLM5/11，GLM正常引用/假设被误拦。未接入聊天发布链，发布顺序/记忆清除/缺decision兼容未验，旧A4未关闭，当前不采用。GENERAL_REPLY_CHECK记录代码、全部失败、逐例结果、判卷修正与耗时；要求后续全部阻断完成后同一最终源码统一终验，不拼接旧结果。未操作生产库/当前Godot/Core/TTS，不部署或合并main，仅授权候选分支提交推送，停在Manager验收。

## 2026-10-14 Codex — 明确更正已有记忆

Codex 2026-10-14：[明确更正已有记忆](assessments/root-cause-repair/a4-pilot/MEMORY_CORRECTION.md)完成窄范围修复与验证：实体/属性/范围/旧版本核验，原子替换与历史保留，保存读回后真实回执；仅本会话覆盖不改全局。受影响337项及运行器38项通过，独立32项包含其中；DS/GLM各3条完成实际进程退出/重启后的事实性核验，实际84次HTTP。GLM展示降级与额外工具失败单列，原失败及独立复评保留。当前发现602个测试，未执行全量终验；通用回复核对器仍未接入，A4不关闭。文件/Issue/邮件/交界保留，未触碰生产库或当前Godot/Core/TTS，未部署、未合并main，停在验收点。

沿4a386a9接手，复用MemoryStore和旧反例；修改storage/main与新增窄语法更正模块、自然聊天回归。memory_independent在同一次持续差异审查中提供未见改述/错误对象、处理失败后复验及最终证据只读核对。扩展原file_models记忆场景和真实双进程运行，不另建预算平台。判据修正保留原始报告和旧侧车，全部业务源码一致；不以表格格式失败冒称事实错误，也不把事实性通过宣称公共格式协议修复。获授权仅在候选分支提交推送及远端回读，未部署或合并main。
