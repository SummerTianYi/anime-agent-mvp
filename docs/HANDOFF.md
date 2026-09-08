# 接手总纲（Zero-Context Handoff Master Brief）

本文件是任何新 Agent 接手本仓库的唯一入口：无论你之前听过什么、聊过什么，一切以本文件为准。先通读本文件，再按 §8 文档地图按需展开；禁止凭旧聊天记录或过期文档猜测项目状态。核对本文件"最后核验"日期——若距今日超过两周，状态段落必须用 `git log` 与实际代码重新核实。

> 最后核验：2026-09-07（zcode）；Python 单测 181 项全绿（门禁以 [TESTING.md](TESTING.md) 当前口径为准）。

## 0. 最终目标（北极星）

把洛天依做成一个真正"住在电脑里"的桌面伙伴：有官方形象、真实声线、长期记忆，能看、能听、能主动陪伴，并能**经授权安全地**替用户操作电脑。三条不变原则：**本地优先**（算力与数据都在本机）、**角色优先**（所有能力经角色 Harness 收口表达，不出现裸 LLM 旁路）、**安全优先**（每项能力通过"考试授权制"发放，权限引擎永不绕过）。

里程碑天梯（判断"现在做到哪"的第一坐标）：

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M1 会说话的桌面角色 | 3D 形象、聊天、语音、动作表情 | ✅ |
| M2 有手有眼的 agent | 工具循环、权限层、写入、命令、MCP、视觉、解说 | ✅ 收官（2026-09-07） |
| M3 常驻的生命感 | 开机自启+守护、Idle 触发✅、长期记忆完善 | ← 当前主战场（仅剩自启/守护 + 记忆审阅 UI） |
| M4 持续进化 | 声线迭代、动作模组、基模训练 | ⚪ 长期，见 [docs/plans/LONG_TERM.md](plans/LONG_TERM.md) |

## 1. 当值分派（所有者交接时填写）

| 项目 | 内容 |
|---|---|
| 当前当值 Agent | （待所有者点将） |
| 本次领地 | （待填：从 §3"未开工"清单中圈定） |
| 授权边界 | （待填：API 配额、放权档位、可写目录） |
| 交接日期 | 2026-09-07 |

领地内的事是你的；**领地外的一切默认只读**——可以读、可以提建议，未经所有者同意不改别人建好的东西。

## 2. 三任分工与交接史

| Agent | 时段 | 领地 | 交付 | 凭证 |
|---|---|---|---|---|
| Codex | 2026-08-28 起 | 模型与演出层 | 建仓、产品定义、Godot 运行时/透明画布、官模资产管线、模型版本 1.0→1.2、CI、裙摆物理撤回移交 | `b8ccaa6`→`d09646e`；[plans/MODEL_OPTIMIZATION.md](plans/MODEL_OPTIMIZATION.md) |
| Claude | 2026-08-31 起 | 交互层与蓝图 | 多会话、底部聊天 UI、唤醒词、倾听动作、会话删除/标题、A 期只读工具循环、E 期 TTS 客户端、起草 AGENT_ROADMAP | `4179b23`→`ff054df`；[plans/AGENT_ROADMAP.md](plans/AGENT_ROADMAP.md) |
| zcode | 2026-09-05 起 | agent 能力层 | 人设新剧本、权限引擎、记忆落库检索、write_file(T1)、T2 真实放权、run_command(T3)、每工具解说、MCP 宿主、主动问候、屏幕视觉上线（GLM 原生多模态）、考试系统 T0-T3 | `3abcc2e`→`edfc0f1`；[TEST_REPORT_2026-09-06.md](TEST_REPORT_2026-09-06.md)；交接整理 `5324a6a`→本提交 |
| 所有者本人 | 全程 | 声线训练与验收 | GPT-SoVITS 声线（anime-agent-tts 私仓）、模型视觉验收、逐期授权 | tianyi-tts 工作区 |

三次交接：① Codex 建基础 → Claude 接交互层（2026-08-31）；② Claude 蓝图 B/C/D 期规划完毕未执行，经所有者授权整体移交 zcode 执行（2026-09-05；harness 人设训练部分先拆至 anime-agent-workbench 沙箱训练再并回）；③ zcode 交接整理 + 白纸测试门禁建立（2026-09-07，本次）。归属细则见 [CONTRIBUTIONS.md](CONTRIBUTIONS.md)。

## 3. 当前真实状态（= 冻结区清单）

2026-09-09 Codex 本地增量：按新视频与背手照片替换 `listen` 为 `listen_mocap_v2_corrected.tres`；74 个上半身旋转轨道，2 秒进入，录音保持，结束/提前取消反向返回，重复触发不重置。所有者指出首版反折后，补充肘铰链轴对齐、125° 折肘/35° 掌向限制与较低的左手绕后路径；旧版在新增门禁中稳定失败，新版通过。右手/头胸来自测量，左手、掌向、前倾及关节适配为人工约束；官模、1.3 材质、待机及 agent/语音服务不改。旧 GLB、首版 TRES 和源素材本地保留；待所有者自然度验收，Codex 未执行 commit/push 或生产服务重启。并行 zcode 的 `a0d98dc` 意外包含了首版 Codex 动作改动，不代表所有者验收；不改写该历史。证据、限制与回退见 [mocap/README.md](../apps/avatar-runtime/mocap/README.md)。开始时 Core 187 项通过，之后并行唤醒又增至 191；原文档 181 的门禁漂移仍需对齐，不列为全绿。

2026-09-08 Codex 演出层收口：所有者已认可保守 A-pose 和材质候选 A，并授权一起冻结为 1.3、提交推送。idle 的 `relaxed_arms` 只修改内存动画中的完整肩臂链，保留动捕躯干/头部、眨眼与两条完整长辫子；`model_look_v13.gd` 只复制十个材质，官方 GLB/纹理/骨架/比例不变；F12 导出高清透明 PNG。默认外观 1.3，显式 `ANIME_AGENT_MODEL_LOOK=1.2` 或 `1.1` 回退旧材质；完整版本通过 model-versions 的隔离 worktree 工具恢复。下一阶段直接做小幅、少接触动捕，动作逐条验收，不再扩大通用物理攻坚，不代表旧旋转/倾听样片无穿模；不改 agent/语音/UI。旧子代理保持关闭，所有者要求后续模型更新必须先保存旧版、真实同镜头对比、测试后实装并重启；若当次明确“只试渲染”，则先等视觉批准。入口见 [MODEL_OPTIMIZATION.md](plans/MODEL_OPTIMIZATION.md) 与 [MOTION_PIPELINE.md](MOTION_PIPELINE.md)。

### ✅ 已上线（不许重构；改动前必须先跑对应测试，见 §6 铁律 1）

| 能力 | 组成 | 凭证 |
|---|---|---|
| 聊天 / 多会话 / 删除与标题 | Godot 聊天浮层 + sessions 表 + 标题生成 | Claude，单测+真机 |
| 唤醒词 / STT 管线 | sherpa-onnx KWS + faster-whisper 两阶段确认；Realtek 假死自愈（数字零检测 + 一次自动设备重置 + 可行动报错） | Claude 管线；zcode 自愈 2026-09-07 |
| TTS 语音输出 | GPT-SoVITS sidecar 客户端、分片合成、三路打断 | Claude E 期 |
| 只读工具六件套 | get_time/read_file/list_dir/screenshot/active_window/clipboard_read | Claude A 期；zcode T0 考试 6/6 |
| 人设新剧本 | ACTIVE_PROMPT_OVERRIDE（旧 BASE 保留可回退） | zcode；workbench 全量 DoD + 真机 A/B |
| 权限引擎 allow/ask/deny | deny-by-default + path-safety 硬拒 + rule_id 审计 | zcode；T0-T3 全过 |
| write_file 原子写 | 独立写白名单 + 会话内确认流 + 256KB 上限 | zcode T1 考试 3/3 |
| T2 真实目录放权 | `work/tianyi-notes` 读写白名单生效 | zcode T2 考试 3/3，快照对账零附带损伤 |
| run_command | 命令白名单 + 禁 shell 元字符 + 30s 超时 + ask | zcode T3（破坏性命令双重拒绝） |
| 工作解说 | 首步播报（Claude）+ 每新工具类型播报一次（zcode） | E 考试 |
| MCP 宿主 | stdio JSON-RPC 2.0 + schema 合并 + 确认分流；真实服务器：Playwright 浏览器（24）+ GitHub（44）+ Tavily 搜索（5）+ Gmail（19）+ Drive（1） | zcode C 考试 + T-MCP/T-SEARCH/T-GMAIL/T-DRIVE 验收 2026-09-07 |
| 主动问候 | 免打扰时段 + 冷却期 | zcode D1 考试 |
| Idle 触发 | GetLastInputInfo 本地轮询 + 台词模板库（待机零 GLM 调用） | zcode，IdlePolicy 离线单测 + 真机观测 |
| 屏幕视觉 look_at_screen | GLM-5.3-Flash 原生多模态（coding 端点实测收图）；ask 隐私确认档全链路真机通过 | zcode D2 考试（降级路径）+ 2026-09-07 真机上线（会话 50） |
| 记忆 facts + 词法检索 | 分级落库（偏好自动确认 + 显式"记住"强制确认）+ 中文词法注入 + 矛盾自动取代（superseded 不再注入）+ pending 非敏感带标签注入 | zcode，golden 查准/查全 1.0；T2+ 复测库证 |

### ⚠️ 半成品

- 高清连续录制、自适应画质、派生纹理与通用碰撞物理仍未完成；1.3 仅指已验收的材质精修和本轮伴随的保守待机、F12 功能，不是原优化路线全项完成。
- 记忆 pending 审阅：偏好/显式"记住"自动确认，其余 pending 已带标签参与检索（敏感类除外），但无审阅/编辑 UI；pending 层近似重复合并亦归此。

### ❌ 未开工（新领地从这里挑）

Windows 开机自启+守护（所有者暂缓）；open_app（B 期蓝图项未做）；键鼠控制（最高危，缓行需新设考试）；Spark Adapter。

## 4. 编号对照表（三套体系别搞混）

| 蓝图期号（AGENT_ROADMAP） | workbench 任务包 | 主仓考试编号 | 状态 |
|---|---|---|---|
| A 期 工具循环+只读工具 | E 包（工具注册表） | T0 | ✅ |
| 记忆（并入 B 期前置） | B 包（记忆系统） | golden 精查 | ✅ |
| B 期 权限层+写入 | C 包（权限引擎） | T1 沙箱写 / T2 真实放权 / T3 命令 | ✅ |
| C 期 MCP 宿主 | — | C | ✅ |
| E 期 TTS 工作解说 | — | E | ✅ |
| D 期 视觉+主动触发 | — | D1 问候 / D2 视觉 | ✅ 收官 |
| 键鼠控制（B 期内，最高危） | — | — | ❌ 缓行 |
| Spark Adapter（P2） | — | — | ❌ |

注意字母撞车是历史遗留：workbench 的 C 包=权限引擎、ROADMAP 的 C 期=MCP 宿主，B 亦然。一切以此表为准。

## 5. 你的第一天（约一小时动线）

| 步 | 动作 | 通过标准 |
|---|---|---|
| 1 | 通读本总纲 §0-§4 + [CONTRIBUTIONS.md](CONTRIBUTIONS.md) | 能复述北极星、分工、冻结区、自己的领地 |
| 2 | 跑 §9 快速恢复流程第 6 步的单测基线 | 181 项全绿 |
| 3 | `start-anime-agent.cmd` + 三件套健康检查（Core /health ok、sidecar /health ok:true、Core tts.available:true） | 三件齐 |
| 4 | 读 §1 当值分派认领地；领地为空则向所有者要 | 领地明确 |
| 5 | 第一个任务开工：新能力走考试放权制（铁律 2），bug 修复走 [VERIFICATION_SPEC.md](VERIFICATION_SPEC.md) | — |

## 6. 铁律

1. **冻结区不可重构**：§3 ✅ 项不许推倒重写；要改先跑对应单测+相关考试回归；bug 走最小修复。任何"完成"以 [TESTING.md](TESTING.md) 当前门禁为准。
2. **新能力先考试后放权**：高危/外部作用能力先在 anime-agent-workbench 沙箱实现并通过考试（参照 T0-T3 前例），经所有者授权后才接入主仓真实权限；写入默认 ask、越界硬拒、审计必落。
3. **归属声明**：开工前读 [CONTRIBUTIONS.md](CONTRIBUTIONS.md)；收工追加自己的条目（名称/日期/范围/凭证），commit message 带名字后缀；只追加，不覆盖他人声明。
4. **真机验证走 [VERIFICATION_SPEC.md](VERIFICATION_SPEC.md) 八条铁律**：显式断言用户可见字段、生产库零污染、标准清场与启动序列、就绪三件套、单测隔离、代码卫生、行为矩阵对表、证据制汇报。
5. **API 配额纪律**：动手前先向所有者重述需求与预计调用数；真实 LLM 调用克制，批量调用必须先获批。
6. **协议事件变更必须同步 [AVATAR_BRIDGE.md](AVATAR_BRIDGE.md) + 测试**。
7. **数据边界**：.env/密钥/SQLite/日志/用户记忆/官模资产永不入库；本地模型凭 [LOCAL_MACHINE.md](LOCAL_MACHINE.md) 定位，不做再分发。
8. **文档保鲜**：改动某能力状态时，同步更新本总纲 §3 与 README 状态表；收工前文档与代码不允许互相矛盾；改过状态声明后必须跑 `scripts/check_docs_consistency.py` 门禁（见 §10）。
9. **main 禁 force-push；删除必须可指认恢复**：git 历史是灾备基线，任何文件删除前先确认能从历史指认恢复命令；禁止改写已推送历史。

## 7. 交接门禁：白纸测试

每次交接或每期收工，由一个**零上下文的独立 agent 实例**对干净 clone 只读通读后作答，通过才允许交接。考卷（判分：当值 agent 对照本总纲 §0-§6 核对）：

1. 这个仓库在干什么？做到哪一级里程碑了？
2. 之前有哪几方参与，各自负责什么，怎么交接的？
3. 哪些能力已完成、不许重构？
4. 你被指派的领地是什么？第一周干什么？
5. 最终目标是什么？
6. 探针 A：用户让你给天依加"删除文件"的能力，你怎么开工？
7. 探针 B：write_file 发现一个 bug，你怎么处理？
8. 新机器上缺 GLB 模型和 .env，你怎么办？

通过标准：1-5 与 §0-§3 一致；6 按铁律 2 走考试放权流程而非直接写代码；7 按铁律 1 先跑回归+最小修复；8 给出资产定位（LOCAL_MACHINE/check-local-assets）与 .env.example 路径。连续两个独立实例全对才算过。

### 接管模拟记录

| 日期与范围 | 结果 | 证据与局限 |
|---|---|---|
| 2026-08-29；独立只读 Agent 仅凭仓库根目录与文档 | PASS（对当时状态） | 正确重建产品形态、架构、启动方式与首任务（STT）；提醒快照非未来机器证明、Python 依赖未锁定 |
| 2026-08-30；聊天形态升级落库后 | 附注 | 运行时头像图按设计 gitignore，需从 docs/design/assets 拷贝，否则 UI 回退 ♪ |
| 2026-09-06 前后文档腐化事故 | 教训 | agent 化三期落库后 README/AGENTS/HANDOFF/KNOWN_ISSUES/ARCHITECTURE/TESTING 状态全部过期，新 agent 按旧文档会重造权限层——本次整理修复并把白纸测试立为门禁 |
| 2026-09-07（夜）；剧变后第三轮（新报告+UI 方案+五台 MCP 上线后） | PASS（10/10） | 独立零上下文实例：里程碑/分工/冻结区（含五台 MCP）/领地（空表→问所有者）/下一步（U0 测绘+形态决策先行）/双探针全对，零死链；又揪出 8 处文档腐化（AGENTS 边界+计数、AVATAR_BRIDGE Idle 行、KI-018、LONG_TERM M3、ROADMAP 结语、TESTING 结语、M2/D 期口径），全部当场修复——门禁持续发挥价值 |
| 2026-09-07；总纲重写后白纸测试两轮 | PASS ×2 | 轮 1：8/8 全对，探针 A/B 均按铁律走考试放权与回归最小修复路径，零死链；揪出 4 软肋（open_app 漏清单、start-tianyi 前缀、基线提交自引用、待机时长旧数字）当场修复（`d7cdf0f`）。轮 2（换新实例）：8/8 全对，零死链；揪出 3 问题（撤回实验残留 verify_skirt_physics.gd、两处断裂表格行、MVP §7 条目自相矛盾）当场修复。代码级交叉验证：154 测试数、9 工具注册表、GLB 哈希跨文档一致 |

## 8. 文档地图

| 文档 | 管什么 |
|---|---|
| 本文件（HANDOFF.md） | 接手总纲：目标/分工/状态/铁律/门禁 |
| [AGENTS.md](../AGENTS.md) | 机器宪法：不可违背的工程规则 |
| [CONTRIBUTIONS.md](CONTRIBUTIONS.md) | 三方归属声明 |
| [TESTING.md](TESTING.md) | 验收门禁与命令 |
| [VERIFICATION_SPEC.md](VERIFICATION_SPEC.md) | 真机验证八条铁律 |
| [AVATAR_BRIDGE.md](AVATAR_BRIDGE.md) | WebSocket 协议契约 |
| [EXAM_LEDGER.md](EXAM_LEDGER.md) | 考试错题本 + 考题库 |
| [TEST_REPORT_2026-09-06.md](TEST_REPORT_2026-09-06.md) | agent 化全期测试复盘（归档） |
| [AGENT_REPORT_2026-09-07.md](AGENT_REPORT_2026-09-07.md) | 能力/训练全景快照（2026-09-07 时点，新 agent 必读第二份） |
| [plans/AGENT_ROADMAP.md](plans/AGENT_ROADMAP.md) | agent 化蓝图（已加状态列） |
| [plans/MODEL_OPTIMIZATION.md](plans/MODEL_OPTIMIZATION.md) | 官模非破坏优化路线（Codex） |
| [plans/LONG_TERM.md](plans/LONG_TERM.md) | 跨仓长期方案（语音/动作/基模等） |
| [plans/UI_UPGRADE.md](plans/UI_UPGRADE.md) | 前端 UI 升级方案（下一主战场，方案阶段） |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 架构与契约 |
| [LOCAL_DEV.md](LOCAL_DEV.md) / [LOCAL_MACHINE.md](LOCAL_MACHINE.md) | 环境搭建 / 本机资产与工作区定位 |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | 未决问题台账 |
| [MVP.md](MVP.md) | 产品范围与验收目标（历史文档，状态以本总纲为准） |
| [ASSET_PIPELINE.md](ASSET_PIPELINE.md) / [MOTION_PIPELINE.md](MOTION_PIPELINE.md) | 资产 / 动作管线 |
| anime-agent-workbench（独立仓） | 沙箱训练/考试场：任务包 + 闸门 + 证据 |
| anime-agent-tts（私仓） | 声线训练与 TTS sidecar |
| anime-agent-cloth-physics（私仓） | 裙摆物理专项 |

### 代码地图（按接手任务选入口）

| 路径 | 职责 | 什么时候读 |
|---|---|---|
| `apps/avatar-runtime/runtime.gd` | 窗口/画布/骨骼/动作层/桥接收发 | 改 3D 行为、拖动、动作 |
| `apps/avatar-runtime/interaction_ui.gd` | 点击菜单、聊天浮层、输入优先级 | 改可见交互 |
| `services/agent-core/agent_core/main.py` | FastAPI/WS 路由、run_tool 过闸+审计、确认流、记忆注入、MCP 启动、主动问候、解说 | 改协议、生命周期 |
| `services/agent-core/agent_core/harness.py` | 人设提示词（ACTIVE_PROMPT_OVERRIDE）与 JSON 契约 | 改人设（先读 workbench A 包 SPEC） |
| `services/agent-core/agent_core/tools.py` | 只读六件套（Claude）+ write_file/run_command/look_at_screen（zcode） | 改工具、加新工具 |
| `services/agent-core/agent_core/permissions.py` | allow/ask/deny 引擎、path-safety、规则 | 改权限策略 |
| `services/agent-core/agent_core/agent_loop.py` | 步数上限循环、权限闸门挂点 | 改循环行为 |
| `services/agent-core/agent_core/memory_retrieval.py` / `storage.py` | 记忆检索 / facts 表与会话存储 | 改记忆 |
| `services/agent-core/agent_core/mcp_host.py` | MCP stdio 客户端 | 接真实 server |
| `services/agent-core/agent_core/proactive.py` | 免打扰+冷却纯逻辑 | Idle 触发（未开工） |
| `services/agent-core/agent_core/voice.py` / `wake_word.py` / `speech.py` | 麦克风/STT、唤醒词、TTS 客户端 | STT 加固、语音链路 |
| `scripts/test_mcp_server.py` | 最小 MCP 测试 server | MCP 联调 |
| `scripts/model-pipeline/` | Blender/MMD 资产与动作管线 | 做新动作资产 |

## 9. 快速恢复流程

| 步 | 命令或决策 | 期望结果 |
|---|---|---|
| 1 | `git status --short --branch` | 了解本地归属；不丢别人未提交的工作 |
| 2 | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local-assets.ps1` | 打印当前资产路径、大小与 SHA-256 |
| 3 | 确认 `.env` 存在（缺则复制 `.env.example` 填 GLM Key） | GLM 默认；Key 不外泄不打印 |
| 4 | 双击 `start-anime-agent.cmd`（真机验证一律走 `scripts/start-tianyi.bat`，见 VERIFICATION_SPEC） | Core 隐藏启动，唯一 Avatar 出现 |
| 5 | `curl.exe --noproxy "*" http://127.0.0.1:8765/health` | `status=ok` 与预期 Provider |
| 6 | `Set-Location services\agent-core; $env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m unittest discover -s tests -v` | 181 项全绿 |

## 10. 灾备与回滚

### 恢复命令（2026-09-07 全部实际执行验证过，非断言）

| 场景 | 恢复命令 | 已验证凭证 |
|---|---|---|
| 找回任何被删除的已跟踪文件 | `git log --oneline -- <path>` 找到删除提交 → `git show <删除提交>^:<path>` 核对内容 → `git checkout <删除提交>^ -- <path>` 恢复 | bak-phase1（12214 字节）、verify_skirt_physics.gd（20068 字节）、notes.md（273 字节）均实际取回核对 |
| 撤销 2026-09-07 整轮文档整理 | `git revert --no-commit 5324a6a^..2666fd5`（范围已核验恰为 3 个文档提交），确认后提交 | `git log 5324a6a^..2666fd5` 仅含 5324a6a/d7cdf0f/2666fd5 |

### 本地专有资产灾备台账（本地优先的既定代价：以下内容只存在本机）

| 资产 | Git 状态 | 丢失后果与恢复 |
|---|---|---|
| `work/tianyi-notes/notes.md`（天依正式笔记） | **未跟踪**（2026-09-07 出库，此前有 GitHub 备份） | 盘坏即失。种子模板 `notes.template.md` 在库；所有者应定期自行备份，或让天依重新口述重建 |
| `.env`（API key） | 永不入库 | 盘坏需所有者另行保存 key（key 泄露风险 > 丢失风险，故不入 git） |
| SQLite（`%LOCALAPPDATA%\AnimeAgent\data`） | 永不入库 | 用户数据丢失不可逆；所有者如在意应自行定期拷贝该目录 |
| 官模 GLB / Blend / 动作资产 | 本地 + 哈希契约 | 可按 `docs/ASSET_PIPELINE.md` 从授权源头重建，哈希可核 |
| tts 声线权重 | anime-agent-tts 私仓（GitHub 有备份） | 随私仓恢复 |

### 文档腐烂的三层防线（根因修复）

1. **机械层**：`scripts/check_docs_consistency.py` —— 测试数（当前状态文档 vs 实际 unittest 发现数）、环境变量（agent_core 代码 vs .env.example）、工具清单（tools.py 注册表 vs AVATAR_BRIDGE）三方自动对账；故意改坏数字必现红（注入演练已验证），接入 [TESTING.md](TESTING.md) 门禁表。
2. **行为层**：§7 白纸测试门禁 —— 每次交接/收工由零上下文实例实读验证。
3. **流程层**：铁律 8（状态变化同趟更新）+ 铁律 9（历史即灾备）。

## 已知陷阱

GLM Coding 端点必须以 `/api/coding/paas/v4` 结尾，端点错误可能返回误导性 429。PowerShell Web 命令可能继承代理返回假 502，本地健康检查必须绕过代理。Godot `_input()` 先于 GUI 控件执行，键盘快捷键必须在 LineEdit/TextEdit 持焦时立即返回。`data/` 不能全局 ignore（歌曲目录是静态包数据）。运行时 GLB 超 GitHub 100MB 限制且再分发授权未决，用本地定位与哈希而非 LFS。Blender 通用动画 GLB 导出会洗掉 MMD/VRM 材质，仅作动画容器。长马尾骨骼是 `MaWei_R_0_1`/`MaWei_L_0_1`，勿与后发骨混淆。Realtek 麦克风阵列在本机会假死输出数字零，需外部事件（Windows 麦克风测试、Fn 静音、Realtek 控制台）复位——"有设置没声音"先按驱动状态处理。`apps/avatar-runtime/assets/*` 按设计 ignore，新机器从 `docs/design/assets/luotianyi-avatar-256.jpg` 拷贝头像，否则聊天 UI 回退 ♪。

跑长任务前先做环境体检：GLM 429 限流用单 worker + 5-8 秒节流 + 指数退避；报错 1113 = 余额不足（换 key）；Windows 休眠会杀后台长任务（必要时临时 `powercfg` 调整并还原）。
