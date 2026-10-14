# 三条基础流程交界收口

日期：2026-10-14。接手基线：`601b81e8a22c381eaa580759cff9ee14003aa443`；分支：`codex/root-cause-repair-batch01-followup-20261012`。实际 Git 根为 `D:/UserData/Administrator/Documents/Codex/2026-10-12/tianyi-repair-batch01-followup`，开始时 HEAD 与基线一致、工作树干净。

**新增交界检查通过，但本轮整体通过条件未满足，暂不能冻结为基础操作内核已通过的候选。** 文件、Issue、邮件在所测自然语言入口、会话和 Provider 替换状态下共用内核运行正确；原 A4 的通用自由正文虚假完成仍是 HIGH 阻断。已完成本轮局部修正、定向回归及一次独立差异/证据复核，停在 Manager 验收。没有部署、合并 main、真实模型请求或真实外部业务调用。

本报告不覆盖已有单流程验收：[文件补验](FILE_TASK_SUPPLEMENT.md)、[Issue 补验](ISSUE_TASK_SUPPLEMENT.md)、[邮件](EMAIL_TASK.md)继续有效；原失败、预算中断、连接超时和各轮通过率保持原样。它们不是任意 Provider 认证，也不证明真实 GitHub 集成、发信、送达或已读。

## 1. 实际复用与修改

仍使用实际 `handle_chat`、`verified_task`、三个窄适配、权限引擎、已展示票据、ActionLedger、ResultPages 和共同交付出口。没有复制聊天/授权循环，没有改提示词、工具 schema、每任务预算、账本/存储机制或运行器，没有按模型名称加入分支。合成 GitHub、Gmail 复用原夹具及捕获 schema，文件真实写读专用测试目录。

业务仅改两处：

- `verified_task.py::proposal_error`：文件任务不能为无关业务的写入/未知副作用调用造票。读取性质复用现有 `tool_effect`，已核实只读工具仍走原权限；不因文件待办存在而封禁用户另行明确要求的只读查询。
- `main.py::_handle_chat_locked`：原“继续”控制分支识别完整的前任务指代命令，例如“继续处理刚才的任务”“麻烦接着完成刚才的事”。有待办时把真实票据带入现有交付校验；成功/unknown 后继续仍沿用原 task id、账本和剩余预算。此输入不构成确认。普通聊天、解释及引用控制词的句子不匹配该完整命令。

源码散列：`main.py` = `4165ad519e9ecdc56041782567cf0fbeaf306682bc64de557f48d91f4c16932e`；`verified_task.py` = `bfed72f352530e03060c96fd0b5df570a4f138e8148f076df48d2f02d5538dc7`。全 Core 清单和基线比较见 [manifest](evidence/baseline-manifest.json)；相对邮件最终 511 基线，仅这两个业务文件变化。独立复核绑定同一源码及业务 diff。

## 2. 首次偏离及处置

| 首次证据 | 首次偏离 | 修正与最终状态 |
|---|---|---|
| [原基线 9 项](evidence/baseline-before.json)，1 失败 | 邮件成功后新建文件任务，替身重提旧 `send_email`，文件适配未拦住，生成第二张无关邮件票据。尚未确认，所以没有第二次发送 | 限制文件任务的无关写调用；最终无新票据/发送，文件任务明确未完成 |
| [局部修正后 10 项](evidence/baseline-after.json)，1 失败 | 保留待办时更换无工具 Provider，输入“继续”，`mode=chat` 的假完成直接显示 | 继续分支携带真实待办进入交付校验；原票据/预算不变 |
| [独立首轮](evidence/baseline-independent-before.json)，6 个功能方法中 4 个失败（共 10 条 subtest 失败） | 较长的继续措辞仍绕过短语匹配；success/unknown 的 task id、预算被重建，success 可再造重复票据；初版文件白名单误挡正常只读 Issue | 完整前任务指代命令进入同一继续分支；文件工具限制复用只读性质分类，恢复 ASK 读取。独立最终 6/6 通过 |

独立首轮另有 2 个既有 A4 诊断观察，**不计入功能通过**，也不将“缺陷仍存在”留作回归成功断言；旧反例及 trace 保留。首跑只读数据库比较曾依赖行顺序，后按 action_id 比较修正夹具，未计作业务缺陷。中间 [10/10](evidence/baseline-after-continuation.json) 并非独立反例修正后的最终证据。中间 file-regression 在业务文件变动前启动、结束时才采样 hash，明确排除；已用冻结代码的 file-final 替代，没有覆盖旧记录。

## 3. 交界与 Provider 替换结果

| 新增检查 | 真实状态与副作用判据 | 结果 |
|---|---|---|
| 同会话文件 → Issue → 邮件 | 三个 task id；文件逐字内容及真实 read_file、Issue 同目标后置读取、邮件 native ID 各归其任务；库重开仍一致 | 通过 |
| 旧成功/外任务引用冒充下一任务完成 | 替身自报 chat、旧 action/read refs 不产生当前任务完成；不替模型补调用 | 通过 |
| 两会话同时待办 | 交换票据确认拒绝、预算不变；有效展示票据只执行所属会话动作一次 | 通过 |
| 跨会话取消、改参、旧版本确认 | 撤销只作用于对应会话；新版本单独展示确认，另一个待办保留 | 通过 |
| pending 更换 Provider | 任务/参数版本/授权与预算保留；进度真实；普通聊天仍正常 | 通过 |
| success 更换 Provider | 重复确认、继续及重复工具调用复用成功记录，不重写/重发、不充值 | 通过 |
| unknown 更换 Provider | 合成写入已发生但回执丢失；保持 unknown，重复调用不派发，预算不重置 | 通过 |
| 无关跨流程重复调用 | 邮件调用不能混入新文件任务造票；文件尚未执行 | 通过 |
| 聊天、解释、必要澄清 | 正常文本可交付，缺必要参数明确澄清，零额外副作用 | 通过 |
| 无工具 Provider | 明确继续既有待办时假完成被真实状态替代；恢复支持工具的 Provider 后原任务仍可正常确认完成 | 通过 |

[主执行最终 10/10](evidence/baseline-boundary-final.json)及 [独立最终 6/6](evidence/baseline-independent-final.json)。独立的额外正常对照包括音乐续聊、解释/引号句，以及文件待办时另行请求 Issue 只读：真正展示并确认读票据后取得标题，原文件仍待确认。测试没有给宿主预置正确意图、授权、动作或结果；可控 Provider 仅返回正常模型接口输出，回执来自实际文件工具/合成服务。

这只验证现有 Provider 接口的依赖替换。既不开发运行时热切换，也不证明任意自然语言均能正确分流。明确新任务仍可取得新预算；替换 Provider 本身、继续旧任务和重复确认不能充值。新业务需求在已有 pending 时如何排队/切换不是本轮新能力，未扩大判据。

## 4. 验证范围与复现

最终源码新增 16 个功能测试、受影响旧测试 148 个全部通过；旧 511 全量结果引用 [email-core-final](evidence/email-core-final.json)，其中未受影响的 363 个本轮复用。当前可发现 527 个测试，**本轮没有重新执行全部 527，也没有重跑旧真实模型样例**。

| 冻结源码下重验 | 结果 |
|---|---|
| 文件 | [20/20](evidence/baseline-file-final.json) |
| Issue（含原独立反例） | [34/34](evidence/baseline-issue-final.json) |
| 邮件（含原独立反例） | [26/26](evidence/baseline-email-final.json) |
| 已有待办状态 | [13/13](evidence/baseline-pending-final.json) |
| 票据/权限/预算 Harness V1 | [55/55](evidence/baseline-harness-final.json) |

全部使用原 [隔离运行器](../batch-01/repro/followup_regressions.py)，导入 Core 前设置独立 data/config、Mock、禁 TTS/wake/MCP。持久合成数据位于 `D:/TianyiRepair/baseline-closure-20261014`；未打开生产库、私人配置或当前服务。原文档检查缺失隔离导致的**旧数据库影响未知**记录继续保留，不能由本轮通过消除。

在候选仓根通过 Git Bash 运行（每次须换一个不存在的隔离目录和 output；原证据只读保留）：

```bash
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 \
  ../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe -B \
  docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py \
  --source-root . --data-dir D:/TianyiRepair/baseline-closure-repro/new-run \
  --output D:/TianyiRepair/baseline-closure-repro/new-run.json \
  --pattern 'test_baseline_closure*.py'
```

两份测试文件在 `services/agent-core/tests/test_baseline_closure{,_review}.py`。旧受影响组依次用 `test_file_task.py`、`test_issue*.py`、`test_email*.py`、`test_pending_status.py`、`test_harness_v1*.py` 替换 pattern；没有新建测试/预算平台。原缺陷复现以保存的 before 源码 hash、输入、输出、动作和副作用为准，不在旧任务上拼装状态。

最终文档检查通过 `DOCS_CONSISTENCY_OK`、`DOCS_ISOLATION_OK`，发现527项与当前文档一致；`git diff --check` 通过。没有改前端/资产，不重复 Godot、前端或当前服务检查。运行器、提示词、schema、旧模型证据和 HTTP 账本均未修改，本轮新增 HTTP 为0。

[完整合成 trace 包](evidence/baseline-traces.json)保留首次失败、两处原 A4 观察及最终每轮请求/答复/账本/服务副作用；只含自备合成数据，不含数据库或凭据。[独立历史复核](evidence/baseline-independent-history.json)确认最终 10 库，[独立差异复核](evidence/baseline-independent-review.json)确认其 6 库，均以 `mode=ro&immutable=1` 重开，动作、消息和事件可关联且库字节未变。中间 10 库复核另列，不冒充最终源码。独立复核只有本次一轮及其反例回验，没有重新做白纸交接。

证据 JSON 的 SHA256 对应本机原始文件字节；仓库 `.gitattributes` 将文本换行规范化为 LF，远端回读使用固定提交的 Git blob ID 核对，不能把换行差异当成试验数据变化。源码散列另按运行时实际文件保存。

## 5. 既有根因的当前归类

依据已有 [根因收口](../../root-cause-audit/closure/REPORT.md)、[第二轮根因](../../root-cause-audit/round-02/ROOT_CAUSES.md)、[首批修复](../batch-01/REPORT.md)和当前代码核对；已明确问题未重新跑真实采样，也未开启全产品审计。下表“关闭”限已经有证据的具体路径，不能扩大到整个类别。

| 类别 | 当前结论、位置与影响 |
|---|---|
| 已关闭的局部控制缺陷 A1/RC02 | 无票据确认不造任务/充值、票据版本/会话归属与拒绝改参、已登记进度查询已修；本次补齐所测继续问法及文件跨业务造票漏口。依据 PENDING_STATUS、现有账本回归及本报告；不是所有自由正文已可靠 |
| 已关闭的局部回执缺陷 A2/RC20 | 成功动作后的模型超时/坏回答仍交付持久回执，失败和 unknown 不冒充成功；三条窄任务当前回归保持。`main.py` 共同出口和 `actions.py` 原机制未被重写 |
| 已关闭的合同子集 B1/RC04/RC06 | GitHub method 分类、Gmail 已知 Error envelope/空查询和发送 native ID、邮件 Error 正常正文保留；Issue 后置读代次、字段保持和文件真实读回有原验收。本轮未变 schema/连接器合同 |
| 已关闭的物理路径子集 E1/RC08、D1/RC05 | 物理根比较堵住原 junction OR 放行；不等于证明所有并发路径替换安全。TTS 确定性编码故障分类保留固定版本 `969f4e293a8abbf4b8f153e8551b2fbff93098bf` 的旧证据；本轮不验证声线/播放 |
| **基础操作内核冻结阻断：A4，HIGH** | `task_delivery.py::validate_decision` 仍允许无当前操作证据的 `chat.reply` 直接显示，且合法 read_ref 的 `report.reply` 可夹带假写入声明。原 `REPORT.md` / independent-final 反例保留；本次独立诊断仍看到整理文件假完成、只读文件却声称改了 Issue（账本无对应写动作）。这是事实性交付漏洞，未证明授权绕过或真实误写，不能降级为文案优化。三个窄适配通过不能补足该通用入口 |
| **数据正确性阻断：C1/RC07/RC10** | `harness.py` 记忆晋升及 `storage.py::add_fact` 仍以作用域/词法相似度处理更正，缺实体/属性替换约束；旧证据显示跨会话仍召回旧值、复合条目替换单位不可靠。`memory_retrieval.py` 补召回覆盖不等于更正安全。不能因本轮合成初态无记忆而宣布数据内核通过；不访问真实记忆重验 |
| **生产/数据阻断：RC01 与隔离事故影响** | 历史路径身份分歧、事务快照损坏与非法时间戳，以及旧 docs 检查默认库影响未核验仍未解除。当前 `check_docs_consistency.py` 隔离入口已修且沿用，但不证明历史库健康；接回生产库之前须在另行授权范围内完成身份/健康/恢复核验 |
| **生产时序阻断：A3** | `tools.py::execute_tool` 的 `wait_for(to_thread(...))` 超时不能停止已派发 worker，现有 unknown 防重放有效但缺迟到结果对账；旧 post-dispatch-probe 已证明可能稍后落盘。`main.py::_task_state` 内存任务合同/预算不等于进程重启可恢复。账本/历史可重开不代表任务计划自动恢复完成 |
| **生产会话交付阻断：A3 的 UI/音频边界** | `interaction_ui.gd` 已有正会话 ID 过滤，但新页面 ID 为 -1 时仍可采用迟到会话；`runtime.gd` 音频消费缺完整 task/session 代际归属。旧静态与时序证据仍未被本轮后台测试覆盖；不能把 Core 两会话隔离冒称 Godot/音频验收 |
| 现有工具数据/失败边界，未关闭 R2-RC14/17 | `tools.py::read_file` 损坏 UTF-8 在分页尾部仍可能额外替换合法字符；`write_file` replace 失败没有 finally 清理临时文件。影响完整读回/残留数据处理，属于现有功能缺陷，不是未来扩展；所测正常 UTF-8 文件通过不消除这些边界 |
| 现有适配/工具可靠性，未关闭 R2-RC15/16/18/19 | 命令预检 `.split()` 与执行 shlex 分词不同、active_window 的 windll 装配层级仍未修；`main.py` Provider message=null 工具路径缺统一形状校验。harness 的坏 reply/补答回执已局部修复，旧孤立左花括号首次原因仍未确定。`build_provider()` 仍未传 reload_config；类能力/本轮替身替换不证明线上重载已装配。这些阻止对应正式能力通过，未在本轮循环采样 |
| 真实连接器待验证边界 R2-RC13 等 | Gmail 特定 cwd 的 OAuth stdout 污染旧证据仍在；本轮合成协议不证明真实启动、认证和远端副作用。真实连接失败历史保留，不由补验成功推断已稳定。协议升级也需重新核对 schema/回执合同 |
| 尚未实现的扩展 B2/RC11 等 | Drive 独立 resources/read 正文桥接、pending-memory 审阅 UI、键鼠控制、Spark、Windows 登录自启等仍未实现或由所有者延期。它们不伪装成三条基础流程验收，也不为本轮新增任务；其中历史任务恢复具有上行生产可靠性影响，不能仅列为便利功能 |
| 评测证据边界 RC09 | 原评分器请求/目标/hash 混淆不能用新局部通过倒改旧 259 项成绩。文件/Issue/邮件采用当前实参、真实副作用及回执判据；原开放分数不宣称已重新验证 |

因此，可以保存并交付**已通过所测交界的修复提交**，不能给出“基础操作内核整体冻结通过”或直接进入生产部署的结论。进入真实连接器验证前，首先须解除 A4 通用操作声明的可信交付阻断；随后真实连接器的启动/认证、固定 schema/回执及专用对象副作用仍需独立授权验收，生产数据和 UI/时序问题也不能被该连接器验收覆盖。

**下一步唯一处理事项：收敛 A4 通用入口中操作声明与真实任务证据的绑定合同，保留普通聊天和有来源摘要。** 本轮不自行扩展实现；其余已登记阻断保留原证据，不同时展开审计或生产修复。
