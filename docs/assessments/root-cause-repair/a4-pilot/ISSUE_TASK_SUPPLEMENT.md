# DS 第二个 Issue 标题样例补验

**本次补验通过，Issue 合成流程具备本范围的收尾条件，停在 Manager 验收点。** 全新隔离初态下，Deepseek-v4-flash 完成真实标题更新提案、正常确认后的唯一一次更新、实际后置读取和准确交付。原 13 项判据全部通过，新增 **6 次 HTTP（22–27）**，沿用原账本后累计 **27/40**；剩余 13 次未使用，补验完成即停止。

接手提交为 `aebcd50d8f7d23e5db5aae9b321805a4e8abe611`，候选分支 `codex/root-cause-repair-batch01-followup-20261012`。Git 根、HEAD、分支与要求一致，工作树起初干净。业务源码、运行器、提示词、工具 schema、标准任务预算及判据完全冻结。本轮没有部署、合并 main、操作当前 Godot/Core/TTS，或访问生产库及真实 GitHub 业务对象。

原 [ISSUE_TASK](ISSUE_TASK.md) 仍记 **3/4**，原 DS 第二例仍为更新提案前的连接超时失败；本次单列 **1/1**。一次成功补验补齐该样本的流程证据，不证明连接稳定性问题已经消失，不关闭其他 A4 缺陷或认证真实 GitHub 集成。

## 本次任务及结果

原任务逐字沿用，没有追加读取指令：

> 请把仓库 SummerTianYi/a4-synthetic 的 Issue #29 标题改为「蓝桥第二次核验：7月12日 / 42kg」，仅修改标题，保留正文、状态、标签、负责人和里程碑等其他用户字段。修改后重新读取同一 Issue 并核验，交付仓库、编号和准确标题。

| 环节 | 结果与实际记录 |
|---|---|
| 真提案 | PASS；模型生成 `issue_write(method=update)`，仓库、#29、标题逐字正确，参数只包含 method/owner/repo/issue_number/title |
| 确认前零写入 | PASS；初始任务和前置读取确认后均无写入；只确认真实展示、参数准确的票据 |
| 正确更新 | PASS；实际合成服务更新一次，正文、状态、标签、负责人、里程碑、locked、state_reason 等保留字段不变 |
| 新读取核验 | PASS；实际服务访问顺序是读取旧值 → 更新 → 读取新值；后读绑定本次成功更新 action，不能由旧同参数读取或更新回执替代 |
| 准确交付 | PASS；仓库、Issue #29、标题完整且逐字一致，含实际后置读取引用 |
| 重复确认与进度 | PASS；补发“确认”和进度询问均无新增 HTTP、工具副作用或写入 |
| 历史与回执重开 | PASS；新增测试库重开后的消息、动作账本、实际读取事件与本次记录一致 |
| 原全部判据 | PASS；13/13，未删减、放宽或替换验收断言 |

最终宿主交付：

```text
Issue 任务已完成：更新成功，已实际重新读取，标题逐字一致且其他用户字段保持不变。
仓库：SummerTianYi/a4-synthetic，Issue #29
核验后的标题：蓝桥第二次核验：7月12日 / 42kg
读取记录：issue-2-request:read:2
```

原 MCP 默认 ASK 保留，所以用户正常确认前读、更新、后读各一张真实票据；没有新增模式，也没有替模型填参数或手动调用工具。最终交付发生在后读确认完成后，写入内部返回不代替读取。普通进度列表沿用旧文本规范化，动作标签中的“7月12日 / 42kg”显示为“7月12号 / 42千克”；实际参数、对象标题及上述完整交付仍逐字正确，本轮冻结源码，未扩展修改该显示行为。

证据：[补验 JSON](evidence/issue-supplement-ds-2.json)、[累计账本快照](evidence/issue-supplement-http-ledger.json)、[账本增量与关联](evidence/issue-supplement-manifest.json)、[冻结清单](evidence/issue-supplement-freeze.json)、[原失败](evidence/issue-live-ds-2.json)、[原 21 次账本快照](evidence/issue-http-ledger.json)。

## HTTP 与冻结一致性

| HTTP | 所属阶段 | 返回与实际效果 |
|---|---|---|
| 22 | 原自然语言任务 | 前置 `issue_read(get)` 提案；等待正常确认 |
| 23 | 前读确认后续行 | 再次提出同参数读取；旧账本复用，无第二次实际前读 |
| 24 | 同一确认续行 | 正确标题更新提案；等待正常确认，尚未写入 |
| 25 | 更新确认后续行 | 再次提出同参数更新；写入去重，实际总更新仍为一次 |
| 26 | 同一确认续行 | 更新后的 `issue_read(get)` 新票据；等待原生确认 |
| 27 | 后读确认后续行 | 引用实际更新与新读结果，准确交付 |

六次 HTTP 均取得协议响应，无本次连接或协议错误。没有第二次任务、模型替换、协议探测或补充重跑。任务内部同参数工具请求由冻结机制处理，不等于新增实际服务副作用。

使用原 `D:/TianyiRepair/issue-task-20261014/http-ledger.json`：开跑前已用 21、剩余 19，满足现有预留 18 次的要求；完成后前 21 条完整相等，新增 22–27 与本次请求一一对应。上限仍为 40，没有新开运行账本、补发额度或修改预算入口。公开原 21 次快照只读保持，新累计快照另存。标准任务仍为 6 模型轮、12 工具调用、1 次纠正、45 秒 Provider 超时。

26 个业务 Python 文件、正式运行器及执行夹具哈希与原失败样例完全相同；217 个冻结文件运行前后相同，包含原材料、Core、schema 和隔离检查入口。原四份本机逐例报告字节不变。补验的归一化输入、合成 Issue 初态、schema、业务/运行器哈希及任务预算均与原 DS variant 2 相同。新目录开始时不存在，运行器创建空会话和空动作账本；原任务数据库没有被恢复或拼装。

## 独立复核及回归复用

本轮仅安排一次新增证据的独立只读复核，不重复全套代码对抗。[独立复核](evidence/issue-supplement-independent.json)得到 `task_passed=true / evidence_valid=true`：原 13 断言、冻结 helper 9 项、比较检查 4 项、证据检查 17 项全部通过；逐一核验 217 文件冻结、22–27 请求关联及真实更新/读取记录。仅以 `mode=ro&immutable=1` 重开本轮新库，消息、动作和事件一致，数据库前后 SHA256 均为 `85fe5e4588d98d2b5a7c7395166751d0efadcfddb94f60944680cf7e41296f26`。未运行模型、服务、回归或重开旧数据库。

审查记录了进度标签格式化限制，以及新空初态由冻结运行器的拒绝覆盖门禁、开跑前记录、首请求和新库证据共同支持，审查者并非亲见开跑。公开冻结清单比原 preflight 多出的 `all_frozen_files_unchanged_after=true` 是导出时的派生断言，已由独立逐文件核对验证，不是原始任务数据变更。

冻结代码复用 [原离线与独立结论](ISSUE_TASK.md#离线验证与独立对抗)：485 项全量与最后一行范围修正后的 3+19+21 项定向复验，以及 39 项运行器检查。没有重跑这些测试、文件或 GLM 案例。原双实例白纸交接保持可读，本轮按用户限定只复核新增证据，不重复安排其他代理。

## 可复现入口

本次实际执行一次的命令如下。它不是继续消耗额度的授权；此次补验已结束，同一路径会拒绝覆盖既有证据。

```bash
PY=../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --scenario issue --source-root . --private-config ../tianyi-repair-batch-01/.env --provider deepseek --variant 2 --data-dir D:/TianyiRepair/issue-supplement-20261014/live-ds-2 --ledger D:/TianyiRepair/issue-task-20261014/http-ledger.json --initial-report D:/TianyiRepair/issue-task-20261014/live-ds-1/issue-model.json --initial-report D:/TianyiRepair/issue-task-20261014/live-glm-1/issue-model.json
```

只有原运行器选择获准模型连接字段。Core 动态导入前沿用独立配置/数据、Mock 初始化、禁 TTS/wake/真实 MCP 和越界访问守卫；真实 Provider 随后接入同一聊天入口，GitHub 传输为合成服务。新增持久库保留于 `D:/TianyiRepair/issue-supplement-20261014/live-ds-2/db`，数据库、凭据、连接端点和模型推理不入库。

本机原始字节哈希与路径脱敏后的公开 JSON 哈希分别记录于 manifest；Git 远端按固定提交的 blob SHA 回读核对。原发布报告、失败及已通过记录不覆盖，生产库影响未知的历史记录仍保留。

本范围当前无剩余流程验收阻塞，可交 Manager 收尾；连接稳定性、真实 GitHub 集成、任意自然语言任务及 A4 其他开放项仍不在通过声明内。TTS 固定版本 `969f4e293a8abbf4b8f153e8551b2fbff93098bf` 不变。

[提交前检查](evidence/issue-supplement-final-checks.json)确认冻结文件和旧四例报告未变、公开证据哈希一致、链接有效，暂存内容通过秘密/大小及 `git diff --check`。公开隔离文档入口返回 `DOCS_CONSISTENCY_OK / DOCS_ISOLATION_OK`，只发现 485 项测试数，没有执行旧回归。最终提交与候选分支远端回读以交付消息的固定 SHA 为准。
