# 天依首批底层根因修复记录

日期：2026-10-12。主仓基线：`b2d871316b35287f17b0771dcd02212b4be2bb72`。独立实现分支：`codex/root-cause-repair-batch01-20261012`。

**当前是已实装、部分桌面验收通过的候选，不是首批全部验收完成。** 任务确认、回执恢复、Gmail合同、物理路径及TTS编码恢复已有实现和回归。真实Godot窗口已完成双模型短聊、文件、Gmail代表场景；GLM还现场触发了写入成功后补答超时，成功回执仍可显示、保存及播报。DS的GitHub标题更新经原生确认成功；GLM的A4自由正文假待办仍复现，不能将DS通过替代GLM失败。

生产源码、配置、原聊天记忆、角色资产与声线未覆盖；使用经身份核验的独立持久测试数据。所有正常任务均经唯一Godot窗口输入、原生确认和语音链路执行，CLI仅独立读回与核验。未合并main。保留原259项清单与旧审计成绩，不以本批机制回归替代全部功能覆盖。

完整历史与本地运行入口见§7，前台逐项证据见§8。初次离线提交主仓`44ae32e0b02da100ac62c6ef0a642df3c8755880`；后续桌面修正与本报告随最终本地提交保存。TTS最终提交`ea5c4abf04518c684a3da5c56994ff8f6f927d49`包含桌面记录，运行代码与`fb681d0a93bd6bd3d8b2785924dbaf264810dc5e`相同。遵守VERIFICATION_SPEC的本地提交、待验收再推送门禁，不提供尚不存在的远端固定链接。

## 1. 已完成的修改与裁决

复用[收口报告](../../root-cause-audit/closure/REPORT.md)、[第二轮根因](../../root-cause-audit/round-02/ROOT_CAUSES.md)和原始证据索引。本轮没有重跑259项清单，也没有重造Harness或授权系统。

| 组 | 原事实 | 本次代码结果 | 验收层级 |
|---|---|---|---|
| A1 任务状态 | 无pending确认新建任务/清缓存；继续错误注入待确认说明 | 分开真实票据确认、无票据确认、有目标继续、空任务继续。无待办确认不调用模型、不派发、不充值，保留目标/预算/缓存；空控制不产生占位任务 | 隔离回归通过；DS/GLM无待办确认现场通过 |
| A2 执行与交付 | RC20真实标签创建后补答超时，提前return吞掉答案 | ProviderError及错误JSON都进入持久化/显示/TTS共用出口。写入、unknown、待确认、成功只读及ALLOW读取结果可独立交付；再次确认不会重放已执行动作 | 隔离回归通过；GLM写入成功后真实补答超时仍交付 |
| B1 连接器合同 | Gmail Error文本成功化、空查询不明；issue_write未识别为写 | 保留原始回执，输出succeeded/failed/unknown及success/business_error/empty/partial类别；共享精确tool/method分类，未知或坏类型method拒绝。正常只读摘要保留 | DS/GLM真实Gmail空结果、业务失败通过；DS issue_write更新通过，GLM未生成真票据 |
| D1 语音恢复 | GBK打印✅导致UnicodeEncodeError→503→同片反复恢复 | UTF8与安全日志边界；确定性编码异常422且不重试；瞬态保持有界恢复。完整栈、错误体读取中断、获锁后健康复核 | TTS43项通过；DS声音测试真人明确听清；GLM含✅两片播放完成，未另取真人听感确认 |
| E1 文件边界 | 词法根或物理根任一满足即放行，junction可出根 | 统一比较目标与授权根的物理路径；权限预检和执行复核共用解析。合法根自身重定向保留；默认读取仅补系统登记Desktop，不扩显式读根或写根 | Windows合成junction回归通过；前台合法根写入及根外拒绝有证据 |

任务修改复用原 `ActionLedger` 的action_id/revision/args_hash、execution_id、显示票据绑定、过期复核、排队前撤销和unknown去重。没有新建另一套授权。原生确认、多动作、拒绝、改参、双击/旧票据、普通聊天、只读实质回答、三档预算回归仍通过。

**A4仍未完整解决：** 当前正式输出合同允许自由reply；raw无tool_calls却声称完成/待确认的任意改述，不能由关键词或正确状态卡完备验证。本次保证由宿主生成的执行状态源自当前任务记录，并阻止无票据确认产生操作；不宣称所有自由正文已无假完成。完整治理仍需结构化操作声明与确定性渲染合同，不能靠增加人设提示词解决。正式人格/系统提示词本轮未改。

## 2. 模块与状态转换

`main.py`：拆分控制输入；有待办才描述待确认。补答异常不再跳过助手历史与pending发布。安全Provider错误事件仍可见，执行回执随后独立交付。ALLOW工具的结果在返回模型前保存为关联session/task/request的tool.result，供当轮补答异常恢复；这不是可执行票据。chat.delivery记录交付来源和账本票据。

`actions.py`：原始MCP envelope保存在账本receipt；面向模型的result/context只投影归一化结果，避免重复大文本/blob。执行、取消及去重状态机未重写。`agent_loop.py`增加outcome，不再把待确认、unknown统一叫失败。`harness.py`增加解析失败标记，错误对象、null型reply及残缺JSON走回执恢复；正常文本降级保持兼容。

| 情况 | 保存/交付 | 禁止行为 |
|---|---|---|
| 无待办确认 | 原任务/cache/预算不变；宿主说明无待确认项 | 不建新目标，不调用模型补造票据 |
| 空会话继续 | 直接说明无可继续任务；不注册假目标 | 不让模型凭“继续”发起动作 |
| 有效票据 | 沿原任务执行并保存真实回执 | 不授权下一张未展示票据 |
| 执行成功、补答失败 | 原成功状态不变，存助手答复并交付真实结果 | 不把答案失败改成执行失败，不重复外部动作 |
| 派发后超时/未知错误 | unknown保留，说明不能确定结果 | 不因重提/新措辞自动重放 |
| 待确认时补答失败 | 待办票据与实际参数仍发布并入历史 | 不谎称执行失败或已完成 |
| 拒绝/改参 | 沿原账本取消旧票据；改参必须新版本确认 | 不复活旧授权 |

## 3. 实际连接器合同与兼容

依据已捕获的[真实工具schema](../../root-cause-audit/evidence/mcp-schema.json)，精确列出GitHub读method、写method、已知只读工具、Drive search、搜索和浏览器只读入口；未知工具保守交付，不因工具名字中恰好有get/create就推断权限。

本机安装的 `@gongrzhe/server-gmail-autoauth-mcp` 为1.1.11，已检查其纯源码：成功read固定以Thread ID/Subject等头部包裹正文；search固定ID字段；外层异常是唯一text块的Error前缀；download有独立失败前缀。本次识别限定gmail、已知tool及该envelope形状。正常邮件主题/正文中的Error不被当业务错误。后续连接器升级须复核此合同，不能把此兼容层当通用MCP错误规范。

空search成功明确显示0条并保留原始空回执。已知业务错误failed；不能确认副作用的写入异常unknown。批量操作存在Promise.all先部分执行、失败后连接器内部逐项重试的实现，因此即便其计数为0成功，有失败时也不能断言无副作用：统一unknown，已知部分完成另标partial，原文保留，宿主不自动重放。

`download_attachment`会写本地文件，未分类成只读。原始回执保存在当前action/session/task下，模型措辞不决定成功。权限ASK不降低。Drive独立resources/read桥接不在首批实现范围。

## 4. TTS编码与恢复

原RC05证据已足以确定首个异常在打印阶段，本次以一条含✅的正常前台短聊验证修后真实声线，不循环采样。侧车在加载模型前配置stdout/stderr为UTF8，并用日志包装器隔离编码/关闭输出流错误；只对日志作转义，不删除合成文本符号，不改变声线。

真实UnicodeError返回422、error_type=encoding、retryable=false，不污染模型健康计数。瞬态服务失败沿原503与有界恢复。Core兼容旧版无typed body的503；错误体截断不会泄漏IncompleteRead绕过SpeechUnavailable。模型失败达到阈值后，排队请求在获锁时重查健康，不能把failed覆盖为ready。

侧车独立记录位于配套仓 `docs/BATCH01_REPAIR.md`，版本为本文开头的TTS完整SHA。配置/参考音频/权重/采样/自检阈值均未修改。播放去重、打断和speech.finished机制沿用；离线通过不等于声卡实际输出或真人听感通过。

## 5. 修前/修后证据

- [基线定向结果](evidence/baseline-regressions.json)：明确导出指定基线源代码并校验导入来源，24个用例中17个断言失败、3个因新合同/新辅助接口尚不存在报错、4个通过。不能将3个接口缺失直接算成3个独立旧产品缺陷。
- [候选定向结果](evidence/candidate-regressions-final.json)：24个通过。随后新增原始回执持久化/模型投影控制，总用例增加为25，随最终全套执行。
- 原基线全套362项通过；初次候选全套387项通过；现场增量后最终395项通过（执行器exit0）。TTS全套43项通过。[逐轮结果及原日志hash](evidence/validation-runs.json)、[初次离线候选摘要](evidence/verification-summary.json)、[最终395项及源码hash](evidence/desktop-followup-regressions.json)分别保留。旧259功能成绩保持原样；这些都是合成机制回归。
- [执行后反事实](evidence/post-dispatch-probe.json)：复用原closure_probe并实际运行。正常写回验真成功；replace后读回失败返回unknown但文件确已改变；外层超时返回unknown后，释放隔离worker才出现产物。证明unknown必要，不证明迟到worker已支持自动对账或Godot跨会话路由。
- 新连接重开合成数据库，确认助手成功回执、request_id/conversation_id及成功账本仍在。这项是存储层验证；另有19:21与20:06正式重启后的Godot历史列表、旧会话重开和完整回答显示证据，分层登记。

脚本：[定向运行器](repro/run_regressions.py)、[部署/私有备份预检](repro/preflight.py)、[暂存内容检查](repro/check_staged.py)及主仓 `services/agent-core/tests/test_repair_batch01.py`。运行器显式设置mock、禁TTS/wake/MCP及临时数据目录，并校验实际导入路径，避免editable install误测生产代码。

初次定向命令的Windows PYTHONPATH分隔符错误曾导入生产包，该轮不作为候选通过依据；已改成显式路径校验的运行器，并从指定基线重新导出验证。原日志保留私有，公开结果只发布脱敏判据；没有覆盖旧审计证据。

## 6. 独立审查与修订

两位新上下文审查者只读代码/合成夹具，未并发操作桌面。

| 审查反例 | 实際修订及复核 |
|---|---|
| 非Gmail只读成功被保守分类吞掉摘要 | 依据真实schema补齐精确read/method表；长结果综合回答仍保留 |
| method传list/dict/null抛TypeError | 先检查字符串类型，坏类型明确deny |
| 确认标点、显式旧票据+yes重置任务 | 规范控制标点并识别显式票据，保留原任务；普通无票据yes/好的保持聊天 |
| 空确认占位导致后续继续造任务 | 空控制使用临时交付上下文，不注册可继续任务 |
| 补答降级丢掉首请求401诊断 | 保留core.error事件，同时仍走持久化交付 |
| 批量“0成功”不等于没有副作用 | 连接器源码独立核对；有失败一律unknown，禁宿主重放 |
| 默认系统Desktop重定向被严根拒绝 | 只恢复系统登记Desktop的默认读兼容；显式根/写根不扩展，解析前后拒绝隐式UNC |
| TTS排队编码错误抹去三次模型失败 | 获锁再检查健康，保留failed；独立反例关闭 |
| HTTP错误体读取中断泄漏异常 | 捕获HTTPException，回退有界瞬态恢复；独立反例关闭 |

第一位审查者最终13项独立内存断言通过，此前四类复测通过；原始回执投影另6项独立断言通过，未发现剩余必须修改项。其建议的脚本禁pyc及显式清空MCP_SERVERS也已补齐。第二位审查者最终TTS5/5、Core错误响应4/4通过，两项反例关闭。两者均只批准所审离线修改，明确不批准生产激活、物理播放或A4自由文本闭环。

现场增量独立审查另复核交付7/7、确认20条分类与3条状态控制通过，见[增量回归证据](evidence/desktop-followup-regressions.json)。反例先于修订：旧pending覆盖聊天、读回正文丢失、等待模型期间取消后假成功、尾页被换回首页，以及“不执行也不取消”误撤销。修后只保留当轮交付归属、实际读回页和取消记录；否定解析限定同句保留意图，双重否定与独立拒绝仍有效。没有改人格提示词。

独立审查明确否决“A4全修好”：无tool_calls的自由reply、只读正文夹带副作用声明、旧待办旁的普通聊天，仍不能凭本批账本出口保证任意语言声明正确。前台GLM随后给出同类反例，故该缺口保持未解决，未用关键词补丁或第二模型自评掩盖。

最终独立材料审查另提出两处表述问题：真人听感只能归于B01-VOICE-03，不能合并宣称DS/GLM都有人声验收；旧387项摘要不能称最终代码hash。两处已修正文档，旧证据原样保留。审查结论为所审修改APPROVE，A4仍未闭环；GLM写入后恢复答复有8片成功回执，随后被新消息打断，未宣称整段播放完成。

## 7. 部署、身份、历史与回退

[预检](evidence/preflight.json)记录生产主仓HEAD `d3ed6d68f2509ad51bea15cf8224c5f3a165d957`、85项dirty，TTS生产HEAD `3814b4c9d32bb17c3638cf851e5649d9c7d17fa7`、7项untracked。原HEAD不代表实际部署。备份包含主仓174个、TTS19个源码文件、未提交差异及原配置/声线配置，位于本机`C:/Users/26052/Documents/Codex/2026-10-12/batch01-private/preflight-01`。收尾[保存核验](evidence/preservation-final.json)逐文件比较，不仅比较Git HEAD。

生产数据库普通路径与UNC文件ID不一致，故未打开、迁移、修复、清空或恢复该库。当前测试库为`D:/TianyiRepair/batch-01-20261012/data/anime-agent.sqlite3`；实际Core health与该路径关联，普通/UNC的volume+file ID一致。复用round02_identity，从显式读事务取得SQLite backup，快照quick_check=ok；原始数据库和快照仅留本机。不能用前后文件hash相同代替事务一致。

唯一测试入口是候选主仓根`start-anime-agent.cmd`，准备脚本`C:/Users/26052/Documents/Codex/2026-10-12/batch01-private/open-repair-window.ps1`只配置候选依赖、核验命名空间/导入来源并调用该入口，拒绝已有运行实例。候选主仓`C:/Users/26052/Documents/Codex/2026-10-12/tianyi-repair-batch-01`，配套TTS为同级`tianyi-tts-repair-batch-01`。没有另起后台Core代替角色完成正常任务。

运行代际：首次DS进程4684；19:21 DS进程20324；19:41 GLM进程19688；20:06正常关窗后经正式入口恢复Deepseek，当前Godot进程21368、窗口2232366。GLM临时配置已从进入对照前备份逐字节恢复，原生产.env未改。最终主仓main.py SHA256 `8b5fdbc36faf0f5dd9a4f5f7d5e35e1b22b3d88488d3c49d43c1e5f19706dc83`，actions.py `acc5e339c703fd494a1402161ba1f6d9feb6c31fc408107496bab9f63abeb8d7`；GLM及最终DS代际加载相同修正。[最终部署/身份/产物核验](evidence/deployment-final.json)确认avatar=1、TTS可用、无待办，最后答复播放完成。

19:21已在历史页查询并重开原DS文件会话；20:06重启自动恢复GLM邮件/原文回答，历史页列出5个已有测试会话，并再次打开GLM声音/文件/假待办会话；20:26又从“回忆”查询并打开最新“GitHub Issue标题更新”。输入、完整回答、request_id、conversation_id及账本回执持续落库，没有删测试聊天。最终62条消息、814事件、11动作均在独立持久测试库中；测试库与私有证据继续保留供所有者访问。生产旧聊天不在测试库中，但原文件未被替换或清除。

回退先正常关闭确认归属的候选Godot，等待该会话Core/TTS/守护退出，再恢复配套源码并走同一根入口。勿用旧Git HEAD覆盖生产dirty tree；勿恢复旧数据库或复活已消费授权；已发生文件/外部动作不会因代码回退自动逆转。当前生产数据身份问题未解除，因此不可直接把候选接回那个旧库。

## 8. 桌面实证及未通过项

| 场景 | Deepseek-v4-flash | GLM-5.2 | 判据与限制 |
|---|---|---|---|
| 短聊、真实声音 | 已显示与播放；B01-VOICE-03真人明确听到且清楚 | 含✅短聊完整显示、真实合成、两片播放完成 | 首次DS问候真人未听到/不清楚，保留失败；不能由后续通过覆盖 |
| 原生文件写入 | ds.txt及最终版本ds-final.txt真实票据执行成功；后者39字节且verified_readback=true | glm02.txt原生确认后写入39字节且verified_readback=true | 两模型均未在最初写入确认后自动完成所要求的read_file，后续明确只读任务才读出正文；不把内部写后校验冒充Agent读回 |
| 保留待办先聊天 | 旧DS误取消ds04；最终版本298433正常祝福、保留e4729ae70dbf4321a2ced94d7b91f4ba，随后384504只执行一次 | 修后“不执行也不取消”正常祝福、原两票据保留 | 新DS/GLM同修正与相同保留句式，初始任务/历史不同；不声称单变量模型胜负 |
| 执行后补答超时 | GitHub读取915536真实45.031秒timeout，已读结果仍由receipt_recovery显示/保存/播报；不是写入后超时 | request avatar-chat-354457：真实45.016秒timeout，已写入成功仍由receipt_recovery交付 | 无重复写入；随后两模型各自的只读任务由天依读出“天依测试，总数一百七十五。”并完整播报（DS673846，GLM1355465） |
| Gmail空与失败 | request844955显示0条；997781显示failed/Invalid id；均完整播放 | request1190755显示0条；1287656显示failed/Invalid id | 同查询、同合成无效ID；分别原生确认，未发信或修改邮件 |
| GitHub method | 1015527产生真实issue_write update票据；1111102确认后仅标题更新成功、结果显示及完整播报 | Issue读取成功；随后751815把issue_write update写成文本，无真实票据；1061803确认被拦住 | GLM阶段标题未改；最终DS后独立核验标题含[B01-DS]。相同专用Issue/method/只改标题，但历史、提示及超时不同，属于多因素代表对照；不推断模型优劣 |
| 无待办确认 | request295292宿主说明无待办，无模型调用/动作 | request1061803同样拦住假待办后的确认 | 保留任务、预算和缓存的内部断言另有隔离证据 |
| 打断与连续播放 | 新消息/切换会话有实际打断事件 | 连续多片成功，新消息打断后新回答继续播放 | 已打断utterance快照内无后续成功回执；未做强制迟到音频前台注入 |
| 历史查询/重开/重启 | 19:21实际完成 | 20:06恢复DS后仍可重开GLM会话 | 旧记录保留，失败与成功都可查看 |

关键关联：[DS初始](evidence/desktop-ds-initial.json)、[DS邮件阶段](evidence/desktop-ds-stage02.json)、[GLM阶段](evidence/desktop-glm-stage03.json)、[最终累积记录](evidence/desktop-final.json)。最终JSON本机文件字节SHA256为`5ee629d534d3aab045dbb1f0032f39ed1f3e540bd5a5b27da1d67bf07f97bd00`（Git文本换行规范化后字节hash可不同）。完整本地原始记录包含回执；公开材料将账户元数据和原始MCP块换为摘要/hash，保留合成正文、票据和调用关联。没有公开密钥、私有推理、数据库、资产或未经脱敏截图。

最终DS关键动作：文件票据e4729ae70dbf4321a2ced94d7b91f4ba，执行b1d10af9d9fa4b1297b60615be3188f5；Issue更新票据af6ed4c90326460c83550a62ec64f3e9，执行e6155d2a2ea843a88f4afe20c3a59597。最终文件与GLM文件同为39字节、SHA256=f3da88e07e499533d2d121420874c2b17c2eb94e54180765a4df00ae36eaef90。前台共10次新消息/会话切换打断，快照内相应utterance无后续播放回执；这仍不是人为强制迟到音频验收。

现场再次发现并修正的交付缺陷：旧pending曾覆盖普通聊天，混合写读成功卡曾吞掉原文，“不执行也不取消”曾误撤销。修前失败、修后33项定向通过及395项全套通过（87.664秒、exit0）见[增量回归](evidence/desktop-followup-regressions.json)。先前392项用例虽通过，执行器清理旧连接时WinError32退出非零；修复隔离运行器关闭连接后再完整通过。一个2秒夹具超时短于两个正常1.2秒展示等待，调整至5秒且保留断言，不当成产品缺陷或隐藏失败。

操作准备偏差也保留：DS03路径少写一层，根外读写被正确拒绝；按钮“取消录音”曾被主执行者误认为播放取消，其点击没有speech.interrupted，不计为TTS打断通过。候选初启漏接既有FFmpeg bin/nltk_data造成预热WinError2及英文路径LookupError，补接原依赖后恢复；不改权重或声线。原音量6，临时25后所有者改为10，保留最新人工值，不把听感失败单因归于音量。

## 9. 剩余问题与后续最小范围

A4仍是首批未完成项：模型无tool_calls时仍可在自由reply声称“待确认”。751815是修后真实反例，账本没有issue_write，不能归因于连接器成功判定，也不追测模型心理。无票据确认和外部写入边界已拦住，但前台误导性文字仍存在。下一步需先确定可信操作状态专用输出与自由正文的边界，再把结构化操作引用绑定Ledger并由宿主渲染；仅加action_refs字段仍允许正文另造声明，不能声称完整治理。不要加提示词关键词、循环重试刷绿或封禁所有正常聊天/只读答案。

另未解决：生产数据身份与历史完整性；迟到worker主动对账；旧chat迟到时向新会话显示/播报的资格；解析后外部进程更改junction的TOCTOU。unknown保护不等于exactly-once或自动撤销。强制迟到音频及跨会话异常路由仍只有对应隔离/旧审计证据，不能由正常前台播放推出全面通过。

原集中方案中的实体/属性/作用域记忆、Drive独立资源、分页/argv/Win32/Provider装配继续保留，不扩成产品全测或顺手改造。本轮实际修的是任务状态、交付、连接器结果合同、TTS日志/重试和物理路径四组。未修改正式人格、模型、动作、声线，也未合并main。

## 10. 对象与交付边界

对象见[TEST_OBJECTS](TEST_OBJECTS.md)。本轮最终44次实际模型传输（DS30、GLM14；40成功、4deadline_exceeded）。真实邮件发送0，旧8封授权还剩7封；Gmail仅空查询和合成无效ID。GitHub只有天依对已登记Issue #1执行一次标题更新，保留[B01-DS]标记；Codex采用只读gh api独立核验，不冒充天依执行。

本地源码/配置备份、测试文件、聊天与事务快照保留。没有清理旧邮件、仓库对象或记忆。当前无需额外OAuth或测试授权；首批仍按部分完成交付，等待剩余项审查与所有者验收。最终完整SHA及当前窗口状态见[STATE](STATE.md)和交付答复。
