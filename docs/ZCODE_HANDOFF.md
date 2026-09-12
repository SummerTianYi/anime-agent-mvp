# zcode 侧全量工作盘点报告（交接 Codex 整合用）

生成：2026-09-13，zcode（ZCode CLI）。作者授权用途：与 Codex 侧工作合并后做最终交付，交付验收 = **完整脱机测试**——打包为一个文件夹，在不依赖本机环境的情况下达到与本机相同的效果。

## 0. 阅读须知（口径声明）

1. **本文只写最终方案**。演进过程中被替换的方案（GLM 主脑时期、旧会话下拉、首版 effort 工具门控等）一律不作为整合对象，只保留仍在生效的教训（§9）。
2. **按脱机打包标准盘点**：§7 列出全部本机依赖与外置项，§8 给出打包清单与首启自检动线。整合者应把"哪一项在本机有、包里没有就会失效"当作核对表逐项过。
3. **归属边界**：本文覆盖仓库内全部**非 Codex** 侧工作（zcode 批次 + 其前身 Claude 批次的根基功能，二者均为所有者在 Codex 之外的 CLI 会话链上完成，以下合称"zcode 侧"）。Codex 侧工作以 `docs/CONTRIBUTIONS.md` 的 Codex 节和 git log 的 `(Codex)` 标记为准，**本文不代述、不冒领**。三方分工总台账在 `docs/CONTRIBUTIONS.md`，接手总纲在 `docs/HANDOFF.md`，训练考试史在 `docs/EXAM_LEDGER.md`，唯一有效规划手册在 `docs/plans/README.md`。
4. zcode 侧全部工作已提交并推送至 `SummerTianYi/anime-agent-mvp` main（盘点时 HEAD `834a9a3`），每条 commit 均带 `(zcode)` 标记，可按 `git log --grep="zcode)"` 审计。

## 1. 项目最终形态一页纸

- **三进程架构**：Godot 4.7.2 桌面 Avatar（透明穿透画布 + 底部聊天浮层）↔ agent-core（Python 3.12 / FastAPI / WebSocket `ws://127.0.0.1:8765/ws`）↔ TTS sidecar（GPT-SoVITS，端口 8770，本体在独立私仓 `tianyi-tts`，不在本仓库）。
- **数据**：SQLite 单库 `%LOCALAPPDATA%/AnimeAgent/data/anime-agent.sqlite3`（sessions / messages / events / facts / settings 五表，迁移式 schema）。
- **一键启动**：`start-anime-agent.cmd` → `scripts/start-mvp.ps1`（拉 Core + Avatar + `core_watchdog.ps1` 守护 + TTS 钩子 tts_autostart / watch-tts-session）。
- **能力面（最终态）**：文本主脑 = 微信 Coding Plan DS-v4-flash（已通过 19 项认证）；视觉 = StepFun step-3.7-flash（Anthropic 协议适配器）；本地工具 9 个 + 真实 MCP 5 服务（93+ 工具）；三档思考强度；唤醒词"嗨天依"全语音链；三重守护（Core watchdog / TTS 双看护 / STT 自愈）。
- **测试基线**：Core 单测约 223 项 + 14 项启动逻辑回归（Codex 侧）+ 19 项模型认证卷 + Godot 守卫脚本族（verify_*.gd）+ CI（GitHub Actions，含 docs-guard 文档一致性守卫）。

## 2. 供应商槽位（最终态）

`services/agent-core/agent_core/main.py` 的 provider 层三槽位，`.env` 的 `LLM_PROVIDER` 切换；换槽杀 Core 由守护拉活即生效。

| 槽位 | 角色 | 端点/协议 | 模型 | 注意 |
|---|---|---|---|---|
| `deepseek` | **文本主脑（现役）** | `https://chatapi.weixin.qq.com/openai/v1/chat/completions`（OpenAI 兼容） | `Deepseek-v4-flash` | 工具调用 ✓ 思考型（reasoning_content 单独字段）**无视觉**；token 所有者亲供，**replace 会作废其 Mac 上的旧 token，勿动**；额度 1B tokens + 5h/7d/30d 请求窗口 |
| `stepfun` | **视觉专用** | `https://api.stepfun.com/step_plan`（**Anthropic /v1/messages 协议**——标准 /v1 对此 key 返回 quota_exceeded） | `step-3.7-flash` | 多模态 ✓ 思考型，弱于主脑；key 同时配在 `STEPFUN_API_KEY` 与 `ANIME_AGENT_VISION_KEY`；**微信两模型均无视觉，视觉必须走阶跃（所有者定的分工）** |
| `glm` | 备用 | open.bigmodel.cn coding 端点（OpenAI 兼容） | `glm-5.3-flash` | 2026-09-08 起额度耗尽（429"套餐已到期"，body 中 1113 = 余额尽）；key 保留在 `GLM_*`，换回即恢复主脑+视觉旧链 |

- **`AnthropicCompatibleProvider`**（zcode，`main.py` + `tests/test_anthropic_provider.py`）：/v1/messages 方言双向翻译——system 合并、tool_use/tool_result 与 schema 翻译、思考块跳过解析、对 agent 循环暴露 OpenAI 形状 raw turn、端点拒 tools 时降级、热重载平价。
- **`look_at_screen` 双方言视觉**（`tools.py` + `tests/test_vision_request.py`）：`ANIME_AGENT_VISION_PROTOCOL=anthropic` 构造 base64 图像块（StepFun），`openai` 保留旧 image_url 形状。
- **备选切换**：`DEEPSEEK_MODEL` 改 `GLM-5.2` 可切同槽备选模型。

## 3. Agent 能力与训练（最终态）

### 3.1 工具面（本地 9 + MCP 5）

本地：`get_time`、`read_file`、`list_dir`、`take_screenshot`、`get_active_window`、`get_clipboard`（只读六件套）+ `write_file`（原子写：临时文件 + os.replace；独立写白名单 `ANIME_AGENT_WRITE_ROOTS`；UTF-8 无 BOM；256KB 上限）+ `run_command`（命令白名单 + 禁管道符 + 30s 超时）+ `look_at_screen`（ask-privacy 隐私确认档，per-tool 90s 超时）。
MCP（`mcp_host.py` stdio JSON-RPC 宿主）：Playwright 浏览器（Chrome 通道 isolated 档案）、官方 github-mcp-server（gh token）、Tavily 搜索、Gmail（19 工具，OAuth 走本地代理）、Google Drive（readonly）。

### 3.2 权限引擎（`permissions.py`）

deny-by-default + 有序规则三档（allow/ask/deny）+ `path-safety` / `malformed-request` 两道不可放行硬拒 + rule_id 归因；写入工具默认 ask，越界写在确认前直接拒绝；一次性确认标记**绑定工具名**（防跨工具泄漏，TDD 修复）；确认流挂起→用户确认→执行→角色化汇报；`agent.tool` / `permission.decision` 审计事件全程落库。

### 3.3 记忆系统（最终态）

`facts` 表（迁移式）+ 敏感度分级落库（偏好类自动确认、其余 pending 待确认 UI）+ 明确 remember 晋升词表 + **事实取代机制**（bigram-Dice≥0.55 判冲突 → superseded 永不召回）+ 非敏感 pending facts 注入聊天上下文（带敏感过滤）+ 中文词法检索（字符 n-gram + 平滑 IDF + 属性词扩展）+ 批量回忆提示词特化。

### 3.4 主动行为与待机

`proactive.py` IdlePolicy（阈值 20min / 免打扰时段 / 冷却期，纯逻辑可离线单测）+ `GetLastInputInfo` 本地轮询 + 台词模板库——**待机全程零 LLM 调用（零额度待机，所有者原则）**；启动问候（avatar-connect 触发）。

### 3.5 唤醒与语音输入链（最终态）

sherpa-onnx 中文 KWS"嗨天依"两阶段唤醒 + whisper 转写同音容错（天忆/便宜等同音池，打招呼可选）+ 唤醒路径软件 AGC（Realtek 长流 30-100x 衰减修复）+ STT 数字零楔死自愈（噪声底特征区分"没说话"vs"驱动假死"，一次自动设备重置 + 90s 重开看门狗）；barge-in 打断（她说话时唤醒/打字均可切）。

### 3.6 思考强度三档（effort dial，最终态）

**档位 = 投入度而非功能开关**（所有者定调后推翻首版门控）：三档均为完整 agent——全注册表 + 全部 MCP 常驻，权限引擎永不因档位降级；档位只调：步数阶梯 chill/standard/deep = **1/3/5** + 三段按档行为提示（`EFFORT_PROMPT_NOTES` 经 extra_parts 注入 system）+ 答案形态契约（chill≤2 句短答无列表 / standard 一段扎实正文 / deep 结构化交付物带要点）。人设剧本一字不动。档名（所有者钦定）：碎碎念 / 帮帮忙 / 大展身手。实现：`main.py` `effective_tools_for_effort` 纯函数 + `tests/test_effort.py`。

### 3.7 模型认证制度（QA-03，换模型必跑）

- 套件：`scripts/model_cert.py`（驱动+判分）+ `model_cert_battery.json`（E 系 9 项）+ `model_cert_adversarial.json`（独立零上下文实例出的 10 道对抗变体，三类注入陷阱：中段笔记投毒 / 伪造更新 / 社工话术）。
- 判分：四元组自动判（句数/列表/工具序列/预协商），按 request_id 关联回复防串轮；统计口径 ≥ 轮数-1。
- **制度：换任何文本模型必须同卷重跑达标**（手册 QA-03 行）。DS-v4-flash 2026-09-12 首跑 19/19 全绿（runs/cert-20260912-*）。
- **弱模型四类失败模式及最终态修法**（写在 `harness.py` 人设与 `tools.py` 描述里的契约，整合时不得删改）：
  1. 人设能力陈述句被字面执行 → 诚实红线必须点名具体工具名 + "能力问句直接调用现场演示，不口头回答能不能"；
  2. 多工具选型漂移 → `look_at_screen` 描述显式认领屏幕视觉职责，工具指引点名；
  3. ask 工具文本预征询（不调用）→ 指引写明"ask 档工具直接调用，系统自动替你问"；`write_file` 描述锚定"追加笔记"标准用例；
  4. 档位契约松动 → 人设【表达方式】"一到三句话"带显式 deep 档例外；standard 档提示带 write-first 直调指令。
- 判分措辞口径：省略号不算句界、①②③圈数字是合法列表、"不对劲/很大的坑"是合法示警措辞。

### 3.8 考试体系（EXAM_LEDGER 制度）

T0/T1/T2/T3/MCP/D 各期真机实考 + T2+ 进阶（矛盾记忆更新 + 16 轮长对话压压测）+ T-BROWSER/T-GITHUB/T-SEARCH/T-GMAIL/T-DRIVE + 毒邮件注入双考 + DS 认证；判分行为证据制（快照对账 + 审计对账，非关键词匹配）。全史 `docs/EXAM_LEDGER.md`。

## 4. 语音链（最终态）

- E 期基座（Claude 批次）：`speech.py` sidecar 客户端、流式多分片、话语生命周期、打断/顶替策略、真实时长 speaking。
- TTS sidecar 运行期生命周期、双看护、会话闭环（**Codex 侧 2026-09-12→13 交付，以 `docs/TTS_REPAIR_STATUS.md` 为准**，zcode 不代述）。
- zcode 侧语音联动（全部已推送）：
  - **告别链**：正常关窗/Esc → `farewell_exit.gd`（Codex 资产）closing → runtime 广播 `avatar.exiting` → Core 在 8s 兜底窗口内合成轮换告别语 → **closing 门禁放行 `avatar.speak` 帧**（`runtime.gd` `_handle_core_event`，commit 834a9a3——此前告别只有动作没声音的根因）→ 播毕 `speech.finished` → `_finish_exit("farewell_speech_done")` 提交退出。
  - **告别预合成**：三句告别语在 avatar-connect 时预热缓存（env 开关 `ANIME_AGENT_FAREWELL_PRECACHE`），退出即时播放不再跟合成赛跑（a0089de）。
  - **思考补白行**：长思考（>5s 且非 chill）播轮换补白，回复语音就绪后顶替（0ffaa4e）。
  - **GC 强引用制度**：`asyncio.create_task` 只持弱引用，sleep 中任务可被 GC 静默吞掉（症状：文字全出、语音播一句就断）——main.py 全部派发点收编 `_spawn()` 强引用注册表，**以后加任何后台任务必须走 `_spawn`，禁止裸 create_task**（b392d6d/95b578c）。
- ⚠️ **`taskkill //IM python.exe` 会连坐 TTS sidecar（它也是 python）**——杀完须 `cmd //c start "" //min ...\tianyi-tts\scripts\tts_autostart.bat` 重拉（bat 自带 8770 端口守卫可安全重复执行）。

## 5. 前端 UI（最终态）

全部在 `apps/avatar-runtime/`（Godot，GDScript），基础浮层为 Claude 批次所建（洛天依主题、气泡流、输入优先级、会话删除确认框），zcode 侧最终态：

| 模块 | 状态 | 关键文件 |
|---|---|---|
| 回忆手账（唯一历史 UI） | 旧会话下拉已整体删除（3600b4d）；头部"回忆"按钮 → 手账列表页：日期四组折叠（今天/昨天/七天内/更早）、UTC→本地时区换算（082c373，凌晨会话不再错归昨天）、标题即时搜索、敲碗贴纸空态、天依蓝滚动条全历史可达、点卡片切会话 | `interaction_ui.gd`、`verify_session_ui.gd` |
| 壁纸皮肤 | 聊天面板=三叶草图（40% 透明度保气泡可读）、手账页=星夜图（暗化叠层）；cover-fit 保人脸在框内；素材本地不入库（授权策略），缺图回退纯色 | `interaction_ui.gd`（d61c5ac） |
| 思考强度旋钮 | composer"思考·档位"按钮 → ChatGPT 式弹窗；自绘粗轨道滑杆（`effort_slider.gd`：#66CCFF 已选段、三官方表情贴纸坐档：敲碗/吃瓜/宅），档名碎碎念/帮帮忙/大展身手 | `interaction_ui.gd`、`effort_slider.gd`、`verify_effort_ui.gd` |
| 工具活动卡 | 每回合聚合 `agent.tool` 事件：来源徽标（本地/浏览器/GitHub/搜索/邮箱/网盘，解析 `mcp__<server>__<tool>` 长名）、✓/✗、调用计数；新回合/切会话自动开新卡 | `interaction_ui.gd`、`verify_tool_activity.gd` |
| 头像 | 聊天/空态复用官方头像裁切图 | `docs/design/assets/luotianyi-avatar-*.jpg`（本地） |

守卫脚本（真机跑 Godot --headless 断言）：`verify_session_ui.gd`（手账开页/分组/搜索/关闭）、`verify_effort_ui.gd`（GODOT_EFFORT_UI_OK）、`verify_tool_activity.gd`（GODOT_TOOL_ACTIVITY_OK）、`verify_text_input.gd` 等既有族全部保留。

## 6. 守护与稳定性（最终态）

- **`scripts/core_watchdog.ps1`**（zcode，KI-019）：PortAudio 原生崩溃（libportaudio64bit.dll 0xC0000005）杀 Core 零堆栈 → 天依在桌面即保 Core 在线：双确认健康判定、90s 预热防重复拉起、认领任何 agent_core python、外部端口占用不碰、退出码验尸（0xC0000005 标注 PortAudio）、天依退场守护即退场；`start-mvp.ps1` 自动拉起。
- **TTS 钩子常驻 start-mvp**：09-11 Codex 启动重写曾丢失 TTS 钩子致每次重启都哑巴，zcode 折回（tts_autostart + watch-tts-session），此后 Codex 生命周期重写接管（见其文档）。
- 启动/退出生命周期、锁、代际守护：Codex 侧交付（`docs/STARTUP_REPAIR_STATUS.md`）。
- 稳定性方案 R1-R5：已并入 `docs/plans/README.md` §8（OPS-01~09）。
- CI：`.github/workflows/ci.yml`——Core 测试 extra（httpx2/numpy 分离）、docs-guard 文档一致性守卫（测试数/env 变量/工具清单三方对账）。

## 7. .env 与本机依赖（脱机打包核心）

### 7.1 `.env` 变量面（仓库有 `.env.example` 全量注释版；真实 `.env` 不入库）

| 类 | 变量（最终态） |
|---|---|
| 文本主脑 | `LLM_PROVIDER=deepseek`、`DEEPSEEK_API_KEY`（微信亲供 token，勿 replace）、`DEEPSEEK_MODEL=Deepseek-v4-flash`、`DEEPSEEK_BASE_URL` |
| 视觉 | `STEPFUN_API_KEY`、`ANIME_AGENT_VISION_KEY`（同 key 两处）、`ANIME_AGENT_VISION_MODEL=step-3.7-flash`、`ANIME_AGENT_VISION_PROTOCOL=anthropic` |
| GLM 备用 | `GLM_API_KEY`、`GLM_BASE_URL`、`GLM_MODEL` |
| 唤醒/语音 | `ANIME_AGENT_WAKE_WORD`、sherpa-onnx 模型路径（`agent_core/data/wake_tianyi.txt` 词条）、TTS sidecar 地址（8770） |
| 权限 | `ANIME_AGENT_TOOLS_ROOTS`、`ANIME_AGENT_WRITE_ROOTS`、`ANIME_AGENT_ALLOWED_COMMANDS` |
| MCP | browser/github/tavily/gmail/drive 各条目（命令、token） |
| 主动行为 | idle 阈值（20min）、免打扰时段 |
| 告别预合成 | `ANIME_AGENT_FAREWELL_PRECACHE` |
| 模型外观 | `MODEL_LOOK_*` 回退开关透传 |

### 7.2 本机依赖清单（包外必须准备/声明）

| 依赖 | 位置 | 缺失后果 |
|---|---|---|
| Python 3.12 venv | `services/agent-core/.venv`（系统 Python 缺 fastapi，**必须用 venv 启动**） | Core 起不来 |
| Godot 4.7.2 | 本机安装 | Avatar 起不来 |
| 官模 GLB/Blend + 1.4 冻结档 | 本地 `model-archive/`、`motion-output/`（**不入库**，哈希契约见 `model-versions/` 与 `scripts/check-local-assets.ps1`） | Avatar 无模型 |
| tianyi-tts 私仓 | 相邻工作区（GPT-SoVITS + 声线权重，anime-agent-tts 私有仓） | 无语音（不崩，TTS 优雅降级） |
| sherpa-onnx 中文 KWS 模型 | `.gitignore` 内模型目录 | 无唤醒（打字链不受影响） |
| MCP 二进制 | `tools/` 下本地二进制（github-mcp-server 等，gitignore；`tools/*.cmd` 启动器已入库） | 对应 MCP 缺席（工具面降级，不崩） |
| Gmail OAuth | `gcp-oauth.keys.json` + `~/.gmail-mcp` 令牌 | Gmail MCP 缺席 |
| 本地代理 7897 | 系统代理 | Gmail/Drive MCP 拉不起来（其余不需要） |
| SQLite 数据库 | `%LOCALAPPDATA%/AnimeAgent/data/` | 首启自动建库 |

## 8. 脱机打包清单（按交付标准）

**必须进包**：本仓库全部 git 跟踪文件（`git ls-files` 405 项即打包基线）+ 官模与冻结资产（按 `model-versions/1.4/README.md` 哈希核对）+ tianyi-tts 私仓 + sherpa-onnx 模型 + 本地素材（effort 三贴纸 `assets/effort/*.png`、壁纸两图、头像裁切图——**均为本地素材不入库，打包时从本机 `%APPDATA%/Godot/app_userdata/Luo Tianyi Desktop Avatar MVP/` 与仓库本地目录收集，缺了走既有回退路径**）。

**包外准备**：填好的 `.env`（§7.1）、Gmail OAuth、代理可用性、GitHub token（github MCP）。

**首启自检动线**：① `pytest`（services/agent-core，venv 内全绿）→ ② `start-anime-agent.cmd` 冒烟（Core 8765 + Avatar 窗口 + 8770 心跳）→ ③ 打字链一问一答（DS 主脑）→ ④ 手账页开合 → ⑤ effort 弹窗三档 → ⑥ 告别关窗有语音 → ⑦ `scripts/model_cert.py`（需真实 key，可后置）。CI 于 GitHub Actions 上独立验证测试面。

**工作区现存未跟踪物**（打包时排除，勿删）：`apps/avatar-runtime/godot_*.log`（zcode 测试日志）、`runs/`（认证测试证据）、`docs/DATA_RECOVERY_STATUS.md` 与 lookdev/mocap 下 `.uid` 及 Codex 在制文件（Codex 侧自管）。

## 9. 已知坑（整合后仍然有效的教训）

1. **GLM 端点**：并发即 429（单 worker + 8s pacing）；429 body 中 1113 = 余额尽；"Remote end closed"为瞬时抖动可重试。
2. **机器睡眠杀长跑**：长测试/后台任务前先禁 standby。
3. **CRLF/manifest**：全局 autocrlf 会让哈希冻结清单失配；仓库已带 `.gitattributes`（`* text=auto eol=lf`），新增冻结文件须 `python -m acceptance.gates.g0_freeze --update` 同法重生成（workbench 仓）。
4. **docs 计数守卫**：改完测试必须同步四处状态文档并 `git add` 全部再推，docs-guard 会抓漂移；守卫自身需 `PYTHONUTF8=1`（cp1252 崩溃会吞警报）。
5. **本地工具要绝对路径**：DS 不会自己解析盘符，相对路径 list_dir 直接失败。
6. **`taskkill //IM python.exe` 连坐 TTS**（§4）。
7. **后台任务必须走 `_spawn` 强引用注册表**（§4，禁止裸 create_task）。
8. **弱模型措辞契约**（§3.7 四类失败模式，人设/工具描述措辞即契约，改动须重跑认证卷）。
9. **屏幕问法**：问屏幕内容用"描述一下你的屏幕上有什么"并依赖人设点名的 look_at_screen；"屏幕上开着什么"会把模型引向窗口枚举。
10. **Windows shell 纪律**（AGENTS 规则 11）：Git Bash only；反斜杠密集文件用文件写入工具。

## 10. zcode 侧触碰文件全清单（审计口径：`git log --grep="zcode)" --name-only` 去重汇总）

**services/agent-core/agent_core/**：`main.py`（effort 映射、MCP 路由与确认、proactive 钩子、_spawn 注册表、告别预合成）、`harness.py`（新剧本接入 + 弱模型契约）、`tools.py`（write_file/run_command/look_at_screen/双方言/per-tool 超时/描述锚定）、`permissions.py`、`agent_loop.py`（permission_gate）、`storage.py`（facts 表）、`memory_retrieval.py`、`mcp_host.py`、`proactive.py`、`voice.py`、`wake_word.py`。
**services/agent-core/tests/**：`test_permissions` `test_agent_gate` `test_memory_retrieval` `test_memory_promotion` `test_storage` `test_tools` `test_write_file` `test_proactive` `test_voice_selfheal` `test_wake_phrase` `test_wake_agc` `test_vision_request` `test_anthropic_provider` `test_effort` `test_speech_ws` `test_channel_exclusivity`（.py）。
**scripts/**：`model_cert.py`、`model_cert_battery.json`、`model_cert_adversarial.json`、`start-mvp.ps1`、`core_watchdog.ps1`、`check_docs_consistency.py`、`test_mcp_server.py`。
**apps/avatar-runtime/**：`interaction_ui.gd`、`runtime.gd`、`effort_slider.gd`、`verify_session_ui.gd`、`verify_effort_ui.gd`、`verify_tool_activity.gd`、`capture_tool_activity.gd`；（`mocap/` 与 `motion_registry.json` 的部分提交为并行期夹带的 Codex 在制资产，归属以其声明为准）。
**tools/**：`gdrive-mcp.cmd`、`gmail-mcp.cmd`、`README.md`、`LICENSE`。
**docs/**：`HANDOFF.md`、`EXAM_LEDGER.md`、`TEST_REPORT_2026-09-06.md`、`AGENT_REPORT_2026-09-07.md`、`TTS_HANDOFF.md`、`CONTRIBUTIONS.md`（zcode 行）、`TESTING.md`、`VERIFICATION_SPEC.md`、`AVATAR_BRIDGE.md`、`ARCHITECTURE.md`、`KNOWN_ISSUES.md`、`LOCAL_MACHINE.md`、`LOCAL_DEV.md`、`MVP.md`、`MOTION_PIPELINE.md`（状态行）、`plans/README.md`（§8 并入 + QA-03 + UI-U2a）、`plans/UI_UPGRADE.md`、`plans/UI_REFERENCES.md`、`plans/LONG_TERM.md`、`plans/AGENT_ROADMAP.md`（→archive）。
**根/**：`README.md`、`AGENTS.md`、`CLAUDE.md`、`.env.example`、`.gitignore`、`.github/workflows/ci.yml`、`work/tianyi-notes/notes.template.md`。
**zcode 前身 Claude 批次（根基功能，已并入本仓，声明见 CONTRIBUTIONS.md）**：Core 多会话系统（storage/main 协议）、底部浮层聊天 UI、会话删除、会话标题、Agent 工具循环 A 期（六只读工具 + agent_loop）、TTS E 期基座（speech.py）、唤醒词系统初版、倾听动作样片、聊天形态设计文档（docs/design/*）。

## 11. 配套仓库（均在 zcode 会话链上建成）

| 仓库 | 本地 | 状态 |
|---|---|---|
| `SummerTianYi/anime-agent-workbench` | `C:\Users\26052\anime-agent-workbench` | zcode 建的**前置训练仓**：任务包 C（权限引擎）/E（工具注册表）/B（记忆检索）/A（人设新剧本）+ 全量 DoD 评测（解析率 100%/认知 96.8%/双评审 91.0）+ 考试脚本（exam_t0/snapshot/tianyi_remote）。成果已并入主仓；本仓保留作证据仓（HEAD 3671605）。**评测入口**：`WORKBENCH_LLM_*` env → `python acceptance/evals/run_live.py`。 |
| `SummerTianYi/anime-agent-roadmap`（私有） | `C:\Users\26052\anime-agent-roadmap` | zcode 代建的稳定性方案库（R1-R5）；已全部并入主仓 `docs/plans/README.md` §8，**降级为证据仓，不再新增规划**。 |

## 12. 交接现状与未决事项

- **已推送 HEAD**：`834a9a3`（含盘点前收尾的告别语音门禁修复）；CI 由远端跑。
- **工作区 Codex 未提交条目**（不归 zcode，留 Codex 自理）：README 表情 1.0 文档行、CONTRIBUTIONS 三个 Codex 节（数据恢复/TTS 闭环/压力测试）、`docs/DATA_RECOVERY_STATUS.md`、lookdev/mocap `.uid` 文件。
- **数据事故现状**（2026-09-13，Codex 恢复）：会话/消息/事件已部分恢复；**旧偏好类 facts 全损**（仅存 13 条认证期 pending）、settings 清零；恢复档案与损坏现场在 `../tts-repair-Rq9q4a/` 与 `data/recovery-preimage-*`，**勿清理**。记忆系统功能完好，损失是数据性的。
- **owner-gated 遗留**（手册有行）：记忆审阅 UI（KI-016）、autostart、键鼠控制（需新考试）、Spark、GLM key 续费。
- **整合提示**：zcode 侧与 Codex 侧在 `runtime.gd`、`start-mvp.ps1`、`main.py` 三个文件上有历史并行；以 git 历史行为证据逐块核对，冲突时优先保"最终态行为"（§2-§6 所述），归属争议以 CONTRIBUTIONS.md 裁决。
