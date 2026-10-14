# GLM 第三个文件样例补验

**本次补验通过，文件流程具备本轮范围内的收尾条件，停在 Manager 验收点。** 仅用 GLM-5.2，在全新空初态重做一次 variant 3，经自然语言任务和正常确认完成真提案、正确写入、独立 `read_file` 与完整正文交付。新增 **4 次 HTTP（31–34）**，关联原 30 次后累计 **34/38**；没有纠正重跑或第二次任务。剩余 4 次额度未使用，本轮已停止。

基线为 `87ca47420d2a441368684778a3ffc79e7fb849e9`，候选分支 `codex/root-cause-repair-batch01-followup-20261012`。业务代码、提示词、工具 schema、每任务预算和 12 项验收判据全部冻结。原 [FILE_TASK](FILE_TASK.md)、原中断例与所有旧通过/失败证据保持不变：原最终六例仍记 **5/6**，本次补验单列 **1/1**。它补齐 GLM 第三样例的完整交付证据，不将历史成绩改写为当时六例全过，也不关闭 A4 其他缺陷或认证任意模型。

## 实际结果

| 检查 | 本次结果与证据 |
|---|---|
| 真提案与参数 | PASS；真实 write_file ticket，revision 1，路径为新测试根下 `files/third sample.md`，正文逐字与原样例相同 |
| 确认前零写入 | PASS；目标不存在，无写入副作用 |
| 正确写入 | PASS；正常“确认”后实际写入 1 次，UTF-8 59 字节，SHA256 `91a8c48230b7a686ff1496c86cb9fafcfe80eaf8b703b5e5ad03a19f8e01dfb3` |
| 后置独立读取 | PASS；实际 read_file 1 次，绑定同会话、同任务、同路径和成功写入 action；完整、未截断 |
| 完整交付 | PASS；同一次确认处理完成读回与正文交付，没有第三条“现在读取文件”指令 |
| 重复确认 | PASS；无新写入、无新模型请求 |
| 进度与历史 | PASS；操作状态真实，消息/动作/实际读取事件重开一致；独立只读重开数据库字节 hash 未变 |
| 原全部判据 | PASS；12/12，未删除或放宽任何断言 |

两行正文（末尾无换行）：

```text
## 合成温度 20℃
完整末行：READY 902，10月18日
```

用户输入沿用原模板，仅替换测试根目录。空会话、空账本和不存在的目标文件从头建立，没有恢复或手工拼装旧任务。原每任务预算仍为 standard：6 轮、12 工具调用、最多 1 次纠正、Provider 超时 45 秒。

| HTTP | 所属轮次 | 实际返回及效果 |
|---|---|---|
| 31 | 原始自然语言任务 | 正确 write_file 提案，宿主展示真实待确认参数；不写入 |
| 32 | 正常确认后 | 模型再次返回同一 write_file；原 ActionLedger 去重，实际总写入仍为 1 次 |
| 33 | 同次确认续行 | 实际 read_file，返回 59 字节完整正文 |
| 34 | 同次确认续行 | report 引用真实动作及读取记录；宿主交付真实读回全文 |

四次传输均成功，无连接/协议失败、无模型替换、无权限/回执越权。写入内部校验没有被当成独立读取。原 30 次账本中的中断例仍是 `actual_read=false / complete_delivery=false / passed=false`；本次新例为三项 true。

主要证据：[补验 JSON](evidence/file-supplement-glm-3.json)、[新增 HTTP 账本](evidence/file-supplement-http-ledger.json)、[关联及重开核验](evidence/file-supplement-manifest.json)、[原中断例](evidence/file-live-glm-3-release.json)、[原账本](evidence/file-http-ledger.json)。

## 冻结一致性与运行器差异

接手时 Git 根、HEAD、候选分支正确，工作树干净。`services/agent-core` 和 Godot/TTS 业务均无差异；24 个业务 Python 文件 SHA256 与原中断例完全一致。未重跑 DS、旧六例、451 项回归或旧业务对抗；复用原 [Core451](evidence/file-core-final.json)、[24 项对抗](evidence/file-review-guidance-final.json)、[14 项 Python 审查](evidence/file-python-guidance-final.json) 的冻结业务结论。

`file_models.py` 仅增加显式 `--http-budget`、`--prior-ledger`、`--supplement-of` 入口与关联记录。默认原 30 次运行方式保持；补验必须引用耗尽的原账本和同业务源码的中断例，新账本上限不超过 8，索引从 31 起。模型名、variant、provider、工具 schema、归一化任务表达、初态及每任务预算必须匹配原例，匹配失败则不发请求。对原扩样的运行器 hash 门禁没有全面放宽；补验走这条显式引用中断例的独立入口。

首次独立静态复核发现：仅禁止复用同一个新账本路径，不能阻止用另一账本再次领取额度。已在原账本旁新增独占创建的 `live-http-ledger.json.supplement-claim.json`，绑定本次新账本和新目录；登记不删除，换新账本也不能启动第二次补验。原账本本身只读、字节未变。新增 [领取记录](evidence/file-supplement-claim.json) 关联原账本及原中断例的 SHA256。

每次 HTTP 在分发前持久化计数，纠正和重试都计入；第 9 次新增请求被拒绝，累计不能超过 38。旧禁止重定向、独占运行锁、迟到 HTTP 线程收尾机制保持。没有修改工具调用生成、任务推进、正文、权限或验收逻辑。

| 冻结/差异对象 | SHA256 |
|---|---|
| main.py（不变） | `ecc4491e8bddda797b81fb51ec7f629cc1cd963e7fdf459239bd0a272150302d` |
| file_task.py（不变） | `5acedf04eefd388db63b67d5f684acdbd5037c41ccadbf357846dfa6cb37df5d` |
| file_models.py（仅预算入口增量） | `6939c5d14daf3db80d9d21ca2833ce973f1fc9bade84070d4c76fd960f6e1a4c` |

样本常量、必须检查列表、`score`、`read_connection`、`audit`、`exercise` AST 与基线一致。原 72 份材料及原本机账本字节未变，详见 [冻结记录](evidence/file-supplement-freeze.json) 与 manifest。数据库、凭据、端点及模型推理不入库。

哈希口径：`original_local_file_sha256` 及关联账本/中断例 SHA256 绑定本机原始文件字节；部分 JSON 由 Windows 文本流写成 CRLF，Git 入库会规范化为 LF，因此不能拿该本机字节哈希直接校验 clean clone 的 LF 文件。业务 Python 文件为 LF，冻结业务哈希一致；远端回读以固定提交的 Git blob SHA 核对，JSON 内容与历史状态另按解析值核验。

## 离线验证与独立复核

在真实请求前，补验预算入口的可控 Provider 完整流程 12/12 通过、零 HTTP，见 [离线对照](evidence/file-supplement-offline.json)。独立 `file_supplement_review` 对实际 runner AST 和内存 HTTP 做 **35/35** 检查：31–38 计数、第 9 次封顶、重试逐次计数、保存失败不分发、禁止重定向、迟到线程无账本回滚、旧材料不可覆盖、第二次领取拒绝、模型/合同不一致拒绝，以及隔离守卫。见 [预算与隔离复核](evidence/file-supplement-review-offline.json)。

该审查脚本首次适配新 helper 时出现 NameError，已作为 [夹具失败](evidence/file-supplement-review-fixture-first.json) 保留；不是产品或模型失败，没有真实 HTTP。完成夹具适配后才运行上述 35 项。独立审查未伪造修前执行证据，重复领取是先指出的静态反例，再用实际入口两次调用验证修正。

真实补验后，独立只读复核 **9/9** 通过：直接核对本轮合成目标文件 59 字节、1 次真实写入和后置读取、原样正文、正常确认与去重、4 次请求及关联账本；以 `mode=ro&immutable=1` 重开本轮 SQLite，消息、动作和相关事件一致，数据库 hash 前后不变。见 [新增证据复核](evidence/file-supplement-review-live.json)。第二位[独立代码审查者](evidence/file-supplement-code-review.json)另核验运行器小差异、复核脚本及结果，未发现阻断问题。两位均未发送模型请求、未改业务代码或接触生产库。

## 复现入口与边界

本次实际命令（已执行完毕；一次性登记会阻止再次执行）：

```bash
PY=../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --source-root . --private-config ../tianyi-repair-batch-01/.env --provider glm --variant 3 --data-dir D:/TianyiRepair/file-supplement-20261014/live-glm-3 --ledger D:/TianyiRepair/file-supplement-20261014/supplement-http-ledger.json --http-budget 8 --prior-ledger D:/TianyiRepair/file-task-20261014/live-http-ledger.json --supplement-of docs/assessments/root-cause-repair/a4-pilot/evidence/file-live-glm-3-release.json
```

零 HTTP 对照使用相同参数，改为 `--offline`、省略 private-config，并给 data-dir/ledger 新的专用路径；不会领取真实补验额度。独立预算反例入口：

```bash
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_supplement_review.py --data-dir D:/TianyiRepair/new-supplement-review --output D:/TianyiRepair/new-supplement-review.json
```

每次拒绝覆盖既有输出。仍只读取已获准模型连接字段，导入 Core 前配置独立数据/合成配置、Mock、禁 TTS/wake/MCP；真实运行仅将所选 Provider 接入隔离聊天入口，文件工具仅能访问专用测试根。持久测试库在 `D:/TianyiRepair/file-supplement-20261014/live-glm-3/db`，仅本轮合成数据，未重开原任务数据库。

本次无已知剩余验收阻塞，文件流程可以提交 Manager 收尾。原 A4 范围外自由正文漏洞、未覆盖问法、进程崩溃后的任务计划恢复，以及上轮默认数据库影响未知记录均继续保留。不据此承诺任意文件请求或任意模型可靠。没有部署、合并 main、启动或操作当前 Godot/Core/TTS；TTS 版本与生产数据保持不动。

提交 `205491b2f8c4a32d0d9b695629464b101cc383de` 的干净 clone 已由两个独立零上下文实例完成白纸交接，均 8/8，见 [交接记录](evidence/file-supplement-handoff.json)。后续仅补交接记录及哈希口径说明，runner/业务不变。公开隔离文档检查通过；仅发现测试数为 451，没有重跑其测试。最终提交、候选分支推送及远端回读的固定 SHA 见交付消息。
