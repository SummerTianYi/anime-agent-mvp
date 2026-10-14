# Provider API 响应解析边界

接手提交 `e72bb06419cea50fefb5604181930a713779c4c3`，工作树起初干净，沿授权候选分支 `codex/root-cause-repair-batch01-followup-20261012` 定向修改。依据 [BASELINE_CLOSURE](BASELINE_CLOSURE.md) 的 R2-RC16，本轮只处理现有 OpenAI-compatible / Anthropic-compatible API 响应及必要的工具批次预检，不改人物输出合同、权限、工具 schema、记忆规则或通用 A4 核对器。

**本轮四项通过：异常受控、没有新增错误操作、已有回执保留、正常接口未被误伤。** 其中真实接口证据包含首次连接超时和补验，不宣称零故障。仅关闭现有 Provider API 解析子问题，A4及底座整体仍开放。

## 原问题、修后与正常对照

测试从网络返回的原始 bytes 注入真实 Provider 的 `_request`，经过原有传输包装、`complete` / `complete_with_tools`、实际解析器；集成测试继续经过实际 `handle_chat`、MemoryStore、ActionLedger 和带副作用计数的合成服务。没有仅给 Agent Loop 预先整理好的结果来证明解析能力。合成发送服务使用 `.invalid` 地址，审计夹具拒绝真实网络、生产库、任意落盘及进程启动。

| 输入或安排 | 修前实际观察 | 修后与对照 |
|---|---|---|
| 空 bytes、损坏 UTF-8、残缺 JSON、null/数组/数字顶层 | 部分路径越过受控异常出口 | 固定、安全的 ProviderError；不展示原始响应或 Python 异常栈 |
| OpenAI `message=null`、错误字段类型；`content=null` 且无调用 | AttributeError、字符串 `None` 或空正常 turn | 均拒绝；不字符串化非文本 |
| 工具参数坏 JSON、null、数组、数字、缺失参数 | 旧路径会以 `{}` 代替部分坏参数 | 拒绝，不补参数，不猜工具名或调用 ID |
| 同响应合法调用在前、损坏调用在后，及反序 | 坏尾部不能在执行前可靠阻断前部 | 整批拒绝，新增票据 0、合成副作用 0 |
| 结构合法但 schema 不合法的尾部，含第26项超出执行预算的未知工具 | 前部可能先进入提案/执行 | 整批合同预检，前部也不派发；沿用既有有界参数纠正回合 |
| `content=null` / 空正文，合法零参数工具 `{}` | 合法旧能力 | 两适配均保留，实际 handle_chat 执行一次；JSON 字符串 `{}` 也兼容 |
| 普通中文、OpenAI 文本块、Anthropic text/thinking/redacted_thinking | 合法旧能力 | 正常保留；只有 thinking、无可交付文本/调用的响应仍算空回复 |
| 操作已成功 / 明确失败 / unknown，随后补答损坏 | 已有回执恢复在部分错误上本就成立 | 扩大到统一受控解析错误；真实状态保留、合成执行仍恰好一次，unknown 不变成“没执行” |

修前主测试19个方法记录80个失败子项、17个错误子项，**这些不是97次独立业务失败**；正常聊天夹具最初漏了既有 `decision` 合同，该夹具失败单列，不算产品缺陷。修正夹具后主19项全部通过。修前已通过的 JSON 错误回执恢复属于正常对照，不把它写成新修复。见 [修前证据](evidence/provider-primary-red.json)、[逐轮主回归](evidence/provider-primary-runs.json)；原有 Provider/Anthropic/Loop 54项基线全过，见 [基线](evidence/provider-baseline.json)。

## 最小实现

- 新增 [provider_response.py](../../../../services/agent-core/agent_core/provider_response.py)：严格 UTF-8/JSON、重复键、非有限数、递归/非法 surrogate、文本块、工具结构与对象参数校验。两个适配共用小型校验器，整体通过后才返回调用集合；OpenAI 保留首个 choice 策略，不把互斥候选合并执行。
- [main.py](../../../../services/agent-core/agent_core/main.py) 两适配将协议错误转换为既有 ProviderError。Anthropic 显式 role/type 必须是 assistant/message，省略字段的旧最小格式仍兼容。HTTP 状态本身不再等于工具不支持：只对有界读取的结构化、明确“不支持 tools”错误保留既有无工具降级；坏 JSON 或普通参数错误不降级。错误正文不进入 UI。错误体最多16KiB，调用方最多等2秒，读取与关闭都在线程内，避免关闭争用阻塞事件循环。
- [agent_loop.py](../../../../services/agent-core/agent_core/agent_loop.py) 在任何调用执行前检查完整集合的既有 schema/任务合同，包括执行预算以外的尾项。不增加协议重试、模型切换或 Mock 成功路径。既有传输恢复与 schema 纠正机制保持原样。
- 回执恢复复用原 `handle_chat` ProviderError 出口及 `task_delivery`，没有修改账本、执行权限和回执生成规则。正常解析不等于授予执行权限。

## 一次独立差异审查

`provider_response_review` 未参与初始实现，独占新增 [独立测试](../../../../services/agent-core/tests/test_provider_response_review.py)，主执行按发现修补后由同一审查者复验。冻结19项全部通过，未解决 CRITICAL/HIGH 为0，结论仅为 `approve_targeted_delta`。见 [逐轮记录](evidence/provider-independent-runs.json) 和 [独立结论](evidence/provider-independent-conclusion.json)。

| 独立反例 | 首次发现 | 处置及结果 |
|---|---|---|
| HTTP400/404/422 搭配残缺错误体，两适配 | 错误变成 ToolsUnsupported，触发第二次 plain 请求并交付“伪正常补答” | 固定受控错误，仅1次请求；显式 no tools / does not support tools 等正常降级仍通过 |
| Anthropic HTTP403 的字符串或对象型 error.message | 合成 Traceback 内容进入 core.error | 固定宿主诊断，不泄漏正文 |
| Anthropic `role=user` / `type=error` 含合法 tool_use | 首个反例产生待确认票据，尚未执行 | 显式 envelope 校验；最终票据和副作用均0，缺省及合法 envelope 控制通过 |
| ObservedProvider 遥测遇 escaped surrogate | 遥测 UTF-8 保存可能先于真实解析器抛错 | 先检查可编码性，只存错误类型/hash；原 bytes 仍交给真实 Provider，实际 handle_chat 受控交付 |
| HTTP 读取超时后同步 close | 静态审查发现可能在事件循环等待读锁 | read/close 同置 worker；本项为源码审查结论，不冒称真实慢连接压力实测 |

独立首次13项中4个红子项属于夹具遗漏旧5xx重试或 schema 纠正响应；改为403及补正常纠正响应后，14项中仍有8个真实失败子项。追加 envelope 反例形成19项，保留4个 envelope 红子项，修后19项全过。原始失败不覆盖。其他反例包括深层 JSON、嵌套重复目标键、混合坏补答、超预算尾项以及成功/失败/unknown 的真实回执。

## 冻结回归与隔离

同一业务源码下 **385项受影响 Core 回归通过**：Provider75（含主19、独立19）、Anthropic10、Agent Loop7、记忆95、存储19、Harness73、文件20、Issue13、邮件10、会话可见性4、WebSocket3、通道互斥12、交付4、权限11、原流程交界16、待办13。没有重复累加审查运行次数。见 [最终回归](evidence/provider-final-regressions.json)。当前可发现669项，未执行全量 Core 或统一终验。

既有共享运行器预算/隔离38项及新 provider 离线聊天+文件13项检查通过，见 [共享运行器](evidence/provider-shared-runner.json)、[离线入口](evidence/provider-offline.json)。直接运行旧 `file_runner_review.py` 时，其历史 AST 夹具缺少现有 `verified_task` 命名空间而中断；没有修改旧审查脚本或伪造 PASS，见 [限制记录](evidence/provider-runner-first-limitation.json)。本轮采用当前共享运行器检查，并由独立测试提取实际 ObservedProvider 验证遥测路径。

文档门禁返回 `DOCS_CONSISTENCY_OK` 与 `DOCS_ISOLATION_OK`，发现669项与当前状态文档一致。变更 Python 编译、`git diff --check` 及暂存凭据/数据/大文件检查通过；发现数量不等于全量运行成绩。

业务冻结 SHA256（本机原始源码字节；Git 换行规范化另计）：

```text
main.py               a9ca55441d7aca689539d233623e6e70e72bf77b29cf7f6a8d345f8c6ff4fc80
provider_response.py  adc73ffd4e02cb1c3aa2676e154debecda02839e421570439b69758ce584c6be
agent_loop.py         3ee95f468fe71b864c904ec29f5ec325647423cb7c4c166281dbd2cce13c5039
```

## 真实 DS / GLM 接口结果

通过原 `file_models.py --scenario provider`，在导入 Core 前设置独立配置和新测试库；只读取显式选择配置中的连接字段。正常聊天经实际 complete 与 handle_chat，文件请求经实际 complete_with_tools、确认票据、受限目录 write_file/read_file 与最终交付。新场景沿用原隔离审计、请求互斥锁、按HTTP派发前计数和线程退出收尾；没有另建预算系统。

| 模型/轮次 | 正常聊天 | 短文件流程 | HTTP次数 | 耗时（秒） |
|---|---|---|---:|---:|
| [DS 首次](evidence/provider-live-deepseek.json) | 请求超时，无正常回答 | 通过，真实写读与回执 | 6 | 138.047 |
| [GLM 首次](evidence/provider-live-glm.json) | 通过 | 提案请求超时，0票据/0写入 | 2 | 55.86 |
| [DS 连接故障补验](evidence/provider-live-deepseek-supplement.json) | 通过 | 通过，真实写读与回执 | 6 | 82.641 |
| [GLM 连接故障补验](evidence/provider-live-glm-supplement.json) | 通过 | 通过，真实写读与回执 | 6 | 62.219 |

本阶段实际 **20 次 HTTP**，四轮累计 338.767 秒；原计数账本为完整组预留48次，并未为用完额度扩样。见 [逐请求账本](evidence/provider-live-http.json)。首次DS的聊天与执行后补答各45秒超时；GLM的文件提案请求45秒超时，均无可交给解析器的响应字节。定位为传输超时后，每模型只安排一次全新目录的同协议补验，业务代码、运行器、schema、45秒预算和判据完全不变；两次均通过，未循环刷成功。

DS首次及补验、GLM补验的文件初提案省略“第一行/第二行”标签，由既有逐字内容合同拒绝，模型在原有纠正回合提供正确参数；确认后重复提出写入被旧账本防重放拦住，实际写入各一次。首次DS补答超时仍交付完整文件原文及真实任务完成回执；这些不是新解析器补造参数或新增重试。两模型合法空正文 tool_calls 均由真实接口提出并通过。

真实接口结果只证明这两种已配置模型的所测正常路径；未配置的Anthropic协议只有离线验证。原始失败与所有补验均入证据，耗时和请求数包含失败，不把补验覆盖成首次全绿。

## 保留、回退及剩余阻断

MemoryStore、记忆更正、ActionLedger、权限、工具 schema、文件/Issue/邮件任务与交付模块均未改；旧记忆报告、取消交界报告、模型/重启结果及全部既有证据逐项与接手提交比对保持，见 [保留核对](evidence/provider-preservation.json)。本轮只重跑受影响确定性回归，没有重跑旧六条记忆模型序列或旧 Issue/邮件真实样例。数据库、凭据和原始日志不入仓；发布 JSON 脱敏，原件与发布件 hash 分开记录于 [证据清单](evidence/provider-manifest.json)。

没有数据库 schema 变更、迁移或生产恢复。回退本轮业务改动可恢复接手版本的 main/agent_loop 并移除新增校验模块；会重新引入本报告的解析漏洞，不能作为常规运行建议。无需回退或恢复数据库，已成功/unknown 的操作记录必须继续保留，禁止因回退重放。

关闭范围仅为 **R2-RC16 的现有 Provider API 解析子问题及本轮发现的对应错误衔接**。R2-RC16 中人物输出 `reply` 合同、历史孤立左花括号首次来源等未在本轮关闭；通用 A4 核对器继续未接入，通用自由正文与真实执行证据绑定仍是阻断。R2-RC15 命令分词、R2-RC17 写失败临时文件、R2-RC18 前台窗口装配、R2-RC19 factory 重载装配等其他阶段事项继续保留。Anthropic-compatible 只有离线字节层与实际聊天入口证据，没有未配置协议的真实接口证明。网络稳定性不由少量成功样例保证。

未操作生产库、当前 Godot/Core/TTS 或真实外部业务；不部署、不合并 main。全部阶段阻断处理完毕后，再以同一最终冻结版本进行统一全量终验；本轮停在 Manager 验收点。

## 复现入口

在仓库根目录的 Git Bash 使用既有隔离 venv 的 Windows Python。每次分配新数据目录及报告路径；隔离运行器拒绝覆盖旧证据，先设 Mock/TTS0/wake0/MCP空再导入实际 Core，不启动真实服务。合成测试复用审计夹具、MemoryStore 与当前主源码。

```bash
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/batch-01/repro/followup_regressions.py --source-root . --data-dir <fresh-data> --output <fresh-report.json> --pattern 'test_provider_response*.py'
# 受影响组：provider, anthropic_provider, agent_loop, memory, storage,
# harness, file_task, issue_task, email_task, session_visibility, main_ws,
# channel_exclusivity, followup_delivery, permissions, baseline_closure, pending_status
# 每组使用 test_<group>*.py 和全新目录。
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --scenario provider --source-root . --data-dir <fresh-offline> --ledger <offline-ledger.json> --provider deepseek --offline
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/a4-pilot/repro/email_runner_review.py --data-dir <fresh-runner-data> --output <runner-report.json>
# 仅在已有模型请求授权时：去掉 --offline，明确指定连接配置；两个模型串行共享同一计数账本。
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B docs/assessments/root-cause-repair/a4-pilot/repro/file_models.py --scenario provider --source-root . --data-dir <fresh-live> --ledger <live-ledger.json> --provider <deepseek-or-glm> --private-config <connection-config>
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 <python> -B scripts/check_docs_consistency.py
```

修前主反例可将接手提交导出到独立源码目录，保留当前测试，运行 `--source-root <baseline-export>` 并设置 `HARNESS_REVIEW_CORE_ROOT=<baseline-export>/services/agent-core`。独立审查的中间红例绑定各自 JSON 中的源码 hash，不把最终测试的所有新案例错误归为接手时已执行的案例。
