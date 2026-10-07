# 第二轮独立分支检查映射

日期：2026-10-08。审查者：Codex `round02_probe_review`。范围是实际部署目录的 Python Core、启动脚本、Godot 与公开配置样例，以及本轮已有覆盖材料。**本次只读源码和已有材料，只新增本文；未运行测试或探针，未启动 Core/MCP/模型/Godot，未请求网络、访问桌面或读取私有数据库。**

本表是可执行检查的准备映射，不是通过清单。原 256 项继续保留；下文的 BM 编号是分支定位键，不能直接加到原通过率分母。原总项、实现分支、独立用户入口三者分别登记；一个分支命中不代表所属总项完成。没有要求参数笛卡尔积，优先覆盖改变副作用、状态、身份、结果结构和错误传播的参数。

## 依据、源码身份与证据复用

优先复用 [COVERAGE_REVIEW](COVERAGE_REVIEW.md) 的原 256 项逐行复核、S/O/G/E 断言索引和新增入口建议，再定向核对生产源码。本轮原有增量以 [COVERAGE](COVERAGE.md)、[local-branches-01](evidence/local-branches-01.json)、[edge-counterfactuals-01](evidence/edge-counterfactuals-01.json) 为入口。本实例审查过这两个探针脚本，但未代替主执行者运行或签署其结果。有效 UTF-8 分页、25 条消息取后 20 条等已有对应证据，不重新称为从未验证。

本文所有代码相对路径指**生产目录**，不是审计工作树同名文件。读取时生产 Git HEAD 为 `d3ed6d68f2509ad51bea15cf8224c5f3a165d957`；HEAD 不足以代表含本地 overlay 的文件，以下实际字节哈希才是本次行号依据。它们也不是运行中进程的内存源码证明。

| 生产文件 | SHA256 |
|---|---|
| `services/agent-core/agent_core/main.py` | `e64a26e426b1cf3c00447f2dc39fc775241114498e1c257ebdd86e3e66d3d3f5` |
| `services/agent-core/agent_core/tools.py` | `9f751b0c507dacad78b8ca6cfc4dd1bb0d83ab1f4137984f32cb07dfb9de54d7` |
| `services/agent-core/agent_core/harness.py` | `f4b0a888d14bc2b20b994971be601cc72255c6a8976a0e271e2881770a170e25` |
| `services/agent-core/agent_core/storage.py` | `91450c232cacdd05d7fb7835e5ee58812da024d0d446b4580905ff59b64fc06b` |
| `services/agent-core/agent_core/result_pages.py` | `2987d5844c5a7e9f4156648c747f3b7c24d0cd1a8f1f48e554e8b7804cf9a1e4` |
| `services/agent-core/agent_core/provider_http.py` | `ba8d0abe47604d4badb4346891121c95479f5da0e65373f838986c7e55faf739` |
| `apps/avatar-runtime/runtime.gd` | `0ad46f150734814e1de2e7deb12799dfd9637cbdff041a80ce5f6ae715519295` |
| `apps/avatar-runtime/emotion_presets.gd` | `a1f9bbea999580c857c45769acfa586dca46b294f5d5975a90f3e597bbc44c33` |
| `apps/avatar-runtime/motion_registry.json` | `6e6662d46dfd9d39fb426f07a8be9fd5d9e32eef805d2b95bcfbc57004aa2e02` |
| `scripts/startup-common.ps1` | `338cf1d74b06ac3f94d48c3e66cca64a5efcdf4a73eeea367f8f327749e3eb36` |
| `scripts/core_watchdog.ps1` | `e2cf1bfb4d772b63f784d17227e3096f5776d4ece13d81ddc6755c81666ee89f` |
| `scripts/start-mvp.ps1` | `f855004c4a1274df5b213999a81ba16293d9619fe6b48f4e5b4e9b165ee15de2` |

## 最小隔离方法

下表引用的隔离方法是后续执行合同，本次未执行。主执行者应先检查拟运行脚本的副作用，再选择对应方法，不能直接导入生产 `agent_core.main` 或启动原 `.cmd`。

| 方法 | 具体准备、边界和可记录结果 |
|---|---|
| I-PY | `python -B` 或导入前 `sys.dont_write_bytecode=True`；只导入已确认无启动副作用的模块，核对 `__file__` 与生产目标。针对 main 仅 AST 抽取指定函数/方法及必要常量；不执行模块顶层、装饰器或全局 `MemoryStore`/录音器初始化。缺依赖是探针失败，不能算业务正确拒绝。 |
| I-FS | 一个新 TemporaryDirectory，内部 `allowed` 与 `sibling` 都是合成夹具；读取根、写入根、显式数据库目录均限定这里。异常后先记录残留和原文件哈希，再关闭连接并清理；区分业务自行清理与探针清理。只导出占位路径、合成字节/摘要，不复制真实数据。 |
| I-IO | 所有进程、网络、屏幕、剪贴板、时钟和播放器边界用替身。命令截获 `subprocess.run`；网络只构造 Request，fake send 返回合成 bytes。为拟执行节点同时检查其他潜在出口，未审查的出口应直接失败。记录替身调用次数、参数及异常来源，不能只数“调用发生”。 |
| I-PS | 复用 `scripts/test-startup.ps1` 已有函数替身思路，先在临时副本设置合成 `.env`、LOCALAPPDATA、唯一 runtimeKey；或由 PowerShell AST 只取指定函数。CIM、TCP、HTTP、Start/Stop、taskkill、sleep、日志、时钟均截获，不执行完整启动/守护脚本。真实命名互斥量也不得与生产共享。 |
| I-GD | 先做静态/纯 RefCounted 计算检查；需要 Godot 时仅在后续单独安排的临时项目中用合成骨骼/动画和替身 bridge/player，禁止 `_ready` 自动连接生产 WS、写生产 `user://` 或截图到生产 `res://`。现有 headless 守卫须先核对这些边界。本次不运行 Godot；形态、动作质量和真实交互仍须唯一现场操作者验收。 |

每项结果至少保留：BM/原 ID、来源哈希、合成输入、期望合同、实际输出/异常、断言、替身调用数、清理状态与证据层。已知错误可以“被复现”，不能因此记为产品 PASS；缺入口可以静态确认为未实现，但不能被 0 次调用包装成成功功能。

## 原 10 项未启用或未实现：分别闭合状态依据

| 原 ID | 当前入口与静态依据 | 最小下一步及有效判据 | 安全边界与允许结论 |
|---|---|---|---|
| EF04 内部推理控制 | `main.py:1379–1393` 的任务预算是 3/6/9 轮、6/12/18 次；`MODEL_REASONING_CONTROLS` 两项均为空。 | AST 取常量；捕获同一合成任务三档构造出的请求 body，分别比较预算、工具集合和有无 reasoning/thinking 参数。 | I-PY/I-IO；允许确认“未接内部推理参数”；不得用三档 UI 或提示词变化当内部推理生效。真实网关支持需另一项协议证据。 |
| TA09 Drive 资源正文桥接 | `mcp_host.py:205–215` 只登记 tool entries；既有复核定位 `tools/gdrive/index.mjs:39` 的 resources/read，与 search:127 起返回名字/MIME 分开。 | 静态检查 Core 入口/调度是否存在 resources/read；用合成 resource link 与嵌入 resource text 分别过实际结果归一化，记录前者是否能再读取。 | I-PY/I-IO；不启动 MCP/OAuth；服务端独立资源读取成功不能补成天依桥接已实现。 |
| VO05 后台唤醒 | `main.py:735` 默认 manual；`:1810–1838` manual 时停止旧 listener 并返回，另有 WAKE_WORD 禁用/构造失败分支。 | AST 抽 startup，fake memory/listener：manual+已有/无 listener；非manual+开关off；非manual+构造 VoiceError。断言 start 次数、stop 次数与 wake.disabled 原因。 | I-PY/I-IO；不触麦克风、不启后台监听。非manual开启分支只测替身；保留“有实现、当前明确禁用”。 |
| NI01 通用衣发无穿模 | `runtime.gd:1322–1432` 是有限肢体可读性/发束修正；motion registry 是五条冻结动作，不能证明通用接触解算。 | 逐个登记有限动作、骨骼覆盖和姿态/碰撞指标；把任意服装、任意动作、任意身体比例列为未实现的独立合同。 | 静态 + 后续 I-GD；不造“通用通过”阈值，不修改官模或物理实现。已有某动作门禁仅回填该动作。 |
| NI02 Windows 登录自启 | `docs/HANDOFF.md:125` 明确暂缓；`start-mvp.ps1` 是手动会话入口，非登录触发注册。 | 定向核对仓内有没有正式注册脚本、卸载/恢复合同和启动项入口；保留当前会话守护 LC01/02 独立状态。 | 仅静态；不读写注册表、任务计划或 Startup 目录。无实现无需人为登录试验；不能以已启动进程代验。 |
| NI03 记忆审阅/遗忘 UI | `storage.py:306` set_fact_status、`:333` pending_facts 是内部方法；本次定向搜索无正式 UI/WS 调用入口。 | 将“列pending→按fact_id批准/拒绝→核对召回”和“遗忘的scope/删除范围”分别列合同；在 I-FS 合成库核对现有内部方法，入口仍标缺失。 | 不用 delete_session 冒充忘记事实；不读取私人事实。功能实现和遗忘策略不属本次修复授权。 |
| NI04 任意桌面键鼠代理 | `docs/HANDOFF.md:125` 缓行；Core 本地工具注册和 Godot 自身输入处理不提供任意桌面控制入口。 | 静态分别列 browser 工具、Godot 本地快捷键和桌面操作边界；查注册表/schema 不出现既有功能冒名。 | 仅静态，不发送系统输入或开考试权限。浏览器 click 成功不能更改此项状态。 |
| NI05 Spark Adapter | HANDOFF:125/138 仍未实现；`build_provider:706–728` 只有 glm/deepseek/stepfun/Mock；CSS 的 avatar-spark 不是适配器。 | AST 枚举 provider factory 分支和可注册类，保存缺少 Spark 分支的范围化证据。 | I-PY 静态；不找/申请 Spark Key，不把 Mock fallback 当 Spark 功能。 |
| NI06 Tauri 设置壳正式链 | `apps/desktop/src-tauri/src/main.rs:3–6` 存在 Tauri 程序；`start-mvp.ps1:50–52` 正式入口启动 Godot。 | 静态追踪原 cmd→start-mvp→run-avatar-runtime，核对客户端 role 与设置持久化入口；将目录存在、可构建、正式启用分列。 | 不启动 Tauri、不替换当前窗口；结论限“正式启动链未调用该壳”。 |
| NI07 任意硬件/离线跨机交付 | `scripts/delivery/{Start-Tianyi.ps1,Verify-Bundle.py,README.md}` 是交付入口；`docs/DELIVERY_STATUS.md` 保留跨机限制。 | 先只读核对清单：Python/模型/资源/声线/配置占位/运行依赖及校验；明确哪些资源须本地提供。下一阶段才在另机或隔离 VM 验收缺缓存、无网络、无GPU/音频等条件。 | 本轮静态不等于可移植或离线可用；不复制受限模型、不安装全局依赖、不更改本机设备。 |

**原 256 之外应单独补登记：`NI-open_app`。** HANDOFF:125 明确 open_app 是未做的 B 期蓝图项；本次定向检索 Core 注册入口没有该能力。下一步是记录缺入口及预期应用定位/授权合同，不能把 `run_command` 或 browser navigate 重新命名为已实现 open_app。这是既有复核已指出的漏项，本表承接而非重复声明为新发现。

## 启动与守护：总项下的独立分支

| 分支键 / 原 ID | 实际入口 | 最小输入与判据 | 复用证据、下一步与隔离 |
|---|---|---|---|
| BM-ST01 / LC01 | `startup-common.ps1:5–35` 配置及 runtimeKey | 继承环境存在/不存在/空串；端口 1/65535 合法，0/65536/非数非法；不同 root/port 不共享锁 key；合成 .env 同名重复值取最后。 | 已有 test-startup:187 验继承端口；补端点/空值与独立 root。I-PS，不读生产 .env。 |
| BM-ST02 / LC01 | `Get-AgentCoreHealth:77–85` | live 正常只一次；仅404退回 health；timeout/500不退回；服务名错/PID错不接受，PID省略的兼容行为单列。 | test-startup:82/87/93 已有主要断言；补服务名/省略PID，避免重复正常组。I-PS fake HTTP，不发loopback。 |
| BM-ST03 / LC01、LC02 | `Get-AgentCoreState:105`、`Stop-ProjectCoreProcesses:126` | venv父+worker、异项目、快照之间bind/消失、PID复用、CIM权限失败；拒绝时启动/终止次数均0。 | test-startup:71/100/113/121/127/153/172 已覆盖若干分支；复用而非计新增功能。后续只补当前哈希缺失的断言。I-PS。 |
| BM-ST04 / LC01 | `Ensure-AgentCore:166–204` | 冷启动/已有健康/尚在预热/达到age与misses双阈值/新进程立即退出/消失/总deadline/ContinueWhile转false；启动次数和目标身份逐项比对。 | test-startup:107/138/145/179/194 已有具体路径；把 StartupSeconds 与 ConfirmFailures 分开而非仅“启动成功”。I-PS假时钟，不真实等待或杀进程。 |
| BM-ST05 / LC01 | `Enter-AgentLock:39`、`start-mvp:43–106` | mutex获得/超时/abandoned；SkipAvatar不启动头像与会话watcher；窗口两次ready才通过；ACK缺失/坏JSON/旧createdTicks/旧avatarTicks不通过。 | 锁、SkipAvatar、窗口采样和ACK不由 health 成功覆盖。先补函数级替身矩阵；不运行 `test_startup_e2e.py`，它明确操作真实测试进程/窗口。I-PS。 |
| BM-ST06 / LC02 | `core_watchdog.ps1:19–76` | 同代watcher重复、avatar代际变化、1次失败/第2次失败、恢复时avatar退出/新avatar重开、启动锁占用；旧watcher不能清理新实例。 | test-startup:160/194 可复用退出原语，但不等于整个watchdog循环验证。抽取一次循环或以计数器终止替身循环，核对ACK清理和Dispose。I-PS。 |
| BM-ST07 / TT05、LC02 | `tts-lifecycle.ps1:73–119`；`start-mvp:107–118` | legacy protocol/failed/stalled/warming/ready × WasReady × misses；heartbeat -5/45秒边界与越界；Attempts 4/5退避；等待TTS时启动锁已释放。 | 决策函数和锁顺序单列；本轮503现场不能证明每个状态分支。I-PS fake health/clock，禁止实际 Start-OwnedTts、GPU或看护。 |

`scripts/test-startup.ps1` 当前源码列出 18 个 Test-Case，本次只读检查其名字和相关断言，不新增一轮“18通过”。它的前段会初始化运行环境；未来复用时仍须合成环境或限定函数抽取，不能因为注释“NO real processes”就忽略配置/日志边界。

## 上下文、缓存与会话

| 分支键 / 原 ID | 实际入口 | 最小输入与判据 | 复用证据、下一步与隔离 |
|---|---|---|---|
| BM-CX01 / ME06 | `storage.py:188–201`；`main.py:1461/1504`；`harness.py:162–193` | 19/20/21条、显式会话/省略会话/空库；先落当前user，再取后20条；组装后system+20条，当前问句恰1次；assistant JSON还原后内容/角色同序。 | R2 local已有25取20，edge已有harness组合；只补边界与默认会话分支。I-FS显式临时库；20是消息行数，不是20轮或全部prompt内容。 |
| BM-CX02 / TA06、TA13 | `main.py:1464–1508` | 有pending批准/否定/改参/普通澄清；无pending继续/无pending确认/新任务；比较task ID、票据、预算、calls/rounds、缓存ref与历史是否各自保留。 | E-CONTINUE及本轮 longfile-confirm 已证部分；尤其无pending确认重置不应被“继续保持”吞掉。I-PY抽方法、fake provider/hub/ledger；不import main。 |
| BM-CX03 / L-read_tool_result | `result_pages.py:18–41` | JSON序列化长度2000/2001；单结果4Mi字符/超限；累计缓存触发最旧淘汰；另实例/已淘汰ref；offset -1/True/字符串/EOF/EOF+1。比对精确内容、next_offset、size与淘汰集合。 | O-PAGES与R2正常分页复用；新增独立登记缓存上限和淘汰，区分字符与UTF-8字节。I-PY纯内存；输入仅合成。 |
| BM-CX04 / ME01–05、NI03 | `storage.py:306–340`；`main.py:1526–1535`；`memory_retrieval.py` | pending/confirmed/superseded × global/session；敏感pending与显式confirmed分别比较；召回异常时chat能继续但有错误事件；删除会话不能默认为删除global事实。 | E-MEMORY已有多条断言；继续沿既有更正反例，不读真实事实。I-FS，仅合成事实/合成敏感标记；取舍不由测试私自改变。 |
| BM-CX05 / EF01–03、TA06 | `main.py:1397–1405/1508–1522/1546–1572` | effort合法三档/大小写/未知/空；新任务设预算，继续不充值；local tools为空而MCP非空、全部schema空两种装配；检查recall_memory/read_tool_result是否可见。 | E-EFFORT只验阶梯和label，不能证明schema相等。I-PY fake tool_entries及provider；记录三档精确工具名集合和调用分支，无MCP启动。 |
| BM-CX06 / PE03、TA11 | `harness.py:195–278` | 合法reply、null/数字/对象/空、单个左括号、有效JSON+杂尾、错误emotion/gesture、NaN intensity；区分解析保留、类型强转、有限fallback。 | edge已覆盖null/数字/空和坏括号，不重复；补对象/有限强度等有不同分支的输入。I-PY；“未抛异常”不是交付成功。 |
| BM-CX07 / WS-chat.message、WS-session.* | `main.py:2026–2125`；`runtime.gd:733–777` | 空/4000/4001长度、非法会话、session切换时迟到history/chat.response、pending按conversationId隔离；请求JSON是null/list时错误来源单列。 | 既有复核已指出输入形状/异步窗口；fake websocket逐条喂合成消息，最后主动断开，不开服务。Godot消费另用I-GD；存储事件不能冒充已广播事件。 |

## 本地工具与参数

| 分支键 / 原 ID | 实际入口 | 最小输入与判据 | 复用证据、下一步与隔离 |
|---|---|---|---|
| BM-LO01 / L-read_file、L-list_dir、L-write_file | `tools.py:36–90/211–235` | 根配置缺省/空/明确根/只读`*`；绝对/相对/引号/环境变量；词法路径在root但resolve后在sibling、反向别名；分别记录读根与写根允许性。 | 原allow-list负例不能覆盖词法/物理路径OR组合。先用Path/resolve替身证明判断；需要实文件时两侧都在I-FS总临时目录，绝不越到真实目录。这是待验证边界，不宣称已发生泄漏。 |
| BM-LO02 / L-read_file | `tools.py:94–124` | 有效UTF-8页尾、开头坏字节且页尾合法多字节、任意中间offset、EOF、文件消失/读取OSError；拼接与全文件replacement解码比较。 | local与edge已覆盖核心增量；当前有效分页应保留已验证。新增故障只mock open/stat，不重读现场文件。I-FS/I-IO。 |
| BM-LO03 / L-list_dir | `tools.py:127–149` | 199/200/201项、大小写乱序名字、目录优先；iterdir失败和单entry.stat失败分开；核对全名序列、截断与size=None。 | local仅检查首项dir和总数，不证明所有名称顺序。夹具以乱序创建，断言精确200项名称。I-FS，或合成Path entries。 |
| BM-LO04 / L-write_file | `tools.py:238–275` | overwrite/append；空/已有尾换行/内容首换行；多字节内容按bytes上限；append后总大小超过上限独立记录。 | local已覆盖四个append组合/坏mode/坏类型/oversize；追加总大小与单次content限额需区分合同，不能自设产品阈值。I-FS并readback bytes/hash。 |
| BM-LO05 / L-write_file | 同上`:261–274` | 临时写失败、replace失败、replace成功但readback失败、读回hash不一致；原文件/新文件状态与unknown分开；残留文件先记录。 | local已有replace残留；补两条readback unknown，不能把ok=False推导为文件未变化。I-FS/I-IO；仅合成文件。 |
| BM-LO06 / L-run_command | `tools.py:392–445` | disabled/empty/不在白名单/metachar/引号不配对；同basename的无空格/带空格Windows路径；nonzero/缺exe/内部timeout/输出4000与4001字符。 | local/edge已有多条；复用并绑定实际Windows路径语义、argv、shell=False、timeout=30。所有subprocess.run均mock，不能因是版本命令就实际执行。 |
| BM-LO07 / 全部L工具调度 | `tools.py:execute_tool`、默认15秒与run_command内部30秒 | 未知工具、arguments非dict、缺required、函数TypeError/OSError；外层超时但worker尚未结束。核对unknown与迟到结果不交付，不能断言进程已终止。 | 原内部TimeoutExpired mock不覆盖外层线程期限。I-PY假函数/事件屏障，不创建真实进程；worker最终释放，避免测试自身悬挂。 |
| BM-LO08 / L-active_window、L-screenshot、L-clipboard_read | `tools.py:152–203` | active_window：合成loader→user32→固定title，零handle/空title/OS错误；screenshot：缺mss/无monitor/成功bytes/编码失败；clipboard：缺依赖/空/16000边界。 | O-DEGRADED只验失败。优先验证下面的active_window静态疑点；I-IO替换ctypes/mss/pyperclip，不查询实际屏幕或剪贴板。接口目前只有title，不应要求返回进程。 |
| BM-LO09 / L-look_at_screen、AD06 | `tools.py:280–382` | protocol=openai/anthropic；模型缺失、截图失败、文件读取失败、端点/key缺失、HTTP错、空文本；choices/content blocks及600字符截断。 | O-VISION可复用协议断言，视觉理解仍待独立实调。fake screenshot指向I-FS合成PNG，fake urlopen回合成wire；不发送图像。 |

**BM-LO08 静态候选：** `tools.py:174` 将 `ctypes.windll` 直接赋给变量 user32，`:178/181/183` 随后直接找 GetForegroundWindow 等符号；代码没有选择 `ctypes.windll.user32`。最小检查应让替身忠实保留 loader→user32 两层，仅在 user32 暴露函数；比较当前实现返回的错误与预期固定 `R2 title`。若将函数直接挂在loader上，测试会迎合实现而掩盖真实调用层级。本次未执行，不能冒称真实桌面已测失败。

## Godot：动作、表情、输出消费与配置

| 分支键 / 原 ID | 实际入口 | 最小输入与判据 | 复用证据、下一步与隔离 |
|---|---|---|---|
| BM-GD01 / AN-*、AV-*、新增本地入口 | `runtime.gd:971–1048`；Core `AVATAR_EVENTS` | 枚举menu/快捷键/local handle_agent_event/Core avatar.command四种入口；pirouette/listen/think本地存在但不自动视为Core允许事件；farewell是exit而非普通菜单。 | 承接COVERAGE_REVIEW已有漏项建议。先静态对照集合，再I-GD计调用；禁止通过修改Core白名单“补测试”。 |
| BM-GD02 / AN-* | `runtime.gd:339–441`；motion registry | authored开关off/默认；registry缺失/坏型/空clips；role=exit排除；Animation与PackedScene两路、0/1/多可播动画、缺骨轨、loop和bone_layer。 | G-MOTION验冻结资产，不等于loader异常与类型分支覆盖。I-GD合成最小骨骼/资源；不替换正式资产。 |
| BM-GD03 / AN-listen、AN-think | `runtime.gd:521–636/790–809` | think重复不重头；录音抢占；listen到末尾hold，停止reverse，reverse途中重新recording续正播；过时finished事件不改变现动作；closing忽略新动作。 | G-LISTEN/G-THINK已验部分；以播放位置/方向、state、骨骼采样判定，而非一条print。I-GD，真实自然度另验。 |
| BM-GD04 / AV表情、口型 | `emotion_presets.gd:21–62`；`runtime.gd:1017–1047/1651–1732` | 三preset × 0/默认/1/负/NaN；未知preset清空；speaking释放嘴、blink压眼形；raw expression覆盖preset；duration=0/负/到期；五个mouth事件精确形状。 | G-EMOTION已有权重/组合，补未覆盖输入；纯RefCounted可先做I-GD计算，真实脸部显示仍未因此通过。 |
| BM-GD05 / AV-turn/reset/nod/wave/greet | `runtime.gd:979–1006/1154–1191` | 左右默认30/自定义正负degrees，连续转向、reset；nod1.35与wave/greet2.35秒；旧动作中断及返回idle；未知事件行为单列。 | 注册名/动画资产存在不算事件参数验收。I-GD固定delta采样，与既有G-MOTION分开；不在线向角色注入。 |
| BM-GD06 / 新增Core输出方向 | `runtime.gd:700–787` | client.ready触发list/history；session.list/history要求Array；旧capture的voice.state/transcript/hint拒绝；chat按conversationId；pending按会话；command payload非dict；closing只接允许的告别语音事件。 | 复用G-SESSION/G-FAREWELL；为每个实际输出类型登记producer、role、consumer和ID，不能仅从Core输入枚举覆盖。I-GD假UI/bridge。 |
| BM-GD07 / UI-hud、拖动、输入与连接 | `runtime.gd:639–693/847–959/1741–1965` | F1前后HUD；输入焦点拦快捷键；7/8px点击拖动边界；desktop/compact、缩放上下限、屏幕边缘clamp；断线send不报成功、重连回载只按有效消息。 | G-CANVAS/G-TEXT已有局部证据，不能把UI搜索child_count当具体结果。I-GD先逻辑；DisplayServer焦点/多屏/click-through必须另列真实前台验收。 |
| BM-GD08 / TT04、AN-farewell | `farewell_exit.gd:20/72/82`；`farewell_speech_gate.gd:10–50` | 重入关闭、动画先/语音先完成、缺资源、8秒deadline、旧exit ID、重复/乱序part、unavailable与已播/未播错误；join仅退出一次。 | G-FAREWELL已有主要断言；冻结hash与音频实听是不同层。I-GD假SceneTree.quit/播放器，不关闭正式角色。 |
| BM-GD09 / 新增外观及autoplay配置入口 | `runtime.gd:223–230/514–518/1574–1600`；`.env.example:35` | look=baseline/1.1/1.2-preview/1.3/1.4/未知；缺face mesh；同值重复不重建；autoplay空→idle、true→pirouette、有效ID/未知ID；authored flag off优先。 | 1.1–1.4已冻结外观不代表配置fallback都验过；样例默认1.3与源码fallback1.4分开记录，不读生产.env猜启用值。I-GD/静态；不得改变用户现用外观。 |

输出事件注意：`permission.decision` 是存储事件，不能因Godot没有同名handler判定网络丢失；`ui.menu.toggle` 在Core发给ui role，`chat.user_message` 属另一路径。应按 [COVERAGE_REVIEW 的输出方向复核](COVERAGE_REVIEW.md) 查真正接收者。`runtime._ready:208/237` 会连接Core并在非headless时写预览图，加载整个runtime场景不是自动安全的纯逻辑测试。

## 模型适配、装配及传输

| 分支键 / 原 ID | 实际入口 | 最小输入与判据 | 复用证据、下一步与隔离 |
|---|---|---|---|
| BM-AD01 / AD01、AD02、NI05 | `_provider_config:676–703`、`build_provider:706–728` | provider三名/未知；key空/有；glm credential source=glm/deepseek/非法；shared key缺失不能退旧key；捕获class、model、endpoint、proxy配置。 | E-PROVIDER有共享配置对照；补实际factory分支，不实例化真实transport。I-PY抽函数+构造器替身；只用R2合成配置，不读取.env。 |
| BM-AD02 / AD03 | 同factory；`:187–208` | factory创建实例是否真的传reload_config；默认None与显式callback必须分成两项；不以构造器支持该参数等于正式启用。 | **静态发现当前factory未传callback**；整个agent_core搜索仅构造器赋值和读取，无补赋值。下一步用factory构造器spy保留kwargs，再复核运行入口是否另有装配。I-PY。 |
| BM-AD03 / AD01/02、PE03 | OpenAI `complete:210–259`、`complete_with_tools:261–338` | content字符串/null/数字/空/list；choices空/缺字段/message=None；tool_calls为空/列表，arguments字符串dict/非dict/坏JSON。比较plain和tools路径异常分类、raw和可见正文。 | edge已有null/数字/message None反例；只补不同结构分支。AST实际方法+fake_send；Request body合成、send次数1，不import main。 |
| BM-AD04 / AD05 | OpenAI异常`:235–248/289–305`；agent_loop降级入口 | HTTP400/404/422与401/429/500分别喂给with_tools/plain；区分ToolsUnsupported、ProviderError与格式错误；降级只调用plain，既有工具不可重执行。 | E-FALLBACK与E-HTTP可复用；若错误是认证/请求参数而非能力不支持，记录当前分类，不将宽泛降级判业务正确。I-PY/I-IO。 |
| BM-AD05 / AD06适配支路 | Anthropic `:406–490/592–621` | 多system合并；user/assistant/tool角色、assistant空→继续块；tool_call_id关联；tools input_schema缺失；max_tokens默认/显式；无key提前拒绝。 | 这些是Anthropic文本/工具协议，不应仅挂“视觉适配”总名后消失。AST抽类所需纯方法，不执行_request；body逐字段比对合成合同。 |
| BM-AD06 / AD06适配支路 | Anthropic `_parse_response:536–568`、`_post:570–590` | content非list/空；text/thinking/tool_use混合；input字符串/对象/坏型；生成raw arguments有效JSON；plain空回复拒绝。 | O-VISION只证明视觉request构造，不能覆盖此provider响应支路。I-PY fake response；合成thinking标记必须不进入可见text，不读取实际reasoning。 |
| BM-AD07 / AD03显式callback参数 | OpenAI`:187–208`与Anthropic`:493–514` | 同host同model换key；同key；缺fresh；改host；改model；401/403/429触发次数。比较每次Request.url与合成header，并禁止真实send。 | E-RELOAD的host保护针对OpenAI；Anthropic实现不同，见下述候选。I-PY fake _request/clock，仅合成凭据；不能声称当前factory已启用callback。 |
| BM-AD08 / AD04 | `provider_http.py:26–35/39–83/96–185` | proxy auto/system/direct及非法；localhost/IPv4/IPv6/指定gateway/普通host；TLS/DNS/reset/incomplete；Retry-After秒/HTTP日期/坏值；deadline、3次上限、取消与两个worker槽位释放。 | E-HTTP已有deadline/重试关键断言；新增独立参数登记不等于都缺测。fake request/response/read1/clock与受控事件，不开socket；迟到worker最终释放且不再交付。 |

**BM-AD02 的状态纠正：** 原 AD03 总项写了启用 yes，并引用显式传入重载回调的隔离测试；当前生产factory的kwargs没有该回调。因此“类支持、隔离测试通过、正式装配启用”必须分开。本文只确认所读磁盘源码的连接关系，未检查运行中实例，不修改原成绩。

**BM-AD07 的静态候选：** Anthropic `_send_with_config_reload` 在fresh host/model/key变化时更新self，第二次只改原Request的header，没有重新构造其URL/body；而OpenAI明确拒绝host/model变化。使用两个 `.invalid` 合成URL与两枚R2假key，fake `_request` 第一次抛合成401，第二次仅保存Request。判据是新host的凭据不得出现在旧URL请求上。当前factory不传callback，这只是显式callback路径待复现的独立参数分支，不是已发生的真实凭据泄露。回调关闭路径也不能代替此检查。

## 原 256 之外的登记与最短执行顺序

以下是需要新增独立索引或从总项拆出的对象；原COVERAGE_REVIEW已提出的项在此承接，不重复计发现数：

| 登记建议 | 与原项关系 | 下一步 |
|---|---|---|
| `NI-open_app` | 原NI清单之外的明确未实现能力 | 静态登记缺入口，保留未来产品合同；不实现或用其他工具冒名。 |
| `LOCAL-avatar.pirouette/listen/think` | 原AN资产存在不等于本地事件入口，且不同于Core AVATAR_EVENTS | 按BM-GD01建立menu/key/local/Core四列集合。 |
| `OUT-Core-to-Godot` 与角色专属输出 | 原WS列表主要是输入方向 | 按BM-GD06分别列producer/role/consumer/ID及关闭态策略；不按函数数量计能力。 |
| `CFG-authored-motion/autoplay/model-look/canvas` | 原UI/AN总项下有独立参数入口 | 按BM-GD02/07/09拆出默认、关闭、合法、坏值和缺资源。 |
| `START-lock/ack/generation/health-compat` | LC01/LC02总项下独立状态分支 | 复用已有18个启动逻辑断言，补未覆盖ACK/参数组合，单列前台重启证据。 |
| `CTX-cache-eviction/task-schema-assembly` | 正常长文续页/20条历史不能代验 | 按BM-CX03/05用纯合成内存数据核对淘汰及工具集合。 |
| `ADAPTER-factory-reload-wiring/anthropic-reload` | AD03类能力、factory装配、条件回调的混合口径 | 先做BM-AD02构造kwargs取证，再做BM-AD07的假凭据反例，不改生产配置。 |
| `LOCAL-active-window-Windows-positive` | 原L-active_window只有平台退化证据 | 优先BM-LO08现实层级的ctypes替身；未通过前不扩成真实隐私读取。 |

建议主执行最短顺序：先闭合 BM-AD02 与 BM-LO08 两个静态疑点，再补 BM-AD07 条件分支、BM-CX03 缓存边界、BM-LO01/05 路径与写后unknown；这些均可零网络、零生产进程、纯合成完成。随后复用已有启动/Godot守卫的具体断言，核对版本差异后只执行缺失分支。真实桌面焦点、形态质量、听感、模型回答和连接器业务操作继续由原任务唯一现场操作者安排；本文不扩大授权。

上述任何静态映射或隔离断言都不能把未启用的10项改成产品通过，也不能替代尚未执行的前台链。无代码修复、无生产配置调整、无数据库操作。本次文档范围完成；各行实际执行与产品验收保持其原有未完成状态。

## 追加复核：原362断言的复用边界与剩余高收益探针

2026-10-08追加。只读核对 `offline-suite.json` 的362个测试ID、相关测试正文、上述S/O/E/G索引及本轮合成证据；本实例未重跑测试。362记录是既有运行证据，下面是具体断言与BM的对应关系，不把测试名称、测试文件存在或362总数当作整项通过。该记录本身没有逐文件源码哈希，故只复用已定位的合同；涉及部署源码差异时需绑定相应函数和本轮来源哈希。启动PowerShell及Godot守卫均不属于这362个Python测试。

### 明确未启用状态：可以闭合状态依据，不必为了计数新跑成功分支

| 原项 | 可复用证据及准确状态 | 仍不能推出的结论 |
|---|---|---|
| EF04 | `test_effort.py:16–38` 已验默认/空/未知/大小写和3/6/9轮、deep18次；`MODEL_REASONING_CONTROLS`为空支持“内部推理控制未接入”。 | 三档预算通过不证明模型内部thinking/reasoning生效；不为此重跑模型。 |
| TA09 | `test_harness_v1_integration.py:113–118` 只证已内嵌resource text被保留；mcp_host缺resources/read调度支持“正文资源桥接未实现”。 | 嵌入正文和独立Drive连接器读取都不能替代Core资源读取入口。 |
| VO05 | O-MANUAL三条断言已证manual不构造后台listener、转写/乱序stop不重启。 | 这是有实现但当前明确禁用；无需启麦克风补成功分支。 |
| NI01 | 有限动作/骨骼修正与G-MOTION/G-LISTEN合同；通用衣发接触解算无实现依据。 | 任一动作或冻结资产通过不等于通用无穿模。 |
| NI02 | HANDOFF明确暂缓；手动启动和守护不构成登录触发注册。 | 无需真实登录、注册表或计划任务试验。 |
| NI03 | `test_memory_retrieval.py:43–65` 已验pending列表、确认提升及session隔离；UI/WS审阅和遗忘入口仍缺失。 | `test_pending_facts_are_not_recallable`夹具是银行卡尾号，只证敏感pending隐藏，不能泛化全部pending；`test_storage.py:229–243`反而明确普通pending可带待确认标签召回。内部状态方法不等于审阅/遗忘UI。 |
| NI04 | 无任意桌面键鼠工具入口，且明确缓行。 | 浏览器操作和Godot快捷键不能回填。 |
| NI05 | wiring五例与实际factory枚举支持无Spark分支。 | 未知provider返回Mock不算Spark支持。 |
| NI06 | 正式cmd→start-mvp→Godot链未调用Tauri；源码存在与正式启用分列。 | 不能据此宣称Tauri不存在或不可构建；362也不覆盖Tauri设置持久化。 |
| NI07 | 交付脚本/依赖清单可静态核对，任意硬件及离线另机合同仍未验收。 | 本机362不证明跨机、缺缓存、无GPU/无网络交付。 |

`NI-open_app`仍须独立登记缺入口；本次不计入原10项分母。另将AD03记录为“类支持、正式factory未接回调”，它是本轮新增装配证据，不偷偷替换原10项之一。

### BM逐组复用：只补右栏所列差异

以下测试路径省略共同前缀 `services/agent-core/tests/`。测试名称以本文上方E/O索引或该文件行号定位，行号和断言正文共同约束其范围。

| BM | 已有具体断言，可复用部分 | 剩余最小差异，不重复整组 |
|---|---|---|
| ST01–ST04 | Python362的O-HEALTH只证API live无依赖探测、详细health离线兼容；另有 `test-startup.ps1:71–199` 的身份、404回退、PID复用、冷启复用、预热/陈旧回收、权限失败及退出取消。 | PS端口边界/空值、service名与缺PID兼容、age与misses各单独到阈值；不能将O-HEALTH扩成PS状态机通过。 |
| ST05 | 原362无mutex/ACK/窗口采样合同；既有启动函数测试也没有此整条链。 | 合成旧generation ACK与锁超时；核对不启动、不误接受旧ACK。SkipAvatar另列一个无启动控制。 |
| ST06 | `test-startup.ps1:160–170/194–199` 已验新avatar存在不清理、旧avatar关闭才清理及恢复中关闭取消。 | watcher自身同代重复、ACK归属/清理和恢复时generation变化；无需重做底层PID矩阵。 |
| ST07 | Python语音恢复测试只证SpeechManager客户端重试/缓存，不能代替PS TTS生命周期。 | PS WasReady×misses决策、heartbeat边界、attempt4→5退避、等待时释放启动锁；使用纯状态函数和假时钟。 |
| CX01 | `test_storage.py:29–52/111–132`已验初始空会话、默认/显式路由、历史UI形状及reopen；local的25取20、edge的20行harness组合已补序列/当前问句唯一。 | 19/20/21边界仅在需确认截断转换时加一组；默认路由不再列为全新缺测。系统提示/任务状态/记忆仍不受20行约束。 |
| CX02 | E-TICKET/E-CANCEL已验确认、取消、改参及真实临时产物；E-CONTINUE已验继续不充值；`test_harness_v1_integration.py:100–109`已验普通后续保留票据且不授权。continuation-counterfactual已证无pending的继续会选错误固定提示。 | 优先核对approve真实回执分支和无pending确认：task ID/intent、缓存ref、预算、actions及传给harness的固定提示一并比较；旧预算测试没断言这些提示正文。 |
| CX03 | O-PAGES精确验尾哨兵、另实例ref拒绝和负offset；本轮长文续页另有证据。 | JSON序列化后2000/2001、4Mi上限、累计最旧淘汰；淘汰后read及bool/string/EOF offset。不重测同一9000字符尾页。 |
| CX04 | E-MEMORY及 `test_memory_retrieval.py:43–65` 已验多字段、scope、pending/confirmed、更正superseded、敏感pending隐藏和状态提升。 | 更正与同词不同项目应沿已有反例；新增仅补召回抛错后chat仍能继续/错误事件，以及删除session对global事实合同。不把测试名“pending不可召回”误读成所有pending隐藏。 |
| CX05 | `test_effort.py:16–38`完整覆盖本表列的effort归一化；E-CONTINUE覆盖继续不充值。 | 三档精确工具集合，尤其local schema空+MCP非空时缺recall_memory/read_tool_result；全部schema空走plain。`every_level_stays_a_full_agent`只验正预算和label，不能复用为schema断言。 |
| CX06 | `test_harness.py:60–105`已有1.8→1.0 clamp、坏emotion/gesture/intensity回退；ContextTests已验尾杂字/内嵌换行/引号修复；edge已证null/数值/空/左括号。 | 非字符串对象、NaN/非有限强度等尚未命中的结构；坏metadata普通组不用重复。 |
| CX07 | O-SESSION覆盖新建/首轮命名/删除/未知删除和ScriptedProvider响应；O-VOICE覆盖旧generation。 | WS null/list、4000/4001，以及Godot异步session切换后迟到history/response；后者不能用storage隔离证明。 |
| LO01 | `test_tools.py:79–99`和 `test_write_file.py:58–72`已有相对/越界/..拒绝、profile后代、写根空禁用。 | 词法路径与resolve实体分处两根的OR合同；只用同一总临时目录内两侧夹具或Path替身。 |
| LO02 | `test_harness_v1_adversarial.py:49–62`早已精确验证有效UTF-8分页；local及edge补坏字节、页边界、offset/EOF/缺文件。 | 仅需文件在is_file后消失或open/read抛OSError的故障来源；不能再称有效UTF-8分页缺测。 |
| LO03 | O-LIST及local证明目录首位、缺目录、200项上限。 | 精确全序列、单项stat失败与iterdir整体失败；199/200/201可在同一合成序列控制中完成。 |
| LO04 | `test_write_file.py:25–46`已有overwrite/append/Unicode/无BOM；local补四种append换行与坏类型/模式/单次超限。 | 仅在产品合同需要时区分追加后总长度与单次内容上限，不自行规定文件总上限。 |
| LO05 | local已证replace失败保留原文件且留下tmp，清理由探针完成。 | replace已成功后readback失败/哈希不符两例：结果unknown与新文件真实状态必须同时记录；避免把失败回执误当无副作用。 |
| LO06 | 本轮local的10个command分支与edge带空格路径拒绝反例已覆盖主要合同；原362没有这整组。 | 只补尚未出现的明确参数分支；`test_tools.McpCommandResolutionTests`针对MCP启动解析，不是run_command白名单。无需重复mock相同10例。 |
| LO07 | `test_tools.py:160–178`已验未知/缺required/成功/TypeError；`:200–219`已验外层短期限失败、长期限成功和默认期限。 | arguments非dict、OSError类别及超时后worker迟到副作用/结果交付的隔离观测；旧超时断言没有证明worker停止。 |
| LO08 | O-DEGRADED只有缺依赖/非Windows；wiring两例新增窗口Loader层级反例和选定User32的正常控制。 | 零handle/空title/OS错误及mss/clipboard成功分支仍独立；不以RC18反例代验真实屏幕或剪贴板。 |
| LO09 | O-VISION已验OpenAI/Anthropic请求形状、thinking过滤和扩展timeout。 | 缺key/空文本/截图或图片读取故障/600字符截断；实际视觉识别保持现场独立合同。 |
| GD01–GD02 | 原362没有Godot事件入口或资源loader断言；G-MOTION源码仅对应冻结资源控制。 | 四种入口集合差异及坏registry/资源类型分支，先静态集合、再隔离合成资源，不加载正式runtime自动连Core。 |
| GD03 | G-LISTEN/G-THINK脚本已有保持/反向/抢占/重复thinking不重启等明确断言，但本轮记录是已审源码而非新执行。 | 中途反向后重新recording、过时finished/closing，复用原守卫可用部分而非重做动作全矩阵。 |
| GD04 | G-EMOTION已有三preset、到期、invalid、speaking/blink及mouth_o覆盖；原362仅Core解析和行为事件映射。 | 尚余四个mouth形状和非有限输入；不能因Core产生avatar事件就称Godot表情可见。 |
| GD05 | Core `test_harness.py:60–79`只证happy/nod生成事件；冻结动作资产不是degrees/duration消费断言。 | 左右符号/累积/reset及动作中断→idle；合成时间步足够，真实自然度仍另验。 |
| GD06 | 历史G-SESSION/G-FAREWELL覆盖各自事件；362语音generation和session存储只是发送端或底层。 | 迟到history/chat与conversationId、非Array列表、坏command payload及closing白名单；按实际producer/role/consumer分组。 |
| GD07 | 历史G-TEXT已验输入焦点阻止A键转向；G-CANVAS仅已审源码；G-SEARCH的child_count>=2存在宽松断言。 | 搜索精确ID/空结果最小反例优先；拖动7/8px、clamp及断线send按独立合同补。焦点/多屏需前台。 |
| GD08 | 历史G-FAREWELL已验旧exit、join一次、乱序/重复/坏count及冻结hash；原362的O-FAREWELL只验Python发送链。 | 只补缺资源/deadline或未覆盖已播/未播故障；不要把同一join控制重记新增。 |
| GD09 | 没有对应的362 Python断言；冻结外观文件不覆盖look/autoplay/authored开关。 | 配置合法/未知/缺face分支按最小集合补；当前外观启用值不由默认样例推定。 |
| AD01–AD02 | E-PROVIDER已验共享GLM配置/不回退旧key；wiring新增三provider实际factory kwargs以及空key/未知Mock，证AD02未传回调。 | 已测factory分支不用再跑；非法credential source及有效配置选择如需增量，只抽配置函数。当前factory未接回调与类支持必须分列。 |
| AD03–AD04 | edge已证plain/tools在null/数值/message=None的差异；E-FALLBACK已证Unsupported降级、预算耗尽plain finalize；`test_provider_resilience.py:68–76`覆盖plain永久HTTP状态不重试。 | tools路径400/404/422的业务参数错误被泛化为不支持工具，宜选一条具体body反例和一条真实unsupported控制；不重复七种plain状态。 |
| AD05 | `test_anthropic_provider.py:32–117/161–178`已有system、user、assistant tool_use、tool_result关联、坏arguments、schema及默认max_tokens。 | 名为system_rows_merge的测试实际只有一条system，故多system合并仍需一例；空assistant、缺schema、显式max_tokens/无key可分列补。 |
| AD06 | `test_anthropic_provider.py:121–157`已有thinking/text/tool_use混合、raw形状/arguments及content非list拒绝。 | 空list/空plain回复、input字符串/坏型及混合未知block，不重做已证混合正控制。 |
| AD07 | E-RELOAD及 `test_provider_reload.py:77–133`完整覆盖OpenAI同host换key、同key、无fresh key、401/403/429及tools重试；resilience:214–220覆盖改host拒绝。 | Anthropic显式callback的改host/改model与空fresh key尚须反例；这是当前factory未启用的条件路径，优先级低于已启用链的实际故障。 |
| AD08 | `test_provider_resilience.py:47–161/222–260`已有直连/系统/非法代理、域名伪装、localhost、TLS/DNS/reset/incomplete、Retry-After短/长/坏值、deadline、取消、两worker槽位及释放后恢复。 | 只补IPv4/IPv6和Retry-After HTTP日期等未覆盖参数。两槽位释放不是新缺口；原362中的LocalWireFaultTests另含真实loopback，本任务禁止网络，不能照搬重跑。 |

### RC18 / RC19证据审核与可推翻其外推的反例

`wiring-counterfactuals-01.json`的7条观察支持现有两条根因的**源码范围**表述。结果中的main SHA为 `7af0c89c3fd171c749c1fee5e94e42a414d68adfb98c39f7a2e9b7d0eca905fc`，tools SHA仍为 `9f751b0c507dacad78b8ca6cfc4dd1bb0d83ab1f4137984f32cb07dfb9de54d7`；不能拿本文前版main哈希替换这份探针来源。脚本SHA `79767bd48302f06871f361d53022803675a491df6140b92c364a6aac70c642f3`与文件匹配；结果文件SHA为 `f5b279bc821f265c6fb6c638e893c30c98a7f3bedbd38d2d1f15035ee9e14c83`。本实例只复核结果和代码，没有重跑。

- **RC18充分支持的结论：** 当前函数在Loader对象上直接找GetForegroundWindow；双层假Loader失败，换为User32对象后同函数依次调用三API并返回精确合成title。因此故障可归到缺少user32库选择。反例边界：这个成功控制不验证真实ctypes函数原型/64位handle、实际窗口权限或空title；若运行进程代码不同、环境预先向Loader注入同名callable，其现场表现可能不同。合成Loader报错文本也不是Windows真实OSError原文。无需为加强这一源码定位主动读取前台。
- **RC19充分支持的结论：** 三个有key分支均没有reload_config关键词；实际构造器是keyword-only且默认None（main:160/384），`:170/393`直接保存它，定向搜索没有其他赋值接线，故当前factory创建的标准类实例不启用重载回调。反例边界：原362主动传callback后能换key是类能力正控制，不能反驳factory缺接线；替换factory/类、构造后外部注入或旧运行进程可使现场对象不同。两个Mock分支只支持fallback，不能证明远端鉴权或热重载失败。没有触发401、读取配置秘密或检查活动实例，不推导线上换key已失败。

### 剩余探针按因果收益排序

1. **CX02：确认回执与无pending后续的真实上下文。** 已有continue预算控制和固定提示反例，新增approve/无pending确认的最小上下文对照，区分宿主错误提示与模型复用历史回执；记录R2 task/合成receipt，不记录普通历史或召回私密内容。v3的116回归+41观测检查只证明观察器合同，本身不证明这一业务因果。
2. **LO05：写后unknown；LO01：路径别名边界。** 前者用合成文件+mock readback证明副作用已发生但结果未知，后者用两侧都在总临时目录的路径实体或Path替身核对OR条件。两者能避免错误重试/权限解释，均无需生产I/O。
3. **CX03：缓存淘汰；CX05：工具schema装配。** 纯内存一次阈值转换与最旧ref失效即可；schema用local空/MCP非空和全空两个条件，捕获精确工具集合。不要重测正常尾页或effort字符串归一化。
4. **AD04：工具不支持与一般400参数错误；AD07：Anthropic条件重载。** 每项采用一条反例加一条正常控制。AD07仅对显式callback成立，当前factory没有启用，不以高影响假设抬成当前线上故障；fake send记录URL/body/假key，0网络。
5. **ST05–ST07：ACK/generation和TTS决策。** 在既有18个启动函数断言之上只补所有权/临界状态，fake CIM/HTTP/process/time，不运行原守护循环或启动入口。
6. **GD06/GD07：迟到会话事件与搜索宽断言；随后GD02/04/09缺参分支。** 先补精确ID及状态断言；必须做Godot时另安排隔离项目，仍不能把逻辑结果当人物观感/前台通过。

RC18/RC19已由本轮探针补到源码根因层，不需要为它们重跑原362；剩余19/20/21、全序排序、IPv6、外观参数等低收益边界保持登记，只有进入相应实际故障或验收合同再选取。本追加没有修改主文档、原成绩、业务代码或任何运行配置。
