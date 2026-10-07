# 第二轮证据索引（持续追加）

本索引由独立覆盖审查者整理现有公开文件；未执行测试、API、桌面、Core/MCP/TTS或业务进程，未读取私有日志、凭据或数据库。结果和现场观察归属原采集者；索引整理及读取文件hash不是新的独立实测或验收。主执行结论见[ROOT_CAUSES](ROOT_CAUSES.md)，进展见[STATE](STATE.md)，逐项映射见[COVERAGE_LEDGER](COVERAGE_LEDGER.json)；状态文件包含历史续记，较早的PID、累计数和“待执行”不代表截止时点现状。

证据层分别为：**前台链**（实际Godot输入、模型/工具/交付观测）、**同身份事务快照摘录**（持久化状态）、**独立真实连接器**（Codex发起，不是天依）、**隔离实现/反事实**（替身、AST或临时数据库）、**诊断自检**、**静态审查/材料准备**。任何一层的成功均不自动升级为整项能力通过；工具提案、原生确认、远端回执、最终答复、播放回执和所有者听感要分开。

## 首选版本与保留旧证据

| 材料 | 首选及版本关系 | 旧版的使用限制 |
|---|---|---|
| observer运行程序 | v1 SHA 4cc6d05e91b7230bcf032b1e4bdcbcca1d79faacf6a64b2820981caec8d6605d；v2 SHA 59050cb15f9e84a4d5aa68237355c59223e8c0446c0af0b04ca178b4ebbd4f7b；v3 SHA 77b2f610ec795e7263a3df5def20503b2b9927a0fd547e66c868ebe96af824fd。v3增加受门控的合成上下文分段观察，运行阶段见STATE。 | v1含schema.type数组会使部分model.http.request记录丢失；v2修序列化但仍以整体上下文hash为主；v3不能回填旧代际缺失。不同版本均是诊断，不是业务修复。 |
| 首组文件trace | [local-group1-trace-v2](evidence/local-group1-trace-v2.json)替代[首版](evidence/local-group1-trace.json)用于解释正文转义；两者选取同一私有前缀、同408条记录。 | 导出v2修脱敏时改变非路径反斜线的问题，不是observer-v2重跑。observer-v1原本缺失的工具请求及hash不可重建；旧版保留，不宜据其反斜线文本作根因判断。 |
| Gmail/TTS故障trace | [gmail-tts-live-trace-v2](evidence/gmail-tts-live-trace-v2.json)309条，优先于[首版](evidence/gmail-tts-live-trace.json)308条；增补正常退出前的恢复代际记录。 | 旧版不是全错；增补不等于原故障修复。两版重叠，不能累计成617条独立观测。 |
| 真实闲置回执 | [real-idle-receipts-v3](evidence/real-idle-receipts-v3.json)优先；[v2](evidence/real-idle-receipts-v2.json)已用julianday选时，v3额外声明基线水位/非法时间筛选边界。 | [首版](evidence/real-idle-receipts.json)以字符串比时间得到0条，结果废止但留档。v2/v3为同次真实闲置的重新提取，不是两次600秒实验。 |
| observer自检 | [observer-check-v3](evidence/observer-check-v3.json)：41诊断断言+116相关回归；[observer-check-v2](evidence/observer-check-v2.json)：10+116；[observer-edges](evidence/observer-edges.json)：6个边缘例。 | [observer-check](evidence/observer-check.json)内部全绿后退出清理失败，后续修复initial_memory关闭；不掩盖该失败。文件名v2不等于所有后来observer-v2改动已由这一份自检覆盖，具体schema数组反例见独立审查。 |
| overlay自检 | [overlay-check-v3](evidence/overlay-check-v3.json)为显式v3及混合入口恢复3项；[overlay-check](evidence/overlay-check.json)是早期临时副本5项。 | 两者均只证明独立复制文件上的安装/复原，不替代真实部署后的关闭诊断、原配置恢复和正式链运行核对。 |
| 浏览器夹具 | [fixture-v3](fixtures/fixture-v3.html)是B01等实际使用的增补版；[fixture-v2](fixtures/fixture-v2.html)保留。 | 夹具存在不等于分支已执行；v3重复delay定时器/网络失败保留旧status两项偏差见COVERAGE_REVIEW，不能把初始auditState当操作成功。 |

## 按机制与前台组查找

下列脚本均指仓库scripts/root_cause_audit目录。脚本是采集、提取或隔离复现入口；列入索引不表示本实例执行或批准其再次运行。表中的“同身份”沿用采集证据的卷号/file ID核对，不能推论已经检查运行中Core的SQLite句柄。

| 机制/组 | 公开文件 | 准确层次及可支持结果 | 对应脚本/来源与已知缺口 |
|---|---|---|---|
| 部署起点/身份 | [deployment-entry](evidence/deployment-entry.json)、[desktop-start](evidence/desktop-start.json) | 起点54部署文件清单与env hash；开场实际Godot会话及事务快照、所有者明确听清。 | [probe.py](../../../../scripts/root_cause_audit/probe.py)、[round02_identity.py](../../../../scripts/root_cause_audit/round02_identity.py)、[round02_desktop_probe.ps1](../../../../scripts/root_cause_audit/round02_desktop_probe.ps1)、[round02_extract.py](../../../../scripts/root_cause_audit/round02_extract.py)。54相同只属于取证起点；后续overlay/模型切换另记。身份异常原因、Core句柄和损坏产生者仍未知。 |
| 全套离线基线 | [offline-suite](evidence/offline-suite.json) | 362条已有单项回归，零失败/跳过；隔离层。 | [offline_suite.py](../../../../scripts/root_cause_audit/offline_suite.py)。98具体旧断言已映射于COVERAGE_REVIEW；全绿不证明前台/外部账号/全部分支。 |
| 诊断透明性/复原 | observer-check系列、observer-edges、overlay-check系列（上表链接） | 替身对象/异常身份、单次调用、关闭控制、隐私字段、临时副本复原等指定断言。 | [round02_observer_check.py](../../../../scripts/root_cause_audit/round02_observer_check.py)、[round02_observer_edges.py](../../../../scripts/root_cause_audit/round02_observer_edges.py)、[round02_observer_check_v3.py](../../../../scripts/root_cause_audit/round02_observer_check_v3.py)、[round02_overlay_check.py](../../../../scripts/root_cause_audit/round02_overlay_check.py)、[round02_overlay_check_v3.py](../../../../scripts/root_cause_audit/round02_overlay_check_v3.py)。程序[observer](../../../../scripts/root_cause_audit/round02_observer.py)、[observer_v3](../../../../scripts/root_cause_audit/round02_observer_v3.py)、[overlay](../../../../scripts/root_cause_audit/round02_overlay.py)；审查归属见ADVERSARIAL/BRANCH_MAP。 |
| 本地/外部准备对象 | [local-fixtures](evidence/local-fixtures.json)、[external-fixtures](evidence/external-fixtures.json)、两版HTML、[TEST_OBJECTS](TEST_OBJECTS.md) | Codex合成材料、账号可用性和对象登记，准备层。 | [round02_accounts.py](../../../../scripts/root_cause_audit/round02_accounts.py)、[round02_prepare_mail.py](../../../../scripts/root_cause_audit/round02_prepare_mail.py)及主执行准备记录。私人对象原文/凭据不在索引；准备、CLI读回不是天依执行。清理仅限登记对象，索引不授权清理。 |
| F01/首组文件读写 | [local-group1-trace-v2](evidence/local-group1-trace-v2.json)、[local-group1-state](evidence/local-group1-state.json) | 3个前台请求；原生write_file票据、58字节产物读回；raw→适配/解析/语音链可分层核对。 | [round02_trace_export.py](../../../../scripts/root_cause_audit/round02_trace_export.py)、round02_extract.py。首组部分出站请求漏记，缺口如上；双转义换行证据用导出v2。 |
| F03长结果/确认对照 | [longfile-confirm-trace](evidence/longfile-confirm-trace.json)、[local-mail-state](evidence/local-mail-state.json) | 实际read_file+缓存read_tool_result取全6801字符；继续保留task/cache，无待办确认重建，分别保留。 | trace_export/extract。证明结果缓存offset，不代验read_file所有字节边界；历史持久化存在不等于task状态保留。 |
| 真人手动录音 | [manual-voice-trace](evidence/manual-voice-trace.json)、[voice-idle-state](evidence/voice-idle-state.json) | 4次实际录音入口和raw STT/回填；170、空串、单数字、完整简体结果分列。 | observer/trace_export/extract。音频仅指纹，未留可独立听辨字节；指定台词不能证明实际每次发音。最后文字另产生chat请求，来源未充分取证，不能记“只回填未发送”通过。 |
| 真实600秒闲置 | [real-idle-01](evidence/real-idle-01.json)、[首选回执v3](evidence/real-idle-receipts-v3.json)、voice-idle-state | 实际GetLastInputInfo 155样本，max673.188秒；一次提醒、receipt/completed、同段skip，所有者听清；选定有效时间窗provider.transport=0。 | [round02_idle_watch.py](../../../../scripts/root_cause_audit/round02_idle_watch.py)、[round02_idle_extract.py](../../../../scripts/root_cause_audit/round02_idle_extract.py)。无模拟时间；零调用只限所选窗口，24历史非法时间列和基线后0非法列分开。 |
| 背景唤醒当前状态 | [wake-disabled-phase03](evidence/wake-disabled-phase03.json) | Core27300在UTC2026-10-07 17:54:58的正式health：enabled/running=false；状态层，manual不变。 | 来源私有identity-glm-start/identity.json，快照hash已列；round02_identity.py。补齐此前VO05代际状态摘录缺口，不等于测试后台唤醒能力；不外推后续新Core。 |
| Gmail真实读取/TTS故障 | [gmail-tts-live-trace-v2](evidence/gmail-tts-live-trace-v2.json)、local-mail-state | 天依读取指定合成邮件、余额75/附件正确；raw含U+2705→实际GBK print UnicodeEncodeError→503/retry，多TTS代际同错。 | observer/trace_export/extract。读取/文字交付成功与语音失败独立，不能归咎Gmail计算或声学GPU；raw/reasoning保留边界见下。 |
| TTS精确反事实/恢复 | [tts-exact-counterfactual](evidence/tts-exact-counterfactual.json)、[tts-recovered-short](evidence/tts-recovered-short.json) | 前者实际print语句内存GBK/UTF8、去字符控制及400/503分类；后者新Core/TTS普通中文两片receipt+completed。 | [round02_tts_counterfactual.py](../../../../scripts/root_cause_audit/round02_tts_counterfactual.py)；历史[tts_encoding_probe.py](../../../../scripts/root_cause_audit/tts_encoding_probe.py)是较早泛编码对照。UTF8 print成功不证明全合成；恢复短句不证明emoji已修，听感未逐项确认。 |
| 独立连接器/启动目录 | [gmail-independent-read](evidence/gmail-independent-read.json)、[drive-independent-read](evidence/drive-independent-read.json) | Codex独立真实MCP+同一raw的部署适配器重放；非法Gmail ID文本缺isError被ok=true、空结果、正常读控制；Drive资源正文可读。 | [round02_connector_reads.py](../../../../scripts/root_cause_audit/round02_connector_reads.py)。首轮私有connector-reads-01.json的Gmail initialize因stdout污染失败；正式CWD成功分列。适配重放不二次远程调用；不是天依前台能力。 |
| Drive前台 | [drive-frontend-trace](evidence/drive-frontend-trace.json) | 2前台请求/4模型HTTP的search及确认；答案明确只有名称不能正文。 | trace_export。OAuth已经有效；Core resources/read桥接缺失，独立正文读取不能补为天依实现。 |
| B01浏览器 | [browser-group1-trace](evidence/browser-group1-trace.json)、[browser-group1-state](evidence/browser-group1-state.json) | 8请求/13模型HTTP/5实际MCP：navigate、resize、snapshot、evaluate、find；单步对照有真实find，但回复仍有伪待办/格式失败。 | trace_export/extract；夹具v3。state的43是累计HTTP，不能全计给B01。hover/console不在本组执行证据；改措辞/task/context的对照不是单变量。 |
| B02/B03浏览器 | [browser-group2-trace](evidence/browser-group2-trace.json) | 9请求/15模型HTTP/5实际MCP：navigate、snapshot、hover、evaluate、console info；error请求无调用却声称成功。 | trace_export。有效approve后仍有伪待办，不全归“无待办继续”分支；已有info输出吻合不证明error实际执行；不能将历史复用猜测当唯一根因。 |
| G01 GitHub | [github-group1-trace](evidence/github-group1-trace.json)、[phase02-final-state](evidence/phase02-final-state.json) | 4请求/6模型HTTP；专用Issue读取/更新真实执行，主执行另有CLI标题正文读回。 | trace_export/extract；准备提交/Issue/PR在TEST_OBJECTS。PR创建是Codex准备，不计天依执行；不扩到其他GitHub method/action。 |
| 继续错误宿主提示 | [continuation-counterfactual-01](evidence/continuation-counterfactual-01.json) | 实际AST条件/常量5合成case，无pending+继续/go on仍写待确认；正常pending/无task/新要求控制。 | [round02_continuation_counterfactual.py](../../../../scripts/root_cause_audit/round02_continuation_counterfactual.py)。证明宿主语义矛盾，不是实模型删除该提示的因果干预；I09归属独立反例、主执行复现。 |
| 本地实现分支 | [local-branches-01](evidence/local-branches-01.json)、[local-branches-script-provenance](evidence/local-branches-script-provenance.json) | 29指定观察；临时文件/数据库、command mock、UTF8边界、20消息会话隔离、sweep后内容核对、replace失败残留。 | [round02_local_branches.py](../../../../scripts/root_cause_audit/round02_local_branches.py)。matched不是能力PASS；tmp由脚本清理不等于write_file清理。脚本hash事后补录，非运行中绑定。 |
| 字节/命令/raw/解析反例 | [edge-counterfactuals-01](evidence/edge-counterfactuals-01.json) | 22观察；坏UTF8+页边界损失、带空格exe误拒、null/类型与适配器异常差异、真实20条组装。 | [round02_edge_counterfactuals.py](../../../../scripts/root_cause_audit/round02_edge_counterfactuals.py)。AST/替身/临时库，零真实命令/模型；未证明真实供应商本轮发过null，不解释旧“{”唯一来源。 |
| 窗口API/factory装配 | [wiring-counterfactuals-01](evidence/wiring-counterfactuals-01.json) | 2个fake Win32层级控制+5个factory构造器spy；正式factory未传reload_config。 | [round02_wiring_counterfactuals.py](../../../../scripts/root_cause_audit/round02_wiring_counterfactuals.py)。没有真实前台标题查询/换key，不证明运行对象；active_window失败是实现问题，不能归“未启用”免验。 |
| 评测可信度 | [grader-counterexamples](evidence/grader-counterexamples.jsonl) | 主执行复现：positive PASS、无关read PASS、1750 PASS、无read FAIL；两个误PASS。 | [round02_grader_counterexamples.py](../../../../scripts/root_cause_audit/round02_grader_counterexamples.py)。独立审查先给反例，主执行复现；不擅改原成绩、不推全部历史均误判。 |
| phase03启动/三档/模型 | [phase03-short](evidence/phase03-short.json)、[effort-frontend-trace](evidence/effort-frontend-trace.json)、[glm-compare-trace](evidence/glm-compare-trace.json)、[model-effort-comparison](evidence/model-effort-comparison.json) | v3正式链短句；DS三档同一文件题及GLM高档各一次，均真实read_file/回执/播放完成；比较表是两trace的派生摘要。 | observer_v3/trace_export；比较表未内嵌专用生成脚本身份。DS/GLM高档初始messages/tools hash相同，模型和进程不同；单题不能排模型强弱，不证明内部推理参数，听感未逐项确认。 |
| 记忆现场与落库差分 | [memory-frontend-trace](evidence/memory-frontend-trace.json)、[memory-before-correction](evidence/memory-before-correction.json)、[memory-after-correction](evidence/memory-after-correction.json) | 6前台请求、受限合成context；显式记住存global，普通更正存session/pending，新会话召回仍见旧预算；两个同身份快照差分既有25事实无变化。 | observer_v3/trace_export/identity；差分文件未内嵌专用提取脚本身份，来源按快照hash定位。索引不展示事实正文、不读原DB。模型承诺与最终fact_id/scope回执不同。 |
| 记忆更正反事实 | [memory-counterfactual-01](evidence/memory-counterfactual-01.json) | 固定实际合成candidate，仅追加显式记住；临时库2case晋升/作用域改变，同时复合事实的词法supersede选错实体条目。 | [round02_memory_counterfactual.py](../../../../scripts/root_cause_audit/round02_memory_counterfactual.py)。零生产DB读；实际替换后候选仍含另实体，不能说其语义全部丢失。隔离变化不冒充现场已发生。 |
| 覆盖/静态独立审查 | [COVERAGE_REVIEW.md](COVERAGE_REVIEW.md)/[json](COVERAGE_REVIEW.json)、[ADVERSARIAL_REVIEW](ADVERSARIAL_REVIEW.md)、[BRANCH_MAP_REVIEW](BRANCH_MAP_REVIEW.md) | 原184+72逐ID分层；98旧断言、工具描述method、UI/WS、未启用/未实现边界；独立反例及处置记录。 | 文档审查，不是独立重跑362或前台。I10时间差为代码差异+主执行截图观察，非独立读取私人消息；补充wake状态在上行，既有报告时点缺口保留。 |

## 私有来源与hash的解释

私有根指针记为{PRIVATE_ROUND02}，对应本工作区work/private-round02；此索引没有打开它。根据TEST_OBJECTS/STATE，observer v1日志在根目录，v2在phase02，v3在phase03。下表使用公开sources条目及记录版本关联目录；目录由阶段记录推定时会明确注明，不把basename当全路径身份证明。

trace公开文件保存的是已筛选、脱敏且去除私有reasoning字段的记录。sources[].prefix_bytes/prefix_sha256绑定私有日志当时最后完整换行之前的前缀，不是持续追加文件的最终hash，也不是公开records序列的hash。model.http.response中的raw字节hash属于过滤前响应，不能由公开净化payload重建；messages整体hash是规范序列摘要，不能还原逐段正文。下面“公开文件hash”是本索引读取时计算的字节hash，仅供冻结版本定位。

事务摘录的snapshot_sha256绑定私有transaction-snapshot.sqlite3；多数公开摘录没有保存具体父目录名，使用hash作原始来源指针，不能猜造路径。卷号/file ID一致及读事务backup水位相等不代表已验证运行中的Core数据库句柄。快照含私人内容，不随索引展开。



### 日志前缀来源（已有公开指纹）

这些行复述各导出自己的sources，重叠前缀不可相加；较长前缀仍可能包含其他未导出的请求。

| 公开导出 | 请求/记录数 | 私有源指针 | 前缀字节 | 前缀SHA256 |
|---|---:|---|---:|---|
| [browser-group1-trace.json](evidence/browser-group1-trace.json) | 8/1274 | {PRIVATE_ROUND02}/phase02/trace-23404.jsonl（版本/阶段映射） | 2142917 | 5a0f301195fd4cd8b68ff7bcb112b4e7896c411ac3bd1ee853f09753acc1cc75 |
| [browser-group1-trace.json](evidence/browser-group1-trace.json) | 8/1274 | {PRIVATE_ROUND02}/phase02/trace-30624.jsonl（版本/阶段映射） | 131867 | d8a28dacb7ca146d7d5e8b5a72d3e34175a5dde36ff33739915f87013b460429 |
| [browser-group2-trace.json](evidence/browser-group2-trace.json) | 9/1216 | {PRIVATE_ROUND02}/phase02/trace-23404.jsonl（版本/阶段映射） | 3802497 | 600391445f99706701bd2e5eca24d4e38ca3f99f95bcc8bcc1f7dde2e06d8d34 |
| [browser-group2-trace.json](evidence/browser-group2-trace.json) | 9/1216 | {PRIVATE_ROUND02}/phase02/trace-30624.jsonl（版本/阶段映射） | 233298 | 42629c870c2e078d59eb58f5a570249c3079cb932b039fb00662f3cc8904b90f |
| [drive-frontend-trace.json](evidence/drive-frontend-trace.json) | 2/286 | {PRIVATE_ROUND02}/phase02/trace-23404.jsonl（版本/阶段映射） | 548359 | 17c3766fd7b21273ef73e5a3b17115b6d07ecda1194f452aa67e0917d5e341c2 |
| [drive-frontend-trace.json](evidence/drive-frontend-trace.json) | 2/286 | {PRIVATE_ROUND02}/phase02/trace-30624.jsonl（版本/阶段映射） | 20223 | eff967bb28a06efd3b05c24b3937f070d076bdc324ffd3d7312a6ecfabcff65f |
| [effort-frontend-trace.json](evidence/effort-frontend-trace.json) | 3/211 | {PRIVATE_ROUND02}/phase03/trace-25684.jsonl（版本/阶段映射） | 809253 | e9fafedba803373c42a9d1bd48974bacb5ecc05e2b54f7830ea6ed302d78c53c |
| [effort-frontend-trace.json](evidence/effort-frontend-trace.json) | 3/211 | {PRIVATE_ROUND02}/phase03/trace-4184.jsonl（版本/阶段映射） | 9698 | d95bb668d85485e4681dc128a778f6f99a834da012f5c5f594c274db1fc7c057 |
| [github-group1-trace.json](evidence/github-group1-trace.json) | 4/424 | {PRIVATE_ROUND02}/phase02/trace-23404.jsonl（版本/阶段映射） | 4404715 | b278f95e1276c36ecde7c185ff4f7bcfa89aca67e1b99a38828c754d62e6d417 |
| [github-group1-trace.json](evidence/github-group1-trace.json) | 4/424 | {PRIVATE_ROUND02}/phase02/trace-30624.jsonl（版本/阶段映射） | 263307 | 322c75866d337abb8fd919957c127dc99b6d50fb43b57ab899ce525564d951df |
| [glm-compare-trace.json](evidence/glm-compare-trace.json) | 1/75 | {PRIVATE_ROUND02}/phase03/trace-16700.jsonl（版本/阶段映射） | 3632 | 2d83320fa120b1efd19256d6a705afc6728731ac381b09947ccb6eb3864b6e56 |
| [glm-compare-trace.json](evidence/glm-compare-trace.json) | 1/75 | {PRIVATE_ROUND02}/phase03/trace-27300.jsonl（版本/阶段映射） | 335736 | 84fe8e18f348ed13e678c0b2502602cc9e5812439864cd2155888398d441fd65 |
| [gmail-tts-live-trace-v2.json](evidence/gmail-tts-live-trace-v2.json) | 2/309 | {PRIVATE_ROUND02}/phase02/trace-14200.jsonl（版本/阶段映射） | 42845 | 657db94063b00c35aadad1e9c227f536cb2a17af0f3bfb634fe365cd6e4e5c26 |
| [gmail-tts-live-trace-v2.json](evidence/gmail-tts-live-trace-v2.json) | 2/309 | {PRIVATE_ROUND02}/phase02/trace-23396.jsonl（版本/阶段映射） | 5524 | fdac3a8cd39c409d47831e058ca1f803c987426b6b2f98f0c25ec6a5f50c600a |
| [gmail-tts-live-trace-v2.json](evidence/gmail-tts-live-trace-v2.json) | 2/309 | {PRIVATE_ROUND02}/phase02/trace-5836.jsonl（版本/阶段映射） | 2275980 | fc674637b7ebf20832c37bd06ad053fb83d04ac288d62c8225c1636cee5ce567 |
| [gmail-tts-live-trace.json](evidence/gmail-tts-live-trace.json) | 2/308 | {PRIVATE_ROUND02}/phase02/trace-14200.jsonl（版本/阶段映射） | 42845 | 657db94063b00c35aadad1e9c227f536cb2a17af0f3bfb634fe365cd6e4e5c26 |
| [gmail-tts-live-trace.json](evidence/gmail-tts-live-trace.json) | 2/308 | {PRIVATE_ROUND02}/phase02/trace-23396.jsonl（版本/阶段映射） | 5524 | fdac3a8cd39c409d47831e058ca1f803c987426b6b2f98f0c25ec6a5f50c600a |
| [gmail-tts-live-trace.json](evidence/gmail-tts-live-trace.json) | 2/308 | {PRIVATE_ROUND02}/phase02/trace-5836.jsonl（版本/阶段映射） | 2273120 | 06c44c1a698889a774fd47b44167e5afb38ff85bb309ffbb9d7e86bf2b0b7e98 |
| [local-group1-trace-v2.json](evidence/local-group1-trace-v2.json) | 3/408 | {PRIVATE_ROUND02}/trace-38584.jsonl（版本/阶段映射） | 182635 | 6b317f73ea9b86272ce079135bc93a035e26528b3dcb19062ca8ba90bfcb077a |
| [local-group1-trace-v2.json](evidence/local-group1-trace-v2.json) | 3/408 | {PRIVATE_ROUND02}/trace-40896.jsonl（版本/阶段映射） | 28232 | 662eca878f049154fe45df85f2e14fdbc7ca0f84efffecd1d098207fecebaaaf |
| [local-group1-trace.json](evidence/local-group1-trace.json) | 3/408 | {PRIVATE_ROUND02}/trace-38584.jsonl（版本/阶段映射） | 182635 | 6b317f73ea9b86272ce079135bc93a035e26528b3dcb19062ca8ba90bfcb077a |
| [local-group1-trace.json](evidence/local-group1-trace.json) | 3/408 | {PRIVATE_ROUND02}/trace-40896.jsonl（版本/阶段映射） | 28232 | 662eca878f049154fe45df85f2e14fdbc7ca0f84efffecd1d098207fecebaaaf |
| [longfile-confirm-trace.json](evidence/longfile-confirm-trace.json) | 3/410 | {PRIVATE_ROUND02}/phase02/trace-14200.jsonl（版本/阶段映射） | 28222 | 4ff5b7c0301da84078739160ab448f8a1822e9da8d45ac430508891d71c64ffd |
| [longfile-confirm-trace.json](evidence/longfile-confirm-trace.json) | 3/410 | {PRIVATE_ROUND02}/phase02/trace-5836.jsonl（版本/阶段映射） | 1705286 | 7503cc5670353acdde2050d03c293bd5efae70f12939e3001c6a2957ef1afa1b |
| [manual-voice-trace.json](evidence/manual-voice-trace.json) | 4/42 | {PRIVATE_ROUND02}/phase02/trace-5836.jsonl（版本/阶段映射） | 267993 | 45f3c97a5877f59ffb8ab163a447d50c2b856a299bf896e47be057b68a3504ad |
| [memory-frontend-trace.json](evidence/memory-frontend-trace.json) | 6/598 | {PRIVATE_ROUND02}/phase03/trace-16700.jsonl（版本/阶段映射） | 35409 | 2bd75d7dbf7037fb3f316f5e99248a9ceab1165ddde9596a47fe59e0ee18b50b |
| [memory-frontend-trace.json](evidence/memory-frontend-trace.json) | 6/598 | {PRIVATE_ROUND02}/phase03/trace-27300.jsonl（版本/阶段映射） | 1183529 | 6b97af9afc0a814e1316fe67934dc9a1cb03e993bfbbfaa26f564d510294deb1 |
| [phase03-short.json](evidence/phase03-short.json) | 1/47 | {PRIVATE_ROUND02}/phase03/trace-25684.jsonl | 349195 | 8d0c8f149061dd42caf798b115a31413e1de28eef5eec6b12bd6dc9e4db42ded |
| [phase03-short.json](evidence/phase03-short.json) | 1/47 | {PRIVATE_ROUND02}/phase03/trace-4184.jsonl | 3800 | e0ddb3a30ee5de41d67c3c320663843170a0d48c9d8a5079bc065987244ac531 |
| [tts-recovered-short.json](evidence/tts-recovered-short.json) | 1/56 | {PRIVATE_ROUND02}/phase02/trace-23404.jsonl（版本/阶段映射） | 121505 | afbad1ee6f340bb26209b078a6f21d4f5c09224813546dca5a69455f1fcdf8d7 |
| [tts-recovered-short.json](evidence/tts-recovered-short.json) | 1/56 | {PRIVATE_ROUND02}/phase02/trace-30624.jsonl（版本/阶段映射） | 2898 | 67d9bd996135e09c9861d83fbb607d425231294ca51657b3d0725cbd392437b5 |

### 事务快照、独立来源与派生文件

| 公开摘录 | 原始来源指针/已有指纹 | 限定说明 |
|---|---|---|
| [browser-group1-state.json](evidence/browser-group1-state.json) | transaction-snapshot.sqlite3；SHA256 c7805f147a7a7d1745d99f5536f14ff9cd9870a48801cf1af5ce9adc0cfe7ec7 | 父目录未在公开摘录保存，按hash关联原identity目录；采集UTC 2026-10-07T16:54:50.875548+00:00 |
| [desktop-start.json](evidence/desktop-start.json) | transaction-snapshot.sqlite3；SHA256 5d061236742102ae5f6aec8bdd2fdb57d3105c5391c90a004d06c8b6d8ef8303 | 父目录未在公开摘录保存，按hash关联原identity目录；采集UTC 2026-10-07T15:00:30.971981+00:00 |
| [local-group1-state.json](evidence/local-group1-state.json) | transaction-snapshot.sqlite3；SHA256 d103fa02da742b0a9a37385bf08f8e5a0e130603e3fa121aff28b861e784d886 | 父目录未在公开摘录保存，按hash关联原identity目录；采集UTC 2026-10-07T15:36:12.341518+00:00 |
| [local-mail-state.json](evidence/local-mail-state.json) | transaction-snapshot.sqlite3；SHA256 da7d8039a984eafb765c13bb21d17449f70381ce210b02987be1d66b651df64a | 父目录未在公开摘录保存，按hash关联原identity目录；采集UTC 2026-10-07T16:15:20.369660+00:00 |
| [memory-after-correction.json](evidence/memory-after-correction.json) | 基线SHA256 de72ba3570a8a8cfe309ae994fd9891415086f4c7a78fb842a53a41ca44e532c；差分后SHA256 11a996c211b7eacc64855d6233e27a77b3e2221f4a3eaef726e0e32f7e2011c6 | 卷3903461716/file ID2533274790580297；不展开事实正文 |
| [memory-before-correction.json](evidence/memory-before-correction.json) | 基线SHA256 de72ba3570a8a8cfe309ae994fd9891415086f4c7a78fb842a53a41ca44e532c；差分后SHA256 aeae3e8d0a3c357338e287cde455c39e7f0645577320fb9a129414724f7035ec | 卷3903461716/file ID2533274790580297；不展开事实正文 |
| [phase02-final-state.json](evidence/phase02-final-state.json) | transaction-snapshot.sqlite3；SHA256 1a2fe41eae30815904e374c3cf9998410fdd4df0962536fedd42926d82518e69 | 父目录未在公开摘录保存，按hash关联原identity目录；采集UTC 2026-10-07T17:36:31.590030+00:00 |
| [real-idle-receipts-v2.json](evidence/real-idle-receipts-v2.json) | transaction-snapshot.sqlite3；SHA256 8c95e5d5e831f77ab48305c1522bacda6530b142929b2d6b1011595cfa6a1a93 | 父目录未在公开摘录保存，按hash关联原identity目录 |
| [real-idle-receipts-v3.json](evidence/real-idle-receipts-v3.json) | transaction-snapshot.sqlite3；SHA256 8c95e5d5e831f77ab48305c1522bacda6530b142929b2d6b1011595cfa6a1a93；基线SHA256 bbe22d0ed043fea6a000652997364e3619e4bfa63edcf8742a4fd48ec8c1ba07 | 父目录未在公开摘录保存，按hash关联原identity目录 |
| [real-idle-receipts.json](evidence/real-idle-receipts.json) | transaction-snapshot.sqlite3；SHA256 8c95e5d5e831f77ab48305c1522bacda6530b142929b2d6b1011595cfa6a1a93 | 父目录未在公开摘录保存，按hash关联原identity目录 |
| [voice-idle-state.json](evidence/voice-idle-state.json) | transaction-snapshot.sqlite3；SHA256 8c95e5d5e831f77ab48305c1522bacda6530b142929b2d6b1011595cfa6a1a93 | 父目录未在公开摘录保存，按hash关联原identity目录；采集UTC 2026-10-07T15:58:49.888852+00:00 |
| [wake-disabled-phase03.json](evidence/wake-disabled-phase03.json) | {PRIVATE_ROUND02}/identity-glm-start/identity.json；快照SHA256 de72ba3570a8a8cfe309ae994fd9891415086f4c7a78fb842a53a41ca44e532c | UTC 2026-10-07T17:54:58.514052+00:00，Core 27300；仅该代际 |
| Gmail/Drive独立读取 | 已知首轮{PRIVATE_ROUND02}/connector-reads-01.json；后续公开摘录未保存准确私有文件名 | 两文件adapter_sha256均为20bc354c081919b193699466ea36db21fb0e4df6d8f4e46c36ffbbb4f855f2d7；不猜补后续路径 |
| model-effort-comparison.json | source_evidence=effort-frontend-trace.json、glm-compare-trace.json | 派生汇总不与源trace重复累计；未附专用生成脚本身份 |
| deployment-entry.json | 54项files hash；env_sha256=55050b08961a662af55a94297d5c464fa705f81d0db8bd4db53f072413f4fbda | 起点指纹不表明模型切换后当前env已恢复 |

### 隔离复现与诊断的内嵌源码/脚本指纹

复述报告已有指纹，没有字段的文件不由当前代码倒填运行时身份。main全文件hash随overlay代际改变，不能与起点54文件无条件混用。

| 公开文件 | 已有指纹字段 | SHA256 |
|---|---|---|
| [continuation-counterfactual-01.json](evidence/continuation-counterfactual-01.json) | script_sha256 | 975b8615d6e13ab88de4bb1010d3e644c25f243e0240df0cc75fc874af8fa3b1 |
| [continuation-counterfactual-01.json](evidence/continuation-counterfactual-01.json) | source_sha256 | e64a26e426b1cf3c00447f2dc39fc775241114498e1c257ebdd86e3e66d3d3f5 |
| [edge-counterfactuals-01.json](evidence/edge-counterfactuals-01.json) | script_sha256 | 1bc98737569cc8cd401693e584687ac247e16d31379217397489b7a57139ffde |
| [edge-counterfactuals-01.json](evidence/edge-counterfactuals-01.json) | source_hashes.tools.py | 9f751b0c507dacad78b8ca6cfc4dd1bb0d83ab1f4137984f32cb07dfb9de54d7 |
| [edge-counterfactuals-01.json](evidence/edge-counterfactuals-01.json) | source_hashes.storage.py | 91450c232cacdd05d7fb7835e5ee58812da024d0d446b4580905ff59b64fc06b |
| [edge-counterfactuals-01.json](evidence/edge-counterfactuals-01.json) | source_hashes.harness.py | f4b0a888d14bc2b20b994971be601cc72255c6a8976a0e271e2881770a170e25 |
| [edge-counterfactuals-01.json](evidence/edge-counterfactuals-01.json) | source_hashes.main.py | e64a26e426b1cf3c00447f2dc39fc775241114498e1c257ebdd86e3e66d3d3f5 |
| [local-branches-01.json](evidence/local-branches-01.json) | source_hashes.tools.py | 9f751b0c507dacad78b8ca6cfc4dd1bb0d83ab1f4137984f32cb07dfb9de54d7 |
| [local-branches-01.json](evidence/local-branches-01.json) | source_hashes.storage.py | 91450c232cacdd05d7fb7835e5ee58812da024d0d446b4580905ff59b64fc06b |
| [memory-counterfactual-01.json](evidence/memory-counterfactual-01.json) | script_sha256 | aeac5874b99256e811ca020251cd28f59466cb468b8ec454ec560c6ad86bfedf |
| [memory-counterfactual-01.json](evidence/memory-counterfactual-01.json) | source_sha256.main.py | 7af0c89c3fd171c749c1fee5e94e42a414d68adfb98c39f7a2e9b7d0eca905fc |
| [memory-counterfactual-01.json](evidence/memory-counterfactual-01.json) | source_sha256.storage.py | 91450c232cacdd05d7fb7835e5ee58812da024d0d446b4580905ff59b64fc06b |
| [memory-counterfactual-01.json](evidence/memory-counterfactual-01.json) | input_trace_sha256 | e20cc08576d914b05119ec3117e01ff7677ae9e45226cd00615f1223810174d9 |
| [observer-edges.json](evidence/observer-edges.json) | observer_sha256 | 4cc6d05e91b7230bcf032b1e4bdcbcca1d79faacf6a64b2820981caec8d6605d |
| [overlay-check-v3.json](evidence/overlay-check-v3.json) | script_sha256 | 2252788e76743f3e48fc58d749b957cf54a8df0d14c5a64665c1424394e52c3d |
| [overlay-check-v3.json](evidence/overlay-check-v3.json) | observer_sha256 | 77b2f610ec795e7263a3df5def20503b2b9927a0fd547e66c868ebe96af824fd |
| [overlay-check-v3.json](evidence/overlay-check-v3.json) | overlay_sha256 | 41da48f37d9ecbd5d56f1e0901eba4518a3427dec578666bf5c5ab0e58119066 |
| [overlay-check-v3.json](evidence/overlay-check-v3.json) | source_entry_hashes.core | da3a01ce8b184880b13350e370903089e088d5f49d6780c76b1f688ae3e78d95 |
| [overlay-check-v3.json](evidence/overlay-check-v3.json) | source_entry_hashes.tts | ef5e8a276d103ecc77dc04876fe483a755b0a5421e089ae2fcb41261ad62a135 |
| [tts-exact-counterfactual.json](evidence/tts-exact-counterfactual.json) | source_sha256 | 4fbbe2b1a4ef43fab3c122af291f4ec8b6ae274d004f7ded69de9883acfdd72c |
| [tts-exact-counterfactual.json](evidence/tts-exact-counterfactual.json) | speech_sha256 | 31b77cd18b09efb68db48a2725fc44dbe97f7c81d9679657c7b46817dd9d4fbc |
| [wiring-counterfactuals-01.json](evidence/wiring-counterfactuals-01.json) | script_sha256 | 79767bd48302f06871f361d53022803675a491df6140b92c364a6aac70c642f3 |
| [wiring-counterfactuals-01.json](evidence/wiring-counterfactuals-01.json) | source_sha256.main.py | 7af0c89c3fd171c749c1fee5e94e42a414d68adfb98c39f7a2e9b7d0eca905fc |
| [wiring-counterfactuals-01.json](evidence/wiring-counterfactuals-01.json) | source_sha256.tools.py | 9f751b0c507dacad78b8ca6cfc4dd1bb0d83ab1f4137984f32cb07dfb9de54d7 |
| [local-branches-script-provenance](evidence/local-branches-script-provenance.json) | 事后脚本hash，非原report运行中绑定 | 0eb6f9072e05e9b6906adf64c9300124d537de85246487889e0dff57b00b3f0f |

## 公开文件版本清单（索引读取时hash）

由本次整理读取公开文件字节计算，不是新业务实测、签名或原始私有证据替代物；JSONL按原字节计算。新文件可在后续追加，不能静默替换旧版结论。

| 公开文件 | 字节数 | SHA256 |
|---|---:|---|
| [browser-group1-state.json](evidence/browser-group1-state.json) | 194366 | 4282c7407c5d3a1a90d36d32f44025f2d17c3d1456aa31161e8fd41021f402f0 |
| [browser-group1-trace.json](evidence/browser-group1-trace.json) | 1018549 | 87b8043bf3b892956e087d7a30fde2df88c31bcfaa3ccdd7a11dc20c5b4f3c61 |
| [browser-group2-trace.json](evidence/browser-group2-trace.json) | 985601 | ea43104ed1dcf45d9334bd947d8d60ea9d808fd684314dcc111034c72a4b2857 |
| [continuation-counterfactual-01.json](evidence/continuation-counterfactual-01.json) | 2336 | a496c461ac06b03359c5b97797bb24e374cf6cf3149d38ef5c0f2ca92d2cbadb |
| [deployment-entry.json](evidence/deployment-entry.json) | 11146 | 7d18645f939de97b11b86c96cf2c06ca006885447dbe18024c1f8f51976b13fc |
| [desktop-start.json](evidence/desktop-start.json) | 3221 | 4df6c9d335a9f5dcf31dd767129074494298f007ecb9a99b37bbe549bcaba322 |
| [drive-frontend-trace.json](evidence/drive-frontend-trace.json) | 209540 | 92fb362a0c74d8fb98cd2f205107ae2d6c9960421c8fecf52c3d944ccab1fc64 |
| [drive-independent-read.json](evidence/drive-independent-read.json) | 2855 | b0f536f16ccd4a6b378370b3506b0deab23333b18f664fdf0fe18be6b3685a5d |
| [edge-counterfactuals-01.json](evidence/edge-counterfactuals-01.json) | 13800 | 9cf356c6e33c3ee31b802f951d80f64bd6bf7144748ca91dff2504977bdb2f5d |
| [effort-frontend-trace.json](evidence/effort-frontend-trace.json) | 166886 | ada104505d34bdbfd379b0c5ac02091b85a126785aca13355934b4c0ccfabaff |
| [external-fixtures.json](evidence/external-fixtures.json) | 1101 | 2c705c6419f8e53a29ab470ba313514a48b4e6ccb0169259bc96ff996c5e966d |
| [github-group1-trace.json](evidence/github-group1-trace.json) | 318195 | 603070b3d48b520456a0576827cd3cdac52a44df53616ee32c80bf7676c428ad |
| [glm-compare-trace.json](evidence/glm-compare-trace.json) | 58301 | 7581538a4ed22647582d11e01b272dd8de1ce4001105b7b4112587c129e7914e |
| [gmail-draft-label-readback.json](evidence/gmail-draft-label-readback.json) | 569 | 23f3abd4fdada5f8e22f9590eb5363af07c9fd59df13b0e670d41ffdd342e781 |
| [gmail-independent-read.json](evidence/gmail-independent-read.json) | 4836 | 6564b9aa92906d9ceefca5927dee537e9c558d91592d458afc18f5bc5605cf82 |
| [gmail-tts-live-trace-v2.json](evidence/gmail-tts-live-trace-v2.json) | 332544 | e8a8f1b5f0c6334d7b73f38a537da5d736b1cd4e7399d0e1991dd89dabf3a807 |
| [gmail-tts-live-trace.json](evidence/gmail-tts-live-trace.json) | 329782 | 118f35cdefb63e0e292adb5773017d567f40d8ead366d93cdebb9268c2f303dd |
| [grader-counterexamples.jsonl](evidence/grader-counterexamples.jsonl) | 251 | fb9e8dd7b59357b012e357ba717ca6bff60d3f5724f65a980ab143e8076e2b09 |
| [local-branches-01.json](evidence/local-branches-01.json) | 17043 | 89b9a31ded3c9e74649788ee4dd8609cabfb68424e20037d4fd1549848824893 |
| [local-branches-script-provenance.json](evidence/local-branches-script-provenance.json) | 479 | 3e0b1f5287f091989e6e7f371a2699d6b8c801df55ce334bf236a4940254dadd |
| [local-fixtures.json](evidence/local-fixtures.json) | 976 | ac9667ea55aa078fa4c0a45c1a92a7a70d19ad8a4d9652ee95ccffef170f411c |
| [local-group1-state.json](evidence/local-group1-state.json) | 28155 | 72e87e44063d2dce3fa752f181452b8d45dbbb33292dcffcf140f19b73cd3b14 |
| [local-group1-trace-v2.json](evidence/local-group1-trace-v2.json) | 263518 | 6b2e227ddd279537f0ae961840821e9e94a2f91231845412182d1f9df2338f4d |
| [local-group1-trace.json](evidence/local-group1-trace.json) | 262952 | cd4b642515c0e085d0918aa9d0ce00a6b09b42beb7cca0adf68a184c1ffd055b |
| [local-mail-state.json](evidence/local-mail-state.json) | 83316 | 81f58a81c7566f96073e68d702cd7b9180fa76743f6ead46723a659f385e6515 |
| [longfile-confirm-trace.json](evidence/longfile-confirm-trace.json) | 497576 | c2d0b8c0a33c12c6784e6c5afd7c96aa22bd8b96cf7ea1f3e2cd4c4e38a9d89c |
| [manual-voice-trace.json](evidence/manual-voice-trace.json) | 23488 | e9657d3c6909903b1d5ad33ac0366d4f6d09ffe8d86f7f882398811cd1e2b908 |
| [memory-after-correction.json](evidence/memory-after-correction.json) | 1479 | 4ce19164d6fef523dbdcd0d5d846b692ce824f4ef0f45aee405b15eadf82bdbc |
| [memory-before-correction.json](evidence/memory-before-correction.json) | 1120 | 5570c712c4e8a69e82c5956d6adc01a38998e09946eb0747c262eb94af739e77 |
| [memory-counterfactual-01.json](evidence/memory-counterfactual-01.json) | 3478 | d111e32508736c146afe9879a21cc355eba6576266c4a59fbd785c3ce6a7ac85 |
| [memory-frontend-trace.json](evidence/memory-frontend-trace.json) | 416373 | e20cc08576d914b05119ec3117e01ff7677ae9e45226cd00615f1223810174d9 |
| [model-effort-comparison.json](evidence/model-effort-comparison.json) | 8983 | e127885b8a3d505bbff3e2d12c79f213490dcc2dbac56a2d30dfbac197e9723e |
| [observer-check-v2.json](evidence/observer-check-v2.json) | 579 | 273ae0e6e9bde0ab906fcddd4b442360a6e4653665a82940d66629f99f3fa76d |
| [observer-check-v3.json](evidence/observer-check-v3.json) | 1981 | 488834b7b4f6b9c3fec890fc5c66b8f77df0f82d12b35097fd8f43059f7b5608 |
| [observer-check.json](evidence/observer-check.json) | 579 | c4a78e689dc8afddf7868c50b0908f22b8eb009276ab3bdc0efe9501100de5d5 |
| [observer-edges.json](evidence/observer-edges.json) | 638 | ae2a152c4ab31272f25e814214258c648e3cfeb2ce0a20ddd8440641b09cb5df |
| [offline-suite.json](evidence/offline-suite.json) | 32848 | d272a39ff98e09e6d903a2a4bfae7b4ced6ddfe0bdc223edbaf714296482da93 |
| [overlay-check-v3.json](evidence/overlay-check-v3.json) | 783 | 2885a85241435672a6ddafa5ab2147ea3ae2c894f0f37b0f93abe9539e35a767 |
| [overlay-check.json](evidence/overlay-check.json) | 464 | 63b3a6d2988176a9f2953dfa8d77708c3a66033e168157f226c5ac3447e6e20d |
| [phase02-final-state.json](evidence/phase02-final-state.json) | 305817 | d384e1998b5af414f27f9da5022a8cb1ba73807ec60588ed32533ea64d873109 |
| [phase03-short.json](evidence/phase03-short.json) | 220411 | 7f8067abc146b9be67195f57826d9d6202cee2138f5654611eacd125af20eca1 |
| [real-idle-01.json](evidence/real-idle-01.json) | 24798 | 5a739221664276f3a37b30d175474285ec6bb81991c2889bbe6357d4551ef60c |
| [real-idle-receipts-v2.json](evidence/real-idle-receipts-v2.json) | 2238 | 808c4c35fe41a73850dd837cb3978facc25f58c0af044ec1720bb0411fecc8bd |
| [real-idle-receipts-v3.json](evidence/real-idle-receipts-v3.json) | 2547 | b651dc86562934bb6e47435a358d48b0c9e28fa26016adcd7b22fcf1e3cdbdcd |
| [real-idle-receipts.json](evidence/real-idle-receipts.json) | 642 | 5616df2d21fb6591b58994ccd85d421b14793d589e125fa7c03b00ea697959b3 |
| [tts-exact-counterfactual.json](evidence/tts-exact-counterfactual.json) | 1207 | e5b1926620bdb5c8f513acfbe2af2817f9ae95b6eb1be1517f50763509feb2ad |
| [tts-recovered-short.json](evidence/tts-recovered-short.json) | 39840 | 048fcf7f15902d018b79ca4c7b7df31bdb87eefae08a82fd02f067ed08729050 |
| [voice-idle-state.json](evidence/voice-idle-state.json) | 38700 | 6071eb2150673885c52f60c8ce6bc7c66f7177fb4d394b13bd8d652363d4f8a2 |
| [wake-disabled-phase03.json](evidence/wake-disabled-phase03.json) | 474 | d3b835e17cc200eeaa5ed68f26bfb94078d69d8e48c6de7be2578c7fcdc74b8f |
| [wiring-counterfactuals-01.json](evidence/wiring-counterfactuals-01.json) | 2746 | f5b279bc821f265c6fb6c638e893c30c98a7f3bedbd38d2d1f15035ee9e14c83 |
| [fixture-v2.html](fixtures/fixture-v2.html) | 3695 | 86459c2ba8d7cf2575e4b26446aadeda8bdfb3ffd5edbe61c91338c150c6bdc1 |
| [fixture-v3.html](fixtures/fixture-v3.html) | 5236 | 8820ea9b0f6685e69bc74e9ed50a9dfaec6f28a3e4fec4a034123aa43cb033a3 |

## 截止与追加规则

目录/字节快照开始于 **2026-10-07 18:19:00 UTC**（Asia/Shanghai 2026-10-08 02:19:00），纳入50个公开JSON/JSONL证据文件和2个HTML夹具。逐文件读取，不声称整个目录具有事务一致性；其后主执行仍新增材料，未列文件不等于没有执行或失败。

后续追加须写明文件/优先版本、采集者与层次、源前缀或快照指纹、脚本身份、覆盖范围与缺口。没有原始指针、脚本绑定或受控正文时保留缺口；不以索引替代原报告/独立审查。当前连接器后续批次、最终配置与诊断恢复以新证据为准；本索引不宣布全审计完成。

## 收尾增补：Gmail第二组与恢复前累计

追加读取时点：**2026-10-07 18:29:07 UTC**（北京时间2026-10-08 02:29:07）。保留前述02:19的50文件截止清单，另纳入以下3个公开证据文件；本索引累计53个JSON/JSONL及2个HTML夹具，未重新执行业务、外部读回或测试。这里的53个文件与覆盖账本的53个有观察ID是不同计数。

| 公开文件 | 证据层及支持结果 | 来源/脚本身份和缺口 |
|---|---|---|
| [gmail-group2-trace.json](evidence/gmail-group2-trace.json) | 主执行当前Godot前台链，4请求/674记录；3个实际MCP raw回执涉及create_label、draft_email、search_emails。标签创建后首次确认的fallback45秒超时、没有答案仍是失败；之后指定草稿与限定搜索分列。记录中7条model.http.request、6条response、1条exception，不将异常算成功响应。 | observer-v3及round02_trace_export.py，phase03来源前缀见下表；本次读取为主执行完成显示名减敏后的公开版本，本实例没有重新执行全量隐私审查。正常草稿正文text/plain且含本轮附件，maxResults=5限定搜索不覆盖全部MIME/附件/搜索/标签参数；听感未逐项确认。 |
| [gmail-draft-label-readback.json](evidence/gmail-draft-label-readback.json) | Codex独立Gmail API读回4次，核对专用label、draft、收件人匹配授权自有邮箱，以及attachment.txt的60字节和hash。 | 独立读回不是天依二次执行，不与前台3个工具调用合并计数；公开文件未内嵌准确私有响应文件名、专用生成脚本身份或完整raw hash，缺口保留。没有发送该草稿的证据；不得算发信成功。 |
| [api-final-before-restore.json](evidence/api-final-before-restore.json) | 同身份事务快照的减敏元数据；UTC2026-10-07 18:24:44.998630记录会话360–374范围85个call_id、attempt合计85。mail_sent=1/授权最多8，独立Gmail读回4次另列。 | 来源transaction-snapshot.sqlite3，hash见下；具体父目录和专用减敏生成脚本身份未在此文件记录。85是恢复前已观察模型HTTP，不是全部外部HTTP、不含OAuth/MCP/GitHub/Drive准备、TTS/STT，也不能代替恢复后最终累计或正式恢复验收。 |

### 本次新增公开文件hash

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| [gmail-group2-trace.json](evidence/gmail-group2-trace.json) | 499353 | 0be5b1231a66d695bac5ed34d191200e75413a0868666b15a265630d1918b4ab |
| [gmail-draft-label-readback.json](evidence/gmail-draft-label-readback.json) | 569 | 23f3abd4fdada5f8e22f9590eb5363af07c9fd59df13b0e670d41ffdd342e781 |
| [api-final-before-restore.json](evidence/api-final-before-restore.json) | 4426 | cf0fa44ce85bfd30b160b190c0672fa2b0561f8b72660411aad81046e0729284 |

### Gmail私有日志前缀与恢复前快照指针

| 来源 | 前缀字节/范围 | 已提供SHA256 |
|---|---:|---|
| {PRIVATE_ROUND02}/phase03/trace-16700.jsonl（按v3阶段记录关联） | 81322 | 0055f07b17dfc3ac0b57a5ef9dcb3ce6348a5a5e3401dfd901da39c9a2f1ec60 |
| {PRIVATE_ROUND02}/phase03/trace-27300.jsonl（按v3阶段记录关联） | 1932008 | 50b98f65b32e314f8791ed5e3c4156a54551cbbb80ac07da83f6128ced25328e |
| transaction-snapshot.sqlite3（公开文件未保存父目录名） | 卷3903461716/file ID2533274790580297；UTC 2026-10-07T18:24:44.998630+00:00 | a53343bbb93e33fcfa9278a0219e08d308adfa3b98fa0ef285a12d5dd9237a7b |
| 本轮合成草稿附件attachment.txt的独立读回 | 60字节 | e3f857710db9f95e301315f504a1b4d7c4a69b1721278331cca204034d7f1d4a |

附件hash只属于该合成附件，不是整个邮件/MIME的hash。日志前缀和公开脱敏文件的hash用途不同，不能互相替代。原始来源、复现脚本和后续恢复证据由主执行保管；本次追加只说明已存在材料，部分审计及其未完成边界不变。后续若增加恢复/最终累计材料应追加新时点，不改写恢复前85次为最终总量。

### 最终恢复补录 02:32

[final-restoration.json](evidence/final-restoration.json)：SHA256 969e52e5b26dd768e83c3bd8c810eff2bc21ebc786d5d7e880b8d9135a912835。最后恢复短句/播放回执、正式配置与两入口hash、健康和同身份事务快照；最终86模型HTTP，替代api-final-before-restore的85作为最终累计，原文件保留。真人听感不代签。
