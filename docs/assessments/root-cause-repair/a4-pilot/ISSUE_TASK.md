# Issue 标题更新与新读取核验

本项实现及定向离线检查通过，真实模型验收 **3/4，部分完成**。DS、GLM 首轮均完成真提案、正确更新、新读取核验和准确交付；扩样 GLM 通过，DS 在更新提案前连接超时，保留失败且未重跑。本阶段使用 **21/40 次 HTTP**，到此停止。剩余阻塞是 DS 第二个编号/标题样本尚无完整执行证据，不能以安全停止替代任务成功。

本报告限于后台合成 MCP。接手基线 `bc58e3135385c49dede46794fb6a757b4a7d0ec4`，候选分支 `codex/root-cause-repair-batch01-followup-20261012`。接手 Git 根、HEAD、分支相符且工作树干净。未部署、未合并 main、未操作当前 Godot/Core/TTS，未访问生产历史或修改真实 GitHub Issue。停在 Manager 验收点，不宣布真实 GitHub 集成或 A4 整体验收通过。

## 范围和实现

自然语言原任务指定仓库、Issue 编号和逐字标题，要求仅修改标题并重新读取核验。模型自行生成工具调用；用户只输入原任务和界面实际展示票据的“确认”。MCP 默认 ASK 保持原样，因此更新前读取、更新和更新后读取分别需要原生确认。确认只批准已展示的一张票据。

直接复用文件流程的 `handle_chat → run_agent_loop → validate_proposal → permission → ActionLedger → receipt delivery`，原有单次纠正、共享任务预算、参数版本、写入去重、权限重验、unknown 禁止自动重写以及状态查询均保留。`verified_task.py` 只将原有文件交付钩子分派给文件或 Issue 窄适配，没有复制一套聊天或授权循环。`file_task.py`、Provider、工具 schema、权限规则、存储及 TTS 未改。

新增 `issue_task.py` 从明确任务提取目标与标题，更新参数只允许 method/owner/repo/issue_number/title。真实读取建立原字段基线，额外字段或错误目标在提案前拒绝；未读到可核验基线不能更新。宿主不填工具参数、不合成工具调用，不以模型自报 chat 证明完成。

`ActionLedger.propose` 新增只读专用的 `read_after` 代次：参数相同但本次成功更新不同，产生新的待确认读取票据。写操作的参数哈希与去重保持原规则。`main.py` 在实际获权读取的派发前捕获本任务已成功的更新 ID，读取结果落入现有 `tool.result` 事件。复用旧账本结果不会生成一条新访问记录。

最终完成必须同时有本任务成功更新和实际后置读取，同一仓库/编号、逐字标题，以及正文、状态、标签、负责人、里程碑等用户字段的前后快照一致。最新读取缺字段、错对象、超时或不一致均不通过；单纯原来就有同标题、旧读取或写入回执不能代替后置读取。成功交付由宿主给出仓库、编号、标题和读取引用；写入成功但核验不足分别报告，不重写。

## 离线验证与独立对抗

变更前先通过原文件 20 项回归，再用实际 `handle_chat` 复现：无调用口头待办可放行、旧读取可被说成更新、额外字段可进入票据、同参数后置读取复用旧项。首次结果保留。主执行的定向测试覆盖 13 项，所有操作均针对可应用额外字段的合成服务，故额外字段保护来自产品门禁。

独立业务审查提出并复现“不要更新其他字段”的否定范围、反引号包裹仓库名导致门禁未启用，以及普通解释误激活。主执行收窄判定边界后，独立 21 项通过；包括标题内控制词/引号、跨任务旧基线、跨会话票据、权限撤回、unknown 重开、并发双确认/拒绝、ASK/ALLOW 读取和文件对照。证据 [首次](evidence/issue-independent-1.json)、[第二轮](evidence/issue-independent-2.json)、[最终](evidence/issue-independent-5.json)、[冻结绑定](evidence/issue-independent-5-binding.json)。首次证据中的夹具问题与产品失败分列，不改写为产品通过。

[第一轮全量](evidence/issue-full1.json)发现两条原 A4 用例被过宽的新入口拦截；另一个反引号失败属于运行时尚未修正的旧导入版本。修复后 [485 项全量](evidence/issue-full-final.json)通过。随后独立 [scope 首次](evidence/issue-independent-scope-2.json)发现“无需重新读取”仍误激活，最后仅改一行否定范围判定，复验 [3 项 scope](evidence/issue-independent-scope-3.json)、[原 A4 19 项](evidence/issue-a4-final.json)及上述独立 21 项全部通过。未变部分复用 485 项结果；明确区分全量版本与最终一行差异，不把此前快照冒充最终源码。原文件 [修前 20 项](evidence/issue-baseline-file.json)、[修后 20 项](evidence/issue-file-after1.json)与全量中的文件测试均通过。

独立 Python/运行器审查要求将执行夹具加入源码绑定、将扩样凭据绑定同一 40 次账本和指定两个模型、比较初态与任务预算，以及正确区分纯连接失败和安全失败。修后 39 项通过，两个审查者互审各自测试入口。证据 [39 项运行器复核](evidence/issue-runner-review-final.json)、[最终小差异绑定](evidence/issue-runner-review-final-binding.json)，前轮诊断及其夹具问题保留。实际业务变更仅 main/actions 和两个新适配模块，其他 22 个 Core 文件与基线一致，见 [逐文件清单](evidence/issue-source-manifest.json)。

## 真实模型逐例结果

四次运行使用同一冻结业务源码、运行器、真实工具 schema 和 standard 任务预算（6 轮、12 工具调用、1 次纠正、45 秒超时）。每个 variant 的两模型任务表达与空会话/空账本/合成 Issue 初态相同。没有预填意图、工具调用或动作结果；只有模型连接由原 Provider 适配层选择。

| 顺序 / 证据 | 模型 / Issue / 标题 | HTTP 索引（次数） | 真提案 / 正确更新 / 新读取核验 / 准确交付 | 结果 |
|---|---|---|---|---|
| [DS 1](evidence/issue-live-ds-1.json) | Deepseek-v4-flash / #17 / 春日核验 READY-17：3cm | 1–6（6） | 是 / 是 / 是 / 是 | PASS；最后模型补答超时，但此前实际后置读取已完成，宿主按真实记录交付 |
| [GLM 1](evidence/issue-live-glm-1.json) | GLM-5.2 / #17 / 春日核验 READY-17：3cm | 7–12（6） | 是 / 是 / 是 / 是 | PASS |
| [DS 2](evidence/issue-live-ds-2.json) | Deepseek-v4-flash / #29 / 蓝桥第二次核验：7月12日 / 42kg | 13–15（3） | 否 / 否 / 否 / 否 | FAIL：connection_or_protocol；45 秒超时发生在更新提案之前 |
| [GLM 2](evidence/issue-live-glm-2.json) | GLM-5.2 / #29 / 蓝桥第二次核验：7月12日 / 42kg | 16–21（6） | 是 / 是 / 是 / 是 | PASS；原计划扩样，不是替代 DS 失败 |

所有目标仓库为合成 `SummerTianYi/a4-synthetic`。三个成功样本均实际访问服务：读取旧值 → 更新一次 → 重新读取一次。确认前零写入，更新只传标题字段，重开消息/账本/读取事件一致；再次确认及进度查询没有新增模型请求或写入。全部 13 项验收断言通过，未用写入回执或缓存结果替代后置读取。

DS 第二例仅有一次实际更新前读取。第 14 次 HTTP 再次提出同参数读取，原账本复用该读取；第 15 次 HTTP 超时，未形成更新票据、未写入，也没有后置读取。交付明确“尚无有效标题更新提案；未生成更新票据”。原判卷的 `preserved_fields=false` 是“原对象替换为期望新标题后整体相等”这一完整目标断言失败，实际正文等保留字段及旧标题均未变化，不能误读成发生了额外字段写入。独立负例证据保留 [失败核对](evidence/issue-runner-review-ds2-failure.json)。DS 第一例的超时发生在真实后置读取之后；两者交付不同来自执行证据，不是模型名称特判。

[冻结 HTTP 账本](evidence/issue-http-ledger.json)索引连续 1–21，与四例请求一一对应。首轮均通过后才扩样；每次开跑分别剩余 40、34、28、25，均满足完整案例预留 18 个槽位。纠正和传输重试全部计数，分发前落盘、禁用自动重定向，迟到线程结束后才释放运行锁。没有另行协议探测、失败重跑或模型替换，不消耗旧文件 30 次及补验 8 次额度，也未重跑文件真实模型案例。剩余 19 次未使用。

最终独立只读复核 [四例与完整账本](evidence/issue-runner-review-live-final.json) **44/44 通过**，绑定最终源码、四份报告及本轮数据库哈希，零模型/业务请求。证据有效与任务通过分别记录：`evidence_verified=true` 不改变 DS 第二例的 FAIL，`all_tasks_passed=false`。

另一独立审查者复核失败专用判据、冻结账本及报告收尾差异，[11 项核对通过](evidence/issue-independent-closure.json)。唯一文档问题是给 scope 复现脚本多写了一个不存在的 `--source-root` 参数，现已删除；业务源码无后续修改。

## 复现入口

使用已有 Python 环境，命令在仓库根目录运行。每次 data-dir 必须不存在；ledger 在同一阶段复用。先选择 --offline 验证隔离，再使用获准的模型连接配置。文件入口原默认行为与补验门禁保持。

```bash
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 ../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe -B \
  docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py \
  --scenario issue --source-root . --offline \
  --data-dir D:/TianyiRepair/issue-repro/offline --ledger D:/TianyiRepair/issue-repro/offline-http.json

# 实际模型：去掉 --offline；两个 provider 使用同一 ledger，独立 data-dir。
# --private-config <获准连接配置> --provider deepseek|glm --variant 1
# variant 2 另加两份首轮 --initial-report <issue-model.json>，门禁要求同源同初态且都通过。

PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 ../tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe -B \
  docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py \
  --source-root . --data-dir D:/TianyiRepair/issue-repro/core \
  --output D:/TianyiRepair/issue-repro/core.json --pattern test_issue_task.py
```

同样入口将 pattern 换成 `test_issue_adversarial.py` 可跑独立反例。真实 schema 复用 `root-cause-audit/evidence/mcp-schema.json` 的 issue_read/issue_write 原始声明；合成服务只替换传输端，正常化、权限和账本仍走实际 Core。

独立小范围反例入口为 `repro/issue_review.py --data-dir <新目录> --output <新JSON>`；运行器离线预算/隔离复核为 `repro/issue_runner_review.py --data-dir <新目录> --output <新JSON>`。运行器的 `--live-report`（可重复）及 `--failed-report` 分别只读核验成功与失败报告，`--live-ledger` 必须指向已解除运行锁的本阶段账本；不会调用模型。所有命令均用上面的 Python 环境和 `-B`。

本轮数据保存在 `D:/TianyiRepair/issue-task-20261014/live-{ds-1,glm-1,ds-2,glm-2}/db`，只含本轮合成材料。导入 Core 前设置并核验独立数据与配置，禁 TTS/wake/真实 MCP；生产路径和外部业务由隔离守卫阻断。只读获准模型连接字段，公开 JSON 省略凭据、端点及模型推理，并替换本地路径为 `<issue-phase>`/`<repo>`。原报告及旧失败/通过材料均保留；本轮仅复用并扩展运行器场景入口。

哈希口径：独立报告的原始报告/数据库哈希绑定本机原字节；公开证据只替换路径字符串并规范 JSON 换行，[导出清单](evidence/issue-evidence-export.json)逐一记录原始与公开 SHA256，原字节另保留于本轮隔离目录。最早失败的 traceback 同样脱敏，判定、失败内容及状态未修改。Git 可能规范 CRLF 为 LF，远端回读最终以固定提交的 Git blob SHA 核对。

## 剩余边界

本项不认证真实 GitHub 服务、任意模型或任意自然语言操作。适配只处理明确 Issue 标题任务；未能明确提取的参数需要澄清。GitHub 返回必须包含目标身份及可比较的用户字段，缺失时明确未完成。历史、动作和读取事件重开不等于实现了所有历史任务自动恢复。多 Issue、其他字段编辑、邮件、记忆等不在本轮范围。

原 A4 首轮无票据假声明、只读摘要夹带写入等范围外开放项，以及原文档检查默认数据库影响未知记录，继续保留于原 REPORT。生产库未检查、恢复或清理。TTS 固定版本 `969f4e293a8abbf4b8f153e8551b2fbff93098bf` 不变。停在 Manager 验收点。

[提交前检查](evidence/issue-final-checks.json)：公开隔离入口得到 `DOCS_CONSISTENCY_OK / DOCS_ISOLATION_OK`，发现 485 项但没有借文档检查重跑全部测试；暂存 Python/JSON、秘密及 50 MB 限制检查通过。原目录 95 份既有材料不变，旧文件运行器是唯一有意修改的既有材料。最后仅删除独立测试文件尾部一个多余空行以通过 `git diff --check`，AST 相等和前后哈希已记录；业务、模型用例及执行夹具仍与四例实测完全一致。没有相关前端或语音源码变化，本轮未运行桌面、Godot、TTS 或真实 GitHub 验收。
