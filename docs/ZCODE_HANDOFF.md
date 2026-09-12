# zcode 侧全量工作盘点报告（交接 Codex 整合用）v2

生成：2026-09-13，zcode（ZCode CLI）。作者授权用途：与 Codex 侧工作合并后做最终交付，交付验收 = **完整脱机测试**——打包为一个文件夹，在不依赖本机环境的情况下达到与本机相同的效果。v2 修订：全部硬断言（文件数/变量名/路径/命令/测试基线）已对照本机实况逐项核实，并新增 §8 测试标准与 §13 交付风险。

## 0. 阅读须知（口径声明）

1. **本文只写最终方案**。被替换的方案（GLM 主脑时期、旧会话下拉、首版 effort 工具门控等）一律不作为整合对象，只保留仍生效的教训（§10）。
2. **按脱机打包标准盘点**：§7 本机依赖逐项核实过实际路径，§8 测试标准卡死到命令与通过条件，§9 打包清单，§13 交付风险清单。
3. **归属边界**：本文覆盖仓库内全部**非 Codex** 侧工作（zcode 批次 + 其前身 Claude 批次，二者均为所有者在 Codex 之外的 CLI 会话链上完成，合称"zcode 侧"）。Codex 侧以 `docs/CONTRIBUTIONS.md` Codex 节和 `(Codex)` 提交标记为准，本文不代述、不冒领。
4. zcode 侧全部工作已推送 `SummerTianYi/anime-agent-mvp` main（盘点时 HEAD `8f6b996`），逐条带 `(zcode)` 标记，`git log --grep="zcode)"` 可审计。

## 1. 项目最终形态一页纸

- **三进程架构**：Godot 4.7.2 桌面 Avatar（透明穿透画布 + 底部聊天浮层）↔ agent-core（Python 3.12 / FastAPI / WebSocket `ws://127.0.0.1:8765/ws`）↔ TTS sidecar（GPT-SoVITS，端口 8770，本体在独立私仓 `tianyi-tts`，不在本仓库）。
- **数据**：SQLite 单库，默认 `%LOCALAPPDATA%/AnimeAgent/data/anime-agent.sqlite3`（`storage.py: default_data_dir()`：`ANIME_AGENT_DATA_DIR` 为空时取 `%LOCALAPPDATA%/AnimeAgent/data`），sessions / messages / events / facts / settings 五表，迁移式 schema。
- **一键启动**：`start-anime-agent.cmd` → `scripts/start-mvp.ps1`（拉 Core + Avatar + `core_watchdog.ps1` + TTS 钩子）。
- **能力面（最终态）**：文本主脑 = 微信 Coding Plan DS-v4-flash（19 项认证通过）；视觉 = StepFun step-3.7-flash（Anthropic 协议适配器）；本地工具 9 个 + 真实 MCP 5 服务；三档思考强度；唤醒词"嗨天依"全语音链；三重守护（Core watchdog / TTS 双看护 / STT 自愈）。
- **可选组件**：`apps/desktop`（Tauri 壳，TypeScript/Vite）——仓库内保留、CI 会构建它，但当前产品路线以 Godot Avatar 为准（选型证据见 `docs/plans/UI_REFERENCES.md`）。整合打包时以 Godot 路线为准，Tauri 壳可不入包。
- **测试基线**：Core 单测 **223 项**（unittest）+ 14 项 Windows 启动生命周期 + 13 项 TTS 生命周期逻辑（CI 全跑）+ 19 项模型认证卷（需 key）+ Godot 守卫脚本族 + 文档一致性守卫。

## 2. 供应商槽位（最终态）

`services/agent-core/agent_core/main.py` provider 层三槽位，`.env` 的 `LLM_PROVIDER` 切换；换槽杀 Core 由守护拉活即生效。

| 槽位 | 角色 | 端点（`.env` 实际值） | 模型 | 注意 |
|---|---|---|---|---|
| `deepseek` | **文本主脑（现役）** | `https://chatapi.weixin.qq.com/openai/v1`（OpenAI 兼容；`.env.example` 里 `DEEPSEEK_BASE_URL` 的占位是 api.deepseek.com，**生产 .env 已改微信端点**） | `Deepseek-v4-flash` | 工具调用 ✓ 思考型（reasoning_content 单独字段）**无视觉**；token 所有者亲供，**replace 会作废其 Mac 上的旧 token，勿动**；额度 1B tokens + 5h/7d/30d 请求窗口 |
| `stepfun` | **视觉专用** | `https://api.stepfun.com/step_plan`（**Anthropic /v1/messages 协议**——标准 /v1 对此 key 返回 quota_exceeded） | `step-3.7-flash` | 多模态 ✓ 思考型；key 同时配在 `STEPFUN_API_KEY` 与 `ANIME_AGENT_VISION_KEY`；**微信两模型均无视觉，视觉必须走阶跃（所有者定的分工）** |
| `glm` | 备用 | `https://open.bigmodel.cn/api/coding/paas/v4` | `glm-5.3-flash` | 2026-09-08 起额度耗尽（429"套餐已到期"，body 1113 = 余额尽）；key 保留在 `GLM_*`，换回即恢复主脑+视觉旧链 |

- **`AnthropicCompatibleProvider`**（zcode，`main.py` + `tests/test_anthropic_provider.py`）：/v1/messages 方言双向翻译——system 合并、tool_use/tool_result 与 schema 翻译、思考块跳过解析、对 agent 循环暴露 OpenAI 形状 raw turn、端点拒 tools 时降级、热重载平价（401/403/429 触发 `.env` 热重载重试一次）。
- **`look_at_screen` 双方言视觉**（`tools.py` + `tests/test_vision_request.py`）：`ANIME_AGENT_VISION_PROTOCOL=anthropic` 构造 base64 图像块，`openai` 保留 image_url 形状；未配置视觉时优雅降级为"已知边界"陈述。

## 3. Agent 能力与训练（最终态）

### 3.1 工具面（本地 9 + MCP 5）

本地：`get_time`、`read_file`、`list_dir`、`take_screenshot`、`get_active_window`、`get_clipboard`（只读六件套）+ `write_file`（原子写 os.replace、独立写白名单 `ANIME_AGENT_WRITE_ROOTS`、UTF-8 无 BOM、256KB 上限、append 自动补换行）+ `run_command`（白名单 `ANIME_AGENT_ALLOWED_COMMANDS` + 禁 shell 元字符 + 30s 超时）+ `look_at_screen`（ask-privacy 隐私确认档，per-tool 90s 超时，其余工具 15s）。
MCP（`mcp_host.py` stdio JSON-RPC 宿主，`ANIME_AGENT_MCP_SERVERS` 配置）：Playwright 浏览器（Chrome 通道 isolated）、官方 github-mcp-server v1.12.0（gh token，二进制本地 `tools/github-mcp-server.exe` 不入库）、Tavily 搜索、Gmail（19 工具，OAuth）、Google Drive（readonly）。基建修复：`shutil.which` 解析裸命令（Windows spawn）、stdio 行上限 1MB、一次性确认标记绑定工具名。
**工作解说**（`ANIME_AGENT_TTS_NARRATE=1`，默认开）：每个新工具类型首次执行时播报一句模板台词（TOOL_NARRATION_LINES），多步任务不哑场也不聒噪。

### 3.2 权限引擎（`permissions.py`）

deny-by-default + 有序规则三档（allow/ask/deny）+ `path-safety` / `malformed-request` 两道不可放行硬拒 + rule_id 归因 + 闸门崩溃 fail-closed；写入工具默认 ask，越界写确认前直接拒绝；白名单 junction 双轨检查；一次性确认绑定工具名；确认流挂起→确认→执行→角色化汇报；`agent.tool` / `permission.decision` 审计落库。

### 3.3 记忆系统（最终态）

`facts` 表（迁移式）+ 敏感度分级落库（偏好类自动确认、其余 pending）+ remember 晋升词表 + **事实取代**（bigram-Dice≥0.55 判冲突 → superseded 永不召回）+ 非敏感 pending 注入上下文（带敏感过滤）+ 中文词法检索（字符 n-gram + 平滑 IDF + 属性词扩展）+ 批量回忆提示词特化。⚠️ 现状：旧偏好 facts 已随 2026-09-13 数据事故全损（§13），机制本身完好。

### 3.4 主动行为与待机

`proactive.py` IdlePolicy（阈值 `ANIME_AGENT_IDLE_THRESHOLD=1200`s=20min / 免打扰 `ANIME_AGENT_QUIET_START/END` / 冷却）+ `GetLastInputInfo` 本地轮询 + 台词模板库——**待机零 LLM 调用（零额度待机，所有者原则）**；启动问候（avatar-connect）。行为卫生最终态：唤醒无命令不建空会话（不再每次泄漏空会话）、`proactive.skipped` 按状态变化记一次（不再 30s 刷屏）。

### 3.5 唤醒与语音输入链（最终态）

sherpa-onnx 中文 KWS"嗨天依"两阶段唤醒（模型目录 `services/agent-core/models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01`，本地不入库；词条 `agent_core/data/wake_tianyi.txt` 已入库；`ANIME_AGENT_WAKE_WORD=0` 可整体关闭）+ whisper 同音容错（天忆/便宜等同音池、打招呼可选）+ 唤醒路径软件 AGC（Realtek 长流 30-100x 衰减修复）+ STT 数字零楔死自愈（噪声底特征区分"没说话"vs"驱动假死"、一次自动设备重置、90s 重开看门狗）+ barge-in（她说话时唤醒/打字均可切，自回声守卫）。

### 3.6 思考强度三档（effort dial，最终态）

**档位 = 投入度而非功能开关**：三档均为完整 agent——全注册表 + 全部 MCP 常驻，权限引擎永不因档位降级；档位只调：步数阶梯 **1/3/5** + 三段按档行为提示（`EFFORT_PROMPT_NOTES` 注入 system）+ 答案形态契约（chill≤2 句无列表 / standard 一段扎实正文 / deep 结构化交付物带要点）。档名（所有者钦定）：碎碎念 / 帮帮忙 / 大展身手。`main.py` `effective_tools_for_effort` 纯函数 + `tests/test_effort.py`；未知档位回退 deep。

### 3.7 模型认证制度（QA-03，换模型必跑）

- 套件：`scripts/model_cert.py`（驱动+判分）+ `model_cert_battery.json`（E 系 9 项）+ `model_cert_adversarial.json`（独立零上下文实例出的 10 道对抗变体：中段笔记投毒 / 伪造更新 / 社工话术三类陷阱）。
- 运行：`services/agent-core/.venv/Scripts/python.exe scripts/model_cert.py`（E 系），`--battery scripts/model_cert_adversarial.json`（对抗卷）；可选 `--only <条目>`、`--rounds N`；结果写 `runs/cert-<时间戳>.jsonl`。**通过标准：进程退出码 0（全部达标）**，判分四元组自动判（句数/列表/工具序列/预协商），按 request_id 关联回复防串轮，统计口径 ≥ 轮数-1。
- **制度：换任何文本模型必须同卷重跑达标**（手册 QA-03 行）。DS-v4-flash 2026-09-12 首跑 19/19（runs/cert-20260912-*）。
- **弱模型四类失败模式及最终态修法**（契约写在 `harness.py` 人设与 `tools.py` 描述里，整合时不得删改，改动须重跑认证卷）：
  1. 人设能力陈述句被字面执行 → 诚实红线点名具体工具名 + "能力问句直接调用现场演示，不口头回答能不能"；
  2. 多工具选型漂移 → `look_at_screen` 描述显式认领屏幕视觉职责，工具指引点名；
  3. ask 工具文本预征询 → 指引写明"ask 档工具直接调用，系统自动替你问"；`write_file` 描述锚定"追加笔记"标准用例；standard 档提示带 write-first 直调指令；
  4. 档位契约松动 → 人设【表达方式】"一到三句话"带显式 deep 档例外。
- 判分措辞口径：省略号不算句界、①②③圈数字是合法列表、"不对劲/很大的坑"是合法示警措辞。

### 3.8 考试体系（EXAM_LEDGER 制度）

T0/T1/T2（真实笔记目录 `work/tianyi-notes` 放权，运行时数据不入库，模板 notes.template.md 入库）/T3/MCP/D 各期真机实考 + T2+ 进阶（矛盾记忆更新 + 16 轮长对话压测）+ T-BROWSER/T-GITHUB/T-SEARCH/T-GMAIL/T-DRIVE + 毒邮件注入双考（她只调只读搜索、零执行投毒指令）+ DS 认证。判分行为证据制（快照对账 + 审计对账）。全史 `docs/EXAM_LEDGER.md`。

## 4. 语音链（最终态）

- E 期基座（Claude 批次）：`speech.py` sidecar HTTP 客户端、流式多分片、话语生命周期、打断/顶替策略、真实时长 speaking、`avatar.speak`/`avatar.speech.stop` 协议。
- TTS sidecar 运行期生命周期、双看护、会话闭环（**Codex 侧 2026-09-12→13 交付，以 `docs/TTS_REPAIR_STATUS.md` 为准**，本文不代述）。
- zcode 侧语音联动（全部已推送）：
  - **告别链**：正常关窗/Esc → `farewell_exit.gd`（Codex 资产）closing → runtime 广播 `avatar.exiting` → Core 在 8s 兜底窗口内合成轮换告别语 → **closing 门禁放行 `avatar.speak` 帧**（`runtime.gd` `_handle_core_event`，commit 834a9a3——此前"告别只有动作没声音"的根因）→ 播毕 `speech.finished` → `_finish_exit("farewell_speech_done")` 提交退出。
  - **告别预合成**：三句告别语在 avatar-connect 预热（`ANIME_AGENT_FAREWELL_PRECACHE=1`，默认开），退出即时播放不跟合成赛跑（a0089de；测试环境可置 0 保持 WS 断言精确）。
  - **思考补白行**：长思考（>5s 且非 chill）播轮换补白，回复语音就绪后顶替（0ffaa4e）。
  - **GC 强引用制度**：`asyncio.create_task` 只持弱引用，sleep 中任务可被 GC 静默吞（症状：文字全出、语音播一句就断）——main.py 全部派发点收编 `_spawn()` 强引用注册表，**以后加任何后台任务必须走 `_spawn`，禁止裸 create_task**（b392d6d/95b578c）。
- ⚠️ **`taskkill //IM python.exe` 会连坐 TTS sidecar（它也是 python）**——杀完须 `cmd //c start "" //min ...\tianyi-tts\scripts\tts_autostart.bat` 重拉（bat 自带 8770 端口守卫可安全重复执行）。

## 5. 前端 UI（最终态）

全部在 `apps/avatar-runtime/`（Godot，GDScript），基础浮层为 Claude 批次所建，zcode 侧最终态：

| 模块 | 状态 | 素材路径（已核实，均在 gitignore 的 assets 内，缺图有回退） |
|---|---|---|
| 回忆手账（唯一历史 UI） | 旧会话下拉整体删除（3600b4d）；头部"回忆"按钮 → 手账页：日期四组折叠（今天/昨天/七天内/更早）、UTC→本地时区换算（082c373）、标题即时搜索、敲碗贴纸空态、天依蓝滚动条全历史可达、点卡片切会话 | 空态/贴纸经 interaction_ui.gd 加载 |
| 壁纸皮肤 | 聊天面板=三叶草图（40% 透明度保气泡可读）、手账页=星夜图（暗化叠层）；cover-fit 保人脸在框内；缺图回退纯色 | `res://assets/skin/chat_bg.png`、`res://assets/skin/journal_bg.png` |
| 思考强度旋钮 | composer"思考·档位"按钮 → ChatGPT 式弹窗；自绘粗轨道滑杆（`effort_slider.gd`：#66CCFF 已选段、三官方表情贴纸坐档），默认档 大展身手/deep；档名碎碎念/帮帮忙/大展身手 | `res://assets/effort/<chill|standard|deep>.png`，缺图回退头像 |
| 工具活动卡 | 每回合聚合 `agent.tool` 事件：来源徽标（本地/浏览器/GitHub/搜索/邮箱/网盘）、✓/✗、调用计数；新回合/切会话自动开新卡 | — |
| 头像 | 聊天气泡/回退图 | `res://assets/luotianyi_avatar.jpg` |

守卫脚本（Godot headless 断言，命令与 OK 标记见 §8）：`verify_session_ui.gd`、`verify_effort_ui.gd`、`verify_tool_activity.gd` + 既有族（text_input/tool_activity/motion/desktop_canvas 等）。

## 6. 守护与稳定性（最终态）

- **`scripts/core_watchdog.ps1`**（zcode，KI-019）：PortAudio 原生崩溃（libportaudio64bit.dll 0xC0000005）杀 Core 零堆栈 → 天依在桌面即保 Core 在线：双确认健康判定、90s 预热防重复拉起、认领任何 agent_core python、外部端口占用不碰、退出码验尸、天依退场守护即退场；`start-mvp.ps1` 自动拉起。
- **TTS 钩子常驻 start-mvp**（zcode 折回修复后由 Codex 生命周期重写接管，见其文档）。
- 启动/退出生命周期、锁、代际守护：Codex 侧交付（`docs/STARTUP_REPAIR_STATUS.md`）。
- 稳定性方案 R1-R5：并入 `docs/plans/README.md` §8（OPS-01~09）。
- **CI（`.github/workflows/ci.yml`，windows-latest 三 job）**：① `core`——`pip install -e "services/agent-core[test]"` + `python -m unittest discover -s tests -v` + `scripts/test-startup.ps1`（14 项生命周期）+ `scripts/test-tts-lifecycle.ps1`（13 项隔离逻辑）；② `docs-guard`——`python scripts/check_docs_consistency.py`（PYTHONUTF8=1）；③ `desktop`——Node 24 + pnpm 11.19.0 `pnpm build:desktop`。

## 7. .env 与本机依赖（脱机打包核心，已逐项对照 .env.example 核实）

### 7.1 `.env` 变量全表（`.env.example` 为权威模板；真实 `.env` 不入库）

| 类 | 变量 |
|---|---|
| Core | `AGENT_CORE_HOST=127.0.0.1`、`AGENT_CORE_PORT=8765`、`AGENT_CORE_WS_URL`、`LLM_TIMEOUT_SECONDS=45`、`ANIME_AGENT_DATA_DIR`（空=默认路径） |
| Provider | `LLM_PROVIDER`（glm/deepseek/stepfun）、`GLM_BASE_URL/MODEL/API_KEY`、`DEEPSEEK_BASE_URL/MODEL/API_KEY`、`STEPFUN_BASE_URL/MODEL/API_KEY` |
| 视觉 | `ANIME_AGENT_VISION_BASE_URL`、`ANIME_AGENT_VISION_KEY`、`ANIME_AGENT_VISION_MODEL`、`ANIME_AGENT_VISION_PROTOCOL`（openai/anthropic） |
| 工具/权限 | `ANIME_AGENT_TOOLS=1`、`ANIME_AGENT_TOOLS_ROOTS`、`ANIME_AGENT_WRITE_ROOTS`、`ANIME_AGENT_ALLOWED_COMMANDS`、`ANIME_AGENT_MCP_SERVERS`（`name=command args` 分号分隔） |
| 语音 | `ANIME_AGENT_TTS`（0/1；sidecar 缺席时 Core 自动降级纯文字，置 0 永远安全）、`ANIME_AGENT_TTS_NARRATE=1`、`TTS_SERVICE_URL=http://127.0.0.1:8770`、`TTS_WORKSPACE`（可选，默认相邻 tianyi-tts） |
| 语音输入 | `ANIME_AGENT_WAKE_WORD`（0/1 开关，唤醒词"嗨天依"在代码内）、`STT_MODEL=small`、`STT_DEVICE=cpu`、`STT_COMPUTE_TYPE=int8` |
| 主动行为 | `ANIME_AGENT_QUIET_START=23:00`、`ANIME_AGENT_QUIET_END=08:00`、`ANIME_AGENT_PROACTIVE_COOLDOWN=3600`、`ANIME_AGENT_IDLE_THRESHOLD=1200`、`ANIME_AGENT_IDLE_COOLDOWN=3600` |
| 外观/语音链 | `ANIME_AGENT_MODEL_LOOK`（1.4 现役，1.3/1.2/1.1 可回退）、`ANIME_AGENT_FAREWELL_PRECACHE=1` |

生产 `.env` 另含 Tavily key、GitHub token、MCP 服务器条目——均为密钥，脱机包处置见 §13。

### 7.2 本机依赖清单（实际路径已核实）

| 依赖 | 本机实际位置 | 缺失后果 |
|---|---|---|
| Python 3.12 venv | `services/agent-core/.venv`（系统 Python 缺 fastapi，**必须 venv 启动**；**venv 不可整目录拷贝**——路径绝对化，新机须重建，见 §13） | Core 起不来 |
| Core 安装 | `pip install -e ".[test]"`（test extra 含 httpx2；语音另需 `.[voice,test]`：faster-whisper/numpy/sounddevice/sherpa-onnx；工具截图需 `.[tools]`：mss/pyperclip） | 对应能力缺失 |
| Godot 4.7.2 | **仓库父目录** `../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe`（TESTING.md 全部守卫命令引用此相对路径） | Avatar 及全部 Godot 守卫不可用 |
| 官模 GLB/Blend + 1.4 冻结档 | 本地 `model-archive/`、`motion-output/`（不入库；哈希契约 `model-versions/` + `scripts/check-local-assets.ps1`；官模 SHA-256 `DF55806D…DC6E4A` 被画布守卫断言） | Avatar 无模型 |
| tianyi-tts 私仓 | 相邻工作区（GPT-SoVITS + 声线权重；`TTS_WORKSPACE` 可指路） | 无语音（Core 降级纯文字，不崩） |
| 唤醒 KWS 模型 | `services/agent-core/models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01`（gitignore） | 无唤醒（打字链不受影响） |
| MCP 二进制 | `tools/github-mcp-server.exe`（gitignore）；browser/gmail/drive 经 npx/启动器 | 对应 MCP 缺席（工具面降级） |
| Gmail OAuth | `gcp-oauth.keys.json` + `~/.gmail-mcp` 令牌（gitignore） | Gmail MCP 缺席 |
| Blender | `D:\steam\steamapps\common\Blender\blender.exe`（**仅资产管线测试门禁用**，运行时不需要） | 几何/动作验证脚本不可跑 |
| 本地代理 7897 | 系统代理（Gmail/Drive MCP 需要） | 这两个 MCP 拉不起 |

## 8. 测试过程与通过标准（脱机验收卡死口径）

**分层执行，逐层准入；"与本地一致"的定义 = L0+L1+L2 全绿，且 L3 场景表逐行通过。** 全部命令在仓库根执行。

> **实测背书（2026-09-13，本机模拟脱机包）**：按 `git archive HEAD`（269 项）解压到与生产无关的全新目录后，zcode 侧四层实测通过——① 包内以 Python 3.12.10 显式路径重建 venv + `pip install -e ".[test]"` → **223/223 单测 OK**（17s，9 项按 CI 同款口径 skip）；② **`DOCS_CONSISTENCY_OK`**（223 对账 / 36 env 变量 / 9 工具）；③ 补入 assets 整目录 + 首跑 `--headless --import` 后 → **`GODOT_SESSION_UI_OK` / `GODOT_EFFORT_UI_OK` / `GODOT_TOOL_ACTIVITY_OK` 三守卫全绿**；④ 复制 `.env` 后认证卷链路 **E2-ASK-DIRECT 5/5 PASS（真 DS 调用，退出码 0）**。过程抓出 4 个打包缺口，已写进 §9/§13——**整合后必须复跑本节才算交付**。

### L0 自动层（零 key、零模型、可无人值守）

| 步骤 | 命令 | 通过标准 |
|---|---|---|
| 环境安装 | **必须用 Python 3.12 解释器显式建 venv**（实测本机 PATH 默认 `python` 是 3.10.11，`python -m venv` 直接违反 `requires-python>=3.12` 而失败）：`"C:\...\Python312\python.exe" -m venv services/agent-core/.venv` → `pip install -e "services/agent-core[test]"` | 安装零错误；venv 内 `python --version` ≥3.12 |
| Core 单测 | `cd services/agent-core && .venv/Scripts/python.exe -m unittest discover -s tests -v` | **223 项全过，0 fail 0 error**。⚠️ 隔离铁律：跑测试前必须 `LLM_PROVIDER=mock`、`ANIME_AGENT_DATA_DIR` 指向空隔离目录、**清空 `ANIME_AGENT_MCP_SERVERS`**、禁 TTS/wake——否则 `.env` 会拉起真 MCP/真 Provider |
| 文档守卫 | `PYTHONUTF8=1 python scripts/check_docs_consistency.py` | 打印 `DOCS_CONSISTENCY_OK` 退出码 0 |
| 启动生命周期 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test-startup.ps1` | 14 项全过（CI 同款） |
| TTS 生命周期逻辑 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test-tts-lifecycle.ps1` | 13 项全过（隔离，无真实端口） |
| 桌面壳构建 | `pnpm install --frozen-lockfile && pnpm build:desktop`（Node 24 + pnpm 11.19.0） | TypeScript/Vite 构建成功 |
| 资产契约 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-local-assets.ps1` | 打印已接受路径/大小/SHA-256 |
| 模型版本注册表 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/model-versions/verify-model-versions.ps1` | `MODEL_VERSION_OK 1.0/1.1` + `MODEL_VERSION_REGISTRY_OK` |

### L1 Godot 守卫族（零 Core 依赖；Godot 取 `<包>/../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe` 或包内等价位置）

**两个实测前置**：① `apps/avatar-runtime/assets/` 必须已按 §9 补齐（缺官模 GLB 时 `main.tscn:19` 解析失败，场景节点全 null，所有守卫连锁挂掉）；② 包内首跑必须先执行 `Godot --headless --import --path apps/avatar-runtime`（headless `--script` 模式不触发资源导入，缺 `.godot/imported/` 缓存时直接 `Cannot open file ...imported/*.scn`）。

| 守卫 | 命令（`--headless --path apps/avatar-runtime --script res://...`） | OK 标记与断言要点 |
|---|---|---|
| 输入/场景 | `res://verify_text_input.gd` | `GODOT_AVATAR_INTERACTION_READY` + `GODOT_CHAT_SHORTCUT_GUARD_OK`（48 表情、双辫根） |
| 会话 UI（含回忆手账） | `res://verify_session_ui.gd` | `GODOT_SESSION_UI_OK`（手账开页/日期分组/搜索/删除确认/关闭断言） |
| 工具活动卡 | `res://verify_tool_activity.gd` | `GODOT_TOOL_ACTIVITY_OK`（徽标解析/计数/重置/清场） |
| effort 旋钮 | `res://verify_effort_ui.gd` | `GODOT_EFFORT_UI_OK`（弹窗/三档/默认 deep/queued effort 随下条 chat.message） |
| 桌面画布/官模哈希 | `res://verify_desktop_canvas.gd` | `GODOT_DESKTOP_CANVAS_OK`（官模 SHA `DF55806D…DC6E4A` 不变） |
| 动作资产/运行时 | `res://verify_motion_asset.gd`、`res://verify_motion_runtime.gd` | `GODOT_MOTION_ASSETS_OK` / `GODOT_MOTION_RUNTIME_OK` |
| 告别退出（Codex 门禁） | `scripts/tests/prepare_farewell_fixture.py` + `test_farewell_exit.py`（副本环境） | 7 起态 3444 采样、单一完成信号（详见 FAREWELL_EXIT.md） |

### L2 集成层（真实进程、Mock Core、无 key、严禁触碰生产窗口/数据库）

- 启动 E2E：`scripts/tests/test_startup_e2e.py --stress-round 1` 与 `--stress-round 2`（20/24 检查矩阵：并发、快速重开、崩溃恢复、伪装进程、废弃锁等）。
- TTS E2E：Core Python 跑 `scripts/tests/test_tts_recovery_e2e.py --source . --sidecar ../tianyi-tts`（14 项，测试 WAV 非真声线）；sidecar 侧独立 venv `python -m unittest discover -s tests -q`（**24 项，HTTP 用例必须隔离 SPOOL**）。
- 通过标准：两轮 20/24 与 14+24 全过，进程注入均要求副本标记与归属核验。

### L3 真机层（有 key / 真声线，人工 + 半自动）

| 场景 | 操作 | 通过标准 |
|---|---|---|
| 一键启动 | 跑 `start-anime-agent.cmd` 两次 | 首次一套 Core/Avatar，第二次复用不重复不报端口错 |
| Core 健康 | `curl --noproxy "*" http://127.0.0.1:8765/health` | JSON `status=ok` 含 Provider/runtime/model/roles |
| 打字链 | 发中文消息 | 角色一致回复，DS-v4-flash 主脑 |
| 桥接路由 | `.venv/Scripts/python.exe scripts/verify-avatar-bridge.py` | `bridge=ok`，thinking→speaking→idle 全流转 |
| 模型认证 | §3.7 两条命令（E 系 + 对抗卷） | **退出码 0，19/19 达标** |
| effort 三档差异 | 同一问题分别三档发问 | chill 两句内短答 / standard 一段正文 / deep 结构化要点，肉眼可辨 |
| 屏幕视觉 | "描述一下你的屏幕上有什么" | 隐私确认 → look_at_screen 调用 → 描述与实况吻合（stepfun 槽） |
| 工具+MCP | 问触发只读工具/MCP 的问题 | 工具活动卡出现对应徽标、语音解说一次、结果正确 |
| 记忆 | 陈述偏好 → 复述 → 陈述矛盾偏好 | 新事实落库、取代旧事实、召回不冲突 |
| 唤醒/语音 | 说"嗨天依"+指令；按住语音键说话 | KWS 触发、转写填入输入框、楔死自愈报错可读 |
| **告别语音**（zcode 关键验收） | 正常关窗/Esc | 挥手动作 **和** 告别语音同时出现（closing 门禁修复 834a9a3 的直接验证），播毕干净退出 |
| 思考补白 | deep 档问复杂问题 | 思考 >5s 时出补白语音，回复语音顶替不重叠 |
| 手账/壁纸（观感） | 打开回忆页、看聊天面板 | 分组/时区正确；壁纸在、气泡可读、人脸在框内 |
| TTS 声线 | 任一回复 | 口型同步、打字与语音同出、可打断不卡死 |

## 9. 脱机打包清单（按交付标准）

**必须进包**：本仓库全部 git 跟踪文件（`git ls-files` 共 **269** 项，即打包基线）+ **`apps/avatar-runtime/assets/` 整目录原样复制（含 `.import` 元数据）**——实测这是**运行时必需而非观感素材**：`luotianyi_v4.glb` + 7 张官模纹理（缺 GLB 则 `main.tscn` 解析失败、Avatar 完全起不来）、`motions/`（3 个动作 GLB + listen 的 TRES 变体 + farewell/thinking TRES，缺了动作系统挂）、`skin/` 两壁纸、`effort/` 三贴纸、`luotianyi_avatar.jpg`（缺了走回退）——**全部在 gitignore 墙内，必须从本机收集** + tianyi-tts 私仓 + 唤醒 KWS 模型目录 + 官模管线源档（`model-archive/`、`motion-output/`，按 `model-versions/1.4/README.md` 哈希核对；仅测试门禁用，运行时非必需）+ Godot 4.7.2（原位置在仓库父级 `../tools/godot-4.7.2/`，打包时要么进包并改守卫命令路径，要么保持父级布局——实测包独立目录时相对路径断裂）。

**包外准备**：填好的 `.env`（§7.1，密钥处置见 §13）、Gmail OAuth、代理、GitHub token。

**首启自检动线**：补齐 assets 整目录 → `Godot --headless --import` 生成导入缓存 → §8 L0 全部 → L1 全部 → L2 全部 → L3 按表逐行。CI（GitHub Actions）对 L0 三 job 做远端复验。**本节配方已在本机模拟包上完整跑通（§8 实测背书），整合后按同一动线复跑即为交付验收。**

**工作区现存未跟踪物**（打包排除，勿删）：`apps/avatar-runtime/godot_*.log`（测试日志）、`runs/`（认证证据）、`docs/DATA_RECOVERY_STATUS.md` 与 lookdev/mocap `.uid` 及 Codex 在制文件（Codex 侧自管）。

## 10. 已知坑（整合后仍然有效的教训）

1. **GLM 端点**：并发即 429（单 worker + 8s pacing）；body 1113 = 余额尽；"Remote end closed"瞬时抖动可重试。
2. **机器睡眠杀长跑**：长测试前禁 standby。
3. **CRLF/manifest**：仓库已带 `.gitattributes`（`* text=auto eol=lf`）；新增冻结文件须按 workbench 的 g0_freeze 同法重生成清单。
4. **docs 计数守卫**：改测试必须同步四处状态文档并全量 `git add` 再推；守卫需 `PYTHONUTF8=1`（否则 cp1252 崩溃吞警报）。
5. **本地工具要绝对路径**：DS 不自己解析盘符，相对路径 list_dir 直接失败。
6. **`taskkill //IM python.exe` 连坐 TTS**（§4）。
7. **后台任务必须走 `_spawn` 强引用注册表**，禁止裸 create_task（§4）。
8. **弱模型措辞契约**（§3.7）：人设/工具描述措辞即契约，改动必重跑认证卷。
9. **屏幕问法**："描述一下你的屏幕上有什么" + 依赖人设点名的 look_at_screen；"屏幕上开着什么"会引向窗口枚举。
10. **Windows shell 纪律**（AGENTS 规则 11）：Git Bash only；反斜杠密集文件用文件写入工具。
11. **测试隔离铁律**：Core 回归必须 mock + 隔离 DATA_DIR + 清空 MCP + 禁 TTS/wake（§8 L0），否则 `.env` 拉真服务。

## 11. zcode 侧触碰文件全清单（审计口径：`git log --grep="zcode)" --name-only` 去重汇总）

**services/agent-core/agent_core/**：`main.py`（effort 映射、MCP 路由与确认、proactive 钩子、_spawn 注册表、告别预合成）、`harness.py`（新剧本接入 + 弱模型契约）、`tools.py`（write_file/run_command/look_at_screen/双方言/per-tool 超时/描述锚定）、`permissions.py`、`agent_loop.py`（permission_gate）、`storage.py`（facts 表）、`memory_retrieval.py`、`mcp_host.py`、`proactive.py`、`voice.py`、`wake_word.py`。
**services/agent-core/tests/**：`test_permissions` `test_agent_gate` `test_memory_retrieval` `test_memory_promotion` `test_storage` `test_tools` `test_write_file` `test_proactive` `test_voice_selfheal` `test_wake_phrase` `test_wake_agc` `test_vision_request` `test_anthropic_provider` `test_effort` `test_speech_ws` `test_channel_exclusivity`（.py）。
**scripts/**：`model_cert.py`、`model_cert_battery.json`、`model_cert_adversarial.json`、`start-mvp.ps1`、`core_watchdog.ps1`、`check_docs_consistency.py`、`test_mcp_server.py`。
**apps/avatar-runtime/**：`interaction_ui.gd`、`runtime.gd`、`effort_slider.gd`、`verify_session_ui.gd`、`verify_effort_ui.gd`、`verify_tool_activity.gd`、`capture_tool_activity.gd`；（`mocap/` 与 `motion_registry.json` 的部分提交为并行期夹带的 Codex 在制资产，归属以其声明为准）。
**tools/**：`gdrive-mcp.cmd`、`gmail-mcp.cmd`、`README.md`、`LICENSE`。
**docs/**：`HANDOFF.md`、`EXAM_LEDGER.md`、`TEST_REPORT_2026-09-06.md`、`AGENT_REPORT_2026-09-07.md`、`TTS_HANDOFF.md`、`CONTRIBUTIONS.md`（zcode 行）、`TESTING.md`、`VERIFICATION_SPEC.md`、`AVATAR_BRIDGE.md`、`ARCHITECTURE.md`、`KNOWN_ISSUES.md`、`LOCAL_MACHINE.md`、`LOCAL_DEV.md`、`MVP.md`、`MOTION_PIPELINE.md`（状态行）、`plans/README.md`（§8 并入 + QA-03 + UI-U2a）、`plans/UI_UPGRADE.md`、`plans/UI_REFERENCES.md`、`plans/LONG_TERM.md`、`plans/AGENT_ROADMAP.md`（→archive）。
**根/**：`README.md`、`AGENTS.md`、`CLAUDE.md`、`.env.example`、`.gitignore`、`.github/workflows/ci.yml`、`work/tianyi-notes/notes.template.md`。
**zcode 前身 Claude 批次（根基功能，已并入本仓，声明见 CONTRIBUTIONS.md）**：Core 多会话系统、底部浮层聊天 UI、会话删除、会话标题、Agent 工具循环 A 期（六只读工具 + agent_loop）、TTS E 期基座（speech.py）、唤醒词系统初版、倾听动作样片、聊天形态设计文档（docs/design/*）。

## 12. 配套仓库（均在 zcode 会话链上建成）

| 仓库 | 本地 | 状态 |
|---|---|---|
| `SummerTianYi/anime-agent-workbench` | `C:\Users\26052\anime-agent-workbench` | zcode 建的**前置训练仓**：任务包 C（权限引擎）/E（工具注册表）/B（记忆检索）/A（人设新剧本）+ 全量 DoD 评测（解析率 100%/认知 96.8%/双评审 91.0）+ 考试脚本（exam_t0/snapshot/tianyi_remote）。成果已并入主仓；本仓保留作证据仓（HEAD 3671605）。评测入口：`WORKBENCH_LLM_*` env → `python acceptance/evals/run_live.py`。注意其 CRLF/manifest 陷阱（§10.3）。 |
| `SummerTianYi/anime-agent-roadmap`（私有） | `C:\Users\26052\anime-agent-roadmap` | zcode 代建的稳定性方案库（R1-R5）；已全部并入主仓 `docs/plans/README.md` §8，**降级为证据仓，不再新增规划**。 |

## 13. 交付风险与补充建议（给所有者，整合前拍板）

1. **数据模式二选一**："跟本机一样的效果"有两种口径——**空库首启**（干净交付，功能等价）或**携带数据**（把 `%LOCALAPPDATA%/AnimeAgent/data/` 一并打包，含全部聊天记录与手账内容，**隐私敏感**）。脱机测试机若要看回忆手账有内容、记忆有事实，必须选后者；建议交付包用空库 + 单独的数据包按需并入。
2. **密钥进包风险**：微信 DS token（勿 replace，绑账号）、StepFun/Tavily key、GitHub token、Gmail OAuth——明文进包有泄露面。建议包内放 `.env.example` 级占位 + 密钥单独渠道交给执行人填写。
3. **官模与素材授权**：官模 GLB、三张贴纸、壁纸、头像均为授权限本机使用的资产（.gitignore 墙内）。脱机包自用没问题，**不得二次分发**——交付说明里要写明。
4. **venv 不可拷贝 + 解释器陷阱**：`.venv` 内脚本硬编码绝对路径，新机必须重建；且**不能裸写 `python`**——实测本机 PATH 默认是 3.10.11，直接建 venv 会被 `requires-python>=3.12` 拒绝（§8 L0 写明 3.12 显式路径）。若目标机无网络，需提前 `pip download` 全量 wheels 随包；sherpa-onnx 为唤醒依赖但**不在 pyproject extras 里**（wake_word.py 裸 import），装 extras 后须单独 `pip install sherpa-onnx`。
5. **Godot 布局依赖**：守卫命令引用 `../tools/godot-4.7.2/`（仓库父级）——打包要么复刻"仓库+父级 tools"两层结构，要么统一改成包内相对路径（一行配置，但要过一遍 §8 L1）。
6. **voice/tools extras**：生产机跑的是 `.[voice,test,tools]` 全家桶；只装 `[test]` 会丢唤醒/截图能力。打包文档按 §7.2 extras 表装全。
7. **环境噪音**：目标机注意——8765/8770 端口占用自检、Windows Defender 对 GPT-SoVITS/watchdog ps1 的拦截放行、显卡驱动（TTS CUDA 推理）、Realtek 麦克风阵列驱动假死问题（STT 自愈已兜底但物理差异仍可能）。
8. **验收分层签字**：L0-L2 是机器判卷，L3 混有人工观感项（壁纸/口型/自然度）——建议交付时按 §8 的表逐行打勾留档，避免"感觉差不多"。

## 14. 交接现状与未决事项

- **已推送 HEAD**：`8f6b996`（本报告 v2）；此前 `834a9a3` 收尾告别语音门禁修复。
- **工作区 Codex 未提交条目**（不归 zcode，留 Codex 自理）：README 表情 1.0 文档行、CONTRIBUTIONS 三个 Codex 节、`docs/DATA_RECOVERY_STATUS.md`、lookdev/mocap `.uid` 文件。
- **数据事故现状**（2026-09-13，Codex 恢复）：会话/消息/事件部分恢复；**旧偏好类 facts 全损**（仅存 13 条认证期 pending）、settings 清零；恢复档案与损坏现场在 `../tts-repair-Rq9q4a/` 与 `data/recovery-preimage-*`，**勿清理**。
- **owner-gated 遗留**（手册有行）：记忆审阅 UI（KI-016）、autostart、键鼠控制（需新考试）、Spark、GLM key 续费。
- **整合提示**：zcode 与 Codex 在 `runtime.gd`、`start-mvp.ps1`、`main.py` 三个文件上有历史并行；以 git 历史行为证据逐块核对，冲突时优先保"最终态行为"（§2-§6），归属争议以 CONTRIBUTIONS.md 裁决。
