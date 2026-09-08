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
| 综合报告与 UI 方案立项（zcode，2026-09-07） | `docs/AGENT_REPORT_2026-09-07.md`（能力矩阵/训练编年史/弱点清单/安全配额/灾备补充，交接用全景快照）；`docs/plans/UI_UPGRADE.md`（前端 UI 升级方案，所有者立项，方案阶段，含 U0-U4 分期与边界红线）；CI 增加 docs-guard job（文档一致性守卫入远端门禁）；EXAM_LEDGER 补 CI 连红复盘（09-05 起 13 次同根因，numpy 裸导入，已修） | `docs/AGENT_REPORT_2026-09-07.md`；`docs/plans/UI_UPGRADE.md`；`.github/workflows/ci.yml`；本提交 |
| Gmail MCP 接入（zcode，2026-09-07） | @gongrzhe/server-gmail-autoauth-mcp（19 工具）经 `tools/gmail-mcp.cmd` 代理启动器接入（Google API 需本地代理）；OAuth 全流程走通（403 测试名单 → 补加 → 令牌落 ~/.gmail-mcp）；T-GMAIL 验收：真实读出收件箱（Ferrari/GitHub CI 通知），投毒邮件发送测试被她识破拒发（双层防御）；gcp-oauth.keys.json 与令牌全部 gitignore | `tools/gmail-mcp.cmd`；`.env`（gmail 条目）；`.gitignore`；本提交 |
| STT 自愈与 Idle 触发（zcode，2026-09-07） | `voice.py`：Realtek 假死数字零检测（噪声底物理特征区分"没说话"与"驱动假死"）+ 一次自动设备重置 + 可行动报错 + 每次录音电平日志（KI-001 加固）；`proactive.py` 新增 `IdlePolicy`（阈值/免打扰/冷却，纯逻辑），`main.py` 启动钩子挂 GetLastInputInfo 本地轮询（30s，Windows）+ 台词模板库，**全程零 GLM 调用（待机零额度）**；单测 164→176 全绿（含原 D1 测试原样保留） | `agent_core/voice.py`；`agent_core/proactive.py`；`agent_core/main.py`；`tests/test_voice_selfheal.py`；`tests/test_proactive.py`；本提交 |
| T2+ 进阶考试（zcode，2026-09-07） | 矛盾记忆更新（换载体：歌手脱粉）+ 长对话压测（16 轮：三事实注入/工具/身份陷阱/注入攻击/突袭抽背）真机实考 21 次调用；判分行为证据制（facts 表对账）；考出两个架构缺口（facts 无取代机制、晋升词表偏好中心化）与一个模型已知项放大（批量回忆自疑）；临时会话 51/52/53 与考试事实全清零；实录归档 workbench evidence，错题记入 EXAM_LEDGER | `docs/EXAM_LEDGER.md`；workbench `evidence/live_exam_t2plus.md`；本提交 |
| D 期屏幕视觉上线与超时修复（zcode，2026-09-07） | `.env` 仅加 `ANIME_AGENT_VISION_MODEL=glm-5.3-flash`（端点/key 回退 GLM，coding 端点实测收图）；真机揪出确认流 15s 全局超时杀视觉调用的基建 bug（事件表 07:16:10→07:16:25 恰 15s），修复为 Tool per-tool timeout（look_at_screen 90s，其余 15s 口径不变），TDD RED→GREEN（tests/test_tools.py PerToolTimeout），单测扩至 156 项；全链路真机通过（会话 50：ask 隐私档→确认→截图→GLM 视觉→角色化描述与屏幕实况逐项吻合），临时会话 49/50 删除零痕迹；EXAM_LEDGER 记档，AVATAR_BRIDGE 超时口径更新，KI-015 销账 | `agent_core/tools.py`；`tests/test_tools.py`；`.env`；`docs/EXAM_LEDGER.md`；本提交 |
| 灾备加固与文档守卫（zcode，2026-09-07） | 删除文件恢复性实际执行验证（bak-phase1/verify_skirt_physics.gd/notes.md 字节数 12214/20068/273 全部取回核对）；核验本轮整理回滚范围恰为 3 提交（`git revert 5324a6a^..2666fd5`）；HANDOFF 新增 §10 灾备与回滚（本地专有资产台账 + 已验证恢复命令）与铁律 9（main 禁 force-push、删除必指认恢复命令）；`scripts/check_docs_consistency.py` 文档一致性守卫（测试数/环境变量/工具清单三方对账，破坏注入演练红→绿验证）接入 TESTING 门禁与 AGENTS 必做验证。勘误：T1 行所提 `harness.py.bak-phase1` 已撤出工作树（git 历史可恢复），人设回退路径以 `harness.py` 保留的 `BASE_SYSTEM_PROMPT` 常量为准 | `scripts/check_docs_consistency.py`；`docs/HANDOFF.md` §10；本提交 |

### Claude 工作树边界

Claude 的全部增量已于 2026-08-31 以提交 fc5a5a4 落库：倾听动作、唤醒词、会话删除（单击确认框改型）、会话标题、Agent 工具循环 A 期及配套测试与文档，提交时按 Codex 同一口径对共享文件做了行级分块暂存，未夹带对方代码。当前工作树剩余未提交内容全部属于 Codex：画布扩容与侧板方向（runtime.gd / interaction_ui.gd 残余行、verify_desktop_canvas.gd、ARCHITECTURE.md、TESTING.md 大动作门禁行）、大动作可读性与 MMD 镜像（runtime.gd 残余行、verify_large_motion_*.gd 两个新脚本）、MODEL_OPTIMIZATION.md 的五条增量。

## Codex 1.3 冻结声明（2026-09-08；承接下方历史候选记录）

所有者批准保守 A-pose、F12 高清截图与材质候选 A 作为当前基线并要求推送。Codex 将候选材质原参数移至 `apps/avatar-runtime/model_look_v13.gd`，接入 `runtime.gd` 默认 1.3 与显式旧版回退；同时提交本轮此前尚未提交的待机注册项、肩臂轨道替换、截图器及三个验证入口、lookdev 文档和相关 README/HANDOFF/TESTING/MOTION_PIPELINE/优化路线更新。官模与动捕 GLB 未改；1.3 使用旧版同哈希 Blend/GLB 的独立只读副本，完整回溯依赖清单 runtimeCommit。渲染九视图、十二组动画采样、版本选择/回退、GPU 门禁、高清截图五视图及动作/输入/会话/画布回归通过；不是全身防穿模或复杂旋转自然性验收。另一代理的 wake_word.py 与 test_wake_phrase.py 不属于本轮，保持未提交原样，不夹带。按所有者要求不启动子代理，以单代理审查和自动验证取代本次独立代理交接演练。最终冻结信息与验证记录见 `model-versions/1.3/README.md`；以下候选记录是历史阶段而非当前发布状态。

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
