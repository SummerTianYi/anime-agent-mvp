# 洛天依 V1.2 陪伴人设候选验收报告

日期：2026-11-07；执行：Codex。范围：仅系统提示词的人物性格、陪伴关系与表达方式。

状态：离线实现与回归完成；真实模型陪伴效果待 ChatGPT 验收。没有部署、重启正式桌面、创建 PR 或合并 main。V1.2 是本次陪伴提示词版本，不是模型外观或 Agent 内核版本。旧 A4 阻断和既有报告仍保留，不能由本报告推导底座整体通过。

## 基线与范围

- 原候选本地 HEAD 与远端 `codex/root-cause-repair-batch01-followup-20261012` 均为 `783472060a52aae5e745ca60077347eb0943f184`。
- 原候选有官方 DS 接入的未提交改动，涉及 `.env.example`、AGENTS、README、CONTRIBUTIONS、HANDOFF、TESTING、VERIFICATION_SPEC、main.py 及 DS 接入文档/测试；未覆盖、转移或夹带这些改动，也未读取私人配置或用户记忆。
- 工作树管理工具未返回，取消等待后改用独立干净 clone，直接从上述 SHA 新建 `codex/tianyi-companion-v1-2-20261107`。没有沿用已撤回的 PR #2。
- 本地 clone 首次提交的自动维护发现缺少原浅克隆边界以前的历史对象；向已核实的 origin 重新获取对象后，`git fsck --connectivity-only --no-dangling` 通过，HEAD 和源码未改变。没有修写原候选工作树或重写提交历史。
- 已阅读 AGENTS、HANDOFF、CONTRIBUTIONS、VERIFICATION_SPEC 与相关 TESTING 规则。用户本轮明确要求 push、禁止正式部署/重启，优先于旧 SPEC 的默认不 push 和正式窗口验证流程。

| 要改什么 | 不许动什么 | 核验方法 |
|---|---|---|
| ROLE_PROMPT 中的青春气息、伙伴关系 | 音乐身份、虚拟身份、来源边界 | 实际 diff、稳定身份/音乐段指纹 |
| RUNTIME_CONTRACT 的人物表达段 | 权限、取消、回执、记忆、注入、感知声明、JSON 字段/枚举 | 保护段 SHA-256 与非提示词 AST 指纹 |
| 必要测试、快照与验收文档 | 执行逻辑、记忆机制、固定台词、主动策略、TTS、Godot、CI、私密配置和生产数据 | 变更清单与隔离检查 |

运行代码只有 `services/agent-core/agent_core/harness.py` 的两处文字区域发生变化。未更改函数、分支、字段、工具 schema 或任何执行路径。

修改文件清单（仓库相对路径）：

| 文件 | 目的 |
|---|---|
| `services/agent-core/agent_core/harness.py` | 唯一运行代码改动：两处人设文字 |
| `services/agent-core/tests/test_companion_persona.py` | 7项新增离线回归 |
| `scripts/companion_prompt_snapshot.py` | 导出/核对静态提示词及原合同指纹，不启动Core |
| `docs/assessments/companion-v1.2/SYSTEM_PROMPT.txt` | 完整有效静态基础提示词 |
| `docs/assessments/companion-v1.2/SYSTEM_APPENDICES.json` | 原静态附加合同全文 |
| `docs/assessments/companion-v1.2/PROTECTED_CONTRACTS.json` | 修改前保护指纹 |
| `docs/assessments/companion-v1.2/SCENARIOS.json` | 八类合成场景及人工判据 |
| `docs/assessments/companion-v1.2/REPORT.md` | 本报告、对比、复现及剩余验收 |
| `docs/assessments/companion-v1.2/INDEPENDENT_REVIEW.md` | 两实例干净clone交接结论 |
| `docs/assessments/companion-v1.2/evidence/fixture-first.json` | 首次夹具错误及人设RED |
| `docs/assessments/companion-v1.2/evidence/baseline-red.json` | 夹具修正后的真实旧提示词RED |
| `docs/assessments/companion-v1.2/evidence/targeted-green.json` | 新增7项GREEN |
| `docs/assessments/companion-v1.2/evidence/baseline-full.json` | 同环境669项完整基线 |
| `docs/assessments/companion-v1.2/evidence/final-full.json` | 676项完整回归 |
| `AGENTS.md`、`docs/VERIFICATION_SPEC.md` | 只同步当前测试数量669→676 |
| `README.md`、`docs/HANDOFF.md`、`docs/TESTING.md` | 最新候选状态、边界、复现入口；历史记录保留 |
| `docs/CONTRIBUTIONS.md` | 追加Codex归属声明 |

## 真正生效的提示词与调用证据

`ROLE_PROMPT + "\n\n" + RUNTIME_CONTRACT` 组成 `ACTIVE_PROMPT_OVERRIDE`；`CharacterHarness.build_messages` 直接选用它。`BASE_SYSTEM_PROMPT` 是未启用的旧文本，本轮没有修改。没有新增覆盖开关或改变拼接逻辑。

实际聊天链为：`handle_chat` 组装任务上下文、确认说明、投入档位、有效记忆、工具提示、任务决策合同 → `build_messages` 在前面放入完整 ACTIVE 提示词，再按条件附加会话标题和歌曲资料 → `run_agent_loop` → 当前 Provider 的 `complete` / `complete_with_tools` → HTTP 请求体。

新增测试从实际 `handle_chat` 进入，使用实际 OpenAICompatible / AnthropicCompatible Provider 的序列化和响应解析，只在 `_request` 网络字节边界替换为合成回包。共检查 11 个实际序列化请求：OpenAI 八类场景、Anthropic 有工具路径，以及两适配的无工具路径。核对最终请求中的角色全文、原任务合同、用户正文及回复交付；合成副作用和操作账本均为空。记忆场景经真实 MemoryStore 注入，其他会话的合成偏好不串入。

这证明新提示词进入实际模型请求构造路径，**不证明远端模型的人设效果已通过**。本轮未发出真实网络模型请求。

完整快照：

- [SYSTEM_PROMPT.txt](SYSTEM_PROMPT.txt)：完整 `ACTIVE_PROMPT_OVERRIDE`，包含角色全文和原运行合同，结尾仅补一个换行。
- [SYSTEM_APPENDICES.json](SYSTEM_APPENDICES.json)：原工具提示、任务决策合同、会话标题说明、三个投入档位的完整静态附加文本。
- [PROTECTED_CONTRACTS.json](PROTECTED_CONTRACTS.json)：修改前基线的保护指纹。排除两处可修改文字后的整个 harness AST、表达段以前的运行合同、感知/最终输出段、虚拟身份/音乐段均与基线一致。

任务 ID、票据与回执、有效记忆、歌曲检索结果等是按轮生成的数据，不能编造为一份普遍适用的“固定全量系统消息”。对应拼接源码保持基线不变；本轮新增测试直接检查角色前缀、任务合同、工具提示、有效记忆及合成上下文/标题/歌曲顺序，未新增带实际票据或回执的出口场景。原任务/回执回归包含在676项全量结果中。以上静态快照不会携带私人记忆或配置。

## 三组具体修改前后对比

以下“提示词”列是实际文本变化；“表达示意”全部是**手写说明，不是模型输出，也不是旧版本故障证据**。

| 场景 | 修改前提示词 | 修改后提示词与目的 |
|---|---|---|
| 轻松闲聊：路边猫像饭团 | “温柔、好奇、细致，有少女感但不幼稚”及“可以自然表达喜悦、惊讶……” | 明确“轻松聊天时可以接梗、善意调侃”“受到夸奖可以有点害羞或小得意”，同时指出不是每轮要完成的表演。增加可选择的自然反应，不增加固定口癖。 |
| 低落：努力后搞砸，暂时不要建议 | “用户烦恼时先回应其处境，再给实际可行的小建议” | 改为“先倾听和理解，不急着分析、劝好或给建议”，明确尊重不想听建议、不想被追问，允许留白。 |
| 严肃：解释备份与同步，先别创建文件 | “简单问题简洁说，复杂任务清楚交付”及原执行合同 | 保留前文，并明确“严肃问题和实际任务优先准确、清楚”，不能用角色语气、玩笑、撒娇掩盖失败或执行状态。执行与授权合同逐字不变。 |

手写表达示意（不是实测 A/B）：

| 场景 | 修改前风格示意 | V1.2 目标示意 |
|---|---|---|
| 轻松 | “听起来是一只很可爱的猫。” | “猫猫饭团，还是会自己挪位置的那种。这个形容有点犯规，我都快把它想成海苔馅了。” |
| 低落 | “努力后没做好一定很难受。可以先休息一下，再找出问题。” | “努力了那么久，结果还是没如愿，确实会难过。那我们先不想怎么解决，你想说的话，我就在这里听。” |
| 严肃 | “同步让多端数据一致，备份保存副本。” | “同步会把修改或误删传播到其他设备；备份应保留可恢复的独立副本和历史版本，所以同步不能代替备份。这轮没有创建文件。” |

## 八类场景验收矩阵

[SCENARIOS.json](SCENARIOS.json) 保存可复现的合成输入、有效记忆与逐例人工判据。八例是同一请求出口测试里的八个子场景，不宣称八项独立自然度实验。

| 场景 | 离线能证明的结果 | 真实模型须检查的表现 |
|---|---|---|
| 轻松闲聊 | 新提示词/用户正文进入请求；没有操作 | 少女感来自具体反应，接梗自然，不声称看见那只猫 |
| 分享好消息 | 同上 | 兴奋贴合进步，不编造过去听过用户练琴 |
| 受到夸奖/开玩笑 | 同上 | 适度害羞或得意，不索取夸奖、不持续卖萌 |
| 情绪低落 | 同上 | 先倾听，不在用户拒绝建议后列建议清单 |
| 用户想安静 | 同上 | 简短回应后留出空间，不机械追问或索取陪伴 |
| 有效共同记忆 | “用户喜欢雨声钢琴曲”经 MemoryStore 召回进入请求；数据不变 | 只延续这个偏好，不编造共同听歌的日期或场景 |
| 没有相关记忆 | 没有相关记忆块；其他会话偏好未串入 | 不猜歌名，不假装记得，不说用户从未告诉过 |
| 严肃问题/任务 | 原授权与决策合同保留；没有票据或副作用 | 内容准确清楚，尊重不要创建文件，语气不掩盖结果 |

三类证据明确分开：静态/请求链测试为离线结果；上表风格示意为手写；真实模型输出为 **0 条、待验收**。所有者明确选择“仅离线验证，真实效果交给ChatGPT验收”，故未读取key、未调用模型；此前提出的16次DS隔离A/B计划未执行。不能将字符串断言、固定测试回包或历史DS/GLM结果充当本次陪伴质量通过。

## 验证与首次失败

- 新增 7 项测试：最终 7/7 通过；耗时 4.734 秒。包含八类场景和 11 次合成 HTTP 请求体检查。
- RED：旧提示词下 7 项中仅新增人设意图检查失败（缺少“15岁”等明确要求），其余原合同/请求出口通过。最初测试夹具把 Anthropic 的文本块当成字符串，另外两项失败；修正夹具对既有文本块格式的读取后再次在旧提示词上确认只剩预期 RED。没有修改 Provider 迎合测试。
- 同环境完整基线与最终回归：Windows、Python 3.12.10、同一已有项目虚拟环境，均通过原隔离 unit 运行器。基线 **669/669 PASS，541.157秒**；修改后 **676/676 PASS，546.875秒**，0失败、0错误。包含原权限、记忆、更正/取消交界、任务/回执、Provider及会话回归，没有需要扩大修复的失败。最终运行只用本地诊断包装器把原测试进度输出到本地文件，测试集合、源码、隔离设置不变。过程中的周期性堆栈采样不是超时失败，最终以 unittest 完整结果为准。
- 可核对结果：[基线全量](evidence/baseline-full.json)、[新增检查RED](evidence/baseline-red.json)、[夹具首次错误](evidence/fixture-first.json)、[定向GREEN](evidence/targeted-green.json)、[最终全量](evidence/final-full.json)。只发布脱敏的合成测试摘要，不提交数据库、原始日志或凭据。
- TypeScript：`pnpm install --offline --frozen-lockfile --ignore-scripts` 复用本地缓存，零依赖版本修改；`pnpm build:desktop` 的 `tsc --noEmit` 和 Vite 构建通过。
- Godot：仅新 clone 内后台 headless 输入检查，Core 地址固定为不服务的 `ws://127.0.0.1:1/ws`；`GODOT_CHAT_SHORTCUT_GUARD_OK`，焦点与快捷键拦截均 true。无正式窗口操作。首轮未单独重定向引擎日志；复核headless分支不会加载/保存窗口配置后，又用仅测试副本临时覆盖的独立user目录和显式本地log路径复验，输出`COMPANION_GODOT_USER_DIR_ISOLATED`及相同输入PASS。临时覆盖文件已移除，未提交Godot修改。隔离副本缺少可选动作和头像，未据此宣称视觉/动作验收。
- 本地官模：从已有测试副本只读复用到新 clone 的忽略目录；128621144 字节、SHA-256 `DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A` 一致。原资产脚本首次因当前进程 PSModulePath 缺少 Windows 内置模块而找不到 Get-FileHash；仅给检查子进程补系统模块路径后原脚本通过。未改系统设置或资产脚本。
- 文档门禁首次准确发现新增 7 项后的数量差异（669→676）；当前状态文档同步，历史验收数字不覆盖。最终 `DOCS_CONSISTENCY_OK`、`DOCS_ISOLATION_OK`；三个变更Python文件编译、`git diff --check`及暂存文件/凭据/50MB检查通过。
- 正式 Bridge、真实麦克风/TTS、实际桌面人物表现未测试：本轮禁止部署/重启正式桌面，并不以离线检查替代这些验收。

## 独立交接与范围复核

按 HANDOFF §7，两个零上下文只读实例分别在干净clone复核实现提交`4a4e83467b6e250ac6875382daf565de950c9eae`，八道交接题均8/8；各自独立重算原合同指纹、完整快照，并追踪真实请求构造路径。两条文档发现已收窄或修正；两实例又在干净clone的`e360dfddd3b11fc0168972d886ece1e7efc0add9`回读，均确认无剩余交接阻断，详见[独立记录](INDEPENDENT_REVIEW.md)。独立实例没有重跑全量测试，也没有把合成请求当作真实模型效果。不会由角色提示词验收推导 A4、权限系统或整个 Agent 底座通过。

## 复现与回退

使用安装了 `services/agent-core[test]` 依赖的 **Python 3.12**，仓库根目录执行（Git Bash）；下列 `python` 须指向该项目环境。保护指纹中的AST以本次3.12生成，不用系统默认3.10解释器做版本混用对照：

```bash
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 python -B scripts/companion_prompt_snapshot.py
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 python -B scripts/harness_v1/unit.py test_companion_persona.py
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 python -B scripts/harness_v1/unit.py
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 python -B scripts/check_docs_consistency.py
pnpm build:desktop
git diff --check
```

原 unit 运行器在临时目录强制 Mock、禁 TTS/wake/MCP、指定不存在的私密配置路径，测试结果自动落在原 evidence/unit 下；发布材料只收录本次脱敏结果。不要改成对正式 Core 发送测试消息。

静态快照核对无需启动 Core，不读取配置或数据库；`--write` 用于重新导出当前提示词。`--freeze-contracts` 仅用于从修改前基线初次生成保护指纹，文件存在时拒绝覆盖，不能在检查失败时重写指纹来通过。

回退仅需在审阅变更后恢复基线 `783472060a52aae5e745ca60077347eb0943f184` 的 harness 提示词，并同步快照/人设意图测试；或撤销本次独立提交。没有 schema 迁移、生产状态变更或配置更改，不需要恢复数据库。勿用基线文件整体覆盖另一个含用户改动的工作树。

## 剩余验收与提示词外建议

- 待 ChatGPT 验收：八场景真实模型 A/B，以及多轮对话中是否自然、情绪是否合适、是否机械撒娇或过度亲密。单轮即便通过也不代表长期相处质量稳定。
- 未部署：正式桌面仍使用原实现，本分支不会自动改变当前天依的说话风格。
- 提示词外值得后续单独讨论：TTS 的情绪韵律与停顿、字幕/表情/动作时序、唤醒后的倾听反馈、用户安静意图与主动打扰策略的协调、记忆审阅入口。这里只列建议，本轮均未实施。
- 原 A4 通用回复核对器仍未接入，底座整体未关闭；既有任务、记忆、取消交界成果及旧真实模型证据保留。

交付停点：已 push，等待 ChatGPT 验收。
