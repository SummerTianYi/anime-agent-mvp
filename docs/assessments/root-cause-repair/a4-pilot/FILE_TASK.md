# 文件任务跨模型交付候选

2026-10-14，Codex；接手 `509e69b9e64b901a221364c3e16823df9fe6dd0d`，分支 `codex/root-cause-repair-batch01-followup-20261012`。本报告只验收自然语言创建文件、正常确认、真实写入、独立读取及完整交付这一条链。历史 [REPORT](REPORT.md)、[PENDING_STATUS](PENDING_STATUS.md) 及 [execution-deviation](evidence/execution-deviation.json) 保留原文。不是 A4 整体关闭或任意模型认证。

**结论：局部实现与离线审查通过，跨模型六例验收部分完成。** 最终同一源码上 DS 3/3 完整通过，GLM 2/3 完整通过；GLM 第三例真提案和写入通过，独立读取前达到 **30/30 HTTP** 硬上限，按未完成交付。没有继续请求、换账本或以安全拒绝算成功。两模型都已实际完成过整条任务，但不能宣称要求的六例全部通过。建议保留此窄流程候选，Manager 验收前仍缺 GLM 第三例读回与完整交付证据；没有据此扩大架构的依据。

| 验收环节（最终源码六例） | 结果 |
|---|---|
| 真提案，路径与正文正确，确认前零写入 | DS 3/3、GLM 3/3 通过 |
| 正确写入，字节及回执一致 | DS 3/3、GLM 3/3 通过 |
| 实际独立读回 | DS 3/3、GLM 2/3；末例额度耗尽，未通过 |
| 完整交付，与真实读取一致 | DS 3/3、GLM 2/3；末例明确未完成，未通过 |

重复确认、真实操作状态和历史/账本重开六例均通过；GLM 末例不存在读取记录，因此 `reads_reopened=false`，没有把空列表相等冒充通过。

## 判据与实现

从实际 `handle_chat` 输入自然语言，Provider 自己产生提案；没有预置意图分类、工具参数或执行结果。正确路径、完整字面正文及权限票据在确认前可见，确认前不存在目标文件；一次“确认”后由原 ActionLedger 执行写入，模型继续调用 `read_file`，用户无需再发读取请求。正文、文件 UTF-8 字节、真实读取事件及写入回执 SHA256 必须一致。重复确认不重复写入，进度查询不授权，历史、动作及读取事件在独立数据库重开后仍一致。

- `agent_core/file_task.py` 增加窄范围的文件写后读义务及共享任务指导；只识别明确中文文件写入并读回的请求，保留解释、缺参和普通聊天。它不生成工具调用、参数或票据。
- `main.py` 沿用任务目标、预算、一次纠正机会和现有授权执行链。字面正文以“内容如下：”之后的字符为准，模型删改正文先拒绝提案，返回首差异位置供一次纠正；不替模型填参。正文约束跨“继续”保留，路径编辑保留正文，明确新正文按新版本重新确认。
- 每个实际读取记录绑定同会话、同任务、同路径且在它之前成功的写入动作。完整连续分页和最终字节哈希共同证明读取完成；写入工具内部 `verified_readback` 不能替代 `read_file`。
- 完成答复由宿主用真实读取正文交付，跳过会改写日期、单位的语音文本正规化。未读取、读取失败或结果 unknown 保留真实回执并明确整个文件任务未完成；已经写入并读回后补答超时，宿主仍能完整交付。

业务代码没有 DS/GLM 名称分支。原工具、ActionLedger、权限、存储、Agent Loop、Provider 适配及跨轮 `task_status` 实现未改。只有文件编辑可以忽略已取消旧版本对纠正机会的阻断；普通任务保持原行为。

## 修前与离线回归

先跑原 A4 的 19 项隔离基线通过，再运行新增自然语言入口回归：初始 10 项有 6 项失败，其中 5 项暴露本流程缺失，1 项是夹具把本轮 `delivery_actions` 也当作持久任务字段比较的过严断言。该夹具改为检查真实待办、目标和预算，保留原失败，不计作产品修复成果。

| 修前现象 | 修后判据 |
|---|---|
| 模型自报 chat，说“已安排待办，请确认”，实际无票据 | 一次纠正仍无有效提案则交付未完成，零写入 |
| 确认后只写入，没有独立读取 | 同一次确认处理继续工具循环；真实读回前不交付完成 |
| 内部写入校验被当作完整交付，正文日期/单位被改写 | 必须有后置 read_file，正文按真实读取结果逐字交付 |
| 写后超时/读取失败仍只有“写入成功” | 写入成功与整个任务未完成分别说明，不重写 |
| 模型提出删掉行首标签的正文 | 原文约束在造票前拦截，一次纠正；再失败不造票 |

最终冻结源码的 Core **451/451** 通过，包含新增 20 项文件行为测试及既有跨轮状态、权限、取消改参、unknown 回归；可控 Provider 统一运行器 **12/12** 通过、零 HTTP。普通闲聊、解释为什么要读回、缺参澄清都保留正常对照。文件测试还覆盖拒绝、坏参数、重复确认、真实写入后回执丢失、读前写后时序、分页及历史重开。

证据：[修前](evidence/file-before.json)、[原基线](evidence/file-baseline.json)、[最终 Core](evidence/file-core-final.json)、[离线统一运行器](evidence/file-offline-final.json)。开发途中出现文件改参后没有纠正机会，以及放宽条件误影响非文件改参，均先保留失败再缩窄修复，见 [编辑反例](evidence/file-preparation-edit.json)、[非文件回归失败](evidence/file-preparation-nonfile.json)。这些过程证据不冒充最终验证。

## 独立差异审查

独立上下文 `file_flow_independent` 先复现不同问法、解释被误拦、分页正文不完整、取消旧版后新任务无法完成、已有待办时新文件请求假承诺，以及跨“继续”/新正文/仅改路径时正文约束丢失。主执行者只修本文件链；原始失败保留在 `file-review-first/second/literal-first/literal-edit/path-edit.json`。最终 [24 项反例](evidence/file-review-guidance-final.json) 全部通过。

`file_python_review` 检查真实代码 AST、传输计数、隔离和判卷，发现“两个空读取列表相等”可以误报持久读取通过，已改为必须有实际读取再与重开事件核对。验证重定向禁用、重试逐次计数、写计数失败不发请求、迟到 HTTP 工作线程结束前不释放运行锁、30 次封顶、私人字段筛选、越界访问拒绝及非文件编辑负对照。最终 [14 项检查](evidence/file-python-guidance-final.json) 全部通过、零 HTTP。旧失败 `file-python-first/grader-first/literal-edit-first.json` 保留。

两份独立结论、最终 Core、真实模型运行绑定同一业务源码：

| 文件 | SHA256 |
|---|---|
| main.py | `ecc4491e8bddda797b81fb51ec7f629cc1cd963e7fdf459239bd0a272150302d` |
| file_task.py | `5acedf04eefd388db63b67d5f684acdbd5037c41ccadbf357846dfa6cb37df5d` |
| file_models.py | `e4734368dfc84c6f443a5a058c03f71734a28b5e3e8e80a0cd6277c2bd65511b` |

## 真实模型逐次记录

所有首次失败及中间版本成功都保留。总计 9 次任务运行、30 次 HTTP：最终源码 6 次任务中 5 次完整通过，历史中间源码另有 1 次成功。不能合并成“最终六例通过”。

| 顺序 / 证据 | 模型 / 样本 | HTTP 索引（次数） | 真提案 / 写入 / 独立读取 / 完整交付 | 结论及首次偏离 |
|---|---|---|---|---|
| [首次 DS](evidence/file-live-ds-1.json) | DS / 1 | 1（1） | 错正文票据 / 否 / 否 / 否 | 提案失败；删除行首，运行器没有确认 |
| [正文约束后 DS](evidence/file-live-ds-1-fixed.json) | DS / 1，中间源码 | 2–6（5） | 是 / 是 / 是 / 是 | 经一次纠正通过；仅历史成功 |
| [首次 GLM](evidence/file-live-glm-1.json) | GLM / 1 | 7–8（2） | 否 / 否 / 否 / 否 | 提案失败；一般纠正后仍删行首，零票据 |
| [最终 DS 1](evidence/file-live-ds-1-release.json) | DS / 1 | 9–13（5） | 是 / 是 / 是 / 是 | PASS；一次正文纠正，重复写调用由旧账本去重 |
| [最终 GLM 1](evidence/file-live-glm-1-release.json) | GLM / 1 | 14–18（5） | 是 / 是 / 是 / 是 | PASS；一次正文纠正，实际读两次，无重复写入 |
| [最终 DS 2](evidence/file-live-ds-2-release.json) | DS / 2 | 19–22（4） | 是 / 是 / 是 / 是 | PASS；更换文件名及全文 |
| [最终 GLM 2](evidence/file-live-glm-2-release.json) | GLM / 2 | 23–25（3） | 是 / 是 / 是 / 是 | PASS；更换文件名及全文 |
| [最终 DS 3](evidence/file-live-ds-3-release.json) | DS / 3 | 26–29（4） | 是 / 是 / 是 / 是 | PASS；再次更换文件名及全文 |
| [最终 GLM 3](evidence/file-live-glm-3-release.json) | GLM / 3 | 30（1） | 是 / 是 / 否 / 否 | 任务未完成；写后 Provider 入口被总额度拒绝，未发送第 31 次请求 |

三个样本分别为 `delivery note.txt`（两行含“第一行/第二行”、日期及 cm）、`different-蓝桥.txt`（kg/Disco/独特尾行）、`third sample.md`（Markdown 标题/℃/日期）；完整文本在逐例 `expected` 中。两个模型各样本的归一化输入、工具与初态相等，源码和预算一致。模型名字仅用于连接与证据标签。

[HTTP 账本](evidence/file-http-ledger.json) 索引连续 1–30，与所有逐例请求一一对应。实际已发请求均得到协议响应；没有本轮连接/协议失败，也没有权限或回执越权失败。GLM 末例自动类别为 `proposal_or_task`，具体原因是预算封顶，不能解释成模型能力已失败或读取已验证。额度剩余 **0**；本轮停止模型测试。

运行条件：各次全新持久测试库、目标文件不存在、相同工具 schema（write_file/read_file）、standard 每任务 6 轮/12 工具调用/1 次纠正，Provider 超时 45 秒；两模型只经既有适配层差异化连接。请求使用同一自然语言模板，第二、三组更换文件名及全文。归一化任务、初始数据、schema、全部业务源码及运行器 SHA256 均随逐例证据保存。初始同源双模型均通过才放行补样。

失败分为连接/协议、提案/任务、权限/回执防护三类；安全拦截不是任务通过。每次发出 HTTP 前写入共用持久账本，禁止自动重定向，内部纠正/重试同样计数，所有运行共用上限 30。历史第一次 DS 错正文提案虽产生真实票据，运行器没有确认，实际零写入；随后增加原文约束。GLM 首次在一般纠正后仍删行首，零票据零写入，随后改为共享的字符差异反馈。没有重跑抹除失败。

## 可复现入口

在 Git Bash、主仓根目录运行。`PY` 指向现有隔离依赖环境，不安装或改全局软件。所有 data-dir 和 output 必须为新路径；同阶段真实模型必须复用同一个 ledger，不能靠换账本重置额度。不要直接运行未隔离的 unittest discovery。

```bash
PY=../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py --source-root . --data-dir D:/TianyiRepair/new-file-regression --output D:/TianyiRepair/new-file-regression.json --pattern test_file_task.py
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --source-root . --offline --data-dir D:/TianyiRepair/new-file-offline --ledger D:/TianyiRepair/new-file-offline-ledger.json
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_review.py --source-root . --data-dir D:/TianyiRepair/new-file-review --output D:/TianyiRepair/new-file-review.json
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_runner_review.py --data-dir D:/TianyiRepair/new-file-runner-review --output D:/TianyiRepair/new-file-runner-review.json
"$PY" -B scripts/test_check_docs_isolation.py
"$PY" -B scripts/check_docs_consistency.py
```

模型入口 [file_models.py](repro/file_models.py) 复用原 [models.py](repro/models.py) 的传输投影与禁止重定向组件，调用当前 Core 聊天入口，不重做平台。通过 `--provider deepseek` 或 `--provider glm` 选择现有适配配置，实际模型名来自获准配置的 `DEEPSEEK_MODEL`/`GLM_MODEL`。同协议更换模型只换连接配置，不修改用例、业务判据或授权规则；其他协议/Provider 不自动兼容或降级认证。

```bash
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --source-root . --private-config ../tianyi-repair-batch-01/.env --provider deepseek --data-dir D:/TianyiRepair/new-ds-1 --ledger D:/TianyiRepair/new-stage-http-ledger.json --variant 1
# GLM 使用同一个 ledger，provider 改为 glm，data-dir 改为新目录。
# 两个 variant 1 均通过后，各模型 variant 2/3 加上以下两个实测报告参数：
# --initial-report D:/TianyiRepair/new-ds-1/file-model.json --initial-report D:/TianyiRepair/new-glm-1/file-model.json
```

命令是以后获准验证时的入口；本轮计数账本不能再启动新阶段冒充剩余额度。返回 JSON 包含独立判据和 failure_category。离线模式才使用可控 Provider；真实模式不回填正确参数、工具调用或动作结果。

## 隔离、历史与剩余边界

本轮专用数据在 `D:/TianyiRepair/file-task-20261014`，每例持久库保留于其 `db` 子目录；库不入 Git。只有合成文本、脱敏请求/回答、回执、hash 及计数证据入库，连接端点、凭据及模型推理字段不发布。只读取获准模型连接字段；动态导入前自行配置独立数据、配置、Mock、禁用 TTS/wake/MCP，审计守卫阻止越界 SQLite/写入/外部进程。离线网络被阻断，真实模型运行只开放选定 Provider 的 HTTP 传输。

历史验收指重新打开每例独立 MemoryStore/ActionLedger，另以只读 SQLite 重开对比消息、动作和实际读取事件；不是当前桌面 UI 重开演示，也没有认证进程崩溃后内存任务计划自动恢复。数据库逐字节未变、逐例计数及源码对应见 [manifest](evidence/file-manifest.json)。未打开、修改或恢复生产库，上一轮默认库影响未知记录继续有效。未操作当前 Godot/Core/TTS；配套 TTS 固定 `969f4e293a8abbf4b8f153e8551b2fbff93098bf`，本轮不修改。

以下边界仍开放：窄文件请求识别之外的无票据假承诺、只读摘要夹带写入声明、任意语言或任意语义意图判断；首次 A4 报告继续有效。独立检查还发现原 `task_status` 未覆盖“刚才那个文件任务现在是什么状态？”这一问法，本轮不扩大其分类范围；已通过的“刚才那个任务现在怎么样？”及原状态回归保持。普通聊天的自由正文不因此获得操作完成证明。

没有前端、Godot 或 TTS 业务修改，本轮不运行桌面/声音/真实外部业务验收，不将历史桌面证据冒充本轮结果。候选代码不部署、不合并 main，停在 Manager 验收点。

最终公开检查入口得到 `DOCS_CONSISTENCY_OK`、`DOCS_ISOLATION_OK`；隔离哨兵 3 项通过，`git diff --check` 通过。业务提交 `994db70e35ef05f54fae0abbc9231ec45bccb0f4` 的干净 clone 经两个零上下文实例完成白纸交接，均为 8/8，核对结果、预算和未部署边界，见 [交接证据](evidence/file-handoff.json)。第二实例另发现 HANDOFF 代码地图的旧 Idle“未开工”文字与已实现清单不一致，属既有文档陈旧项，本轮不改。

独立审查和计数不替代缺失的最后一例模型验收。后续提交只补本交接记录，业务源码不变；最终提交及远端回读由交付消息提供固定 SHA 链接，Git 中的报告与证据是该提交快照。
