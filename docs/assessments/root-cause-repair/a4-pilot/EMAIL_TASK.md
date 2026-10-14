# 单收件人纯文本邮件：合成 Gmail 验收

2026-10-14，Codex。接手基线 `fb35fa14a4ef29364cd2ef495bbd8ced8b3a7fa8`，候选分支 `codex/root-cause-repair-batch01-followup-20261012`。实际 Git 根、HEAD、分支与用户坐标一致，接手时工作树干净。本报告只覆盖后台合成 Gmail；不代表真实发信、送达、已读、任意模型认证或 A4 整体关闭。未部署、未合并 main，当前 Godot/Core/TTS、生产数据和原阶段证据不变。

## 范围与实际接口

沿用仓内 [捕获的 Gmail schema](../../root-cause-audit/evidence/mcp-schema.json) 的完整 `send_email` 定义，没有为测试删减可选字段。缺少的成功回执信息只读本机已安装 `@gongrzhe/server-gmail-autoauth-mcp@1.1.11` 的源码补齐；没有启动连接器、读取 OAuth 配置或接入邮箱。[合同及源码散列](evidence/email-connector-contract.json) 记录了核对位置。

原生成功结果只有单个文本块 `Email sent successfully with ID: <原生ID>`；错误为单个 `Error: <错误信息>` 文本块，不含可供核验的收件人、主题、正文。产品从同一动作的已确认参数取得这些字段，从原生回执取 ID；测试端独立比对合成服务保存的邮件。受理回执不证明送达或已读。

## 复用与增量

- 复用真实 `handle_chat`、`agent_loop`、权限复查、原生确认票据、ActionLedger、失败/unknown 保存、结果交付补救及跨轮状态查询。没有复制聊天循环、降低授权或添加模式按钮；没有模型名称业务分支。
- 新增 `email_task.py` 窄适配，通过既有 `verified_task` 钩子约束单个地址及逐字主题/正文，只允许 `to/subject/body` 与可选 `mimeType=text/plain`。缺失或歧义参数要求澄清；未授权字段和错误内容在造票前拒绝。宿主交付完整正文和原生 ID，模型自报 chat、成功或送达均不能代替账本。
- Gmail 成功 envelope 必须带可核验的原生 ID；不识别的成功格式转为 unknown，不自动重发。正文里的 Error 不参与错误判定。
- 邮件默认 MIME 的省略与显式 `text/plain` 共享去重指纹；兼容既存显式默认参数的旧哈希，不迁移或覆写旧用户记录。
- `file_models.py --scenario email` 接入合成服务与邮件验收，复用已有配置白名单、隔离审计、互斥 HTTP 账本、请求前计数、45 秒超时及扩样门禁。每任务仍为 6 步、12 工具调用、1 次纠正；本阶段 40 次 HTTP 上限，完整案例预留 18 槽。

## 修前、修后及独立反例

修前同一自然语言任务可被错误地址、额外 cc/bcc、附件/HTML 或改写正文的模型调用造票；无调用的口头待办可直接展示；成功答复遗漏主题/正文；显式默认 MIME 还可绕开原参数指纹，生成第二张票据。首轮测试的两个可控 Provider 答复不足错误也单独保留，补齐替身答复后再记录业务失败，没有把测试错误充当产品失败。

修前 10 个测试方法中有 7 个失败（计 16 个失败记录，包含参数 subTest；0 errors），见 [修前证据](evidence/email-before.json)；替身答复不足的早期运行另见 [初始记录](evidence/email-before-fixture-shortfall.json)。首次模型验证前 Core **510/510** 全通过、0 跳过、0 模型请求，见 [全量回归](evidence/email-core-before-feedback.json)。其中文件、Issue、权限、确认、防重复、unknown、跨轮进度原回归均保留；没有重跑旧双模型样本。该全量绑定首次模型版本；下述反馈文案调整后另做定向复核，不能把它称为最终版本重新运行过的全量。TypeScript/Godot/TTS 不受本次代码影响，未启动相关进程检查。

独立 Python 审查通过真实 `handle_chat` 找到并保留以下反例，修后 **15/15** 通过，结论绑定完整业务源码散列：[01 自然措辞](evidence/email-independent-01-natural.json)、[02 扩展对抗](evidence/email-independent-02-expanded.json)、[03 改参顺序](evidence/email-independent-03-edit-order.json)、[04 正文改参](evidence/email-independent-04-body-edit.json)、[05 最终复核](evidence/email-independent-05-final.json)。

| 独立反例 | 实际修正 |
|---|---|
| “发封纯文本邮件”漏启用约束，错误地址可造票 | 补齐窄邮件命令的发送词形，并保留过去时闲聊和流程解释 |
| “请告诉我，发送邮件后多久算送达”被误拦 | 解释请求保持原回答 |
| 换收件人但新地址未解析，仍沿用旧地址 | 明确改值却缺失参数时清除旧约束并澄清 |
| 新地址写在主题之后被漏读 | 从正文前完整参数区取地址，屏蔽引号中的主题数据 |
| 正文改参未解析，旧正文仍可造新版票据 | 未取得新字面值时撤销旧正文约束并澄清 |

同组正常对照覆盖正文/主题中的 Error、取消、确认和伪消息 ID、文件正文里的邮件命令、普通聊天、流程解释、旧显式 MIME 票据确认、重开后的 UNKNOWN、跨任务/会话回执隔离。未给任何模型预置正确意图。

运行器独立复核 **38/38** 通过。首次发现捕获 schema 文件未纳入冻结指纹，现已纳入既有 `protocol_runner_hashes`；实际 schema 内容不变。证据：[修前](evidence/email-runner-review-before.json)、[修后](evidence/email-runner-review-after.json)。包含首轮/扩样门禁、计数、40 次封顶、18 槽预留、隔离和全部 12 个验收判据的失败对照。它没有新建预算平台或改变每任务预算。

两份最终离线完整样例各 **12/12** 通过：[样例一](evidence/email-offline-final.json)、[样例二](evidence/email-offline-variant2.json)。原文件/Issue 报告、原中断和连接失败继续保留；此前文档导入造成的默认数据库影响仍为未知，本轮没有打开、恢复或修改该数据库。

## 首次模型偏离与最小反馈调整

首个 DS 样例使用 2 次 HTTP，未通过，见 [原始失败](evidence/email-live-ds-1.json)。模型将正文的行首标签当作说明删掉，宿主逐字校验正确拒绝，零票据、零派发、零邮件；第二轮模型给出无真实引用的 report 并要求用户重述，宿主交付未完成。[独立证据核对](evidence/email-runner-review-first-live-failure.json) 11/11 通过，证明失败记录与空副作用一致，**不表示该任务通过**。

只调整 `email_task.GUIDANCE` 和同一参数校验的错误反馈：强调行首标签也是正文，指出不一致字段和首处字符差异，让模型在已有一次纠正内提交真实调用。没有填写工具参数、修改判据或延长预算，也没有固定地址、主题、正文或模型名称分支。首次失败和已消耗的 HTTP 1–2 保留，新版本验证单列。

该文案调整后的邮件定向回归 [25/25](evidence/email-feedback-regression.json) 通过；独立审查随后补充真实入口的“错误调用→差异反馈→正确调用→唯一票据→确认一次受理”行为对照，最终 [16/16](evidence/email-independent-06-feedback.json) 通过，`corrections_used=1`。当前 Core 共 511 个测试，之前 510 项全量保留原版本含义；交接发现的最终全量缺口已通过下述511项实际运行补齐。其余公共业务文件与该全量版本完全一致。最终 `email_task.py` SHA256 为 `4f059774e5e2128b4c02912553e49e3b7b13e4626a5ebb05d0a6ac645ecf8438`。

## 双模型逐例结果与预算

最终业务源码、工具 schema、45 秒连接超时与任务预算冻结后，DS/GLM 首例都通过才开始变更参数的第二例。四例全部从新目录、空会话、空账本、空合成邮箱开始；发送前展示真实票据，测试只对参数正确的票据输入正常“确认”。没有真实邮件调用，也没有追加任务指令或手工拼装动作。

| 运行 | HTTP 索引 / 次数 | 真提案 | 仅受理一次 | 邮件参数一致 | 准确回执交付 | 全部判据 |
|---|---|---|---|---|---|---|
| [原 DS 首例，反馈修正前](evidence/email-live-ds-1.json) | 1–2 / 2 | 未形成 | 零发送 | 正文改写被拒 | 明确未完成 | 未通过，原失败保留 |
| [DS 首例，最终版本](evidence/email-live-ds-1-feedback.json) | 3–6 / 4 | 通过 | 通过 | 通过 | 通过 | 12/12 |
| [GLM 首例](evidence/email-live-glm-1.json) | 7–10 / 4 | 通过 | 通过 | 通过 | 通过 | 12/12 |
| [DS 第二例](evidence/email-live-ds-2.json) | 11–12 / 2 | 通过 | 通过 | 通过 | 通过 | 12/12 |
| [GLM 第二例](evidence/email-live-glm-2.json) | 13–15 / 3 | 通过 | 通过 | 通过 | 通过 | 12/12 |

最终同源四例 **4/4**，不同版本的原失败单列；不是把全部历史改写成4/4。DS最终首例仍先删掉正文标签，但在第3次HTTP的明确差异反馈后，第4次提交正确调用，使用原有一次纠正额度。确认后第5次再次提出相同发送调用，ActionLedger复用成功回执，合成服务仍只有一封邮件；不是由夹具去重。

每例12项均检查：确认前零副作用、真实正确提案、恰好一次受理、参数逐字一致、任务/参数/原生ID回执关联、完整交付、重复确认零重发、进度真实、消息历史重开、动作账本重开、合成邮箱重开、源码不变。成功交付包含收件人、主题、完整两行正文和原生ID，并限定为“发送请求已受理”。合成邮箱的每例ID由各自空服务产生，跨例相同ID不能替代会话、任务、参数和回执关联。

[本阶段HTTP账本](evidence/email-http-ledger.json)记录实际 **15/40** 次，含首次失败的2次；剩余25次未使用。没有纯连接补验，没有隐藏协议探测或预算外重试。所有模型调用已停止。导出只替换测试路径并使用仓库LF换行，不改变结果；[导出清单](evidence/email-export-manifest.json)保留原始与发布JSON的SHA256，原本机失败和旧阶段证据不改写。独立审查中的原始文件SHA按本机原字节记录，Git发布文件按固定提交的blob核对。

独立最终[只读证据复核](evidence/email-runner-review-live.json) **55/55** 通过，审查新增HTTP为0；对四例新测试库使用只读连接核验持久消息、动作、事件和邮箱，对照全部HTTP编号1–15及源码/schema/预算。另发现GLM在第9、14次HTTP也实际重复提出同参发送，均只有一次真实派发。证据的 `all_current_tasks_passed=true`，而纳入旧失败的 `all_tasks_passed=false`，两者保留各自含义。产品与运行器独立审查均无本范围未解决阻断。

[发布前核对](evidence/email-publication-check.json)确认Git blob业务字节与最终模型记录一致、19份导出SHA可核、原阶段报告与证据不变，暂存内容无凭据/数据库/超50MB文件。隔离文档检查返回 `DOCS_CONSISTENCY_OK` 与 `DOCS_ISOLATION_OK`，`git diff --check` 通过。

业务、测试及模型证据提交为 `e32e57cbbd5e9ff10ff4573c0fb719e9ef9186ad`。按仓库白纸交接要求，两位零上下文实例只读该提交的干净clone，八问均由主执行者评分8/8；[交接记录](evidence/email-handoff.json)保留各自答案、证据核对及门禁缺口。它们指出全局文档的旧Idle/UI状态与归属表述存在漂移，本次邮件修复没有扩大到这些旧文档问题，不将全仓文档描述为无矛盾。

两位检查者都指出最终版本尚无全量记录，故在源码冻结不变的前提下，用原隔离入口新建测试目录补跑 [最终Core 511/511](evidence/email-core-final.json)：0失败、0错误、0跳过、0模型请求。该记录与最终四例业务源码散列一致，覆盖公共机制以及受影响的文件/Issue回归；未重跑任何旧模型样例。原510、定向25及独立16的记录仍保留。后续收尾提交只增加文档与证据，停在Manager验收，不部署或合并main。

白纸检查者随后独立只读核对新增全量JSON与原干净clone，27/27源码散列相同，确认511项结果与零模型调用记录，撤销该门禁缺口。最终[发布检查](evidence/email-publication-final.json)另核对20份导出及收尾暂存文件，原发布前检查保留。当前本邮件范围无未解决阻断；旧文档漂移、其他A4问题和真实邮箱验收仍不在通过范围内。

## 复现入口

使用现有隔离 Python，Git Bash：

```bash
PY=../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py --source-root . --data-dir D:/TianyiRepair/email-repro/core --output D:/TianyiRepair/email-repro/core.json --pattern 'test_email*.py'
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --scenario email --source-root . --offline --variant 1 --data-dir D:/TianyiRepair/email-repro/offline --ledger D:/TianyiRepair/email-repro/offline-http.json
```

所有目录必须全新；不能指向生产库或恢复旧任务。真实模型入口删除 `--offline` 并添加 `--private-config ../tianyi-repair-batch-01/.env --provider deepseek|glm`，只读取连接白名单字段，工具仍为合成服务。使用同一个本阶段 `--ledger`；variant 2 必须提供两个同源、同 schema、等价初态且通过的 variant 1 `--initial-report`。不能重跑已通过样本或重置账本刷成绩。

合成任务一：`qingzhu@example.invalid`，主题“青竹合成回执 175”，正文两行“第一行：Error 是正常正文”和“第二行：蓝桥 42kg”。任务二更换为 `lanqiao.29@example.invalid`、主题“蓝桥第二次核验：7月12日”、正文“请保留原句：取消订单是测试文字”和“完整末行 READY 902，长度3cm”。测试只发送原始任务及正确票据的“确认”，不替模型补参数或调用工具。

## 边界

本适配只覆盖明确的单收件人、逐字纯文本邮件任务，歧义参数要求澄清，不推断联系人地址。不包括抄送、密送、附件、HTML、群发、草稿、回复线程、任意自然语言意图或真实 Gmail 验收。其他 A4 首轮无票据假声明、只读摘要夹带写入等开放项继续登记；本范围的通过不关闭这些问题。TTS 固定版本 `969f4e293a8abbf4b8f153e8551b2fbff93098bf` 未变。
