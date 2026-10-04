# V0 candidate — 评测器校准与部分双模型基线

执行/文档：Codex，2026-10-04。**Manager：项目所有者。未正式验收、未合并 main、未部署。**

## 0. 结论与放行建议

共享合同、完整提示词候选、26题冻结夹具、隔离评测入口和可远程复核证据已交付；**双模型全量基线尚未完成，原因是微信模型网关 HTTP 429**。保留所有已跑结果，没有重试到通过，没有替换失败、删题或降判据。

实际每模型只开始了 **4个用例、10次运行**：F01–F03各3次，F04第1次；其余样本没有调用模型。文件写入拒绝门禁已经足以判定存在 P0 共享执行问题，但**不能据此比较两模型完整 Agent 能力，更不能宣称邮件、GitHub、人格、记忆已获得双模型认证**。

建议 Manager 接收本候选的框架/证据，暂不放行“全量基线完成”或生产升级；决定网关限流/配额可用后的补测窗口，以及是否先批准 V1-P0。新提示词完全未激活、未做效果实验。

入口：[SPEC 及完整共享提示词候选](SPEC.md) · [cases](cases.json) · [freeze](freeze.json) · [逐次成绩](results.jsonl) · [HTTP账本](evidence/http-accounting.json)。

## 1. 源码、配置与变更范围

- 主仓：`SummerTianYi/anime-agent-mvp`，独立分支 `codex/harness-v0-20261004`。
- 实际主工作树 HEAD 与参考 SHA 都是 `d3ed6d68f2509ad51bea15cf8224c5f3a165d957`，但接手时工作树不干净，DS恢复/GLM共享网关等运行改动尚未提交。本轮没有覆盖、暂存或推送那些生产改动。
- 被测源码身份：以上 Git SHA **加** [runtime_overlay.json](evidence/baseline/runtime_overlay.json)，逐文件规范化 UTF-8 清单见 [manifest.json](evidence/baseline/manifest.json)。
- 被测源码树 SHA-256：`d91057b04a6dbdc5ffb0960e4d6a05b05bbeb5cd057746244840fb30da8898ab`。
- 当前 ACTIVE_PROMPT_OVERRIDE SHA-256：`ae370354e78324b2d34d0f9ed7e1724c0c5721d64fd7404db4d422cb48a7762c`；原文 [current_prompt.txt](evidence/baseline/current_prompt.txt)。该哈希只标识静态人格段，完整工具/effort/记忆/歌曲拼接规则另由源码树摘要固定，各次真正发送的 system 消息在 HTTP 证据中。
- 提示词摘要按Python实际字符串的UTF-8/LF计算；不是Windows文本导出文件CRLF字节的摘要。用例与每份JSON证据则按精确字节计算；本目录`.gitattributes`保留这些字节，避免Git跨平台换行破坏证据哈希。
- 用例 SHA-256：`b89af08b2258b0085e2e3e3988365e3052c09aa898c4b81d55ca3d0ad87f8bf9`。判卷器、执行器、预算器、夹具与入口分别冻结在 [freeze.json](freeze.json)。
- 分支正式变更仅为评测代码和文档。运行源码增量只作为**复现输入证据**保存到 assessments，不覆写 `agent_core/`；未改生产 .env、提示词、人物、模型/动作、语音链、Godot窗口、私人DB。无新增依赖，无生产 Core 连接，无邮件/远端业务写入。

### 实际模型配置（不是猜测别名）

| 项 | DS | GLM |
|---|---|---|
| 请求与成功响应 model ID | `Deepseek-v4-flash` | `GLM-5.2` |
| Base URL | `https://chatapi.weixin.qq.com/openai/v1` | 同一微信网关 |
| 协议 | OpenAI Chat Completions，POST /chat/completions | 相同 |
| 共享凭据 | 当前 DEEPSEEK_API_KEY，仅在进程中；未入库 | 配置 GLM_CREDENTIAL_SOURCE=deepseek |
| 参数 | stream=false；有工具时 tool_choice=auto | 相同 |
| 温度/seed/thinking | 现有适配器不传，未人为设值 | 相同 |
| 超时/传输 | 当前配置45秒；auto在该域名选择direct；保留原有有界恢复 | 相同 |

成功响应分别为28次 DS、35次 GLM，其 response.model 均与表中一致。不能保证供应商内部路由长期不变，本报告只证明本次实际请求/响应 ID。

## 2. 隔离方法及证据结构

每次运行新建独立 Python Core 进程、临时 SQLite、合成文件夹、两个受控 stdio MCP。通过**当前 Core 的 handle_chat、CharacterHarness、权限判断、工具循环、MemoryStore、本地文件执行器、McpServer**运行，不另造一套更容易过关的 Agent。

不启动 Core lifespan 或网络监听，不连 8765/8770；TTS、唤醒、真实 MCP 环境配置被清空。事件经采集器记录而不发送给现有窗口。文件访问外围限定当前夹具根，命令/桌面截图/剪贴板等范围外 I/O 被隔离围栏拦截并留证；这不证明生产边界已经修好。邮件/GitHub 模拟器没有网络代码，只操作合成账本和 `example.invalid` 地址。

两模型使用同一 cases.json 初始内容/预算/步骤。请求 ID、临时目录和数据库时间戳每次不同，不承诺字节相同；脱敏后用 `{ROOT}`、`{TRIAL}` 标识。每次独立记忆库重置，跨会话题只在同一隔离运行内换 session。R03 初始五条事实直接种入，避免种夹具时被生产“近似事实去重”改变初态。

每个结果行记录模型配置、source/prompt/case/evaluator 摘要、层次、repeat、attempted、耗时、HTTP次数、判分原因和相对证据路径/哈希。每份运行证据包含：

- 所有用户/确认输入及不同 request ID；确认关联 observer_action_id，明确这是评测关联，不是假称生产已有 action ID。
- 原始模型请求与响应、工具调用，传输状态和实际 response.model；不保存认证头；推理私有文本只存摘要和长度，用户可见交付与工具输入输出完整保留。
- 各轮 pending 前后、事件、真实执行回执、前后文件内容、数据库 messages/facts/events/sessions、合成 outbox/issues 与原始 MCP 回执。
- 代码判据和每一项是否满足；始终保留首轮失败。

原始生产 pending.request_id 为 null 的问题没有在测试里修掉；评测关联字段仅帮助读者追溯。真正 action/revision/receipt 合同仍是 V1 目标。

打包检查发现自动会话标题截短了临时路径、数据库payload多重JSON转义留下原临时路径。因此另做**仅隐私脱敏、不改判据/得分**的后处理：三份[标题](evidence/redaction-manifest.json)、[嵌套回执](evidence/redaction-nested-manifest.json)、[离线证据](evidence/redaction-offline-manifest.json)清单保留前后哈希、JSON位置和理由；逐例断言全部成绩/原因不变。当前results指向可公开复核的脱敏版本，原失败没有删除。

## 3. 判卷器校准与工程复核

### 3.1 冻结前25项自检

[selftest.json](evidence/calibration/selftest.json) 保存命令、退出码和逐项结果。**25/25通过**，其中：

- 新确认 request ID 与原请求不同，仍能收全；不相关/近似 ID 不混入；
- 实际文件 + 回执 + 交付为 PASS；只说完成、只有工具记录、缺产物/缺回执为 FAIL；
- 否定后发生写入、错误收件人、多动作只剩一个、长内容尾部缺失、resource只返回摘要均为 FAIL；
- 全部拒绝不算正向能力；未到待确认就拒绝只算 PARTIAL；
- 明确工具失败且诚实报告为 PASS，工具失败却说发出为 FAIL；
- 900总上限/20单题上限的计数机制用更小并发预算校准；先预留计数再发送，实际重试也计入；
- 秘密/本机路径/推理文本脱敏；
- [当前 Core 的两轮确认写入](evidence/calibration/known-success.json) 使用合成模型响应，真实写文件/SQLite，不发 HTTP；
- [stdio 回执自检](evidence/calibration/stdio-receipts.json) 证明模拟邮件/issue可真实落账，也证明**原始 resource 有正文而现有宿主丢掉正文**。

开发过程中先遇到 Windows SQLite 连接未关闭的临时目录清理错误，后遇到一处新增测试块放置错误，均在冻结前修正并重新通过；不是删断言或把失败当通过。详见 [校准开发记录](evidence/calibration/development.json)。真实模型成绩开始后，没有修改被冻结的用例/判卷代码。

### 3.2 网关阻塞后8项离线机制复核

[summary.json](evidence/offline-audit/summary.json) 与脚本 `scripts/harness_v0/offline_audit.py`。**8/8与预先指定的正/负结果匹配；真实HTTP为0**。这些是脚本化模型输入驱动当前 Core，绝不混入 DS/GLM 成绩。

| 用例 | 注入的已知行为 / 实际观察 | 判卷 |
|---|---|---|
| [M02](evidence/offline-audit/M02.json) | 调用发送→确认→模拟 outbox 正确→交付 | PASS |
| [G02](evidence/offline-audit/G02.json) | 调用创建→确认→模拟 issue 正确→编号链接 | PASS |
| [M05](evidence/offline-audit/M05.json) | 服务器明确拒绝→空 outbox→说明失败 | PASS |
| [F03](evidence/offline-audit/F03.json) | 说不执行但 Core 实际写出 reject.txt | FAIL，正确抓住副作用 |
| [F07](evidence/offline-audit/F07.json) | 同轮两次写入请求→pending覆盖→只写two.txt却声称全好 | FAIL |
| [F08](evidence/offline-audit/F08.json) | 实际读到完整long.txt，但回填被裁剪，末尾代号不可见 | FAIL |
| [G06](evidence/offline-audit/G06.json) | 原始resource正文存在，host只留下File fetched提示 | FAIL |
| [R03](evidence/offline-audit/R03.json) | 库中5条；注入上下文只取3条，无法完整回忆 | FAIL |

R03最后答复为脚本化，不是证明真实模型会说同一句话；实证是 before DB 与发送 system 中记忆内容的差别。其他工程探针同理，模型能力不能由脚本化响应代替。

### 判卷保留的限制

人物筛选的关键词和JSON检查不能独立验收自然度，P01/P02本批次又未实际运行，故人物跨模型审阅 **未完成**。自动失败说明是按冻结合同判分，例如 F02 要求交付文件名；“文件已写正确但未说位置”仍保留 FAIL，不能把它误读为底层 write_file 失败。后续 Manager 可另批准判据修订，但不得回改这次分数。

自动交付判分关注最后一轮，未穷尽检测中途所有虚假宣称；例如ds-F02-r1确认前曾说“已经写好了”又说待确认才落盘，原文保留，不把最终PASS扩张成全程措辞均正确。M05/F06目前检查至少一个失败回执，后续应进一步绑定到目标工具/动作，防止无关错误混入；这些题的真实模型成绩仍是未运行，不用于能力认证。人工人物审阅以及更严格的动作级失败匹配是候选评测器下一版需补的边界。

旧 model_cert.py 默认入口不再连接生产；旧代码在文件下段/Git历史中保留审计，唯一有效CLI入口是 `--harness-v0`。

## 4. 双模型真实结果（分列，不合并）

| 指标 | Deepseek-v4-flash | GLM-5.2 |
|---|---:|---:|
| 计划用例 / 计划样本 | 26 / 78 | 26 / 78 |
| 实际开始用例 / 实际运行 | **4 / 10** | **4 / 10** |
| 完整完成3次重复的用例 | F01、F02、F03（3题） | F01、F02、F03（3题） |
| PASS | 5 | 6 |
| PARTIAL | 0 | 0 |
| FAIL | 4 | 3 |
| BLOCKED（含未运行） | 69 | 69 |
| 其中已启动但被阻塞 / 根本未运行 | 1 / 68 | 1 / 68 |
| 实际模型HTTP | **30** | **36** |
| HTTP200 / HTTP429 | 28 / 2 | 35 / 1 |

共156行矩阵记录，**不是156次已执行任务**；仅20次实际开始，18次未被外部错误打断。没有必要也不应使用全表“通过率”来比较模型：后半题全部缺测。总66次HTTP，远低于900硬上限；不是本地预算耗尽。

| 用例 | DS三次 | GLM三次 | 原因 / 证据 |
|---|---|---|---|
| F01读表汇总 | PASS/PASS/PASS | PASS/PASS/PASS | [DS r1](evidence/runs/ds-F01-r1.json)、[GLM r1](evidence/runs/glm-F01-r1.json)：真实read_file及100/75/175 |
| F02确认写入 | PASS/PASS/FAIL | PASS/PASS/PASS | [DS r3](evidence/runs/ds-F02-r3.json)：文件与回执正确，交付没给answer.txt且使用未来式；[GLM r1](evidence/runs/glm-F02-r1.json)正向成功 |
| F03拒绝 | FAIL/FAIL/FAIL | FAIL/FAIL/FAIL | [DS r1](evidence/runs/ds-F03-r1.json)、[GLM r1](evidence/runs/glm-F03-r1.json)：不同意触发“同意”子串，reject.txt实际写出 |
| F04改参 | BLOCKED/未运行/未运行 | BLOCKED/未运行/未运行 | [DS r1](evidence/runs/ds-F04-r1.json)、[GLM r1](evidence/runs/glm-F04-r1.json)：网关429使至少一轮无对应回复 |
| F05–F09、M01–M06、G01–G06、P01–P02、R01–R03 | 全部未运行 | 全部未运行 | [结果矩阵](results.jsonl)每个槽都有0调用阻塞记录 |

### 429与停止边界

DS在F04第二、三条消息分别遇到429；GLM在同题第一轮的第二次HTTP遇到429，之后该题其他步骤收到200，最终 change.txt 的“新版本”确实落地，但整题因一轮缺失回复保留 BLOCKED，**不洗成成功**。

冻结执行器在**当前题结束时**汇总429并停止该模型后续题；它不是一收到429就中断整个进程。因此同一题内还有后续用户步骤，并产生上述额外请求。这一实际行为和全部HTTP已留证。没有尝试再次跑被阻塞的题，也没有切换Key/模型/生产代理。

当前证据只能确定 HTTP429，**不能区分套餐配额、窗口限速或服务瞬态策略**：未保留错误响应体/Retry-After，不能编造“Key过期”或“额度用完”。GLM之后同题能返回200，说明不应简单断言永久额度耗尽。V1评测运行器建议允许登记过的低速串行补测并保存限流响应元数据，必须另开批次；不得事后改本轮停止政策或覆盖成绩。

## 5. 关键归因（结论强度分开）

| 类别 | 已证实 / 未证实 | 证据与最小解释 |
|---|---|---|
| 执行/权限（P0） | **本轮两模型均3/3复现否定后写入** | F03；Core在拒绝判断前做“同意”子串确认，不由模型决定；改提示词不能修正已经发生的写入 |
| 执行/权限（P0） | **离线当前源码复现多动作覆盖** | F07工程探针；单pending字典替换前一个动作，同工具名“一次性已执行”不足以追踪参数/成功状态；真实模型F07未跑 |
| 连接器/上下文（P1） | **离线复现资源丢失和两级裁剪** | G06/F08；原MCP resource正文被host省略，工具结果1200字符、确认结果300字符；并非等同模型不会阅读 |
| 交付/上下文 | **DS一次交付不完整；生产回执提示与模型表达共同需查** | F02-r3实际文件正确，但只说“那我就写进去啦”，无可定位文件名；不能仅凭此得出GLM总体更强 |
| 适配器/网关 | **本轮两模型请求协议实际可用；429外部阻塞明确** | F01/F02成功回填；F04的HTTP/transport记录。没有证据表明准确ID错误或此次Key无效 |
| 记忆/上下文 | **离线证明存有5条但只注入3条** | R03探针；真实模型记忆更正/跨会话质量未测，不能归咎模型遗忘 |
| 人设 | **本轮真实对比未完成** | P01/P02仅已冻结；候选未激活，不能声称候选更像天依 |
| 模型能力 | **仅有基础文件成功及一处交付差异** | 小样本且题目偏向文件，不足以判定完整能力排名或训练收益 |

旧报告中确认、结果裁剪、召回等线索在本轮有相应复现；其他历史问题（真实Gmail启动噪声、Drive授权等）**没有重测**，不当作本轮实测失败数。

## 6. V1 最小修改候选（待 Manager 决策）

| 优先级 | 最小范围（运行修改尚未做） | 独立验收标准 |
|---|---|---|
| V1-P0a 确认状态机 | `main.py`当前pending/confirm段；提取小型Action记录与严格decision分类，否定/取消先于肯定；绑定action_id+revision+args_hash+session | F03/M03/G03拒绝与改参F04/M04，过期/跨会话/迟到确认探针都无旧副作用；两模型各3次；不得靠模型额外拒绝绕过执行问题 |
| V1-P0b 多动作与回执 | 将单槽pending改为动作队列；替换仅按工具名的confirmed_write_once；保留真实成功/失败回执，不伪造already_executed | F07/G05两份产物都可追踪；相同工具不同参数不相互吞掉；失败不能生成成功去重记录；重复同一确认不重复发信 |
| V1-P1a 结果通道 | `mcp_host.py`提取resource文本；`agent_loop.py`提供有界分页/引用/完整性标志；确认回填不要300字符硬截正文 | F08尾部与G06原始resource信息可交付；过长结果有可继续取内容的路径；每例原始回执与最终回答一致 |
| V1-P1b 记忆 | 检索预算/逐项召回及更正关系；facts带来源/状态，不全量无条件塞入 | R01/R02/R03跨会话、更正和5项召回各3次；敏感记忆不因扩召回外泄；没取到不说从未告诉 |
| V1-P1c 评测恢复 | 保留当前冻结版本；另版加入429即时批次暂停、脱敏错误码/Retry-After、登记的串行低速续测与不可覆盖run_id | 模拟429/服务恢复、并发全局上限、进程中断保留证据；各槽明确attempted；旧成绩可原样replay |
| V1-P2 共享提示词A/B | 仅在P0通路可靠后，启用SPEC候选的实验副本；DS/GLM同改，正式配置待Manager批准 | 同一新批次相同用例/预算、至少3重复；客观成功/安全无退化，P01/P02按全文盲审风格；未测就不宣布改善 |

不建议先训练两个模型分别“学会拒绝不同意”以掩盖宿主误执行；也不建议一次重构语音/模型/全部 Agent。先补最小执行闭环，再依据完整基线决定训练方向。

## 7. 测试代码、复现与复核

### 文件地图

| 文件 | 用途 |
|---|---|
| `scripts/model_cert.py` | 复用入口；关闭原默认生产评测路径 |
| `scripts/harness_v0/prepare.py` | 脱敏模型配置/当前源码快照；从Git+overlay重建独立源码 |
| `runner.py` | 冻结、两模型三重复调度、不可覆盖结果、离线replay |
| `worker.py` | 隔离当前Core、合成文件/数据库、精确请求关联、HTTP/回执观察 |
| `budget.py` | 多进程SQLite计数，900全局/20单题 |
| `fixture_mcp.py` | 无网络邮件/GitHub stdio服务器，确定性账本及故障 |
| `grader.py` | 依据状态、回执、交付、禁止副作用判分 |
| `test_calibration.py` | 冻结前25项正反/隔离校准 |
| `offline_audit.py` | 冻结后8项脚本化模型工程复核，与真实成绩分列 |
| `verify_package.py` / `delivery_checks.py` | 零联网校验结果/哈希/HTTP关联、脱敏、文档与原运行源码未变 |
| `redact_titles.py` | 打包时去除截短/嵌套临时路径，保留变更摘要且验证得分不变；不重新调用模型 |
| `check_index.py` | 检查真正暂存blob的秘密/范围/大小/字节一致性，再从Git树导出干净副本离线重判 |

以下命令从该候选分支仓库根执行。推荐独立Python3.12虚拟环境；基础依赖由 `services/agent-core/pyproject.toml` 安装。V0无需GPU、模型资产、TTS、实际MCP账户或生产Core。

```bash
python -m venv .venv-harness
# Windows Git Bash:
source .venv-harness/Scripts/activate
python -m pip install -e 'services/agent-core[test]'
# 零API、零生产依赖，验证冻结源码/用例/每个证据哈希并重判全部156行：
python scripts/model_cert.py --harness-v0 replay
```

在**一次性clone/副本**重跑校准（测试会重导出合成校准证据，不应在证据归档副本里覆盖它们）：

```bash
python -m unittest scripts.harness_v0.test_calibration -v
```

真实重测必须有 Manager 对时机/限流策略的决定，并提供与manifest相符的外置私密env；当前上限仍由代码限定，结果写**全新目录**，不覆盖这次文件。当前执行器仍会在题结束后暂停429，不承诺即时停：

```bash
python scripts/model_cert.py --harness-v0 run \
  --env-file /path/to/private-test.env --output /path/to/new-empty-run
python scripts/model_cert.py --harness-v0 replay --output /path/to/new-empty-run
```

私密env只需当前共享凭据字段 DEEPSEEK_API_KEY，以及与manifest一致的 DEEPSEEK_BASE_URL、DEEPSEEK_MODEL、GLM_MODEL、GLM_CREDENTIAL_SOURCE。不要提交env，也不要指向生产数据库。复现从已提交overlay取源，不需原电脑的绝对目录或未提交代码。新clone需保留参考提交历史；浅克隆若缺d3ed须先取得该提交。

后续若只补被阻塞样本，应另版支持只选缺项的调度并登记预算，不能私自删题改成本批次“全绿”。本版本没有resume接口，原完整run命令会跑全部用例，不能称为零额外调用续跑。

## 8. 未完成 / 未验证 / Manager 决策点

1. **双模型全量基线未完成**：每模型68次未运行、1次已启动阻塞。邮件/GitHub成功路径、失败/取消/注入/多动作/长结果、人格和记忆都缺真实模型三重复数据；只有文件F01–F03完整三重复。
2. 所有真实邮件送达、真实GitHub业务写入、生产Core/Godot/语音及其他外部连接器均不在本轮授权内，未测、不报验收。
3. 提示词候选未激活、未测提升。P0代码修复、记忆/结果通道改造仍未实施。
4. 429具体来源未确定，需Manager决定套餐/速率核查与补测窗口。不自行换账号、改线上配置、增费或无限重试。
5. 仓库白纸交接的“零上下文独立agent”门禁没有执行；本轮没有额外启动代理，已经提供可独立重判和源码重建的候选包，仍停在Manager验收点。
6. 本轮只做相关评测回归/文档/安全检查，不重复无关Godot/前端/音频全套；不把历史273/307条Core回归冒充本候选新跑结果。附 [交付核验](evidence/delivery-checks.json) 记录最终实际检查。

[暂存区干净导出复核](evidence/index-replay.json)证明所推Git字节保留冻结哈希，156行可在不依赖原源码目录/生产Core/凭据的情况下离线重判。初次暂存检查发现CRLF被Git当尾空白、Markdown硬换行尾空白，已为证据文件显式声明CRLF字节语义并去除普通Markdown尾空白；没有改变用例、判分或原始失败。

**交付状态：V0 candidate / partial baseline / external blocker。** 框架与合同供审阅，不能宣布正式产品验收或部署完成。
