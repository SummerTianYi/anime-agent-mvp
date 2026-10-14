# 明确更正已有记忆：定向修复与验收

本轮只处理用户明确指向已有事实的更正。接手 `4a386a9776e65ef07cd3058f7cab98b4f4b0e8d1`，沿 `codex/root-cause-repair-batch01-followup-20261012` 修复。通用回复核对器仍未接入；A4及整个底座不在本轮关闭。未部署、未合并main，未操作当前Godot/Core/TTS或生产数据库。

## 结果与证据范围

本范围四项均通过：更正对象准确、保存确实成功、换会话/真实进程重启仍取新值、其他记忆未被误改。最终业务源码下受影响337项回归、既有运行器38项、独立32项（已包含在337项内）通过；DS/GLM各3条完整记忆序列通过事实性核验。DS3历史回复及部分GLM查询降级为真实工具回执，表格格式及无关get_time失败不在本轮修复。此处的通过仅指下述明确更正范围，不代替全部阶段阻断处理后的同一冻结版本统一验收。

## 原问题与修复

依据 [RC07/RC10](../../root-cause-audit/round-02/ROOT_CAUSES.md) 与 [BASELINE_CLOSURE记忆阻断](BASELINE_CLOSURE.md)：已有事实的纠错会落入普通 `memory_candidate` 晋升，未带“请记住”的更正可能只成为pending/session记录；旧记录仍有效。`add_fact` 又按文字相似度停用旧事实，既不能证明更正对象，也会误伤相似项目。聊天曾先发布模型回复再保存，用户可先收到与实际写入不符的承诺。

合成初态为“晨星项目预算120”“暮云项目预算180”“用户最喜欢的颜色是蓝色”。聊天输入“晨星项目预算更正为175。”，不附加记忆指令，不传事实ID。修前反例保留：旧值仍可被取用；相似度路径可停用暮云。最早夹具缺少decision的记录属于夹具无效，不作为业务修前依据。有效修前与修后JSON均收入证据清单。

修后把更正解析、定位、版本校验、保存和回执放在宿主明确的窄入口：

- [memory_correction.py](../../../../services/agent-core/agent_core/memory_correction.py) 识别实体、属性、旧值（若明确提供）、新值和全局/会话范围。支持明确的项目预算、负责人、日期及常见用户属性；实体必须精确对应，仅规范“项目/的”等明确表述，不以文字相似度决定覆盖。没有唯一候选、旧格式不能完整拆分、猜测或含糊问句时澄清，不猜ID。
- [storage.py](../../../../services/agent-core/agent_core/storage.py) 用 `BEGIN IMMEDIATE` 在一个事务内重新解析自然语言并核验所选旧记录的ID、完整内容、状态、作用域和会话；新版本、旧版本停用及更正来源同事务提交。复合记录按已核验的字符位置只替换一个值，其他条目原样保留。模型构造的ID/字段不能绕过核验。
- 提交前和提交后读回检查新旧内容、状态、作用域、所属会话、来源请求及局部覆盖映射。只有成功提交并核验后才回复“已更正并读回核验”。事务内失败回滚旧有效值；提交后读回失败则回答“不能确认”，不虚称回滚或重试写入。
- 更正请求在等待聊天锁之前捕获旧版本，事务内做比较后写入；晚到的旧版本被拒绝。同一请求ID返回历史结果且不重复写入；新请求写同值为无变化。明确提供不匹配的旧值也拒绝。
- `add_fact` 不再靠相似度停用记录。旧 `memory_candidate` 分支不能再次保存已有键、旧值或引用中的更正；普通新事实继续原晋升规则，保存结果先核验再发布。明确文件/Issue/邮件请求仍由既有任务适配器处理。
- “只在本次会话”针对全局事实建立仅该会话可见的字段覆盖，原全局事实不变。召回按字段叠加，复合记录中其他字段随后发生的全局更新仍可见。pending不自动晋升，敏感记忆不借更正放宽，其他会话的pending/session记录不进入候选。
- 自动注入只使用当前有效事实，明确其优先于历史对话。`recall_memory(query="全部记忆")` 可获取全部本会话可见事实；`include_history=true` 才另列已替代版本并注明原确认状态。历史仍可追踪，不能再作为现值。

通用发布前检查模块、文件/Issue/邮件适配器、权限引擎及既有行动账本不因本轮接入其他流程。新更正事件记录旧值、新值、范围、请求来源和实际结果；前端WebSocket响应契约不变。

## 确定性回归与独立反例

最终业务源码下受影响的337项回归通过：存储19、全部记忆66、WebSocket3、会话可见性4、通道互斥12、Harness73、Agent循环7、投入10、权限11、后续交付4、文件20、Issue34、邮件26、交界16、待办13、A4程序19。这里只运行指定组，没有全量Core、Godot或桌面构建验收，也没有重复旧文件/Issue/邮件真实模型样例。既有运行器隔离/计数38项通过。

新增主回归24项以自然语言 `handle_chat` 入口为主；ID伪造及兼容性另作存储检查，不代替自然语言能力。覆盖明确更正、相似实体、不同属性、复合局部更新、局部范围、歧义、普通聊天/引用、失败回滚、提交后结果未知、重放、旧版本迟到、真实回执、历史/注入/工具召回、敏感/pending/跨会话隔离以及人工旧格式库兼容。三种离线样例还经过真实loopback WebSocket、Uvicorn Core启动/退出，并在新OS进程重新启动读取同一合成测试库。

独立审查者未参与初始修复，用未给主执行的改述和错误对象案例进行一次持续差异审查。发现后依次修复：更新为/实际上是等明确表述漏识别、历史pending标签缺失、不确定“吗/吧”被写入、排队请求会话漂移、扩样未等待真实重启、仅数字命中误判答案、带引号实体/礼貌尾句误判、触发器篡改局部记录所属会话后假成功。复验保留每个失败，不删除断言。集成回归另发现文件等任务的“改成”被记忆澄清截走，已收窄到记忆属性/明确记忆，复验三个业务流程和交界均通过。

独立最终32项通过，包含新增改述/错误对象以及判据、复评门禁反例；最终记忆66项包含24项主回归、32项独立回归及原10项。详见 [独立审查](evidence/memory-review-final.json)、[最终记忆回归](evidence/memory-final-frozen-memory.json) 和 [保留模块逐文件比对](evidence/memory-final-preservation.json)。失败与中间版本回归不作为最终通过基线，均按原件保留。

[交付证据复核](evidence/memory-review-delivery-final.json) 另行核验最终数量及清单：早期独立审查元数据中的59项/25独立指针属于当时路由收窄记录，最终数量以66项/32独立为准；原记录不覆盖。提交前仅清理新测试文件空白，未改语句或断言，复用已通过的行为证据。

文档一致性检查确认当前可发现602个Core用例，并返回 `DOCS_CONSISTENCY_OK` / `DOCS_ISOLATION_OK`；这只证明文档与发现数量及接口清单一致，不是602项全量执行。变更业务源码编译和 `git diff --check` 通过。

## DS / GLM真实Provider逐例

复用 [file_models.py](repro/file_models.py) 的Provider、连接字段白名单、禁止重定向传输、进程锁和HTTP账本，只新增memory场景与两进程恢复入口；场景在 [memory_model_case.py](repro/memory_model_case.py)。每阶段预留完整序列请求余量，初始两模型的完整重启序列成立后才允许第二/第三例。记忆更正由宿主处理，不耗用模型；之后的当前会话、新会话、历史及重启后回答使用真实模型和实际工具结果。

三个固定样例分别是：预算120→175；白鹭负责人林岚→陈青（同条预算260保持，白鹭二号顾宁保持）；青禾截止日期10月18日→11月6日（同条预算420、青禾二号日期及歌手偏好保持）。全链检查实际有效记录、自动注入、真实recall结果与最终答案的实体/属性/值对应，不以“记住了”或数字出现作为通过。

| 模型 / 样例 | 保存/同会话/新会话/重启/其他事实 | 请求数 | 两阶段耗时（秒） | Core PID（首次→重启） | 逐例证据 |
|---|---|---:|---:|---|---|
| DS 1：晨星预算 | 通过（事实性） | 8 | 33.640 | 48972 → 50160 | [首次](evidence/memory-live-final-ds1-memory-model.json) / [重启](evidence/memory-live-final-ds1-memory-restart-model.json) |
| DS 2：白鹭负责人/复合预算 | 通过（事实性） | 8 | 51.563 | 50240 → 24232 | [首次](evidence/memory-live-final-ds2-memory-model.json) / [重启](evidence/memory-live-final-ds2-memory-restart-model.json) |
| DS 3：青禾截止日期/复合预算 | 通过（事实性） | 8 | 75.297 | 25776 → 10564 | [首次](evidence/memory-live-final-ds3-memory-model.json) / [重启](evidence/memory-live-final-ds3-memory-restart-model.json) |
| GLM 1：晨星预算 | 通过（事实性） | 16 | 149.765 | 4776 → 49060 | [首次](evidence/memory-live-final-glm1-memory-model.json) / [重启](evidence/memory-live-final-glm1-memory-restart-model.json) |
| GLM 2：白鹭负责人/复合预算 | 通过（事实性） | 12 | 125.969 | 51088 → 7860 | [首次](evidence/memory-live-final-glm2-memory-model.json) / [重启](evidence/memory-live-final-glm2-memory-restart-model.json) |
| GLM 3：青禾截止日期/复合预算 | 通过（事实性） | 13 | 137.766 | 36780 → 52060 | [首次](evidence/memory-live-final-glm3-memory-model.json) / [重启](evidence/memory-live-final-glm3-memory-restart-model.json) |

阶段实际共 **84次HTTP请求**，逐次HTTP耗时合计 **685.188秒**，各进程测试阶段墙钟合计 **713.001秒**（包含初始失败与定位后复验，不含人工分析等待）。最终六序列占65次；其余19次为最初DS序列及GLM首阶段，原记录保留。沿用原格式共享账本，序号连续、不覆盖、不另设费用平台；144为本组运行器保护上限，未为用尽上限扩样。

模型调用、耗时、源码及运行器hash见 [逐例汇总](evidence/memory-final-summary.json)、[HTTP账本](evidence/memory-live-http-ledger.json) 与 [全部原件/脱敏件清单](evidence/memory-manifest.json)。

独立逐字及只读数据库复核见 [六例最终审查](evidence/memory-review-live-final.json)。展示边界逐例保留：DS3历史回复、GLM1当前/新会话及重启回复、GLM2重启回复、GLM3同会话回复使用宿主JSON摘要，未满足所请求的表格样式；GLM1重启与GLM3同会话另含夹具明确拒绝的get_time失败/unknown提示。它们给出的当前事实与历史标签均正确，但不算公共JSON输出协议、表格样式或该额外工具成功。

连接层保留一次错误：第69次请求为DS3历史补答的 `TimeoutError`。此前history召回已成功，宿主最终交付实际历史回执，当前日期与旧日期仍明确区分；没有因超时重发更正，也没有隐去失败或再刷同例。最终六例自身阶段耗时574.000秒、HTTP耗时552.626秒，以上总计另包含19次早期请求。

首次GLM在正确召回后违反既有JSON/decision输出合同，宿主保守降级为真实执行记录摘要；原表格限定判据报同会话/新会话答案失败。保留该原始失败，单独审查降级摘要是否逐项给出正确实体、属性和现值，公共合同不因此放宽，也不把裸数字出现当答案。最初定位时的DS首例（live-ds1）末句提及“旧值120已作废”属于多余历史说明，未把120作为现值；单列展示边界。

最终GLM首例的第一次判据修后复验又遇到带明确history标签的宿主回执；重启后还有夹具拒绝的get_time调用。三者均未改变记忆事实。此后没有继续重跑首例刷格式，而是对已采集最终可见答离线复评：只允许精确的对象/属性/值或绑定请求的宿主recall回执，历史必须标明superseded；仅识别两种固定get_time失败提示，不接纳任意混杂文字。

复评以原报告SHA、完全相同的业务源码、审核过的原运行器hash及当前判据hash绑定，另存不可覆盖侧车；只重算三项答案展示检查，所有保存/召回/隔离/无误改等原检查必须为真。原passed与sequence_complete不改。effective_sequence_complete只有实际after_restart阶段且新旧PID检查等全真才成立，before阶段永不能升格。DS/GLM首例依据侧车后才扩样；扩样全程冻结业务与最终判据。原JSON格式/表格合同未满足及额外工具失败仍列为边界，并非修复成功。见 [最终判据审查](evidence/memory-review-time-receipt-final.json)。

## 兼容、隔离与回退

存储仅增加 `fact_corrections` 和 `fact_overrides` 两张表及其索引，不批量改写原facts格式或扫描整理旧记忆。新测试库和人工创建的旧schema库验证通过；无打开、迁移、修复或恢复生产库行为。旧的不可可靠拆分复合内容需要用户指出明确条目，不能整条覆盖。旧版本完整保留，局部覆盖与更正审计保存于同一测试库。

回退源码可恢复接手提交，但旧二进制不理解新局部覆盖/更正历史，且恢复原相似度停用风险。不能把“旧schema还能打开”当作语义兼容，更不能在真实已更正数据上盲目回滚运行。若将来获准部署，应先备份并验证适用版本的恢复路径；本轮未部署或实施生产回退。新表无需删除；测试证明其为增量兼容，不证明任意历史数据库可无条件运行旧逻辑。

所有运行目录均为本轮自行构造的隔离目录；禁TTS、wake、MCP和后台触发，不对当前服务发送请求。只读取指定Provider配置的连接字段，凭据不打印、不入仓。入仓证据仅包含合成事实、脱敏代码hash/请求/回执/检查结果；SQLite、日志和凭据留在仓外。证据清单同时记录原件与脱敏件hash，不能把脱敏件hash冒充原始文件hash。

## 复现入口

在Windows Git Bash下使用已有隔离venv。所有DATA与LEDGER路径须替换为全新测试目录；不得指向生产数据。以下 `<python>` 为该venv的Windows Python路径，配置只在真实模型阶段使用现有白名单读取。

```bash
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py --source-root . --data-dir <fresh-data> --output <fresh-report.json> --pattern 'test_memory*.py'
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --scenario memory --source-root . --data-dir <fresh-data> --ledger <ledger.json> --provider deepseek --variant 1 --offline
# 上条进程结束后，用同一合成库启动新的Core进程
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --scenario memory --source-root . --data-dir <same-data> --ledger <same-ledger.json> --provider deepseek --variant 1 --offline --memory-resume <same-data>/memory-model.json
```

真实运行去掉 `--offline` 并加 `--private-config <authorized-config>`；分别选择deepseek/glm。两者variant1的重启报告通过后，variant2/3必须同时传入两个 `--initial-report <completed-restart-report>`，各自新目录，继续共用原HTTP账本。每个首阶段/重启阶段都核验业务源码及运行器hash、前一PID已退出、隔离目录与报告一致性。原报告判据仅因上述展示形态误判时，可显式离线调用memory_model_case.write_presentation_review(path, source_hashes, protocol_runner_hashes)生成绑定当前判据hash的新侧车；读取门禁不会自动生成复评或接受任意旧版本。旧报告和旧侧车不覆盖。过程报告不会覆盖；失败保留后先定位再决定修后补验。

## 剩余边界与验收点

本轮不是通用语义记忆引擎。实体别名、未覆盖属性、代词跨句消解、多目标批改、模糊暗示、不可拆的旧格式等不自动覆盖；应澄清或保留现状。没有向量库、知识图谱、全部旧记忆清理或pending审核UI。当前词法检索的范围/排序局限仍在；本轮提供明确的全部可见记忆召回入口，不声称任意查询必定召回全部。

旧版本防护使用已捕获的记录版本、请求去重和用户明确提供的旧值。若一个从未收到过的新请求既没有旧值也没有可核验的版本来源，不能凭自然语言推断它在网络中原本应先于哪次更正；本轮不构建客户端乱序重排协议。

只有同一范围中的本轮明确更正可据证据声明通过。通用自由回复的可靠交付、模型协议稳定性及A4其他阻断未因此关闭。最终统一全量验收仍须等待其他阶段阻断完成后，以同一冻结版本运行；本报告不拼接旧阶段模型成绩来宣称底座通过。
