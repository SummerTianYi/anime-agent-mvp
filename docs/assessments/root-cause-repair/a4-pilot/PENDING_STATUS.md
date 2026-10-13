# 已有任务的跨轮进度交付修复

**本项通过，停在 Manager 验收点。** 本报告只验收“已登记真实操作之后，明确询问任务进度”的状态交付：原跨轮反例已修复，定向 13 项纳入最终 Core431 回归，独立 13 项/37 检查通过。本项无已知未解决阻断；A4 整体仍开放，旧报告及数据库影响未知记录保留原样。

## 工作基线与边界

- 仓库：`SummerTianYi/anime-agent-mvp`；候选分支：`codex/root-cause-repair-batch01-followup-20261012`。
- 接手：`8ae77011bfd824dfc5aa33e0c687cc417c867f08`；本机根：`D:\UserData\Administrator\Documents\Codex\2026-10-12\tianyi-repair-batch01-followup`。已核对根、HEAD、分支及工作树，接手时无未提交改动。
- 隔离入口独立提交：`e8c2e385239163cd0ed4c8741c52a19826b3a726`。
- 本轮真实模型请求及外部业务调用均为 **0**。全部使用已有隔离测试环境、合成输入、可控 Provider 与工具替身；不操作 Godot/Core/TTS 服务，不部署、不合并 main。
- 没有打开、核验、修改或恢复生产数据库；上一轮默认库初始化的实际影响仍未知，详见原始 [execution-deviation.json](evidence/execution-deviation.json)。本轮隔离修正不追溯证明上一轮无影响。

## 隔离入口前置修正

`scripts/check_docs_consistency.py` 的公开入口自行分配临时目录及合成配置，再启动独立子进程。子进程在任何 Core 动态导入之前核对专用目录、配置路径/内容、所有权 nonce 与 Mock/TTS/wake/MCP 配置；异常即退出。导入审计守卫阻止非隔离 SQLite、私人配置读取、越界写入及外部 I/O。

三项隔离测试包括：五种错误上下文必须在 Core 导入之前退出；真实 discovery 正常运行；公开入口覆盖继承的错误配置。默认数据目录替身和配置哨兵均未访问/改变。证据：[pending-isolation.json](evidence/pending-isolation.json)。隔离代码先于业务修改独立提交，并经独立 Python 差异审查。

## 修前与修后

原始独立反例通过真实 `handle_chat` 输入“写入合成文件”，产生真实账本待办，再问“刚才那件事现在怎么样？”。Provider 替身自报 `decision.mode=chat`，声称文件已处理好。修前这句谎言直接交付，真实账本仍为待确认，工具执行次数为零。修前失败已重新复现并保存：[pending-before.json](evidence/pending-before.json)。最终源码重放交付“待确认，尚未执行”，状态轮零模型/工具调用，票据未改变：[pending-after-final.json](evidence/pending-after-final.json)。

修复将明确进度询问放在确认/取消判断之前，由宿主读取当前会话完整 ActionLedger 并按任务分组交付。状态查询不依赖本轮 `delivery_actions`、模型 mode 或当前聊天任务是否已替换。待确认、成功、失败、取消、过期、执行中及 unknown 分别显示；同一任务的部分成功与其余待办一起列出。明确目标只在当前会话解析；模糊指代对应多个任务时分别列明。

查询复用原聊天的消息保存、响应事件与待办展示路径，不调用模型、确认或执行工具，也不重置操作任务及预算。普通聊天继续使用现有回答路径，保留原票据、参数版本和操作预算；操作预算耗尽后的闲聊只允许一轮无工具回答。有效确认、重复确认、取消及改参仍经过现有机制。“先取消，再告诉我状态”以及“先不要执行，只问进度”包含明确拒绝，保持既有锁前撤权优先，不被纯查询入口吞掉。

代码集中在 `agent_core/task_status.py` 和 `agent_core/main.py`；ActionLedger、权限引擎、工具、存储、TTS 及既有 A4 决策合同保持原实现。`chat.delivery` 审计事件记录实际查询的 task_ids，不借当前闲聊任务归属历史操作。

## 验证记录

定向测试从自然语言进入实际聊天处理入口，不预置正确意图，查询时准备自报 chat 且谎称全部完成的 Provider 返回。覆盖多种明确问法、普通闲聊、耗尽预算闲聊、确认后查询/重复确认、多待办部分完成、多任务、终态与 unknown、跨会话、历史任务恢复、引用解释，以及取消/改参控制。

开发首轮发现两种问法未正确处理，保留失败：[pending-target-first.json](evidence/pending-target-first.json)。定向用例最终增加至 13 项，全部并入 Core 常规测试。最终冻结业务源码的 **431/431 回归通过，零失败、错误或跳过**：[pending-core-final.json](evidence/pending-core-final.json)。测试中音频采样、HTTP 和 MCP 均使用原有合成夹具，不连接当前桌面服务。

独立上下文审查先复现反例，再由主执行者修正；审查者不改业务源文件。首次 9 例有 7 例失败，随后补充的文件引用撤销、目标空格、完成动词及拒绝前缀也保留首次失败，没有覆盖或把已复现漏洞改判为通过：

| 反例/正常对照 | 首次发现 | 定向修正 |
|---|---|---|
| “刚才让你写的文件，现在完成了吗？”、“文件还没写完吗？” | 仍收到模型假完成 | 补齐关系指代、逗号、负向问句及组合状态动词 |
| “刚才那个任务有没有被取消？” | 询问误撤销票据 | 纯取消状态问句先查账，不作为撤销授权 |
| “任务先取消，再告诉我状态” | 撤销被吞；排队确认实际执行 1 次 | 对象限定为任务指代或有效目标结构，复合命令保留原撤权流程 |
| “先取消待办再告诉我first.txt的状态” | 文件目标入口也吞撤销 | 含控制语义的对象仅在精确匹配本会话字面目标时可查账；其余沿用原撤权 |
| “先不要执行，只问刚才任务进度如何？” | 新增前缀剥离吞拒绝，放行排队确认 | 删除这条剥离，将其纳入拒绝回归 |
| “你现在怎么样？” | 普通问候被账本替代 | 要求实际任务名词/对象，不能只匹配“你”或空对象 |
| `review draft.txt`、带引号/绝对路径/含控制词的字面文件名 | 空格丢失，或目标外缘空格导致漏识别 | 保留内部空格，只规范对象外缘；按本会话真实目标核验 |
| “刚才那个文件保存了吗？”、“这个任务处理好了没有？” | 仍收到模型假完成 | 状态动词与完成后缀组合识别；不删除生成回答中的关键词 |
| 两项待办、一项成功一项待确认；另一会话结果；正常闲聊 | 正常对照 | 分任务/逐操作显示；跨会话不引用；聊天及任务预算保留 |

首次失败证据：[初轮](evidence/pending-review-initial.json)、[文件引用撤销](evidence/pending-review-file-revocation-initial.json)、[目标外缘空格](evidence/pending-review-final.json)、[状态动词](evidence/pending-review-verbs-initial.json)、[拒绝前缀](evidence/pending-review-hold-initial.json)。最终独立结论以收尾冻结版证据为准，不使用早期中间版本的 PASS 替代。

运行器互审还发现两项验收漏洞并修正：独立脚本现在显式覆盖并核验实际 fixture 源码根，前后业务 hash 稳定才可通过；历史反例脚本会捕获入口异常，因此新的单例重放另外要求两轮无异常、确实交付待确认状态、票据保留且查询无模型/工具调用。异常注入负对照必须拒绝，正常对照必须通过。早期诊断证据未记录实际 fixture 根，不用于最终版本绑定。无检查、子测试异常、审计阻断和缺少 tearDown 也不能在逐例 JSON 中显示 PASS。

最终独立审查 **13/13 用例、37 项行为检查通过**，源码前后稳定，实际 fixture 根已核验（故意传入错误继承根的负对照也通过）；详见 [逐例证据](evidence/pending-review-final-03.json) 与 [独立结论](evidence/pending-review-verdict-final.json)。Python 互审的异常注入、根绑定及证据投影负对照见 [初次修正验证](evidence/pending-python-review.json)，最终拒绝前缀小差异复核见 [最终 Python 结论](evidence/pending-python-review-final.json)。已发现的本范围问题没有遗留阻断。

独立结论绑定的最终业务 SHA256：

```text
main.py        0b8f14efdec380dd8dcc825cd9ad015f0bfa0a9d8b539faaf3b4892389f17eb9
task_status.py 40a95e164c96c4ba572a7d25c7d1e2c2c35e3fd15a35fcbd32a203643d29d4c5
```

只对这两个业务文件及新增定向测试作产品修改。既有 `actions.py`、`agent_loop.py`、`task_delivery.py` 的 hash 与接手版本一致；提交前再次核对最终文件与独立结论一致。未运行与本次 Core 状态交付无关的桌面构建、Godot/资产或真实 Bridge 检查。

收尾重新打开所有本轮 JSON 证据，并核对最终 Core 回归/独立审查/实际源码三方 hash 相同；旧报告及影响未知记录的 Git 内容未改变。隔离哨兵 3 项再次通过，文档入口输出 `DOCS_CONSISTENCY_OK` 和 `DOCS_ISOLATION_OK`，记录见 [pending-validation-final.json](evidence/pending-validation-final.json)。

## 复现命令

在仓库根的 Git Bash 执行。`PY` 指向已有隔离虚拟环境，不安装全局依赖。每次使用新的输出/数据路径，运行器拒绝覆盖历史证据；所有示例数据路径均为专用测试目录。

```bash
PY=../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B scripts/test_check_docs_isolation.py
"$PY" -B scripts/check_docs_consistency.py
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/pending_replay.py \
  --source-root . --output D:/TianyiRepair/pending-replay-new.json
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/pending_review.py \
  --output D:/TianyiRepair/pending-review-new.json
"$PY" -B docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py \
  --source-root . --data-dir D:/TianyiRepair/pending-target-new \
  --output D:/TianyiRepair/pending-target-new.json --pattern test_pending_status.py
"$PY" -B docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py \
  --source-root . --data-dir D:/TianyiRepair/pending-full-new \
  --output D:/TianyiRepair/pending-full-new.json --pattern 'test_*.py'
git diff --check
```

原始失败也可将 `pending_replay.py --source-root` 指向单独导出的接手提交源码；不切换或覆盖当前候选工作树。测试 fixture 只使用内存数据库并阻断真实 I/O。仅运行 docs guard 的公开入口，无需调用者准备私人配置或数据。

## 剩余边界

- 本项不修复首轮无票据的假待办/假完成声明，也不修复只读摘要夹带写入完成声明；这些旧 A4 反例仍开放，不能据本项通过宣布 A4 关闭或整体可集成。
- 状态查询呈现已登记操作的真实状态，不证明原始自然语言目标的所有潜在步骤都已实现。通用意图识别、自由文本语义担保与模型成功率不在本轮范围内。
- 本轮采用有限的中文明确进度问句识别及本会话目标解析，正常聊天和解释仍走原路径；未声称任意语言、任意改写或复杂混合意图都具备语义担保。多任务指代不唯一时列出各项，避免猜中一项就报告全体完成。
- 无真实 DS/GLM 复测、桌面或语音验收。未改 TTS；停在候选分支 Manager 验收点。
