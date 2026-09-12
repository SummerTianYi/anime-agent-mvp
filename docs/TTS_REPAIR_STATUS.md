# TTS 运行期恢复验收记录（Codex，2026-09-12→13）

## 正式交付（Codex，2026-09-13）

所有者已实际验证并批准实装、推送。正式会话此前已通过原 `start-anime-agent.cmd` 激活，03:43只读复核为 Godot41708、Core42476、CUDA TTS38112及双看护在线，不为提交重复重启健康窗口。下方时间点均为历史实测，不能用旧段落的“未push/未实装”覆盖本节；最终远端状态以 Git 提交为准。本修复跨主仓与 [anime-agent-tts](https://github.com/SummerTianYi/anime-agent-tts)，必须配套更新；声线权重、自检.9阈值、模型资产及正式数据不变。并行zcode的 `0ffaa4e` 语音联动保留，已被其运行时引用但漏入库的 `emotion_presets.gd` 仅补齐原文件，并带原行为守卫，不借机调整表情。

配套语音仓提交为 [1b2b497](https://github.com/SummerTianYi/anime-agent-tts/commit/1b2b49779a7e8795ad93093af8550f7a189a9119)，已核对远端main。主仓精确暂存树 `4e141f39540a445e7ee1679dc2669e1aa551a305`（含zcode最新联动，提交前仅再补本文证据）通过223 Core＋24 sidecar＋14启动＋13 TTS逻辑、文档、Godot导入/输入、4207帧204019表情断言，以及两次独立原CMD启动→合成WAV→实际Godot播放→正常/重复关闭清理。证据为 `C:/Users/26052/AppData/Local/Temp/codex-tts-release-3a1mx10r/final-results.json` 和 `C:/Users/26052/AppData/Local/Temp/codex-farewell-uc9tpr44/e2e-035323/results.json`；本轮不重复声线GPU故障注入。初次复制过长的可再生shader缓存及私有两层.pth未递归找到FastAPI导致的测试环境失败保留；仅纠正副本搭建，未改生产依赖或运行代码。输入检查最终显式指向隔离地址，全部测试数据、音频与窗口独立。

03:54共享环境只读复核发现正式Core已换代为14496/15432，但原Godot、TTS及双看护身份保持且健康；早先“9进程完全不变”审计因此不能复用为本轮结论。本轮未向正式Core发停止指令，不凭该现象归因于某个agent或宣称自己修复了这次换代；最终独立窗口测试以其新保护快照验证通过。正式数据库未进行验收读写/恢复/清理；没有24h观察、子代理或无限故障承诺。

## 追加高强度测试：覆盖场景通过，正式会话保持原样（Codex，2026-09-13 03:31）

所有者自行验证无问题后要求加强对抗测试。本轮只增加测试与验收记录，没有替换运行代码、重启正式窗口、操作正式数据库、开启24h观察、启动子代理或commit/push。遵循隔离回归、错误恢复及Windows桌面测试门禁：独立Core/Godot/TTS、随机端口、独立APPDATA/LOCALAPPDATA/TEMP/数据/SPOOL、Mock Provider、禁用麦克风/工具/MCP，保留启动前9个正式进程代际；进程类测试顺序执行。此轮保留真实原CMD、Windows进程、HTTP、WebSocket和Godot AudioStreamPlayer，**只用合成短WAV替代GPU推理**，不冒称再次完成真实声线冷启动、GPU压力或音质验收；上一轮真实声线证据仍见下文。

| 新增验证 | 结果与证据 |
|---|---|
| 离线回归复跑两轮 | 每轮Core223＋sidecar24＋启动14＋TTS逻辑13＝274，全部通过。新增HTTP用例覆盖16次合成请求（8路并发）、6个不完整请求体、16次连接取消、真实30秒排队超时返回429及过载后再合成；结果分别在`C:/Users/26052/AppData/Local/Temp/codex-tts-offline-lvbzvh8l/results.json`、`C:/Users/26052/AppData/Local/Temp/codex-tts-offline-0qfxipvg/results.json` |
| 两轮复合故障，共9次检查 | 6个原CMD并发、冻结TTS看护同时终止TTS、Core/TTS同时终止、最外层看护被终止后由3个原CMD补回；第二轮再连续终止TTS三次。每种故障后均有新的私人Mock回复→Godot播放开始/结束，健康实例不被重复创建，原测试Godot在运行期故障中保持不变。`C:/Users/26052/AppData/Local/Temp/codex-farewell-bzx48ynz/e2e-030423/results.json`及各场景`compound-faults.json` |
| 旧看护延迟恢复跨越关窗，两轮 | 暂停旧TTS看护，真实WM_CLOSE结束旧Godot后立即用3个原CMD重开，检测到新Godot进程才恢复旧看护。最终两轮交接、完整归属复查、Core→Godot播放以及正常/连续关窗后的清理均通过；旧看护没有误杀新会话。`C:/Users/26052/AppData/Local/Temp/codex-farewell-a0flwjgp/e2e-032536/results.json`及各场景`close-race.json` |
| 静态及报告门禁 | 4个Python文件语法、2个PowerShell驱动解析、8种故障标记组合、文档一致性及两仓diff检查通过。最终静态记录`C:/Users/26052/AppData/Local/Temp/codex-tts-stress-static-taocp693/results.json`；复现入口见[TESTING.md](TESTING.md)末段 |
| 正式进程与清理复核 | 03:31核对启动前9个进程PID/创建时间全部未变，四个测试副本均无遗留进程；正式Godot41708响应正常、Core42476健康、TTS38112为ready，看护27220心跳年龄0.576秒。只读核对记录：`D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/tts-repair-Rq9q4a/stress-final-20260913-033127-637.json` |

两次测试自身失败保留，不追改为PASS：`codex-farewell-0ms_rnlx/e2e-030148`因Python普通环境字典的Windows变量大小写而在注入前中止，改从`os.environ`取得SystemRoot后复跑；`codex-farewell-u5yinj3y/e2e-031914/repeated`在等待新Godot时额外读取Core进程/端口两份非原子快照，误把新worker37528判为未核实，安全拒绝操作。该副本的三份原CMD日志均已Ready37956、Core日志明确Started37528，确认是观察器问题；新增仅观察Godot的`startup-driver.ps1 -Action inspect-avatar`，启动完成后仍执行完整Core/TTS归属核验，未放宽生产安全校验，随后新副本两轮通过。旧复合报告的`faultsChecked:false`只反映原`--voice-faults`开关，真实覆盖在`voiceMetrics.compoundFaults`；报告字段已修正并通过8组合真值表，最新交接报告同时明确`faultModes`。上述失败目录均位于`C:/Users/26052/AppData/Local/Temp/`。

**保证边界**：已验证的TTS进程/看护故障可恢复；进程死亡和真实模型重新预热必然有短暂无声，不能承诺零中断。最外层Core看护自身被终止后，本轮验证的是**重新执行原CMD补回**，不是它自动复活；同时终止所有看护、Windows/显卡驱动故障、资源持续不足和断电不属于已通过的无条件保证。没有为追求字面上的“任何情况”新增系统服务或无限层看护，也没有修改所有者当前已认可的运行版本。

## 正式会话激活基线，禁止操作正式数据（Codex，2026-09-13 02:48）

所有者重新收窄目标：原 `start-anime-agent.cmd` 重开后语音就绪，Godot会话存续期间TTS故障能自行恢复；本轮不做数据库恢复、清理或迁移，不改模型/动作/声线权重/参考音频/自检算法或.9阈值，不开24h观察、不启子代理、不提交或推送。OPS-08原提案和启动链接入归zcode，E期语音能力归原作者；此次生命周期、最小缓存修复及下列验证归Codex。00:50的数据部分恢复仍是历史事件，见本机保留的 `docs/DATA_RECOVERY_STATUS.md`（未入库），不能据此覆盖后来新增的数据。

在此前候选基础上补齐两处闭环：Core会话看护独立检查TTS看护（不以Core故障为前提），用45秒心跳识别看护退出/卡死，只替换精确身份的看护进程、不连带重启健康Core/TTS；原CMD等待真实模型预热结束才报告 `Voice ready`，最长180秒、关Godot即取消等待。心跳回执改为原子替换，Windows PowerShell 5.1的空备份参数经过实际双次写入验证。仍不把端口监听、HTTP响应、模型可用、音频播放混为一项。

| 本轮检查 | 结果与证据 |
|---|---|
| 隔离离线回归 | Core223、sidecar20、原启动14、TTS生命周期13全部通过；`C:/Users/26052/AppData/Local/Temp/codex-tts-offline-use6_4uh/results.json`。禁用真实Provider/MCP/唤醒、独立数据和SPOOL目录；新增就绪/取消/心跳用例记录过RED→GREEN |
| 原CMD + 合成测试WAV两轮 | 正常/重复关窗、看护被终止/挂起、sidecar被终止、实际Core/Godot播放与清理通过；恢复26.437/23.157秒。证据：`C:/Users/26052/AppData/Local/Temp/codex-farewell-79vh4834/e2e-020518/results.json`；不是声线冷启动速度 |
| 原CMD + 完整真实声线两轮 | 复制权重/配置/脚本到独立工作区、独立3.10 venv、独立Core/Godot/端口；CUDA推理、首合成自检、看护故障和sidecar故障恢复、中文回复合成/播放、正常及重复关闭均通过。实际sidecar冷恢复60.187/58.765秒，首次预热约64秒；`C:/Users/26052/AppData/Local/Temp/codex-farewell-myoseivc/e2e-021138/results.json` |
| 实际音频输出 | 上述 `idle/tts-playback.jsonl`、`repeated/tts-playback.jsonl` 都有 started → audio-mix → finished；WASAPI、未静音，峰值0.616076/0.466209，采样88576/86016。只采集独立Godot输出总线，不录麦克风；证明引擎有音频输出，不等于用户耳边听感或声卡故障恢复验收 |
| 最终Windows边界矩阵 | 最终源码14/14通过并完成独立进程清理；`C:/Users/26052/AppData/Local/Temp/codex-tts-e2e-xzlhfzzp/results.json`。单次终止7.406秒恢复（合成测试WAV），持续卡顿在真实120秒退避预算内116.109秒恢复；覆盖旧协议/重复实例/排他绑定、并发请求、单次与连续错误、HTTP/合成卡死、缓存恢复、快速换窗、恢复中关窗和外部占用解除 |
| 静态、桌面与输入 | 最终10文件编译、独立Godot输入门禁与原子心跳实测重跑通过；`C:/Users/26052/AppData/Local/Temp/codex-tts-static-_v32ewuh/result.json`。桌面TypeScript/Vite构建、文档一致性和两仓diff检查通过，构建产物仅在本地独立工作区 |

失败记录不抹除：合成WAV集成首轮 `codex-farewell-us6wtgrr/e2e-020145` 及边界首轮 `codex-tts-e2e-d1jkj1aq` 在新worker绑定端口恰好晚于CIM快照时，测试观察器中止；生产看护安全推迟并正确拉起新worker（后者日志确认33552），没有把外部PID当成可杀对象。两处测试观察器仅对该错误最多重查3次，持续外部占用仍拒绝；原子心跳的首轮WindowsPS空参数异常也保留，改用 `NullString.Value` 后实际两次写入通过。

**正式激活（02:48已验证）**：所有者回复“go on”允许正常关窗/原命令重开。先核验原Godot28676创建时间及实际工作目录属于本项目，再正常CloseMainWindow，未强杀；临时核验脚本首次因WindowsPS传递Python引号失败而安全拒绝关窗，修正后才执行。原命令启动新Godot41708，健康Core1072/42476按入口规则保留，接入Core看护27772、TTS看护27220及TTS38112（父24168）。启动器报告 `Voice ready`；Core详情 `tts.available=true`，sidecar `service=tianyi-tts, protocol=1, phase=ready, device=cuda`，首推理/自检完成、.9配置保持，新生成两份有效32000Hz/0.9秒预热WAV。随后再次执行相同原CMD，Godot/Core/TTS/两个看护的PID与创建时间均不变、窗口响应且心跳推进，通过幂等复核。没有对正式会话发送测试聊天、建立/删除测试会话或查改数据库；真实中文回复→Godot音频输出仍以此前两轮隔离证据为准，不冒称本轮做了正式Provider聊天测试。

本地证据：`../tts-repair-Rq9q4a/activation-20260913-024538-975.log`、`live-voice-20260913-024706.json`、`repeat-start-20260913-024831-505.json`（后两者同目录）。正式进程保留运行，不再注入故障。激活前8770已缺席、旧TTS26604/18788此前在共享环境中消失，原因不明；本轮没有结束它们。共享HEAD仍为zcode的`d61c5ac`，不是TTS提交，未commit/push。正常应用启动可能自行保存其运行状态，但本次验收不执行正式数据库检查、恢复、清理、替换或测试消息操作。

**承诺边界**：本轮已验证的是故障后自动恢复，而不是物理意义“任何情况下零中断”。真实声线重新加载约一分钟；合成持续卡住要达到120秒阈值，连续故障随后进入120秒退避。恢复期间文字可用，但不补播失败的旧句子；显卡/驱动失效、模型缺失、磁盘不可写、外部端口长期占用、整个进程树被结束或音频设备故障不能靠无限重试保证发声。24h长稳和声卡拔插未做，亦不是所有者当前要求的交付门禁。两仓库代码均尚未推送，当前正常会话的激活与重复启动已通过上述实际核验。

以下为此前候选及数据暂停阶段的历史记录；其“当前/下一步/未验证GPU/必须24h”等旧表述不覆盖本节。

## 根因与实现

| 层级 | 已确认问题 | 本轮处理 |
|---|---|---|
| 会话看护 | 当前8770健康但没有TTS watcher；旧watcher只有退出清理，没有运行期复活 | 独立会话看护处理进程消失、HTTP卡住、连续合成错误和持续合成卡顿 |
| 启动/退出竞争 | 旧TTS块在配置/启动锁前执行，并按脚本名广泛结束watcher；旧清理仅查端口PID | Avatar就绪后启动看护；TTS互斥、Core启动互斥、Avatar PID+创建时间，以及TTS脚本/venv/端口/父进程归属校验 |
| 假健康 | 加载模型后立即ok，首推理与Whisper未预热；合成卡住仍ok | 先排他绑定端口再载入模型；真实首合成+自检结束才ready；合成持续超120秒标stalled，连续3次模型失败标failed |
| 恢复后仍哑 | Core把负面健康结果缓存60秒，已通过新增测试复现 | 负面缓存最多2秒；非法响应使缓存失效，增加不含用户正文的诊断日志；不重写分片/打断状态机 |
| 合成队列/重复启动 | 旧锁无限等待；旧服务绑定端口前就加载模型 | 合成锁最多等待30秒，超时429；正常短合成仍串行衔接；断开客户端不计模型失败；重复启动在加载模型前失败 |
| 历史证据不足 | 旧日志有重复LISTENING/ConnectionAbortedError，但没有完整退出原因链 | 新日志记录时间、原因、PID、次数、退出码和每次启动的独立日志；不把所有历史断声归于同一次崩溃 |

唯一日常入口不变：根 `start-anime-agent.cmd` → `scripts/start-mvp.ps1` → Core/Avatar就绪 → 释放Core启动锁 → 启动TTS看护。看护关闭时在同一个Core启动锁下检查是否已有新Avatar，再清理或交接；不能持有Core启动锁等待TTS看护回执，以免反向锁等待。旧健康sidecar缺少新协议时，只在下次正式新会话经过归属核验及双确认后重启升级，否则残留旧进程会永远不加载新代码。

| 文件 | 用途 |
|---|---|
| `scripts/tts-lifecycle.ps1` | Codex新增：配置、归属、健康、退避、看护回执 |
| `scripts/watch-tts-session.ps1` | 从单向清理改为双向恢复/退出；绑定Avatar代际，不拥有Core或无关Python |
| `scripts/start-mvp.ps1` | 正式链路接入时机与锁顺序；保留zcode接入TTS的需求，不保留广泛结束watcher的实现 |
| `scripts/start-tianyi.ps1` | 保留原文件作为正式启动器的兼容转发，不删除入口，也不保留第二套生命周期 |
| `services/agent-core/agent_core/speech.py` | 先跑25项语音基线，再最小修复缓存/异常响应；原E期能力仍归原作者 |
| `../tianyi-tts/scripts/tts_server.py`、`service_health.py` | **另一个Git仓库**：HTTP、预热、阶段/卡顿健康；仅推主仓不足以交付修复 |
| `../tianyi-tts/scripts/tts_autostart.bat` | 手动兼容入口改为相对自身定位；netstat只防方便性重复调用，不代表模型健康；正式看护不通过它判活 |
| `scripts/test-tts-lifecycle.ps1` / `scripts/tests/test_tts_recovery_e2e.py` | 无模型逻辑测试 / 独立端口与真实Windows进程、HTTP故障注入；明确使用合成测试WAV，不冒称声线测试 |
| `scripts/tests/test_farewell_exit.py --tts-fixture-sidecar ...` | 原CMD、独立真实Core/Godot及测试sidecar；模型和动作只复制到临时副本，不操作用户窗口 |

配置：`ANIME_AGENT_TTS=0`、工作区缺失或`-SkipAvatar`不启动本地TTS；远程/自定义路径URL不接管。默认工作区是主仓相邻`tianyi-tts`，默认URL为`http://127.0.0.1:8770`；测试用`TTS_WORKSPACE`与`TTS_SERVICE_URL`指定独立副本。相同sidecar仅应由一个项目会话拥有；跨项目共享不要依赖此单会话所有权模式。

日志：`%LOCALAPPDATA%/AnimeAgent/logs/tts-watch.log`为JSONL；每次启动有独立`tts-时间-PID.stdout.log`与`.stderr.log`。进程缺失会启动，HTTP/明确失败需双确认；未就绪冷启动宽限180秒，曾就绪实例不再获得冷启动宽限。连续重启间隔2/4/8/16秒，随后120秒；连续健康60秒重置预算。外部或无法核验的端口占用只记录并等待，绝不结束该进程。恢复期间保持文字，不延迟补播已失败的旧句子。

## 验收记录

| 检查 | 结果与证据 |
|---|---|
| 修改前基线 | Core语音25、sidecar自检11通过；新增缓存回归先RED后GREEN |
| 全量离线测试 | Core223、sidecar20、PowerShell生命周期10通过；关闭TTS/wake/MCP、Mock、独立数据库 |
| 第一轮Windows故障 | 7项通过，定向终止后10.266秒恢复；`C:/Users/26052/AppData/Local/Temp/codex-tts-e2e-_pdv2fll/results.json` |
| 第二轮对抗 | 11项通过，定向终止后11.250秒恢复，包含慢并发、单次错误不重启、连续错误、HTTP/合成卡顿、快速换窗、恢复中关窗；`C:/Users/26052/AppData/Local/Temp/codex-tts-e2e-lq_h6l4f/results.json` |
| 加强轮失败保留 | `codex-tts-e2e-p8841gha`：排他绑定中文错误触发测试读取器解码异常；端口冲突解除后仍残留上一用例的crash开关造成超时。两项均为测试问题，已修正，未冒充该轮全绿；终轮另记 |
| 原CMD入口 | 正常关闭、连续关闭、告别停滞3轮通过，Core可用/合成计数增长/TTS与Core跟随退出；`C:/Users/26052/AppData/Local/Temp/codex-farewell-py7xda0z/e2e-235836/results.json` |
| 真实声线CPU试验 | 冷启动含自检预热95.610秒、随后合成34.359秒、有效WAV2.180秒；`../tts-repair-Rq9q4a/real-cpu/result.json`。完整复制涉及的代码/配置/权重，无可写硬链接；CPU两线程、离线缓存，不启第二个GPU声线实例，不播放声音 |
| 资产/构建/输入 | 官方GLB SHA `DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A`不变；桌面TS/Vite构建、独立副本Godot输入门禁通过 |

## 激活、未验收与回退

终轮补记：`C:/Users/26052/AppData/Local/Temp/codex-tts-e2e-e42x9tv9/results.json` **14/14通过**，定向终止后7.203秒恢复；第六次连续故障进入生产120秒退避，119.031秒后恢复。前一轮`codex-tts-e2e-vd9s__wh`误用45秒期限检查这个退避阶段而失败，已按真实退避预算将该项期限设为150秒，普通故障仍保留45秒门禁，未缩短生产退避以讨好测试。`codex-farewell-6yekdzm2/e2e-001618/results.json`通过原CMD启动→真实Core中文回复→测试WAV→独立Godot静音AudioStreamPlayer开始/完成→正常告别→Core/TTS清理；播放信号在同目录`idle/tts-playback.jsonl`，不是实际扬声器听感验收。10项TTS逻辑、14项原启动逻辑、20项sidecar（修正下方隔离问题后重跑）、223项Core、11文件编译、前端构建、资产/输入/文档守卫通过。编译初次缓存前缀过长触发WinError206，改用短文件名输出后通过，没有改变系统长路径设置。

共享环境复核：23:31首次盘点中的Avatar/Core/旧Core watcher到收尾已不再是相同进程；首轮E2E的保护快照便已显示新的Avatar37716/39916，后续又出现新的Core与Godot。因此本轮不声称整个共享环境从始至终无人修改，也不将这些换代归为本次修复成果；本代理的故障/关窗目标始终是带隔离目录和身份校验的测试实例，每轮开始所保护的进程在该轮结束时存活。原TTS26604/18788身份始终保持。全任务初始身份复核因此没有通过，证据在`../tts-repair-Rq9q4a/protected-final.json`；未擅自重启或恢复其他agent正在使用的实例。工作期间另有zcode提交8692269（UI），不包含本轮TTS修改。

隔离事故记录：第三次审查发现新增HTTP单测虽替换模型计算，却遗漏替换模块`SPOOL`，此前20项sidecar测试中的成功请求曾调用默认正式`out/spool`的过期清理。可能删除超过15分钟的`utt_*.wav`临时文件；没有清理前清单，无法确定数量或保证恢复，不能声称本轮对正式文件零写入。已暂停该组测试，将`SPOOL`改为每例独立临时目录并加入路径断言，随后重跑；未触及权重、语料、模型、配置或聊天数据库，原运行进程保持。后续模拟合成必须同时隔离计算与输出/清理目录。

当前用户进程仍运行启动时加载的旧代码，本轮没有替用户重启。下一次正常关闭后使用原CMD命令重开才加载修改；旧sidecar升级后需重新预热。**未完成真实GPU故障恢复、真实扬声器听感/设备中断及24h长稳**，不得称最终验收全过。约10–11秒恢复来自合成计算被替代的测试，不能当作全声线冷恢复时间；CPU实测95.610秒预热也说明“任何环境≤40秒有声”不能无条件承诺。磁盘/权限/驱动/模型损坏或外部端口占用时安全退避保留文字，不靠误杀或无限重试保证成功。原自检算法重试后择优返回，保持.9配置不意味着每条语音均达到.9；该策略没有被本轮重写。

下一步：所有者允许结束当前窗口后，用同命令重开，核验sidecar含`service=tianyi-tts, protocol=1, phase=ready`和Core `tts.available=true`；在获准且不影响使用的条件下补GPU恢复/实际播放与24h长稳。两仓库仅在最终授权后分别提交推送。回退材料在本地`../tts-repair-Rq9q4a/before/main/`与`before/sidecar/`；仅在相关进程退出后逐一比对恢复本次文件，不`reset --hard`、不覆盖并行agent的README/UI/表情变更，不动数据库、声线或模型版本目录。


## 历史事故与本地记录边界

上述SPOOL隔离事故保留供回归审查，不隐瞒已发生的副作用。数据损坏诊断与恢复是另一个历史任务，本次不检查或改写正式数据库，也不将其记录及数据打包上传；原始完整过程文件已原样备份到本机 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/tts-repair-Rq9q4a/TTS_REPAIR_STATUS.pre-release.md`，独立恢复记录保留在主仓本地 `docs/DATA_RECOVERY_STATUS.md`。复现测试及失败证据位于上表本地路径，不包含用户消息正文、声音素材或数据库。
