# 记忆更正与操作取消交界补修

接手提交 `9b1ad2b7de48be4c8436e8151013085cb54fe1a3`，工作树起初干净，沿已授权分支 `codex/root-cause-repair-batch01-followup-20261012` 完成。本轮只补操作取消与记忆入口的交界，不扩展记忆解析，不重构内核。

**本交界通过，明确记忆更正阶段具备收尾条件。** 这不表示 A4 或底座整体通过；通用回复核对器仍未接入，全部阶段阻断处理后的同一冻结版本统一验收仍待执行。本轮没有部署或合并 main，没有操作生产数据或当前 Godot/Core/TTS，没有真实模型或外部业务请求。

## 原反例与实际副作用

初态由测试自行构造：MemoryStore 已保存“晨星预算120”“暮云预算180”“用户喜欢蓝色”；当前会话有合成发送服务的待确认票据。请求经实际 `handle_chat` 进入，不直接调用分类函数代替集成链路，也不预填事实 ID。

| 输入/安排 | 修前实际结果 | 修后实际结果 |
|---|---|---|
| `取消刚才的操作，晨星预算更正为175。` | 仅回复记忆澄清；票据仍为 awaiting_confirmation | 票据持久状态 cancelled，回复取消结果及记忆澄清 |
| `晨星预算更正为175；取消刚才的操作。` | 同上 | 同上 |
| 两种语序各配一条先到的排队确认：持有 chat_lock，确认排队，再接收取消，最后释放锁 | 释放前票据仍 awaiting_confirmation；释放后各产生 **1次合成服务调用** | 释放前已 cancelled；释放后均 **0次合成服务调用**，旧精确票据不能执行 |
| 单独 `取消刚才的操作。` | 正常取消 | 正常取消，记忆不变 |
| 单独 `晨星预算更正为175。`，以及“改为／改成”控制 | 原记忆功能正常 | 保存并读回后回执；待办及票据保留，新会话可召回新值 |

修前15项中9项失败、6项通过，见 [修前入口证据](evidence/memory-followup-red.json)；176项既有相关基线全过，见 [基线](evidence/memory-followup-baseline.json)。这证明现有回归漏掉了组合交界。上述发送计数来自审计隔离夹具的内存副作用记录，**不是发生过真实邮件误发的声明**；夹具禁止外部连接、生产数据库和真实服务调用。

复合句的记忆部分仍按原规则澄清，三个事实保持原值，不把取消语句拼进新值。两种原例的修后答复为：

> 当前会话的1项待确认操作已取消，未执行；旧确认票据已失效。
>
> 尚未更正。请明确要更正的对象、属性和新值；一次更正一项已有记忆。

这是取消成功、记忆未改的真实组合回执，不把“取消成功”误报成“记忆已保存”。随后单独明确更正继续使用原事务、旧版本及作用域校验。正常更正／跨会话、写入失败、重放、迟到旧版本及历史召回等旧确定性测试全部保留并重跑。

## 代码与决策边界

业务改动仅在 [main.py](../../../../services/agent-core/agent_core/main.py) 和 [actions.py](../../../../services/agent-core/agent_core/actions.py)：

- `handle_chat` 在等待锁之前独立识别完整取消分句，不再因 `correction_plan` 存在就一律设为 other。取消按既有账本落库、撤销票据并阻止对应任务继续提出操作，然后才进入锁内的记忆处理。
- 锁内记忆路径把账本取消结果与 `correct_fact` 的实际结果一起交付，失败或澄清也不会丢弃取消回执。已派发的动作只说明“已经派发，未撤回或回滚”，不改成 cancelled，不重试或伪造回滚。
- 引号、代码及明确冒号正文是数据。未加引号的明确正文延续到消息尾；有闭合引号则保留引号外的独立命令。引用路径在锁前、锁内使用同一受保护控制文本，原用户文本仍完整进入消息和记忆审计。
- 取消匹配完整命令及当前操作指代；“不要取消”、记忆的新值、引用、错误命名对象不因出现取消字样撤权。记忆“改为／改成”不重新归入操作改参。
- 对“邮件／文件”核对动作工具类别，只取消匹配集合。`ActionLedger.cancel` 新增可选 `action_ids` 过滤，未传时保留原语义。旧任务邮件取消不会阻断当前文件任务，其他会话的账本与票据保持不变。

没有修改存储 schema、MemoryStore 事务、更正来源/历史、敏感与 pending 规则、会话可见性、召回、旧值比较、权限引擎、Provider 或前端事件契约。新增 `permission.declined` 审计记录实际取消票据与已派发动作 ID，不用模型生成执行结论。

## 一次独立差异审查与处置

独立审查者未参与初始实现，新增未用于修改代码的改述、错误对象与数据边界反例。首次10项5失败，保留原成绩；完成定向修补及防过修控制后，冻结源码12项全过，未解决发现为0，结论 APPROVE，仅限本交界。

| 独立反例 | 首次发现 | 处置与最终结果 |
|---|---|---|
| `晨星预算更正为175；请取消刚才那项操作。` | 仍待确认 | 补完整指代，持久取消 |
| `晨星预算更正为175；刚才那封邮件不要发送。` | 排队确认造成1次合成发送 | 支持对象前置否定执行；锁前撤权，最终0次副作用 |
| `晨星代号更正为以下内容：启航；取消刚才的操作。` | 数据末句误取消 | 正文边界保护，账本和事实均不改 |
| 文件待办 + `晨星预算更正为175；取消邮件。` | 误取消文件 | 按工具类别选择撤权集合，文件保留 |
| `资料原文：取消刚才的操作；晨星预算更正为175。` | 原分类路径把引用当指令 | 修锁前/锁内同源控制文本；该缺口原已存在，不归为本次新增 |

新增控制还覆盖：引用引号外的真实取消仍生效、否定取消、错误命名对象、跨会话、派发后 unknown 不声称撤回、旧任务邮件取消后当前文件精确票据仍执行一次。见 [独立逐轮证据](evidence/memory-followup-review-runs.json) 和 [最终独立结论](evidence/memory-followup-independent-conclusion.json)。中间11项通过属于中间源码，最终结论绑定下述冻结 hash。

## 最终定向回归

冻结源码下 **250项通过**：存储19、记忆95、Harness73、待办13、会话可见性4、WebSocket3、通道互斥12、交付4、权限11、原流程交界16。其中记忆95包含原66、主回归17和独立12，不重复累加审查运行次数。当前可发现631项，未执行631项全量。见 [最终回归](evidence/memory-followup-final-regressions.json) 与 [主回归修复过程](evidence/memory-followup-primary-green.json)。

主回归除两种语序及排队副作用外，覆盖单独取消/单独更正、“不要取消”、引用及记忆内容、歧义、保存失败回执、其他会话、已派发进行中/已成功、两种对象过滤和剩余精确票据执行；既检查内存账本，也 SELECT 读回存储票据，最终回复从真实 `chat.response` 核对。已派发场景通过合成服务的事件屏障固定时序，不靠猜测休眠窗口判断是否已经执行。

业务冻结 SHA256：

```text
main.py     ae4e1a3e0be7e5cae89cf3b79c3e18e63f9760d179d29c6c494dfd3f2e624904
actions.py  b85c51f46967436d3093508a61ac8085db9a3727a9341b1d638f4cd6cb24e894
```

文档发现数量/接口清单检查返回 `DOCS_CONSISTENCY_OK` 与 `DOCS_ISOLATION_OK`；变更 Python 编译、`git diff --check` 和暂存凭据/数据/大文件检查通过。发现数量不是全量执行成绩。

## 既有成果、兼容与回退

[MEMORY_CORRECTION.md](MEMORY_CORRECTION.md)、既有 DS/GLM 六序列、真实进程退出/重启证据、原模型失败及展示限制全部保留，没有覆盖旧证据。`storage.py`、`memory_correction.py`、原模型运行器及其他业务模块逐文件与接手版本比对，见 [保留核对](evidence/memory-followup-preservation.json)。本轮没有重复 DS/GLM、进程重启或旧文件/Issue/邮件真实模型样例；新增真实请求为 **0**。原六序列属于原冻结版本证据，加上本次受影响回归支持记忆阶段收尾，不冒充本次对新版本做过全量模型重验。

本轮没有数据库迁移，取消仍使用原 harness_actions 持久状态，新增过滤参数对原调用兼容。代码回退可恢复接手版本的 main/actions，但会恢复本报告的取消缺陷；已取消票据不得因回退复活，不能通过恢复旧数据库撤销账本历史。没有执行生产回退或数据恢复。

仍有边界：未支持任意复合记忆解析或任意指名业务对象取消；无法可靠定位时保留数据并澄清，明确邮件/文件只按已登记工具类别匹配。已经派发的业务不具备撤回/回滚能力。旧报告中的模型展示降级与 get_time 夹具失败、通用回复核对器采用失败及 A4 阻断继续保留。

## 可复现入口

使用既有隔离 venv 的 Windows Python，在仓库根目录的 Git Bash 下执行。`<fresh-data>` 和 `<fresh-report.json>` 必须使用新建测试路径；运行器拒绝覆盖旧证据，默认 Mock、关闭 TTS/wake/MCP，不启动真实 Core 服务。新测试复用带 I/O 审计拒绝器的内存 MemoryStore 和合成服务。

```bash
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py --source-root . --data-dir <fresh-data> --output <fresh-report.json> --pattern 'test_memory_cancel*.py'
# 受影响组分别使用新目录运行：
# test_storage*.py, test_memory*.py, test_harness*.py, test_pending_status*.py,
# test_session_visibility*.py, test_main_ws*.py, test_channel_exclusivity*.py,
# test_followup_delivery*.py, test_permissions*.py, test_baseline_closure*.py
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B scripts/check_docs_consistency.py
```

主测试为 [test_memory_cancel_boundary.py](../../../../services/agent-core/tests/test_memory_cancel_boundary.py)，独立测试为 [test_memory_cancel_review.py](../../../../services/agent-core/tests/test_memory_cancel_review.py)。修前行为可从接手提交导出独立源码目录，保持当前测试目录，传入 `--source-root <baseline-export>`；独立审查夹具同时设置 `HARNESS_REVIEW_CORE_ROOT=<baseline-export>/services/agent-core`，避免误用当前源码。

证据只包含合成事实、合成 `.invalid` 对象、脱敏回执、检查结果和源码 hash；库、原始日志、凭据不入仓。原始 JSON 与发布 JSON 的不同 hash 分别记录于 [证据清单](evidence/memory-followup-manifest.json)，不将脱敏件冒充原件。
