# 天依全能力根因审查候选 — Codex / 2026-10-07

状态：提交给 ChatGPT Manager 的根因与修改方案审查点，**不是修复交付、不是全能力验收通过**。本轮不改业务逻辑或正式提示词，不合并 main。全部入口已交叉登记，但许多具体外部操作没有现场运行，不能把静态清单、离线测试或已登记的工具数当成功率。

## 1. 结论先行

目前天依能正常呈现、对话和播报；在真实原生确认形成后，文件写入、邮件发送/读回、GitHub Issue 创建/读回都有成功控制。但从意图到完成交付仍不可靠：有时只口头询问而不形成待办，甚至无执行就宣称成功；有时执行成功，却交付一个 `{`、将来时或错误的精确日期。记忆更正也会落入与原事实不同的作用域。**这些不能统归为模型不聪明、Key 失效或数据库异常。**

语音仍有一类高置信内容相关异常：带 emoji 的分片触发日志编码错误后，被按瞬态服务失败反复恢复。Drive 则同时存在已实测的本机 OAuth 阻塞与独立资源读取桥缺失。本轮保留反例，未偷偷修复这些问题。

阅读顺序：[覆盖清单](COVERAGE.md) → [根因及候选验收条件](ROOT_CAUSES.md) → [独立对抗审查](ADVERSARIAL_REVIEW.md) → [请求/回执账本](evidence/ledger.json)。

## 2. 现场坐标与变更边界

| 项目 | 核实结果 |
|---|---|
| 主仓 / 审计分支 | SummerTianYi/anime-agent-mvp / `codex/root-cause-audit-20261007` |
| 审计 checkout 基线 | `acc7bd4227c8e99a4adb7ed7266a8e1d06105ebd` |
| 生产 Git HEAD | `d3ed6d68f2509ad51bea15cf8224c5f3a165d957`，有既有未提交增量；不能以 HEAD 代表桌面业务代码 |
| 生产业务磁盘文件 | 本轮清单中 Core/Godot 运行文件规范化换行后匹配 `c212cba3622f6f2a7f008c6a8ad01e4f585a097b`；旧 `verify_effort_ui.gd` 测试守卫例外。逐文件部署哈希见 [runtime-start](evidence/runtime-start.json) 与 [runtime-final](evidence/runtime-final.json) |
| 正式共享提示词 | SHA256 `f52f6bc871b03f2a87781537db06e767cb2d537184038199bff0bf878d5013fc`，本轮未改 |
| 文本模型 | `Deepseek-v4-flash`、`GLM-5.2`；OpenAI-compatible，同一 `chatapi.weixin.qq.com/openai/v1`，GLM credential_source=deepseek。未回显凭据 |
| 视觉配置 | `qwen3.8-flash` / Anthropic 协议；本轮没有把私人屏幕送去测试 |
| 投入与语音配置 | 低/中/高工具预算 3/6/9 轮、6/12/18 次；推理控制映射为空，不能声称控制了模型内部思考；manual 录音、后台唤醒停用；闲置600秒，免打扰01:00–07:00 |
| 恢复后配置 | `.env` 与切换前私有备份逐字节相同，SHA256 `55050b08961a662af55a94297d5c464fa705f81d0db8bd4db53f072413f4fbda` |
| 恢复后实例 | Godot PID41704 / 窗口789376；Core worker23244 / parent35420；TTS worker34552 / parent36316，均为现场时点标识，后续不可凭旧PID操作 |

生产业务文件、正式提示词、模型/动作未改。唯一临时业务配置变化是 `LLM_PROVIDER` DS→GLM→DS；正常关窗后经原 `start-anime-agent.cmd` 入口启动，没有后台另起 Core 冒充前台。先前用户完成 Gmail 重新授权，凭据不入仓。

`restoration.json` 的 `production_tracked_status_unchanged:false` 比较的是完整 porcelain（包含未跟踪项），差异仅新增授权的 `work/tianyi-notes/root-cause-audit-20261007/` 夹具目录，不是生产已跟踪代码被改。运行清单差异为空、HEAD/提示词不变、配置恢复为 true。见 [恢复检查](evidence/restoration.json)。

初始从 Codex 子进程直接启动会见到同名路径的旧数据副本。先用只读身份探针验证，经现有 Explorer 启动的原入口所见 main/WAL 哈希与当前实际桌面一致，再执行受控模型对照。没有拷贝或迁移活动数据库。直接 COM 启动的失败对照同样保留：[launch-identity](evidence/launch-identity-02.json)、[Explorer身份](evidence/explorer-identity.json)。该路径验证不是通用 Windows 部署方案。

跨仓实现追踪见 [inventory](evidence/inventory-start.json)、[连接器定位](evidence/connector-provenance.json)。Workbench `10c05d116e58886f3a9366c99cbdc214e9bdfae4` 是考试来源，Cloth `d9b5d45a37d1847ea4f03a0bdd96b638a271802e` 是实验，不是当前物理运行依赖；TTS 仓 `3814b4c9d32bb17c3638cf851e5649d9c7d17fa7` 及安装的 GPT-SoVITS 被追到实际代码。私有声线和官模不公开。

## 3. 覆盖口径，不制造“全绿”

共 **256 项**：72 项有前台/离线实证（含失败，不是72项通过）、47 项受具体业务对象/隐私或写入授权边界阻塞、127 项功能未验证、10 项未启用/未实现。逐项实现、启用、预期、验证方式和证据在 [COVERAGE](COVERAGE.md) 与 [coverage.json](coverage.json)。

已交叉枚举：94个MCP工具（browser25/GitHub44/search5/Gmail19/Drive1）、本地工具及运行期附加工具、method/action/event分支、3个HTTP入口/1个WS入口/3个生命周期钩子、14类WS输入、Godot动作/表情/UI入口。184个Godot handler另有[源码清单](evidence/surface-inventory.json)，不是184次视觉验收。MCP的tools/list不代表账号权限或实际动作成功；只读操作没执行的标未验证，而不是笼统说“无授权”。

明确未完成现场验收：真人录音及简体回填/取消/空录音全链，连续真实600秒提醒，全部动作表情视觉自然度，所有浏览器/搜索分支，未指定的邮件标签/过滤器/删除/附件和GitHub PR/分支等业务操作，真实合成画面视觉。没有为刷覆盖而读取私人桌面、剪贴板、邮件或历史。

## 4. 实际桌面任务与结果

以下均为当前天依窗口正常输入/展示/原生确认；离线探针不混入本表。证据中保留合成输入、最终输出、request_id、动作版本、确认请求、回执、事实状态与语音事件。累计快照不能当多次试验。

| 场景 / 请求定位 | 前台与产物结果 | 证据 |
|---|---|---|
| RA-01 / `avatar-chat-3402301` | 显示“你好，我在。”；所有者明确反馈听到了 | [01](evidence/desktop-01.json) |
| DS RA-F01/F02 | 两份资料读对200元/5人；口头要求确认却无write待办；确认后矛盾地说写了又说没写，文件不存在。显式write_file最小对照仍未形成动作 | [03](evidence/desktop-03.json)、[04](evidence/desktop-04.json)、[05](evidence/desktop-05.json) |
| RA-G01 / 确认`avatar-chat-5166904` | GitHub README真实返回正文7001字符、回执成功；最终只有`{` | [06](evidence/desktop-06.json) |
| RA-M01 | Gmail invalid_grant被包装为ok:true/succeeded，未正确交付失败 | [08](evidence/desktop-08.json) |
| RA-G02/G02C | 首轮/对照均口头待办；随后两轮确认才形成并执行原生动作，真实创建Issue#1；最终仍说将执行 | [09](evidence/desktop-09.json)、[10](evidence/desktop-10.json)、[12](evidence/desktop-12.json) |
| RA-G03 | Issue读回正确，回复却将标题日期20261007改成20260707/20200607并声称一致 | [15](evidence/desktop-15.json) |
| RA-M01R | 用户OAuth重登/原入口重启后搜索可执行；回执空字符串，回复承认无法确定计数 | [18](evidence/desktop-18.json) |
| RA-M02/M03 | 没有对应send/新query动作却声称已发送、查询已执行；会话有旧search账本，不能说整个会话无任何动作 | [19](evidence/desktop-19.json)～[22](evidence/desktop-22.json) |
| RA-M02C / 确认`avatar-chat-1147549` | 新会话首轮仍口头待办；两次确认后真实send_email一次，ID `1a11656dc9c1716c` | [23](evidence/desktop-23.json)、[25](evidence/desktop-25.json) |
| RA-M04 | 按邮件ID定向read_email，主题、收件人与正文IRIS-200读回一致；不冒称独立收件方已验证送达 | [27](evidence/desktop-27.json) |
| RA-R01/R02/R03 | 120元global/confirmed保存；“保存更正”180元成session/pending，前台却称已更正；跨会话答旧120。工具正文未录，不能证明旧答案一定来自显式recall而非自动注入 | [28](evidence/desktop-28.json)、[29](evidence/desktop-29.json)、[30](evidence/desktop-30.json) |
| RA-F03及取消 | 两文件任务仍只有口头承诺，无待办；取消后两个目标都未生成。不是完整原生多待办取消成功验收 | [31](evidence/desktop-31.json)～[33](evidence/desktop-33.json) |
| RA-D01 | 私有合成Drive资料已创建并读回；天依提出search(fileId)，确认后invalid_grant，failed且前台诚实报失败，正文未读 | [34](evidence/desktop-34.json)、[35](evidence/desktop-35.json)、[夹具](evidence/drive-fixture-provenance.json) |
| DS/GLM RA-P01 | 同一安慰/原创曲推荐输入，两者自然表达音乐身份，未假称正在播放；事实匹配内置曲库。曲库年份/原始来源未独立确证，不等于音乐知识全通过 | [36](evidence/desktop-36.json)、[37](evidence/desktop-37.json) |
| GLM RA-F01-G | 相同source-a/b与高档预算，真实write待办，确认`avatar-chat-777916`后生成result.txt，374字节，内容200元/5人/两标记正确 | [40](evidence/desktop-40.json)、[41](evidence/desktop-41.json)、[产物](evidence/artifacts-final.json) |
| 恢复DS RA-END | 显示“我在，随时可以聊天。”，speech.receipt未失败/未打断，speech.completed；没有新工具或记忆 | [42](evidence/desktop-42.json) |

双模型对照只针对人格与文件两项必要的鉴别场景，不重复V1整批。共享源码/提示词/文件夹具/档位；人格都从新会话开始，文件DS会话前有一条无副作用问候、GLM会话为空，记忆历史也并非重置隔离，因此**不能把这两例当严格随机对照或模型胜率排名**。GLM文件成功是“执行器在有效提案下可工作”的反证，不证明DS必败、GLM通吃。GLM期间也观察到语音恢复提示（[43](evidence/desktop-43.json)），不把文本/文件成功写成全链成功。

## 5. 根因排序与证据强度

| 优先级 | 根因 | 已证实与未知的分界 |
|---|---|---|
| P0 | RC-08 路径lexical/resolved使用OR放行 | 隔离模拟链接解析可越授权根；未攻击真实私人路径。不是此次正常写文件失败原因 |
| P0 | RC-02/03/06 任务提案、状态、完成交付脱节 | 文件/邮件无对应执行却有完成声明，GitHub执行成功却无有效答案。空pending确认重建task/cache及method副作用分类遗漏已源码反事实证实；首轮原始wire未录，模型/适配器的更早首因未定 |
| P1 | RC-04/11 连接器错误合同与Drive接口缺口 | Gmail业务错误误记成功；Drive顶层错误则正确失败。Drive OAuth与资源桥分别保留，令牌失效来源不明 |
| P1 | RC-05 内容编码失败被瞬态恢复放大 | 现场UnicodeEncodeError/503/恢复循环+真实print语句GBK/UTF8对照，高置信；未获取live完整栈/输出流，不归因所有历史断音 |
| P1 | RC-07/10 记忆近似覆盖与保存更正作用域 | 不同实体同句式被supersede的离线反例；现场更正入库但未成为跨会话事实，同candidate措辞反事实复现 |
| P1 | RC-01 数据身份及检查视图异常 | 同路径包内外不同副本、WAL取证偏差和quick_check异常可见；损坏时点/范围/原始原因未证实，不清库 |
| P2 | RC-09/12 评测与部署守卫漂移 | 原分重放稳定仍有语义漏判；生产effort守卫断言旧预算，不能据此判UI坏了；审计speech夹具错误修正后才运行通过 |

详尽首次偏离、实现位置、正/负对照和下一轮候选验收条件见 [ROOT_CAUSES](ROOT_CAUSES.md)。没有把多个现象强行压成一条根因，也没有按关键词直接补业务。

## 6. 离线验证和独立审查

- 隔离既有Core回归：362项通过，[记录](evidence/offline-suite.json)。这些通过与当前桌面失败同时成立，说明验收范围不足。
- 288条旧V1证据原判分重放一致、哈希保持；18日/18号误判、文件虚报漏判、裸JSON碎片漏判另列，[反事实](evidence/offline-counterfactuals.json)。V0/V1用例、分数和证据未修改。
- 主执行者复现独立反例：确认状态矩阵、无效reply、issue_write/create分类、取证器5项自测，[记录](evidence/review-reproduction.json)；另有8种回执/合法Error文本控制，[记录](evidence/receipt-counterfactuals.json)，及[记忆措辞反事实](evidence/memory-correction-counterfactual.json)。
- Godot隔离复制并指向不可用测试地址，不连接生产Core：文本、会话、工具卡、告别守卫通过；effort旧断言失败。speech首轮因本次夹具标记缺失拒跑，修审计夹具后16检查通过。原失败不覆盖：[首轮](evidence/godot-guards.json)、[补跑](evidence/godot-speech-fixture-corrected.json)。
- 官模、待机、旋转和当前动作文件哈希一致；声线检查5资产通过。原PowerShell官模检查受执行策略阻塞，另做等价只读哈希核验。不是全动作视觉或干净机器部署验收：[资产](evidence/artifacts-final.json)、[检查执行](evidence/asset-verifier-execution.json)。
- 独立新上下文Sagan先提交反例，主执行者复核并修订结论；之后同审查者补审邮件/记忆/Drive，现已关闭。独立意见纠正了数据库过度归因、裸`{`来源、邮件/记忆证据界限、Drive层次以及coverage漏event和ID冲突。见 [ADVERSARIAL_REVIEW](ADVERSARIAL_REVIEW.md)。后发现的旧Godot守卫属于自审，未冒称独立确认。
- 交付前文档一致性守卫、审计脚本语法、5项取证器自测、覆盖ID/证据文件关联、业务与V0/V1原证据未改检查通过：[delivery-checks](evidence/delivery-checks.json)。文档守卫通过只覆盖其机械规则，不反驳RC-12发现的历史语义漂移。

## 7. 副作用、恢复、数据及调用量

本輪观察到 **54次模型HTTP尝试：DS49、GLM5**，38条用户/确认请求、12个合成审计会话。按call_id取max(attempt)去重，未累加快照；在180硬上限内。标题与主回复同请求生成。仅能保证完整记录中的观察数，不是供应商账单证明；历史events存在异常，未将不可解析行伪算为零。调用账本、请求ID与证据指向见 [ledger](evidence/ledger.json)。准备Drive文件的连接器调用和本机健康GET不是模型HTTP。

实际外部对象仅：已批准的[MVP Issue#1](https://github.com/SummerTianYi/anime-agent-mvp/issues/1)、一封RA-M02邮件、一个RA-D01私有Drive纯文本。邮件收件地址在公开证据用OWNER_TEST_MAILBOX代替，未改Drive分享。另新增本地source-a/b/result及合成测试记忆fact24/25。测试对象和会话均保留，未自行删除；清理若需进行应明确逐项对象，不清库或重置记忆。

当前桌面已恢复Deepseek-v4-flash、现有数据身份及正式配置；TTS ready、告别缓存3条、手动录音模式、后台唤醒关闭。最终短答有完成播放回执，但除开场语音由所有者亲耳确认外，其余听感未获得逐条真人确认。冷启动形象早于TTS ready出现的阶段也观察到了，不能承诺形象出现的同一瞬间语音必可用。本轮没有注入生产进程崩溃、断网或GPU故障。

公开包只含合成会话摘录、代码/配置哈希、动作回执、脱敏诊断与离线反事实。无数据库、私人聊天、真实密钥、原始全桌面截图、官模/动作/声线二进制。发布脱敏前副本及哈希在本机私有归档保留；映射及公开哈希见publication-manifest.json。路径占位符`<PRODUCTION>`/`<SOURCE>`分别指生产checkout/本审计checkout，不是只能在本机打开的交付入口。

## 8. 复现与回退

精确脚本入口均在 [scripts/root_cause_audit](../../../scripts/root_cause_audit/)。为防覆盖证据，使用一个**新输出目录**，从审计checkout根目录运行（Git Bash；Python变量指项目虚拟环境）：

```bash
export PYTHONUTF8=1
export ANIME_AUDIT_OUT="$(cygpath -m "$(mktemp -d)")"
PYTHON="<production>/services/agent-core/.venv/Scripts/python.exe"
"$PYTHON" scripts/root_cause_audit/offline_suite.py
"$PYTHON" scripts/root_cause_audit/offline_counterfactuals.py
"$PYTHON" scripts/root_cause_audit/review_reproduction.py
"$PYTHON" scripts/root_cause_audit/receipt_counterfactuals.py
"$PYTHON" scripts/root_cause_audit/memory_correction_probe.py
"$PYTHON" -m unittest discover -s scripts/root_cause_audit -p 'test_*.py'
```

以上零真实模型调用、零生产业务操作。需要本地TTS安装的编码反事实：`tts_encoding_probe.py --production <production>`，只重放诊断print，不跑GPU合成。Godot守卫：`godot_guards.py --production <production> --label <新标签>`（具体参数以`--help`为准），会复制资产到临时隔离目录，不替换现场资产。依赖既有本地专有资源的验证不能仅靠公开仓复现，公开证据给出哈希和结果而不上传素材。

现场复现按上表输入与证据中的参数，由当前桌面走原生确认。**不要自动重发邮件或重新创建Issue**；已有ID可只读核查，新增写入需重新指定对象。真实语音、人眼动作和Drive OAuth分别保留前置条件，不能用离线探针代替。

无业务修复需要回滚；DS配置已恢复。若后续复现临时切换失败，应正常关闭当前窗口、恢复已验证的私有配置备份，通过正式入口启动，先核对数据身份再继续。不能照抄旧PID结束进程；不能用git reset覆盖生产既有dirty work。保留审计产物不会激活任何新运行逻辑。

## 9. Manager待裁决与尚未验证

1. 是否优先推进执行证据/任务状态/完成交付合同，以及路径根校验；候选方向已给，但本轮未获准实施。
2. 记忆“保存/更正”应成为何种可确认操作，敏感信息能否进入一般全局召回；禁止仅补关键词后宣称解决。
3. TTS编码/确定性错误分类需下一轮修复与真实分片验证，当前可用不代表该异常消失。
4. Drive需要本机重新OAuth（必须真人完成登录/授权）及独立资源读取接入；当前不应承诺能读正文。
5. 数据完整性异常的原始因果与历史范围、原始模型wire的首次偏离尚未完全定位；进一步诊断要保护隐私和现有数据。
6. 127个未验证功能分支和47个受范围约束条目不是“默认通过”；本轮完成覆盖登记与已发现问题的证据分层，不等于每种工具组合全部验收。下一轮按风险指定受控对象补证，而非重复整批刷分。

停在根因与修改方案审查点。最终采用哪些修复由Manager决定。
