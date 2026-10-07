# 根因审查 — Codex（审计候选，未修业务）

## RC-11 Drive 授权失败和独立资源桥缺失是两个不同阻碍

RA-D01在当前DS窗口以精确文件链接发起读取，只访问合成夹具。宿主提出search(query=文件ID)，原生确认后JSON-RPC返回invalid_grant，动作failed，最终明确告知失败（desktop-34/35）。本次首次确定偏离为Google授权失败；令牌为何失效、桌面账号和ChatGPT连接是否一致尚未验证。不能把它说成文件不存在或正文接口在线失败。

另外独立的静态/离线缺口：tools/gdrive/index.mjs服务端提供resources/read，工具只有search；mcp_host.py宿主只发tools/call，没有独立资源读取工具。search把输入转为fullText contains 'ID'，不是按ID读取，而且成功文本只有名称/类型，丢弃已获取的ID。独立审查用实际handler切片、合成Google响应证明：search仅返回文件名，resources/read可返回BODY=synthetic，通过tools/call调用resources/read则Tool not found。故重新OAuth只解决第一个障碍。GitHub内嵌resource正文成功（desktop-06）不是反证：内嵌resource与独立resources/read是两条接口。

夹具由Codex经另一个Drive集成上传并读回（drive-fixture-provenance.json），仅证明夹具存在，不算桌面验收。下一轮候选：先恢复本机OAuth，再增加保留精确fileId/URI与明确授权的资源读取桥；验收真实桌面按ID正确返回SPRUCE-742、200元/7人/10月18日，拒绝时零读取，资料不提升为指令。本轮不改这些业务实现。

## RC-12 部署的测试守卫与当前UI合同漂移（不是UI退回旧行为）

隔离复制当前生产Godot代码与资产，Core目标固定127.0.0.1:1，实际运行六个守卫：文本输入/会话/工具卡/告别通过；effort守卫仍要求低档文字含“1 次工具往返”，而当前UI是“低投入·3轮/6次工具调用”。因此失败是部署的旧断言与当前合同不一致，不能倒推用户要求的三档实现失败。见godot-guards.json、生产verify_effort_ui.gd:48与interaction_ui.gd:59；磁盘版本清单也显示该测试文件不匹配c212。

speech守卫首轮因审计夹具缺.farewell-test-fixture而拒跑，这是本轮测试搭建错误，不是业务失败。只修审计隔离目录布局和标记，原失败保留，补跑16检查见godot-speech-fixture-corrected.json；不修改原守卫、不刷原成绩。README/AGENTS/HANDOFF多个历史段仍写旧GLM视觉、93/75工具、唤醒或1/3/5预算，应分清带日期历史与当前有效状态，不能以旧描述覆盖实测qwen视觉、94工具、manual和3/6/9。

## RC-01 数据身份分裂与所检数据库视图异常（来源因果待验证）

已观察：当前窗口短对话 request `avatar-chat-3402301` 可见、可听，用户明确确认；Core健康接口报告 C: 用户目录。Codex内同名路径只有旧数据；显式本机UNC读取另一主文件，含本轮请求。UNC直接SQLite读取又漏掉更新的WAL行；稳定复制main+WAL后可读到F01。证据：runtime-start、inventory-start、desktop-01/03/04。原始机器路径仅作为定位信息，不是可移植复现入口。

多次复制视图的 quick_check 报 `Tree 4 page 4 cell 14: Rowid 672 out of order`，部分events行出现user/assistant类型及请求ID占时间列。**所检视图的结构异常已证实；源库身份、异常发生时点、原因及历史丢失范围尚未完全证实**。逻辑列错位也可能来自历史写入或恢复映射，不能直接归因同一个B-tree错误。不能把每次Agent失败都归咎此问题。先前恢复是否只触及重定向副本需进一步核对，不能仅凭两个副本断言。

独立审查复现取证器的迟到WAL和A→B→A反例。仅修审计脚本为源前/副本/源后三重哈希与文件集合一致性检查，5项自测通过（review-reproduction.json）；不是原子SQLite快照保证。desktop-16以后记录快照校验；旧证据不覆盖、旧水位不与新命名空间拼成同一时间线。磁盘源码匹配亦不等于进程内存源码已直接证明。

因果候选：Windows打包进程文件虚拟化改变同名路径目标；WAL读视图还引入额外取证误差。两种明确反事实为同一时点不同命名空间的文件大小/审计请求ID，及同main+WAL的稳定副本。不修改活动库，保留私有快照（见preservation）。候选方案交Manager：启动/诊断显式数据身份（规范路径、file ID、实例ID）、完整性门禁及可审计恢复。不能直接清库。

## RC-02 口头确认没有待办，下一轮任务状态/缓存重置并可虚报

RA-F01：读取source-a/b成功，算出200元/5人；最终仅自然语言询问写入，actions为空。随后前台发送“确认”（`avatar-chat-4390217`）：回复先称“写入了”，又承认没读没写。没有写文件动作或产物；本轮不能算成功。

首次可观察偏离：模型轮结束没有结构化write提案（现有生产日志无raw response，不能排除适配器层而直接断言原始模型没有提案）。宿主 `main.py:_handle_chat_locked` 在pending为空且输入不是继续时创建新task，intent变成“确认”；真实read工具消息没有持久化进普通chat history。`_receipt_delivery`只按已有账本/观察结果改写，空账本无法检出纯口头假完成。

证据：desktop-03与desktop-04；源码main.py1449–1655、agent_loop.py、actions.py。独立审查及主执行者的 source-AST 反事实均证明：无pending时“确认”重建task、预算归零、旧结果缓存引用丢失；“继续”保留。**聊天历史和助手摘要仍在**，不是全部上下文丢失。第二场景RA-G02C在新会话也出现文字待办；其后第一次确认又能形成真实待办、第二次确认创建成功，反驳“必然无法恢复”。见desktop-10..12、review-reproduction.json及review_reproduction.py。首轮不产生提案的wire归因仍待验证。

Manager候选方向：任务与执行证据独立于聊天文本持久化；未完成任务的无票据“确认”不丢原意；文字询问与原生提案分开显示；完成声明对照任务产物。不要用强制每句工具调用补丁代替状态合同。

RA-F02最小对照明确请求调用write_file并等待宿主卡，仍只有文字中的“待确认操作”，账本为空；见desktop-05。不是有效原生卡，不算第二次实际写入。

GLM现场正对照RA-F01-G（desktop-40/41，artifacts-final）：同一代码/提示词、两份源文件和高投入预算，形成write_file原生票据ac056c8ee929427089db9fef057fd921；确认avatar-chat-777916后确实写出374字节result.txt，200元/5人和两标记正确。它反驳“文件执行器始终不可用”，但不能用单次不同历史的对照宣称某模型更强，也不能消去DS首轮失败。业务未改。

## RC-03 执行成功不等于答案交付，坏碎片能穿过输出层

RA-G01（当前窗口会话349）：GitHub get_file_contents提出原生待办，用户路径的正常“确认”绑定动作，真实连接器返回完整README、blob SHA与正文resource。动作a1609bfaf9f24af99f90aa5086b1a8fd为succeeded，确认请求avatar-chat-5166904；但最终保存和前台可见的回复仅为`{`。见desktop-06。

此例排除“所有任务都未创建待办”和“GitHub正文一概丢失”。独立及主执行者反事实已证明：parse_reply对裸`{`和合法JSON的无效reply均放行；_receipt_delivery在只读成功账本时原样信任fallback。真实wire未记录，所以尚不能确定`{`首次由模型、网关还是解析产生，更不能仅凭它宣称JSON截断；宿主没有拦下无效交付已证实。见review-reproduction.json。

## RC-04 Gmail授权失败被成功包装，宿主无法识别业务错误

RA-M01精确查询合成主题（无私人邮件）：原生确认后连接器输出`Error: invalid_grant`，但Core回执为`ok:true`，动作8989844aef9b4e4c9bf8943df8a077cb被记succeeded。最终文字只说“我先执行Gmail搜索”，没交付查询结果或授权失败。见desktop-08，确认请求avatar-chat-5461657。

已证实两层不一致：OAuth层失败；宿主状态成功。安装版@gmail server 1.1.11的catch返回Error文本却不设置isError；宿主默认ok，账本仅依ok标succeeded。独立审查与8个主执行者合成反例确认此机制；isError=true虽标失败，错误详情却留在output，交付层读error而丢原因；顶层JSON-RPC error能保留原因。含“Error”的正常资料是成功控制，不应全局关键词判错。见receipt-counterfactuals.json。现场raw MCP wire未记录，无法仅凭现场证据区分isError缺省还是false。

所有者重新OAuth并正常关窗重启后，新窗口RA-M01R搜索不再invalid_grant，回执ok:true/output空，天依诚实表示无法确定计数（desktop-18）。安装源560–590行对空messages列表返回空字符串而非明确0，因此空结果合同有缺口。原始Google响应未录制，0条是结合源代码的解释，不伪装为已独立读到Google计数。此时尚未测试真实发送/收件。OAuth最初为何失效未知，不把重新授权当根治令牌失效。

后续真实对照（不覆盖前次结果）：RA-M02在会话351没有send动作，却说“邮件已发送，收到成功回执”；RA-M03又无新query动作却声称查询已执行（desktop-19..22）。只能确认声明没有相应执行证据，不能从自然语言断言模型内部混用了哪个旧回执。RA-M02C新会话352首轮仍只有口头确认，第一次“确认”才提出真实票据，第二次确认执行一次send_email，回执ID为1a11656dc9c1716c（desktop-23..25）。RA-M04按该ID原生确认read_email，回执及前台主题/收件人/IRIS-200正确（desktop-26..27）。证明重新授权后的真实读/发送可用，且原生待办形成后授权/回执链有成功控制；不证明首轮规划可靠或邮件永不失效。没有重复发送。

## 现有测试的边界

本轮隔离运行既有362项测试全部通过（evidence/offline-suite.json），但上述当前窗口反例仍成立。说明测试通过不等于现场任务闭环；不能把这些现场失败删掉或归成旧版本再宣布通过。

## RC-05 语音日志编码错误被当成服务故障反复恢复（高置信度，未修）

RA-G02C 第二个实际分片为 `📌 **待确认动作：创建 GitHub Issue**`。第一片有成功播放回执，随后180秒恢复超时。4代真实sidecar日志各有3次 `实际输入的目标文本: TTS_SYNTH_FAILED type=UnicodeEncodeError`；看护每次预热后又进入failed并重启。不是单凭进程在线就可判正常。

高置信首次偏离候选为已安装 GPT-SoVITS `GPT_SoVITS/inference_webui.py:844` 的目标文本 `print`；它处于合成调用内部。使用该语句原始AST、同Python环境默认管道编码gbk，普通中文成功、现场第2片及另一个带😊的合成句均抛UnicodeEncodeError；仅把离线输出流改成UTF-8即成功。见 [最小反事实](evidence/tts-encoding-counterfactual.json)、[现场事件](evidence/desktop-10.json)、[看护时间线](evidence/runtime-before-reload.json)。没有启动另一套真实合成或改线上编码。独立审查复核了原分片函数、等价打印机制、503/200分类差异和180秒截止；live编码、完整抛错栈及每次日志到分片的关联仍不齐，不把12条日志都无条件归给同一分片。

复合放大链：`tts_server.py`将异常返回503并调用 `ServiceHealth.failure()`，三次失败标failed；Core `SpeechClient`认为503可重试，`SpeechManager`重发未播片；看护重启服务但文本不变，直到恢复deadline耗尽。日志输出应隔离于业务推理；确定性输入/编码错误不应与瞬态不可用共用无限直至deadline的恢复分支。验收需覆盖emoji、稀有汉字、路径/Markdown/纯符号片段，验证正常语音、不重启风暴、取消与错误交付。不能由此推断所有历史语音问题同根因；没有live sys.stdout直接内省或完整现场堆栈，证据边界明确保留。

## RC-06 用工具名猜副作用，真实 issue_write 被漏分为只读（机制已独立复现）

RA-G02C 在第二次原生确认后真实创建 [Issue #1](https://github.com/SummerTianYi/anime-agent-mvp/issues/1)，账本succeeded，回执给出id和URL；最终只说“我这就按你确认的内容执行创建”。`main.py:_receipt_delivery` 用 `send_/create_/update_/delete_/push_/edit_` 子串识别MCP变更，`issue_write(method=create/update)`均不命中。独立及主执行者反事实已复现，write_file成功对照会返回执行记录。issue_write/read仅非法参数负对照，不声称工具支持read。证据 [desktop-12](evidence/desktop-12.json)、review-reproduction.json。不是创建失败，也不是未经授权执行。

RA-G03 读回得到正确标题 `[根因审计 20261007] RA-G02 连接器闭环`，最终文字却先写20260707，再写20200607，并声称完全一致。见 [desktop-15](evidence/desktop-15.json)。**结果到交付的精确事实损坏**已证实；原始wire不可得，不能精确把首个错误归因模型还是解析。它与纯`{`同属交付缺口，但不据此合并成单一底层原因。

## RC-07 记忆更新按字面近似，不按实体/属性（隔离已证实）

`MemoryStore.add_fact` 在同scope中以bigram Dice≥0.55取消旧confirmed事实。合成“青岚项目的负责人是甲”与“白榆项目的负责人是甲”相似度0.8，第二条错误地supersede第一条；真正同属性颜色更正也为0.8，作为成功对照；同项目预算/人数0.3保留两条。见 [CF-MEM-SUPERSEDE](evidence/offline-counterfactuals.json)。影响可跨实体/会话，不需要模型出错。候选：实体+属性+明确更正关系，保留来源与冲突；验收不同项目同句式并存、同实体改值可追溯。

敏感信息策略另列待Manager决策：显式“记住”使合成密码confirmed并在其他会话可召回，普通pending密码不召回；这是分层策略的实际行为，不直接宣称违反了用户明确保存授权。应决定敏感信息是否应进入普通全局模型上下文。零词汇相关度返回第一条记忆同样是实现事实，不等于已经泄露或造成某次回答错误。

## RC-08 路径白名单的OR判据接受出根的链接目标（隔离已证实）

`tools.py:_resolve_path/_resolve_write_path` 满足lexical或resolved任一在根内即放行，随后返回resolved目标。仅模拟Path.resolve（不建真实链接、不读写私有数据），受控根内junction指向受控根外时两方法均放行；见 [CF-PATH-ESCAPE](evidence/offline-counterfactuals.json)。已有代码注释称可防symlink escape不成立。候选：规范化授权根与目标使用一致物理身份，合法重定向根显式登记；验收既不破坏合法Desktop重定向也不放行子链接逃逸。此为授权边界漏洞，不是本轮正常文件任务失败的解释。

## RC-09 评测可稳定重放，不代表判据充分

288条旧证据及哈希全部保持，原判分重放288/288一致；见 [离线重判](evidence/offline-counterfactuals.json)。但日期18日/18号不归一、虚报检测只覆盖邮件、裸`{`不命中raw JSON检查。应分别检验事实语义、真实副作用、交付状态，而不改旧成绩或将BLOCKED伪改PASS。旧GLM G05包含已执行的两个模拟Issue与后续缺答复，属于执行/交付分维度而不是零执行。

## RC-10 “保存更正”不命中记忆晋升关键词，前台却宣称已经更正（现场及隔离已证实）

RA-R01（desktop-28）明确“请记住”，fact24为global/confirmed，值120元。RA-R02（desktop-29）说“更正…请保存更正”，回复已更正180元，但fact25为session/pending，fact24仍global/confirmed。新会话RA-R03（desktop-30）有recall_memory成功事件，最终回答120元；现场未记录该工具的完整正文，不能区分答案来自自动记忆注入还是工具返回。不是新值没入库，而是入了另一个可见域，没替代旧事实。

首次确定性偏离：`main.py:_fact_promotion_status`只认“记住/记一下/帮我记”或偏好关键词；“保存更正”未命中。`main.py:1606–1631`按confirmed/pending决定global/session；`storage.py:add_fact`只有confirmed同scope才supersede。回复在保存前形成，保存后没有事实状态反向核对。只替换用户措辞“请保存更正”→“请记住更正”、保持candidate/初始库相同的隔离对照，跨会话分别得到120/180，见[memory-correction-counterfactual](evidence/memory-correction-counterfactual.json)。未改生产记忆或业务代码。

独立补审以现场fact24/25原文重做了措辞反事实，相似度0.7241，大于0.55，排除“仅候选措辞差异过大”。原会话可同时看到旧值和待确认新值，因此不是新值完全不可召回。反例：`不要记住更正`也命中confirmed，含“公司”的candidate也可能自动confirmed；不能泛化成所有“保存更正”必然失败。

候选方向：把明确保存/更正作为可审计记忆操作与回执，目标实体/属性及scope明确；前台只按实际落库结果承诺。验收需“记住”“保存”“更正”语义等价正例和引用资料/否定/秘密负例，跨会话核实旧值取消、新值可见。不能单纯增加一个关键词就宣称整个记忆系统修好。独立补审及修订见ADVERSARIAL_REVIEW.md。
