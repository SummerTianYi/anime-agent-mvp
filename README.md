# Anime Agent MVP

Codex 2026-10-14：[记忆更正与操作取消交界](docs/assessments/root-cause-repair/a4-pilot/MEMORY_CORRECTION_FOLLOWUP.md)完成定向补修：明确取消在聊天锁前撤权，记忆澄清同时交付实际取消结果；数据、否定和错误对象不撤权，已派发不冒称回滚。冻结源码下受影响250项通过，含主17项和一次独立审查12项；当前发现631个测试，未执行全量终验。旧记忆事务、跨会话/重启和双模型证据保留，零新增真实模型或外部业务调用。本交界关闭，明确记忆更正阶段具备收尾条件；通用回复核对器仍未接入，A4和底座整体不关闭。未部署、未合并main、未操作生产数据或当前Godot/Core/TTS，停在验收点。

Codex 2026-10-14：[明确更正已有记忆](docs/assessments/root-cause-repair/a4-pilot/MEMORY_CORRECTION.md)完成窄范围修复与验证：实体/属性/范围/旧版本核验，原子替换与历史保留，保存读回后真实回执；仅本会话覆盖不改全局。受影响337项及运行器38项通过，独立32项包含其中；DS/GLM各3条完成实际进程退出/重启后的事实性核验，实际84次HTTP。GLM展示降级与额外工具失败单列，原失败及独立复评保留。该阶段发现602个测试，未执行全量终验；通用回复核对器仍未接入，A4不关闭。文件/Issue/邮件/交界保留，未触碰生产库或当前Godot/Core/TTS，未部署、未合并main，停在验收点。

Codex 2026-10-14：[通用回复发布前核对试点](docs/assessments/root-cause-repair/a4-pilot/GENERAL_REPLY_CHECK.md)未通过采用门禁：新增受限提取/记录核验模块及原运行器reply入口，未接入handle_chat。人工严格DS9/11、GLM5/11，24/40次HTTP；GLM格式/空响应与超时导致正常引用/假设误拦，旧A4仍开放。程序19项和原预算/隔离38项通过，发现546项但本轮未全量执行。既有文件/Issue/邮件/交界源码保持；后续全部阻断解决后必须同一最终版本统一重验已修功能和组合，不拼接旧版本结果。未部署、未合并main，停在Manager验收。

Codex 2026-10-14：[三条基础流程交界收口](docs/assessments/root-cause-repair/a4-pilot/BASELINE_CLOSURE.md)完成所测交界修正与验证：新增10项及一次独立6项通过，受影响旧回归148项通过，其余复用邮件最终511项基线；当前发现527个测试，未重跑全量。只修改文件任务无关写调用门禁和既有任务继续分支，Provider替换保留票据、预算、成功/unknown防重放。零真实模型与外部业务调用。A4通用自由正文假完成仍为HIGH阻断，故本轮整体通过条件未满足，不能冻结基础操作内核整体通过；下一步仅处理通用操作声明与真实证据的绑定合同。未部署、未合并main，停在Manager验收。

Codex 2026-10-14：[单收件人纯文本邮件](docs/assessments/root-cause-repair/a4-pilot/EMAIL_TASK.md)完成窄范围实现与后台合成 Gmail 验收。复用既有任务/授权/账本/回执，新增邮件目标及逐字参数约束、原生消息 ID 核验和默认 MIME 去重兼容。最终同源 DS、GLM 各两例均通过；首次 DS 正文改写失败保留，修正反馈后重新验证，阶段共15/40次HTTP。最终源码Core511项隔离全量通过，独立对抗及证据复核通过。只证明发送请求被合成服务受理一次，不证明真实发信、送达、已读或A4整体关闭；未部署，停在Manager验收。

Codex 2026-10-14：[DS第二Issue样例补验](docs/assessments/root-cause-repair/a4-pilot/ISSUE_TASK_SUPPLEMENT.md)通过，冻结业务/运行器/schema/判据，一次全新合成任务完成真提案、仅标题更新一次、新读取核验和准确交付。新增6次HTTP（22–27），原40次账本累计27/40；原批次3/4和连接失败保留，本次1/1单列，Issue合成流程具备本范围收尾条件，不代表连接稳定或真实GitHub认证。未部署，停在Manager验收。

Codex 2026-10-14：[Issue仅改标题并重读核验](docs/assessments/root-cause-repair/a4-pilot/ISSUE_TASK.md)完成窄范围实现，复用文件授权/执行/交付链，新增目标与字段约束、读取代次和前后核验。后台合成MCP实测3/4：DS/GLM首轮及GLM扩样通过，DS扩样在更新提案前连接超时，零写入且不冒充完成；21/40次HTTP，未重跑失败。文件相关回归保持，A4其他开放项不关闭，未部署，停在Manager验收。

Codex 2026-10-14：[GLM第三文件样例补验](docs/assessments/root-cause-repair/a4-pilot/FILE_TASK_SUPPLEMENT.md)通过。业务冻结87ca474，仅新增显式补验预算入口；一次新初态任务的真提案、正确写入、独立读取和完整交付均通过，新增4次HTTP、累计34/38。原5/6记录不变，本次1/1单列，文件流程具备本范围收尾条件；A4其他开放项保留，不部署，停在Manager验收。

Codex 2026-10-14：[文件任务跨模型交付](docs/assessments/root-cause-repair/a4-pilot/FILE_TASK.md)完成窄范围实现，Core451及独立24+14项通过。最终同源六例真提案/正确写入均通过；DS三例、GLM两例完整读回交付，GLM末例因30次HTTP硬上限未读回，六例验收部分完成。保留跨轮状态与原授权机制，A4其他开放项不关闭；未部署，停在Manager验收。

Codex 2026-10-14：[已有待办的跨轮进度修复](docs/assessments/root-cause-repair/a4-pilot/PENDING_STATUS.md)完成，Core431隔离回归、独立13例通过。状态按会话/任务完整账本交付，保留普通聊天及现有撤权流程；文档检查入口先行独立隔离修正。本项通过仅指此窄范围，不关闭A4其他缺陷；零真实模型/外部业务调用，未部署，停在Manager验收。此前数据库影响未知记录保留。

Codex 2026-10-13：[A4 小范围控制链试验](docs/assessments/root-cause-repair/a4-pilot/REPORT.md)完成局部实现与验证，Core418项隔离回归通过，但独立对抗仍4/14失败。首轮双模型6/10，记录23次请求入口（底层重定向计数不可追溯）；不扩样、不建议集成，停在Manager验收。未部署、未操作当前Godot/Core/TTS进程；文档检查遗漏隔离，默认数据库初始化影响未核验，详见报告。以下保留历史记录。

Codex 2026-10-12 后台续作：[最新FOLLOWUP](docs/assessments/root-cause-repair/batch-01/FOLLOWUP.md)。Core399项回归与独立对抗支持局部异常回执修复，TTS43项通过。GLM假待办仍复现，本批未通过；独立分支可远程审查，未部署、未操作当前桌面。下段保留上次桌面历史。

Codex 2026-10-12：[首批底层根因修复候选](docs/assessments/root-cause-repair/batch-01/REPORT.md)修复任务/回执、连接器合同、物理路径及配套TTS日志恢复。Core395项隔离回归、TTS43项通过；正式新开Godot，独立持久测试数据下已有DS/GLM文件、Gmail、正常聊天及重启历史证据，DS声音试听获真人确认，GLM实际写入后补答超时仍交付成功回执。已恢复Deepseek配置。生产源码/原数据库未覆盖；A4自由正文仍未闭环，首批部分验收通过。

Codex 2026-10-04：本分支为 [Harness V1 candidate](docs/assessments/harness-v1/REPORT.md)，不是main正式发行；共享双模型任务执行与手动语音/600秒提醒/投入档位修复。桌面实际激活和人工反馈以报告为准。


Codex 2026-10-04：配套[非Agent系统综合评估与DS诊断](docs/NON_AGENT_SYSTEM_ASSESSMENT_2026-10-04_CODEX.md)已补齐模型/表情、动作/物理、语音、UI、启停、数据与分发状态。外观默认1.4、五版档案及现用声线校验通过；通用防穿模与跨机等效运行仍未完成。本次DS四次独立请求成功，所有者确认原窗口已能回复；未改配置或运行实现，截图发生时的精确传输原因仍待定位，不能称彻底修复。

Codex 2026-10-04：新增[Agent能力全景评测](docs/AGENT_CAPABILITY_ASSESSMENT_2026-10-04_CODEX.md)（56个真实模型场景、84轮对话、36项定向探针；原Core273项回归通过）。当前定位是受监督的短任务/陪伴型Agent，不是可靠的无人值守代办系统；授权误判、执行回执、工具正文传递、记忆召回及部分MCP连接器有待修问题。此次仅评测与报告，不是运行功能修复；下方旧考试成绩保留为历史证据。

**项目文档提交入口：[PRD — 已实现功能、目录及关键文件用途](PRD.md)**。本仓库保存可公开源码；受限模型/声线资源、私人凭据及内部过程数据不随项目文档上传，详见 [交付范围](docs/DELIVERY_STATUS.md)。

这是一个 Windows 本地优先的 3D 二次元桌面角色 MVP，产品形态是类似 VTuber 的独立桌面角色，而不是 Codex、Claude 或传统聊天窗口的复制品。当前角色由 Godot 渲染，点击角色可打开"聊天 / 互动"菜单，文字或语音输入由本地 Python Agent Core 处理。本机最新验证配置为微信 Coding Plan DS-v4-flash 文本主脑 + Qwen3.8-Flash 视觉（Token Plan Anthropic 协议）；回复中的情绪和动作元数据驱动模型表情与骨骼动作。Codex、Claude、zcode 等 Agent 只用于开发，不是生产运行时依赖。

## 当前结论

Codex 2026-10-07：[全能力根因审查候选](docs/assessments/root-cause-audit/REPORT.md)已记录当前桌面成功控制和反例。文件/邮件/Issue可实际执行，但提案、完成交付、记忆更正、连接器及语音仍有缺口；不是全能力验收通过。本轮只审计，业务/提示词未改，现场已恢复DS，停在Manager审查点。

Codex 2026-10-04：五仓分工及实装依赖已核对，**本仓是产品主仓，私有 TTS 仓是直接运行配套**；Workbench 已验收能力已并入本仓，Roadmap 是历史规划证据，Cloth Physics 是未实装实验。按所有者选择保留分仓，补齐现用声线备份；官模/动作继续只留本地。完整责任表、发现的 e5/e20 备份缺口与恢复范围见 [仓库与运行依赖地图](docs/REPOSITORY_MAP.md)。本轮不改变正在运行的天依。

Codex 2026-10-03：公共语音链路新增分片播放回执、去重补送、坏音频重合成及成功后提醒冷却；告别音频脱离临时spool，并提前加载到Godot内存。Core273项、Godot播放/退出回归、合成音频与真实CUDA声线的四场景闭环及组合进程故障通过；已由原CMD重启激活，所有者确认“倾听和语音回复都正常”并授权GitHub发布。主仓与配套 [anime-agent-tts](https://github.com/SummerTianYi/anime-agent-tts) 均以Codex标记提交，实际同步以远端提交记录为准。状态及边界见[TTS记录](docs/TTS_REPAIR_STATUS.md)。未来场景沿用公共播报入口，不各自重建TTS看护；下方较早日期的未发布/待人声验收描述保留为历史。

Codex 2026-10-02：本地最新接口配置为 DS 文本主脑 + Qwen3.8-Flash 视觉，均已实测联通。STT/TTS 缓存离线加载、待播语音恢复和启动快照竞态修复已通过回归、真实 CUDA 播放双轮及组合故障验证；按所有者选择恢复当前可证实历史并以原 CMD 正式启动。23:49 核对 Godot/Core/TTS、CUDA 声线就绪及麦克风唤醒监听正常；真实人声交互等待所有者确认。本轮未 commit/push。正式状态与边界以 [本轮 TTS 记录](docs/TTS_REPAIR_STATUS.md) 为准；下方 9 月记录为历史证据。

Codex 2026-09-13 三方整合：保持 zcode 的 DS 主脑 + StepFun 视觉与已批准人物/声线，补齐告别共同完成、Drive OAuth 刷新、Windows MCP 路径引号、窄范围唤醒误听确认及 TTS 正健康缓存修复与回归。Core 当前238项基线。公开说明见[当前源码交付](docs/DELIVERY_STATUS.md)，私人原始验收记录不入库；不是任意电脑完全等效的发布声明。

Codex 2026-09-13：TTS会话恢复已实装并经所有者验证，获准配套推送主仓与独立语音仓。原CMD等待真实预热、运行期双看护恢复、退出清理及短负缓存生效；274项离线回归两轮、复合故障/快速重开及两轮真实声线播放通过。[交付证据与边界](docs/TTS_REPAIR_STATUS.md)。本次不重启健康窗口、不操作正式数据，亦不承诺故障恢复零间隙。

Codex 2026-09-12：已接入退出专用告别第一版。正常关Godot（或原Esc退出入口）先播放已批准的4.1秒挥手、轻摇头及闭眼微笑，再退出并由原守护清理Core；重复关闭不重播，缺资源或动画停滞可降级退出。此轮未操作当前运行窗口，新代码在下次启动加载。[实装、隔离测试、恢复与限制](docs/FAREWELL_EXIT.md)。

Codex 2026-09-12：已确认的思考动作第一版接入正式菜单「思考」及 agent thinking 状态；每轮完整播放一次9.5秒后回待机，身体74轨与两条完整辫子34轨使用同一烘焙动画，不运行实时求解器，也不延迟文字/语音回复。模型仍为1.4；本地资产SHA、恢复方法、测试与下一批录制说明见 [思考动作交付](apps/avatar-runtime/mocap/thinking/README.md)。

Codex 正式表情1.0：惊讶、生气及所有者认可的折中版哭泣已接入运行时，沿用模型外观1.4，不改官模结构或材质。实现为 `emotion_presets.gd`，公开功能与限制见 [PRD](PRD.md#3-godot-角色与动画文件)；私人渲染及回退二进制档案留在本地。

| 范围 | 状态 | 说明 |
|---|---|---|
| 3D 桌面角色 | 已完成基础闭环 | 默认使用当前屏幕工作区大小的透明穿透画布；角色在固定光轴的 2× SubViewport 中渲染，再作为二维透明层拖动，避免离轴"压扁"和旧 560×760 窗口裁切；支持转身、缩放、位置保存与 `compact` 回退模式 |
| 高清截图 | 已接入（Codex，2026-09-08） | 聚焦角色且不在聊天输入框时按 F12，默认导出 2880×3480 透明 PNG 到 Godot 用户目录 `portraits`；不改变日常比例，不含连续录像，见 [`docs/plans/MODEL_OPTIMIZATION.md`](docs/plans/MODEL_OPTIMIZATION.md) |
| 当前外观与下一阶段 | 正式 1.4 五官 A2 + 保守 A-pose（Codex，2026-09-10） | 已验收实装，公开源码与版本清单在本仓库，受限资产独立本地冻结。`ANIME_AGENT_MODEL_LOOK=1.3` 回退旧外观；[档案、证据与完整恢复](model-versions/1.4/README.md)。下一阶段仍为小幅、少接触动捕。 |
| 倾听动作第一版 | 已验收冻结（Codex，2026-09-09；内部资产 FK v2） | 平顺抬臂、前倾增加4°、右手收近，肘腕与录音进退不变；新增无损动画 PNG 避免 GIF 瞳色失真。旧资产及官模 1.3 保留。[验收、复现与回退](apps/avatar-runtime/mocap/README.md)。不宣称通用无穿模。 |
| 角色菜单 | 已完成 | 点击角色打开聊天或互动菜单 |
| 退出告别 | 已接入；整合修复本地验证通过（Codex，2026-09-13） | 正常等待批准动作与本次告别语音共同结束，8秒异常兜底；资源SHA不变，详见[整合说明](docs/DELIVERY_STATUS.md) |
| 聊天界面 | 已完成并真实验证 | 底部半透明浮层，洛天依主题、气泡可滚动，支持新开/切换/删除会话与历史回载 |
| 文字聊天 | 已完成并真实验证 | 多会话；Godot → WebSocket → Core → 当前 DS 主脑 → Godot；本机最新 Qwen 配置提供独立视觉结果，隐私确认门禁保留 |
| 角色 Harness | 已完成两轮 | 洛天依身份、自我认知、结构化回复、表情与动作映射；2026-09-05 注入训练版新剧本（旧剧本保留可回退） |
| 歌曲知识 | 已完成种子库 | 20 首原创曲，本地检索后按需注入，不包含翻唱和歌词 |
| 表情与动作 | 已完成动作注册表；保守待机（Codex，2026-09-08） | 48 个形变槽；12.47 秒动捕保留躯干摇晃/转头，待机双臂恢复原先斜下外展姿态；贴腿原素材不覆盖，可关闭 `relaxed_arms` 回溯。通用防穿模未解决，第一阶段只逐条验收小幅动作，详见 [`docs/MOTION_PIPELINE.md`](docs/MOTION_PIPELINE.md) |
| 本地记忆 | 基础存储/更正/跨会话可用；完整闭环待补 | SQLite消息与facts；当前评测发现top3召回遗漏、敏感项显式记住策略及遗忘执行入口缺口，见[2026-10-04评测](docs/AGENT_CAPABILITY_ASSESSMENT_2026-10-04_CODEX.md) |
| 语音转文字 | V1 candidate：手动录音与本地简体回填 | sounddevice + faster-whisper；Realtek 驱动假死检测（数字零特征）+ 一次自动设备重置 + 可行动报错 |
| TTS 语音输出 | 本轮恢复修复已本地激活 | GPT-SoVITS 真实声线、分片合成、打断及解说；瞬态故障有限等待恢复，旧回复被打断后不迟到播放，超时明确报错并保留文字 |
| Agent 能力层 | 文件、Issue与邮件窄流程通过，A4仍开放 | 原[文件任务](docs/assessments/root-cause-repair/a4-pilot/FILE_TASK.md)5/6与[补验](docs/assessments/root-cause-repair/a4-pilot/FILE_TASK_SUPPLEMENT.md)1/1、原[Issue批次](docs/assessments/root-cause-repair/a4-pilot/ISSUE_TASK.md)3/4与[补验](docs/assessments/root-cause-repair/a4-pilot/ISSUE_TASK_SUPPLEMENT.md)1/1保持历史。[邮件最终同源四例](docs/assessments/root-cause-repair/a4-pilot/EMAIL_TASK.md)4/4，首次正文改写失败保留，邮件阶段15/40次HTTP。仅后台合成MCP流程待Manager验收，不代表真实GitHub或Gmail集成、送达或连接稳定性。 |
| 一键启动 | 已修复；真实启动/退出及最终两轮对抗通过 | 根目录 `start-anime-agent.cmd`，Core 隐藏运行；关Godot自动清理对应会话，重复调用不多开；[证据与边界](docs/STARTUP_REPAIR_STATUS.md) |
| Windows 登录自启、守护 | Core已验收；TTS隔离故障验证及正式原CMD激活/重复启动通过 | 当前会话已接入双看护，详情见[修复记录](docs/TTS_REPAIR_STATUS.md)。不承诺冷恢复零间隙；登录任务、音频隔离与长期观察仍属其他工作 |
| Idle 触发 | V1 candidate：连续600秒、同段一次 | 键鼠空闲本地检测 + 台词模板库，待机零 GLM 调用；键鼠控制按蓝图缓行需先设考试；Spark 暂缓 |
| 前端 UI 升级 | 已立项（方案阶段） | 当前聊天浮层与能力不匹配；方案见 [`docs/plans/UI_UPGRADE.md`](docs/plans/UI_UPGRADE.md)，为下一主战场 |

## 零上下文接手

新 Agent 不应根据旧聊天记录猜测项目状态。**先读 [`docs/HANDOFF.md`](docs/HANDOFF.md)（接手总纲）与 [`docs/AGENT_REPORT_2026-09-07.md`](docs/AGENT_REPORT_2026-09-07.md)（能力/训练全景快照）**，再读 [`AGENTS.md`](AGENTS.md) 与 [`docs/CONTRIBUTIONS.md`](docs/CONTRIBUTIONS.md)（归属声明），然后按任务查阅 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)、[`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md)、[`docs/ASSET_PIPELINE.md`](docs/ASSET_PIPELINE.md)、[`docs/MOTION_PIPELINE.md`](docs/MOTION_PIPELINE.md)、[`docs/plans/README.md`](docs/plans/README.md)（项目长远方案手册：所有 agent 的模型、动捕/物理、Agent/记忆、UI、声线与跨仓规划统一入口；旧方案只作历史档案）、[`model-versions/README.md`](model-versions/README.md)、[`docs/TESTING.md`](docs/TESTING.md)、[`docs/VERIFICATION_SPEC.md`](docs/VERIFICATION_SPEC.md) 与 [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md)。当前机器的受限模型、工具和兄弟工作区位置集中记录在 [`docs/LOCAL_MACHINE.md`](docs/LOCAL_MACHINE.md)，其中不包含密钥、Cookie 或用户对话。

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
