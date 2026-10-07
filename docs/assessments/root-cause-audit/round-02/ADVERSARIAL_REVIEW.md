# 第二轮独立对抗初审（开放）

审查者：Codex 独立新上下文 coverage/observer 审查实例。初审日期：2026-10-07；最新增补：2026-10-08。

**状态：初审仍开放。先提交反例；不替主执行者宣布第二轮完成。** 基线为 `837318335307c85bb288265d0b80b4c7256d46f0`。已读 AGENTS、HANDOFF、CONTRIBUTIONS、VERIFICATION_SPEC，以及第一轮 REPORT、ROOT_CAUSES、COVERAGE、ADVERSARIAL_REVIEW 和 coverage.json。生产 dirty work 未动；未操作桌面、未启动 Core/MCP/TTS、未调用真实模型或外部服务。仅修改本实例负责的本报告与 COVERAGE_REVIEW.md/JSON。纯内存复现通过 `python -B` 运行，避免生成项目字节码。

主执行者正在修改诊断脚本；下述诊断发现按**被审版本及复核状态**记录，不能用旧行号替代当前文件复核。观察器内存反例对应 SHA256 `f9cf3512adf0e8228eab9d910b28bc5df210cac3f3e6152dbdf1b14ada412328`。

## 已提交反例

### [MEDIUM] R2-I01：schema 中的描述型 method 漏过覆盖枚举

位置：`scripts/root_cause_audit/surface_inventory.py:24–26`、`coverage.py:120–128`；直接证据：`evidence/mcp-schema.json:3663`。

实际 `sub_issue_write.method` 没有 `enum`，但 description 明确列出 `add/remove/reprioritize`；`replace_parent=true` 又改变 add 的转移语义。现有脚本只读取 enum，所以 COVERAGE:143 仅有工具总项，三个 METHOD 行都不存在。“全部入口已交叉登记”不能覆盖这三个分支。

本次机械核对结果：256 行、256 个唯一 ID、94 个 schema 工具均有总项；28 个顶层 method/action/event enum 值均有映射；缺失上述 3 个描述型 method。原四桶计数确为 72/47/10/127，但计数自洽不等于分支穷尽。

同类 UI 入口缺口：`apps/avatar-runtime/runtime.gd:949–950` 的 F1/HUD 开关没有独立覆盖行；`coverage.py:103` 的手写 UI 列表不含 HUD。184 个函数名清单保留了 handler 名称，但未登记该用户入口的预期和验证状态。

建议：补显式描述型分派清单，标注来源，不靠关键词自动推定所有参数都有副作用；新增行仍应未验证。PR review 的 method/event 已有独立登记，但 create 无 event（pending）与 create+event（直接提交）应作为组合夹具，不把两条单字段登记当组合验收。

### [MEDIUM] R2-I02：读取回执未绑定当前请求或目标，V1 判卷可误 PASS

位置：`scripts/harness_v0/grader.py:83–86`，由 `scripts/harness_v1/grader.py:35` 继承；V1:67–86 只对 mutation 额外检查票据。

使用原 F01 case，当前 request 为 current、回复正确，但唯一 read_file 回执属于 unrelated-old 且读取 wrong.txt，V1 返回 PASS。移除该无关回执才返回 FAIL/actual_read。没有篡改旧成绩，也未运行模型。这是 EV01 应补充的请求/对象关联负例；不是说已证明旧的 288 条记录都存在误判。

### [MEDIUM] R2-I03：数字子串让错误的精确结果通过

位置：`scripts/harness_v0/grader.py:70–71`，V1 仍继承该检查。

原 F01 正确总额为 175；保留当前请求的正确 sales.csv 回执，仅将回复改成 `100 + 75 = 1750`，V1 仍返回 PASS。它独立于上一个回执错误；不是等价表达问题，而是精确事实错误被子串检查接受。应把实际数值/字段匹配与解释文本分开，不修改旧成绩来消除反例。

### [MEDIUM] R2-I04：诊断边界异常能够阻断原业务

位置（f9cf3512 版本）：`round02_observer.py:38–40,67,174,311`。

纯内存执行实际观察器定义、替代文件读取和 VoiceSelfCheck 后：

- control.json 的内容为合法 JSON `[]` 时，`enabled()` 抛 AttributeError；`emit()` 在 try 外调用它，chat wrapper 也在原 handle_chat 前调用。因此控制文件类型错误会阻断业务，而非仅关闭诊断。
- TTS `sys.stdout=None` 时，`sys.stdout.isatty()` 在原 VoiceSelfCheck.run 前抛 AttributeError，原函数调用次数没有增加。未声称当前生产 TTS 恰好处于该 stdout 状态；这是可确定的诊断透明性边界。

建议：控制对象先做 dict 校验；所有观测元数据读取都走不会抛出的辅助路径；保持原调用、返回值和异常对象不变。主执行者收到后正在修订，**此处尚未独立复测修订版本**。

### [MEDIUM] R2-I05：同文本 TTS hash 不能唯一关联请求

位置（f9cf3512 版本）：`round02_observer.py:263–266,298–302`。实际调用边界：配套 `tianyi-tts/scripts/tts_server.py:211–218` 在获取合成锁后才调用 VoiceSelfCheck.run；Core `SpeechClient.synthesize` 的许可记录在发送前产生。

内存夹具同时含 A/B 两个请求的同文本 hash 且都在 600 秒内，调用实际 wrapper 时总选择最后一条 B。A 迟到、取消后同步请求尚未结束、或者不同请求产生相同回复时，不能据此断言“这次 sidecar 异常属于 B”。没有证据声称本轮已经发生该并发顺序。

建议：把多个候选标为 ambiguous 并保留候选请求与时间，不凭最新文本匹配得出唯一因果。若引入诊断关联 ID，应验证只在诊断传输层透传、不改变业务授权、缓存或去重语义。

### [MEDIUM] R2-I06：TTS 健康失败会阻断独立的数据库取证

位置（初审版本）：`round02_identity.py:69–71`。

先读 Core /health，再无保护读取 TTS /health，之后才校验文件身份和打开 SQLite。TTS 连接拒绝、超时、503 或非 JSON 会直接走全局 failed，导致最需要研究语音异常时拿不到数据库事务快照。主执行者已接受应把 TTS 健康记录为独立结果；**修订待复核**。这是诊断耦合，不是业务数据库错误。

## 已接受修订及归因边界

1. **原观察器 pending 字段无效。** 初版 `task_state` 读取不存在的 `core._pending_actions`，实际主程序用 `_actions().pending(session)` 和 `_pending_writes`，`_shown_confirmations` 仅是首张票据。主执行者随后改为 pending_head 与 action ledger；独立实例已看到源码修订，尚未对真实多待办运行复核。不能将早期 trace.pending=null 当成“无待办”。
2. **合成前缀不使上下文自动变为合成。** Core `main.py:1528–1543` 会注入全局记忆；初版 observer 保存完整 request body，单靠字段黑名单不会移除 messages[].content 中的记忆。主执行者改为请求内容 hash/长度及响应字段白名单。已看到修改，未宣称完整隐私测试通过。原始模型输出/工具返回也可能复述记忆，仍须私有保存与人工审核后导出。
3. **文件身份与事务一致性是两层改进。** normal/UNC 主文件 volume_serial+file_index 相同，且 SQLite BEGIN 后读取水位再 backup，比 main/WAL 三次哈希复制更强。若被核对身份的事务快照仍有相同 quick_check 结构错误，原先“只是并发文件复制竞争造成异常”的解释显著减弱；仍不能证明损坏发生时间、写坏者、历史恢复范围，或 24 条时间列异常与同一个 B-tree 问题同因。
4. **15700 不是重定向探测器。** 它只记录此进程无 package identity；主执行者提供的两种文件视图都返回 15700 已构成反证，不能把 unpackaged 字样当全部身份结论。
5. **Core 句柄身份尚有边界。** /health 的 memory.path 只是字符串（`main.py:1897`）；当前脚本比较的是探针自己的路径打开结果，未直接取得 Core 当前 SQLite 句柄的 file ID。旧审计 request 存在只证明共同历史。新增由当前桌面产生的合成 nonce、Core PID/启动时间、同一事务快照中的 nonce 能强化关联，但不应谎称直接测了 Core 句柄。
6. **54 文件哈希相同是部署磁盘证据。** 不直接证明已加载模块，也不证明内存中临时诊断 monkeypatch 不存在。增加观察器后应单列诊断文件/hook 的 before/after hash 与启停证据。
7. **ME06 的“静态+隔离”须细分。** `review_reproduction.py:87–97` 的 history 只有两条，load_messages 是忽略 limit 的 stub。它支持确认后聊天历史保留，不是 20 条窗口截断的动态验收。20 是 `main.py:71,1504` 的静态事实；21/22 条边界及跨会话隔离仍可增加内存夹具。

## Hook 签名与关键采集缺口

已沿真实调用点核对：

| Hook | 实际合同 | 初审判断 |
|---|---|---|
| 两 Provider._request | 同步，输入 Request，返回 bytes | 转发形态匹配 |
| 两 Provider.complete / complete_with_tools | async | async wrapper 匹配 |
| McpServer._roundtrip | async，payload/timeout | 匹配 |
| Core run_tool / _execute_authorized_tool | async | 匹配 |
| harness.parse_reply / _receipt_delivery | 同步 | 实例/函数包装形态匹配 |
| SpeechClient.synthesize | self,text,speed=1.0 | *args/**kwargs 可保留 |
| VoiceSelfCheck.run | self,text,speed,raw_synth,base_temperature | *args/**kwargs 可保留 |
| MemoryStore.add_event | event_type,payload=None | 初版 wrapper 要求 payload 且直接 .get，未完整保留默认参数合同；当前业务搜索到的调用都传 dict，不将其夸大为已发生故障 |

需要补的透明性矩阵：disabled/enabled；正常返回/业务异常/CancelledError；控制文件不存在/空/非 dict；输出路径不可写；stdout None/不可用；每个例子比较原函数调用数、参数、返回对象/异常对象、TRACE reset。这些是诊断工具验收，不能重写业务期望。

观察器只 hook send_roles；定向 hub.send 的事件（例如 chat.history.response）不在 godot.outgoing 中，不能据此判定“前台没收到”。voice.normalize 在手动转录任务中通常没有 chat TRACE，无法靠 chat wrapper 证明 STT 前处理全链；需显式 captureId 到合成录音夹具的观测范围。TTS以同文本许可匹配只提供候选关联，见 R2-I05。

## 无真实账号的最小夹具计划

| 范围 | 合成夹具 | 应验证内容 |
|---|---|---|
| method/action 分支 | schema 本地 JSON；调用记录型 fake executor | sub_issue add/remove/reprioritize、replace_parent；PR pending/直接提交/撤回组合；只验证路由/授权/回执，不冒称 GitHub 真实操作成功 |
| MCP 错误与资源 | fake _roundtrip 返回 isError、JSON-RPC error、空 content、embedded resource、独立 resource URI | 业务/协议/交付三层保持一致；合法 Error 文本不误判 |
| 任务/结果缓存 | :memory: SQLite，两个会话、21/22 条历史、两个同名不同参数动作 | 无票据确认/继续、窗口截断、旧票据/跨会话/过期 ref、取消后的完整状态 |
| 语音/闲置 | fake transcriber/clock/recorder/speech callback | 空录音零模型/零记忆、旧 capture 不回填、599/600/601 秒、01:00/07:00边界、续片前活动检查 |
| UI/协议 | 主执行者准备隔离 Godot 场景和 fake WebSocket，仅合成会话 | F1/HUD、历史筛选/删除、旧会话响应、speech/permission状态；不由本审查者操作桌面 |
| 身份/取证器 | 私有临时合成 SQLite/WAL，两连接、nonce、读事务、故意错身份 fake | source/dest水位一致、并发提交不混快照、错身份拒绝、TTS不可用仍可采样；不修真实库 |

只有主执行者后续真实执行并保存证据的条目才能升级状态。此表本身不是通过记录。

## 可直接复用的评测反例

从本 checkout 根目录以 `python -B` 运行下列正文。仅导入两个纯判卷模块并读取合成 cases.json；无外部调用、无 Core 导入、无文件写入：

```python
import copy
import json
from pathlib import Path
from scripts.harness_v1.grader import grade

cases = json.loads(Path("docs/assessments/harness-v1/cases.json").read_text(encoding="utf-8"))["cases"]
case = next(c for c in cases if c["id"] == "F01")
files = case["initial_fixture"]["files"]
base = {
    "source_manifest": {"harness_version": "v1"},
    "turns": [{"request_id": "current"}],
    "events": [{"type": "chat.response", "request_id": "current", "text": "100 + 75 = 175"}],
    "before": {"files": copy.deepcopy(files)},
    "after": {"files": copy.deepcopy(files)},
    "executions": [{"kind": "read", "tool": "read_file", "request_id": "current",
                    "arguments": {"path": "/fixture/sales.csv"},
                    "result": {"ok": True, "output": files["sales.csv"]}}],
}
checks = [("positive", base)]
unrelated = copy.deepcopy(base)
unrelated["executions"][0].update(request_id="unrelated-old", arguments={"path": "/fixture/wrong.txt"},
                                 result={"ok": True, "output": "unrelated"})
checks.append(("unrelated-receipt", unrelated))
wrong = copy.deepcopy(base)
wrong["events"][0]["text"] = "100 + 75 = 1750"
checks.append(("wrong-total", wrong))
missing = copy.deepcopy(base)
missing["executions"] = []
checks.append(("no-receipt", missing))
for label, evidence in checks:
    result = grade(case, evidence)
    print(json.dumps({"case": label, "verdict": result["verdict"], "reasons": result["reasons"]}))
```

本独立实例实际结果：

| 夹具 | V1 v1.2 结果 |
|---|---|
| positive | PASS |
| unrelated-receipt | PASS（反例） |
| wrong-total | PASS（反例） |
| no-receipt | FAIL，actual_read（负控制） |

## Review Summary

下表记录初审提交的六组 MEDIUM 问题；已接受/已改项仍以各节复核状态为准，未伪造“独立复测通过”。

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 6 | info |
| LOW | 0 | pass |

初审结论（历史记录）：未发现已证实 HIGH/CRITICAL；六项 MEDIUM 已提交，不能据此给出总体批准。以下复核更新替代初审中的“待复核”状态。

## 追加复核：诊断透明性与撤销（2026-10-07）

本节是独立实例再次实际执行的纯内存复核。观察器先复核 `4cc6d05e91b7230bcf032b1e4bdcbcca1d79faacf6a64b2820981caec8d6605d`，随后对最终候选 `59050cb15f9e84a4d5aa68237355c59223e8c0446c0af0b04ca178b4ebbd4f7b` 重跑下述全部观察器内存夹具，并追加真实 schema 测试；安装器为 `e3e3803dfbe52ec28036e6f8b74913df338d950cdbcb67a014c61e08d8741435`。未执行生产应用或操作窗口，未创建测试脚本、数据库或其他证据文件。下附代码仅从审计仓读取源码，其文件写入接口均为内存替身。

### 原反例修订的独立结果

| 输入或故障 | 最新结果 | 当前源码位置 |
|---|---|---|
| control 为 []、null、42、字符串 | enabled 返回 False，无异常 | observer:34–41 |
| add_event 省略 payload、None、list；dict 内 request_id 为 list | 原函数调用及同一返回对象保留，无新增异常 | observer:72–79,256–261 |
| hub.send 发已登记会话的历史响应 | 保留原返回对象，新增 godot.direct 可见 | observer:278–283 |
| stdout=None 或 isatty 抛 ValueError | 原 TTS 函数仍执行，返回对象和 TRACE 清理保留 | observer:64–69,367–380 |
| 同文本对应 A/B 两条许可 | trace 标为 ambiguous-tts-text，保留两个候选 | observer:350–362 |
| 许可混合 null、[]、42、坏 epoch、损坏 JSON 与有效 A/B | 无效行跳过，有效候选保留，原 TTS 函数正常执行 | observer:351–364 |
| 录音 owner 持 threading.Lock | stt.capture 存在，不再 dataclasses.asdict 深复制 owner | observer:295–301 |
| synthetic_voice_until 有效/过期 | 有效时看到 capture、raw、simplified；过期时不新增 trace | observer:287–304 |
| 旧 generation | 仅 stt.capture，没有 raw/simplified；原 handler 的过期判定仍有效 | observer:298–299 与真实 handle_voice_transcription |

据此，R2-I04 的已报告透明性反例已闭合；R2-I05 的错误唯一归因已消除，**文本 hash 仍不是唯一请求关联证据**。I06 当前 identity:71–75 已把 TTS 健康失败记为独立 unavailable，源码耦合已解除；本实例未请求真实健康端点或生成快照。

主执行者的 `observer-check-v2.json` 记录 10 项观察器检查及 116 项相关回归通过；`observer-edges.json` 记录六组边缘检查，包含原异常对象保留。本实例读过结果与测试源码，但没有将这些主执行者结果混称为自己重跑。第一次测试结束时 initial_memory 未关闭的清理失败应保留为原始结果，不等于测试断言失败，也不能从证据历史删除。

### [MEDIUM，已闭合] R2-I07：非原子覆盖与严格恢复哈希冲突

初版 overlay SHA256 `49537319af563af466eb2d4b908333c31cc8a4800cf77558556fd22fdca78d38` 在第 75/92 行直接 write_bytes 覆盖入口，恢复第 82 行只接受 before/after 哈希。若入口写到一半抛 OSError，现存有效备份也无法通过该恢复入口使用。随后 `7b56eb9f…` 虽原子化入口，第 86–87 行仍直接写第二个 TTS sidecar；中断时 Core 可能已安装，而恢复因损坏 sidecar 哈希拒绝。此路径是静态可证实的恢复缺口，正常往返不能排除它。

当前 e3e3803d 版本的第 19–28、80–86、103 行对备份、manifest、sidecar 与入口使用同目录临时文件、flush/fsync、os.replace；没有放宽未知业务变更拒绝规则。独立测试执行真实 AST，对三个写入位置分别模拟“写 17 字节后 OSError”，随后关闭故障并运行真实 restore 分支：

| 故障位置 | 后续 restore | 两入口原字节 | 备份原字节 | sidecar 移除 |
|---|---|---|---|---|
| apply Core 入口 | restored | True | True | True |
| apply TTS sidecar | restored | True | True | True |
| restore Core 入口 | restored | True | True | True |

此测试验证脚本分支，未代替真实 Windows os.replace 或机器断电测试。读取过主执行者 `overlay-check.json` 的正常复制文件往返结果；其五项检查支持字节恢复和控制关闭，但该旧结果没有安装器 hash，应在最新版本的部署记录里绑定源 hash。两个真实入口均 import sys，生成 hook 对 sys.modules 的引用有实际定义。

### 限定部署条件与仍开放范围

截至上述 hash，已报观察器业务透明性和安装器故障恢复问题均已闭合，**没有尚未解决、必须阻止本轮受控诊断安装的代码级反例**。这是诊断代码候选结论。真正安装后仍应核对 Core/TTS 各自 observer.installed 的 PID 与源码 hash、control 到期门、实际 trace 可写，以及结束后的原字节恢复和 sidecar 移除；这些现场步骤尚不在本实例的完成声明中。主执行者报告已正常退出 Godot，六个原会话相关 PID 均不存在；本实例没有独立操作或枚举桌面验证。

`synthetic_voice_until` 是时间门，不验证音频确实合成，也不绑定单个 capture/session。仅应在本轮专用合成录音窗口启用，结束或失败后关闭；窗口内任何录音都会按该门采集。stt.capture 只证明进入 wrapper，不证明 STT、转写接受、chat 提交或 Godot 展示成功。TRACE 在 asyncio.to_thread 的本次真实 handler 抽取夹具中传播成功，不代表所有未来线程创建方式都自动传播。

生产配置、业务提示词、资源未由 overlay 修改；但运行时函数确实会被包装。只移除磁盘文件不会撤销已运行进程中的 monkeypatch，恢复前仍须正常停止相关运行时，后续启动再检查原路径。原始响应与工具返回可能复述记忆，诊断文件仍应在既定私有目录，导出前审核；字段白名单不意味着整个响应都是合成内容。

R2-I01 覆盖映射遗漏、I02 回执关联、I03 数值误判仍开放。文件身份与真实 Core 句柄、数据库异常来源、未验证能力、账户相关链路及最终用户验收仍按前述边界处理。**本轮诊断代码可部署，不等于第二轮根因审计完成，也不等于 256 项能力全部验证。**

### 可复用纯内存复现：观察器

在审计仓目录以 `python -B` 执行以下正文。读取实际 observer 和真实 handle_voice_transcription 的 AST；其余 Core/TTS、模型、网络及文件写入均为进程内替身。输出包含被审源码 hash，便于后续改版重跑。

```python
import ast, asyncio, hashlib, io, json, sys, threading, time, types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace as NS

path=Path("scripts/root_cause_audit/round02_observer.py")
source=path.read_bytes()
sha=hashlib.sha256(source).hexdigest()
results={}
class MemNode:
    def __init__(self,fs,name=""): self.fs,self.name=fs,name
    def __truediv__(self,name): return MemNode(self.fs,str(name))
    def read_text(self,**kwargs):
        if self.name not in self.fs.files: raise FileNotFoundError(self.name)
        return self.fs.files[self.name]
    def read_bytes(self): return source
    def open(self,mode,**kwargs):
        if self.fs.fail_write: raise OSError("synthetic unavailable trace path")
        node=self
        class Sink(io.StringIO):
            def __exit__(self,*args):
                node.fs.files[node.name]=node.fs.files.get(node.name,"")+self.getvalue()
                self.close()
        return Sink()
class MemFS:
    def __init__(self):
        self.files={"control.json":json.dumps({"enabled":True,"expires_epoch":time.time()+3600})}
        self.fail_write=False
        self.root=MemNode(self)
    def events(self):
        return [json.loads(line) for name,text in self.files.items() if name.startswith("trace-") for line in text.splitlines()]
def load():
    g={"__file__":str(path),"__name__":"observer_test"}
    exec(compile(source,str(path),"exec"),g)
    fs=MemFS()
    g["Path"]=lambda *_:fs.root
    g["_root"]=fs.root
    return g,fs
def control(fs,value): fs.files["control.json"]=json.dumps(value)
def config(fs,**extra): control(fs,dict(enabled=True,expires_epoch=time.time()+3600,**extra))
@dataclass
class Capture:
    generation:int=1
    capture_id:str="capture-A"
    session_id:int=7
    owner:object=None
    phase:str="recording"
    def valid(self,generation): return self.generation==generation and bool(self.capture_id)
class P1:
    def _request(self,req): return b"{}"
    async def complete(self,*args,**kwargs): return "reply"
    async def complete_with_tools(self,*args,**kwargs): return {"content":"reply","tool_calls":[]}
class P2:
    def _request(self,req): return b"{}"
    async def complete(self,*args,**kwargs): return "reply"
    async def complete_with_tools(self,*args,**kwargs): return {"content":"reply","tool_calls":[]}
class MC:
    async def _roundtrip(self,*args,**kwargs): return {}
fake=types.ModuleType("agent_core.mcp_host"); fake.McpServer=MC
package=types.ModuleType("agent_core"); package.__path__=[]
sys.modules["agent_core"]=package
sys.modules["agent_core.mcp_host"]=fake
class Speech:
    def synthesize(self,text,speed=1.0): return {"ok":True,"text":text,"speed":speed}
calls=[]
singleton=object()
def add_event(event_type,payload=None): calls.append(("event",event_type,payload)); return singleton
async def send(ws,payload): calls.append(("send",ws,payload)); return singleton
async def send_roles(roles,payload): calls.append(("roles",roles,payload)); return singleton
async def noop(*args,**kwargs): calls.append(("async",args,kwargs)); return singleton
def plain(*args,**kwargs): return singleton
core=types.ModuleType("fake_core")
core.__dict__.update(asyncio=asyncio,VoiceError=type("VoiceError",(Exception,),{}),
    VOICE_INPUT_MODE="manual",wake_listener=None,voice_capture=Capture(),
    handle_chat=noop,OpenAICompatibleProvider=P1,AnthropicCompatibleProvider=P2,
    run_tool=noop,_execute_authorized_tool=noop,run_agent_loop=noop,
    harness=NS(parse_reply=plain),_receipt_delivery=plain,normalize_voice_text=plain,
    _fact_promotion_status=plain,memory=NS(add_event=add_event,add_message=plain,add_fact=plain),
    hub=NS(send=send,send_roles=send_roles),SpeechClient=Speech,_task_state={},_result_pages={},
    _shown_confirmations={},_pending_writes={},_action_ledger=NS(records={}),
    transcribe_wav=lambda data:"synthetic STT",simplify_transcript=lambda text:text+" simplified")
async def voice_event(kind,generation,**payload):
    if core.voice_capture.valid(generation):
        return await core.hub.send_roles({"avatar","ui"},dict(type=kind,captureId=core.voice_capture.capture_id,conversationId=core.voice_capture.session_id,**payload))
core._voice_event=voice_event
tree=ast.parse(Path("services/agent-core/agent_core/main.py").read_text(encoding="utf-8"))
fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=="handle_voice_transcription")
exec(compile(ast.Module(body=[fn],type_ignores=[]),"actual voice handler","exec"),core.__dict__)
g,fs=load()
g["install_core"](core,"memory")
for value in ([],None,42,"bad"):
    control(fs,value)
    results["control_"+type(value).__name__]=g["enabled"]() is False
config(fs)
results["add_event_default"]=core.memory.add_event("synthetic") is singleton
results["add_event_none"]=core.memory.add_event(event_type="synthetic",payload=None) is singleton
results["add_event_list"]=core.memory.add_event("synthetic",[]) is singleton
asyncio.run(core.handle_chat("[R2-test]", "request-A",7))
before=len(fs.events())
results["direct_return_identity"]=asyncio.run(core.hub.send("ws",{"type":"chat.history.response","conversationId":7,"messages":[]})) is singleton
results["direct_session_observed"]=any(x["stage"]=="godot.direct" for x in fs.events()[before:])
before=len(fs.events())
config(fs,synthetic_voice_until=time.time()+60)
asyncio.run(core.handle_voice_transcription(b"synthetic-audio",1))
stages=[x["stage"] for x in fs.events()[before:]]
results["voice_active_stages"]=stages
results["voice_trace_reset"]=g["TRACE"].get() is None
before=len(fs.events())
config(fs,synthetic_voice_until=time.time()-1)
asyncio.run(core.handle_voice_transcription(b"expired-audio",1))
results["voice_expired_no_trace"]=len(fs.events())==before
config(fs,synthetic_voice_until=time.time()+60)
core.voice_capture.owner=threading.Lock()
before=len(fs.events())
asyncio.run(core.handle_voice_transcription(b"synthetic-lock-owner",1))
results["voice_lock_owner_stages"]=[x["stage"] for x in fs.events()[before:]]
core.voice_capture.owner=None
before=len(fs.events())
asyncio.run(core.handle_voice_transcription(b"stale-audio",0))
results["voice_stale_stages"]=[x["stage"] for x in fs.events()[before:]]
try:
    core.memory.add_event("synthetic",{"request_id":[]})
    results["event_list_id"]="ok"
except Exception as exc:
    results["event_list_id"]=type(exc).__name__
g2,fs2=load()
calls2=[]
class Voice:
    def run(self,text,speed,raw_synth,base_temperature): calls2.append(text); return singleton
tts=NS(VoiceSelfCheck=Voice)
g2["install_tts"](tts,"memory")
config(fs2)
digest=hashlib.sha256(b"same").hexdigest()
fs2.files["tts-allow.jsonl"]="\n".join(json.dumps({"sha256":digest,"trace":{"request_id":r},"epoch":time.time()}) for r in ("A","B"))
fs2.files["tts-allow.jsonl"] += '\nnull\n[]\n42\n{"epoch":"bad"}\n{broken'
g2["sys"]=NS(stdout=None,stderr=None,flags=NS(utf8_mode=1),version="synthetic")
results["tts_stdout_none_return"]=Voice().run("same",1.0,None,0.7) is singleton
results["tts_stdout_none_calls"]=len(calls2)
results["tts_ambiguity"]=[x["trace"] for x in fs2.events() if x["stage"]=="tts.sidecar.in"][-1]
results["tts_trace_reset"]=g2["TRACE"].get() is None
class ClosedStdout:
    encoding="utf-8"
    errors="strict"
    def isatty(self): raise ValueError("I/O operation on closed file")
g2["sys"].stdout=ClosedStdout()
before=len(calls2)
try:
    Voice().run("same",1.0,None,0.7)
    results["tts_closed_stdout"]="ok"
except Exception as exc:
    results["tts_closed_stdout"]=type(exc).__name__
results["tts_closed_stdout_original_called"]=len(calls2)>before
results["tts_closed_stdout_trace_reset"]=g2["TRACE"].get() is None
print(json.dumps({"source_sha256":sha,"results":results},ensure_ascii=False,indent=2))
```

### 可复用纯内存复现：安装器中断

以下执行实际安装器的函数定义及 apply/restore 分支。Path、os.replace/fsync 由内存替身接管，不访问生产，不调用 subprocess，不修改任何真实文件。

```python
import ast,hashlib,io,json,time,uuid
from pathlib import Path,PurePosixPath
from types import SimpleNamespace as NS
from datetime import datetime,timezone
source=Path("scripts/root_cause_audit/round02_overlay.py").read_bytes()
observer=Path("scripts/root_cause_audit/round02_observer.py").read_bytes()
tree=ast.parse(source)
nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.If))]
sha=lambda b:hashlib.sha256(b).hexdigest()
class P:
 def __init__(self,s):self.s=str(s)
 def __truediv__(self,x):return P(self.s+"/"+str(x))
 def __str__(self):return self.s
 def __eq__(self,o):return str(self)==str(o)
 @property
 def parent(self):return P(str(PurePosixPath(self.s).parent))
 @property
 def name(self):return PurePosixPath(self.s).name
 def with_name(self,n):return self.parent/n
 def resolve(self):return self
 def exists(self):return self.s in fs
 def read_bytes(self):return fs[self.s]
 def read_text(self,**kw):return fs[self.s].decode()
 def write_bytes(self,b):
  if failing(self.s):fs[self.s]=b[:17];raise OSError("interrupted")
  fs[self.s]=b;return len(b)
 def write_text(self,s,**kw):return self.write_bytes(s.encode())
 def open(self,mode,**kw):
  path=self.s
  if "x" in mode and path in fs:raise FileExistsError(path)
  fs[path]=b""
  class Sink:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def write(self,v):
    b=v if isinstance(v,bytes) else v.encode()
    if failing(path):fs[path]+=b[:17];raise OSError("interrupted")
    fs[path]+=b;return len(v)
   def flush(self):pass
   def fileno(self):return 42
  return Sink()
 def unlink(self,missing_ok=False):fs.pop(self.s,None)
def failing(p):return fault[0] is not None and (p==fault[0] or p.startswith(fault[0]+".r2-"))
def replace(src,dest):fs[str(dest)]=fs.pop(str(src))
core="production/services/agent-core/agent_core/main.py"
tts="tts/scripts/tts_server.py"
side="tts/scripts/_round02_observer.py"
old=b'import sys\nif __name__ == "__main__":\n    pass\n'
out={}
code=compile(ast.Module(body=nodes,type_ignores=[]),"<overlay-under-review>","exec")
for phase,target in (("apply_entry",core),("apply_sidecar",side),("restore_entry",core)):
 fs={core:old,tts:old,"repo/scripts/root_cause_audit/round02_observer.py":observer,"repo/docs/assessments/root-cause-audit/round-02/evidence/deployment-entry.json":json.dumps({"files":{"services/agent-core/agent_core/main.py":{"sha256":sha(old)}}}).encode()}
 fault=[target if phase.startswith("apply") else None]
 a=NS(mode="apply",production=P("production"),tts=P("tts"),private=P("private"))
 g={"a":a,"ROOT":P("repo"),"Path":P,"ast":ast,"json":json,"sha":sha,"datetime":datetime,"timezone":timezone,"time":time,"uuid":uuid,"os":NS(fsync=lambda fd:None,replace=replace),"manifest_path":P("private/overlay-manifest.json"),"control":P("private/control.json"),"print":lambda *a,**kw:None}
 try:exec(code,g)
 except OSError:pass
 if phase=="restore_entry":
  a.mode="restore";fault[0]=core
  try:exec(code,g)
  except OSError:pass
 a.mode="restore";fault[0]=None
 try:exec(code,g);outcome="restored"
 except SystemExit as e:outcome=str(e)
 out[phase]={"exact_original":fs[core]==old and fs[tts]==old,"backup_is_original":fs["private/core-entry-before.py"]==old,"restore_result":outcome,"sidecar_removed":side not in fs}
print(json.dumps({"source_sha256":sha(source),"fault_injection":out},indent=2))
```

### [MEDIUM，已闭合] R2-I08：schema 的非字符串 type 导致请求 trace 丢失

主执行者现场报告旧版 4cc6d05e 的三条 model.http.request 缺失，stderr 出现 ROUND02_OBSERVER_WRITE_FAILED；响应和其他阶段仍存在。旧 observer:48、54 用 `value.get("type") in set`，遇到工具 schema 的 `{"type":["string","null"]}` 或名为 type 的 property 对象会抛 TypeError，emit 捕获后丢失整条观察记录。**旧轮请求链缺失必须保留，不能用后来的修订补称完整链。**

最终候选 59050cb1 在第 48、54 行先验证 type 是 str，第 90 行将版本标为 r2-observer-v2。本实例重新执行前述完整观察器夹具，结果与表格相同；另把实际 mcp-schema.json 中 94 个工具转换为 OpenAI function 工具形状，加 1 个 nullable type 数组夹具，通过真实 wire_request → emit → safe → JSON 写入内存：

- 成功生成一条 model.http.request，95 个工具均存在，nullable 数组原值保留；序列化记录 94,647 字符。
- messages 里的合成隐私哨兵未出现，请求正文仍只有身份 hash/长度。
- response 中 reasoning_content 和 typed reasoning 哨兵未出现，合成正文仍保留。
- 独立补测 type 为 object 的 schema property，以及列表内该对象，safe 均保留结构。

这是明确夹具下的隐私与完整性检查，不保证模型把隐私直接复述在允许 content 字段时也可自动消除。主执行者通知当前运行仍是 4cc6d05e，59050cb1 尚未部署；本次候选结论针对新 hash，现场重启验收仍由主执行者完成。

可复用真实 schema 的零外部调用正文：

```python
import hashlib,io,json
from pathlib import Path
source=Path("scripts/root_cause_audit/round02_observer.py").read_bytes()
g={"__file__":"scripts/root_cause_audit/round02_observer.py"}
exec(compile(source,g["__file__"],"exec"),g)
catalog=json.loads(Path("docs/assessments/root-cause-audit/evidence/mcp-schema.json").read_text(encoding="utf-8"))
tools=[{"type":"function","function":{"name":s["server"]+"__"+t["name"],"description":t.get("description",""),"parameters":t["inputSchema"]}} for s in catalog["servers"] for t in s.get("tools",[])]
tools.append({"type":"function","function":{"name":"synthetic_nullable","parameters":{"type":"object","properties":{"value":{"type":["string","null"]}}}}})
body={"model":"synthetic","tools":tools,"messages":[{"role":"system","content":"PRIVATE_MEMORY_SENTINEL","reasoning":"PRIVATE_REASON_SENTINEL"}]}
records=[]
class Root:
 def __truediv__(self,name):return self
 def open(self,*a,**kw):
  class Sink(io.StringIO):
   def __exit__(self,*a):records.append(self.getvalue());self.close()
  return Sink()
g["_root"]=Root();g["enabled"]=lambda:True
g["emit"]("model.http.request",{"body":g["wire_request"](body)},{"request_id":"synthetic-schema"})
assert len(records)==1
result=json.loads(records[0])["data"]["body"]
assert len(result["tools"])==len(tools)
assert result["tools"][-1]["function"]["parameters"]["properties"]["value"]["type"]==["string","null"]
assert "PRIVATE_MEMORY_SENTINEL" not in records[0] and "PRIVATE_REASON_SENTINEL" not in records[0]
response={"choices":[{"message":{"role":"assistant","content":[{"type":"reasoning","text":"PRIVATE_REASON_SENTINEL"},{"type":"text","text":"synthetic answer"}],"reasoning_content":"PRIVATE_REASON_SENTINEL","tool_calls":[]},"finish_reason":"stop"}]}
filtered=json.dumps(g["wire_response"](response))
assert "PRIVATE_REASON_SENTINEL" not in filtered and "synthetic answer" in filtered
print(json.dumps({"observer_sha256":hashlib.sha256(source).hexdigest(),"actual_tools":len(tools)-1,"nullable_fixture":True,"request_trace_written":True,"request_chars":len(records[0]),"message_body_omitted":True,"response_reasoning_omitted":True}))
```

## 2026-10-08 增补：提取器和独立连接器的限定复核

本节复核版本：

| 文件 | SHA256 |
|---|---|
| round02_extract.py | `8153a5e6a38ebc083bc0417d86669c008ddebf2a06b333f630a486ece16d5e52` |
| round02_idle_extract.py | `4a393c65788af5a03fd5900d1fd994cf770db203ecf225e1e828a2ccb98e69eb` |
| round02_connector_reads.py | `5c935dd1e73ca7810a21246fc9bfaef18587a2988a35ed93a1ea518738425061` |

### 先保留反例，再界定修订的意义

1. **非法时间戳使“窗口中 provider=0”不能单独推出绝对零调用。** 执行当前 idle 提取器实际 SQL 的内存夹具中，两个正常 UTC 时间、一个 +08:00 时间均正确入选；另一个基线后的 provider.transport 时间为非法字符串，窗口计数仍为 0。当前第 28、41–44 行已另列该坏行，因此能暴露此反例而不会静默隐去。实际 `real-idle-receipts-v3.json` 则记载基线事件 ID 7469 后非法时间戳列表为空；全库 24 条历史异常仍保留，不能说数据库已修好。
2. **空请求 ID 与无关会话误关联的夹具已被修订排除。** messages.request_id 的真实表约束为 `NOT NULL DEFAULT ''`（storage.py:63）。我最初提交的 None 关联反例违反健康表约束，撤回其“可达生产缺陷”归因；不能把它计为已发现业务故障。合法默认空字符串也不能作为跨会话关联键，当前 extract:33 已同时排除 None 和空字符串。内存表遵守该 NOT NULL 约束：插入 NULL 被 SQLite 拒绝；显式空 request_id 的无关 session 99 事件不再进入 R2 session 42 导出；正确非空 request_id 和正确 session_id 的事件仍保留。
3. **精确白名单不是自动隐私批准。** extract:16、28 的 `--allow-user-text` 使用完整字符串成员判断；相同字符串接受，添加前缀或改变大小写拒绝，原有 R2 标记和“确认”等控制词继续允许。第 65 行已改为打印消息 ID，闭合原先“文件脱敏、终端却输出原消息正文”的口径差异。第 30–32、54–61 行仍会导出所选会话的回复、事实及动作，邮箱正则不能消除任意隐私；已有全局记忆混入模型上下文的边界仍适用。保持私有审核后导出，不能仅靠 R2 前缀声明全部内容都是合成。
4. **闲置窗口与实时时长分开。** idle:23–25、45–48 的窗口从本次最后输入 tick 所属的首个采样开始，到 identity 的采集开始 UTC；`max_idle_seconds` 来自真实 GetLastInputInfo 样本。identity.py:60 的 utc 不是备份完成时间。这支持明确采样窗口内的事件关联，不应扩成窗口之前或之后没有任何调用。v1 字符串时间比较返回空的原证据保留为废止版本，不回填成通过；julianday 的 v2/v3 是后续重取结果。

内存复测实际 AST/SQL 结果：精确白名单通过、子串/大小写变体拒绝；合法关联事件仅 7354/7355；混合时间格式入选 101/102/106；基线后非法时间行 103 单列。未打开真实数据库、未运行整个提取器、未启动服务。

### 可复用纯内存提取器反例与修订检查

以下只读取被审脚本，执行选定的实际 AST 与 SQL；数据库全部为 `:memory:`。None 负例专门验证表约束，不能再次作为生产可达输入引用。

```python
import ast,hashlib,json,sqlite3
from pathlib import Path
from types import SimpleNamespace
base=Path("scripts/root_cause_audit")
ext=(base/"round02_extract.py").read_bytes()
idle=(base/"round02_idle_extract.py").read_bytes()
tree=ast.parse(ext)
body=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="main").body
requests=next(n for n in body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="requests" for t in n.targets))
event_init=next(n for n in body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Tuple) and n.targets[0].elts[0].id=="events")
event_loop=next(n for n in body if isinstance(n,ast.For) and any(isinstance(n2,ast.Constant) and isinstance(n2.value,str) and "SELECT * FROM events WHERE id>" in n2.value for n2 in ast.walk(n)))
session_loop=next(n for n in body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=="session")
input_guard=next(n for n in session_loop.body if isinstance(n,ast.If))
checks={}
for label,content,allow,accept in [
 ("exact","synthetic voice line",["synthetic voice line"],True),
 ("substring","prefix synthetic voice line",["synthetic voice line"],False),
 ("case","Synthetic voice line",["synthetic voice line"],False),
 ("r2_marker","[R2-example] synthetic",[],True),
 ("control","确认",[],True)]:
 g={"rows":[{"role":"user","content":content}],"args":SimpleNamespace(allow_user_text=allow),"session":42}
 try:
  exec(compile(ast.Module(body=[input_guard],type_ignores=[]),"<actual-input-guard>","exec"),g)
  actual=True
 except RuntimeError:actual=False
 assert actual==accept
 checks["input_"+label]=actual
with sqlite3.connect(":memory:") as db:
 db.row_factory=sqlite3.Row
 db.executescript("CREATE TABLE messages(id INTEGER,request_id TEXT NOT NULL DEFAULT ''); CREATE TABLE events(id INTEGER,event_type TEXT,payload TEXT);")
 db.execute("INSERT INTO messages(id) VALUES(1)")
 db.execute("INSERT INTO messages VALUES(2,'r2-good')")
 try:
  db.execute("INSERT INTO messages VALUES(3,NULL)")
  raise AssertionError("fixture schema permits NULL unexpectedly")
 except sqlite3.IntegrityError:checks["none_rejected_by_schema"]=True
 fixtures=[
 (7353,"synthetic.unrelated",json.dumps({"request_id":"","session_id":99})),
 (7354,"synthetic.request",json.dumps({"request_id":"r2-good","session_id":42})),
 (7355,"synthetic.session",json.dumps({"session_id":42})),
 (7356,"synthetic.array","[]"),(7357,"synthetic.invalid","invalid")]
 db.executemany("INSERT INTO events VALUES(?,?,?)",fixtures)
 g={"messages":[dict(r) for r in db.execute("SELECT * FROM messages")],"sessions":[42],"db":db,"json":json}
 exec(compile(ast.Module(body=[requests,event_init,event_loop],type_ignores=[]),"<actual-event-filter>","exec"),g)
 checks["requests"]=sorted(g["requests"])
 checks["included_event_ids"]=[r["id"] for r in g["events"]]
 assert checks["included_event_ids"]==[7354,7355]
queries=[n.args[0].value for n in ast.walk(ast.parse(idle)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="execute" and n.args and isinstance(n.args[0],ast.Constant)]
time_query=next(q for q in queries if q.startswith("SELECT *"))
bad_query=next(q for q in queries if q.startswith("SELECT id"))
with sqlite3.connect(":memory:") as db:
 db.row_factory=sqlite3.Row
 db.execute("CREATE TABLE events(id INTEGER,event_type TEXT,created_at TEXT)")
 db.executemany("INSERT INTO events VALUES(?,?,?)",[
 (1,"old.bad","broken-before-baseline"),
 (101,"proactive.idle","2026-10-08 00:00:01"),
 (102,"speech.completed","2026-10-08T00:00:02Z"),
 (103,"provider.transport","broken-after-baseline"),
 (104,"before.window","2026-10-07T23:59:59Z"),
 (105,"after.window","2026-10-08T00:00:11Z"),
 (106,"offset","2026-10-08T08:00:03+08:00")])
 window=[dict(r) for r in db.execute(time_query,("2026-10-08T00:00:00+00:00","2026-10-08T00:00:10Z"))]
 bad=[dict(r) for r in db.execute(bad_query,(100,))]
 checks["julianday_valid_ids"]=[r["id"] for r in window]
 checks["invalid_after_baseline_ids"]=[r["id"] for r in bad]
 checks["valid_window_provider_count"]=sum(r["event_type"]=="provider.transport" for r in window)
 assert checks["julianday_valid_ids"]==[101,102,106]
 assert checks["invalid_after_baseline_ids"]==[103]
 assert checks["valid_window_provider_count"]==0
hashes={n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in ["round02_extract.py","round02_idle_extract.py","round02_connector_reads.py"]}
print(json.dumps({"hashes":hashes,"checks":checks},ensure_ascii=False,indent=2))
```

### 独立连接器脚本只读结论

固定远端业务请求限于已登记 R2 邮件的搜索/读取、合成不存在对象以及 Drive 搜索/已登记 URI 的 resources/read（第 33–44 行）；没有 send/modify/delete/create。脚本读取 .env 并启动自己的 MCP 子进程，设置 npm offline；本地日志/OAuth 刷新等连接器固有副作用不由 `external_mutations: []` 排除。原始回执先存 row（第 80–82 行），再让部署适配器回放同一回执（第 83–95 行），未二次远程执行工具；适配错误、启动错误分别保留，不再丢失前面成功的 raw。

最新第 55–75、99 行记录启动 stdout 的前 20 行长度、hash 和最多 2000 字符前缀，ObservedStream.readline 原样返回字节，委托其余属性；已沿 McpServer.start/_roundtrip 的真实 readline 调用点检查。该前缀只写私有报告，仍须人工检查后才能导出；它能定位非法 stdout 行，不能把 JSONDecodeError 直接解释为 OAuth 无效。第 133–136 行已分列 calls_attempted、transport_errors、adapter_errors、startup_errors，清理行不再算工具案例。

第 103–126 行只清理本次 MCP 根及采集到的 PID+create_time 后代，根等待与后代等待均有 5 秒界限；没有按进程名称广泛终止。剩余边界是 children 枚举遇到 psutil.Error 时第 106–107 行忽略，因此空的 remaining_owned_children 只代表已识别后代的等待结果，不能独立证明所有后代都已列全。此处不是许可扩大清理范围；实际清理完成仍由主执行者核验。

主执行者报告首次独立 connector-reads-01 只有 Drive 3 项完成、Gmail initialize JSONDecodeError；本实例未运行该脚本，不能代签其实际调用或清理。随后下节的天依前台 Gmail 读取成功是另一条证据链；独立启动失败不覆盖为成功，也不否定前台实际读取回执。

### Grader 反例的主执行复现

已只读核对 `round02_grader_counterexamples.py` 沿原 F01 构造数据、调用现有 grader，未启动模型或连接器。主执行者 `-B -m` 运行结果保存在 `evidence/grader-counterexamples.jsonl`：positive PASS、unrelated PASS、1750 PASS、missing FAIL/actual_read。它独立复现 R2-I02/I03；本审查没有修改 grader、旧成绩或验收标准。

## 2026-10-08 增补：Gmail 成功后的 TTS 故障链

这是对既有业务故障归因补充证据，不是业务修复，也不另增加诊断发现计数。只读检查 `gmail-tts-live-trace.json`（308 条，SHA256 `118f35cdefb63e0e292adb5773017d567f40d8ead366d93cdebb9268c2f303dd`）及 v2（309 条，SHA256 `e8a8f1b5f0c6334d7b73f38a537da5d736b1cd4e7399d0e1991dd89dabf3a807`）；v2 相比原版只新增旧 Core 的 seq825 503 异常，末记录为 2026-10-07T16:13:07.953936Z。不能把文件名 v2 或 TTS 新 PID 当作业务故障已修复。

| 可核对节点 | 观察结果及含义 |
|---|---|
| Core 5836 / seq650、652、653 | 确认请求 avatar-chat-1913607 执行已登记 read_email；真实 MCP raw 和适配结果均成功，正文 120−45=75、附件 R2-attachment.txt；不是空回执或独立 Codex 读取冒充天依 |
| Core 5836 / seq658、660 | 模型又提出同一 read_email；不能仅用 calls_used=2 断言第二次远端读取，当前导出中实际 mcp.raw.out 只有一条 |
| Core 5836 / seq686、688 | 该轮最终模型原始 content 已含“已经读取完毕 ✅”，适配后保留；不是 Godot 或 TTS 观察器新造的字符 |
| Core 5836 / seq695、696 | normalize 输入输出相同，含 ✅；voice_text.py:23–27 只执行预设单位/日期替换，并不承诺移除 emoji |
| TTS 14200 / seq84、85 | 首片“已经读取完毕 ✅”；stdout/stderr=gbk、errors=surrogateescape、isatty=false、utf8_mode=0；异常栈明确到 inference_webui.py:844 的目标文本 print，UnicodeEncodeError U+2705 position 7 |
| Core 5836 / seq712 | HTTP 503 转 SpeechUnavailable(retryable=True)，与 speech.py:152–158 一致 |
| TTS 23396 / seq2、3 | 替换后的 TTS 再收到同首片，在同一 GBK print 行触发同异常；换进程但保留该编码条件并未解除问题 |

**首个已证明的运行异常是输出流编码边界。** 模型选择了触发字符、normalize 保留它是上游数据事实；不能直接把“删 emoji”宣布为正确修复。成功 Gmail 回执与正确计算排除“邮件读取失败导致这次语音错误”的解释；确定的 print 栈也不支持把这次首异常归为 GPU 推理、播放器或录音设备故障。它不排除修正 print 后还会遇到其他完整合成问题。

TTS `tts_server.py:224–230` 将任意合成异常计入 lifecycle.failure 并返回 503；Core `speech.py:156、337–378` 将 503 作为可重试，并在原 utterance 仍有效时重试同一 text。因此可确定的文本/日志编码错误被包装成临时不可用，重复首片是已有恢复机制的后果。恢复循环有 deadline/cancel 检查，不能称“无限重试”。308 条导出中有 66 条 client.in、55 条 client.exception，但 sidecar.in 仅 13 条；只有 6 条 sidecar.exception 明确为这类编码异常。v2 新增一条 client.exception。不可把全部 503 算成 GPU 合成次数，loading/未就绪也会在进入 sidecar 前返回 503（tts_server.py:181–185）。

### 确切文本的零外部调用反事实

本实例独立读取部署的 inference_webui.py，SHA256 `4fbbe2b1a4ef43fab3c122af291f4ec8b6ae274d004f7ded69de9883acfdd72c`，仅提取第 844 行 print AST；用现场 text 和 stdout_errors 在 BytesIO/TextIOWrapper 中执行。speech.py SHA256 `31b77cd18b09efb68db48a2725fc44dbe97f7c81d9679657c7b46817dd9d4fbc` 的 HTTP 分类函数也仅用抛出合成 HTTPError 的替身调用。

| 输入/输出条件 | 独立结果 |
|---|---|
| 原首片 + GBK / surrogateescape | UnicodeEncodeError，start=7/end=8，匹配现场 U+2705 |
| 只移除 ✅ 的首片 + 同 GBK | print 成功 |
| 原首片 + UTF-8 / surrogateescape | print 成功 |
| 实际 SpeechClient.synthesize，假 400 / 假 503 | retryable=False / True |

与主执行者 `evidence/tts-exact-counterfactual.json` 的结果一致。没有导入 GPT-SoVITS、调用实际 synth、使用 GPU、启动子进程或网络。UTF-8 print 通过**不是**完整 TTS 合成通过。

```python
import ast,contextlib,hashlib,io,json,logging,urllib.error
from pathlib import Path
from types import SimpleNamespace
trace_path=Path("docs/assessments/root-cause-audit/round-02/evidence/gmail-tts-live-trace.json")
trace=json.loads(trace_path.read_text(encoding="utf-8"))
tts=Path("C:/Users/26052/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/tianyi-tts")
source=(tts/"GPT-SoVITS/GPT_SoVITS/inference_webui.py").read_bytes()
node=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=="print" and "实际输入的目标文本:" in ast.unparse(n))
code=compile(ast.Module(body=[node],type_ignores=[]),"<deployed-print>","exec")
record=next(r for r in trace["records"] if r["stage"]=="tts.sidecar.in" and r["trace"].get("request_id")=="avatar-chat-1913607")
original=record["data"]["text"]
assert original=="已经读取完毕 ✅"
cases=[]
for text,encoding in [(original,"gbk"),(original.replace("✅","").rstrip(),"gbk"),(original,"utf-8")]:
 raw=io.BytesIO()
 stream=io.TextIOWrapper(raw,encoding=encoding,errors=record["data"]["stdout_errors"])
 result={"text":text,"encoding":encoding,"errors":stream.errors}
 try:
  with contextlib.redirect_stdout(stream):
   exec(code,{"text":text,"i18n":lambda s:s})
  stream.flush();result["status"]="printed"
 except UnicodeEncodeError as exc:
  result.update(status=type(exc).__name__,start=exc.start,end=exc.end,reason=exc.reason)
 cases.append(result)
assert [r["status"] for r in cases]==["UnicodeEncodeError","printed","printed"]
assert cases[0]["start"]==7 and cases[0]["end"]==8
speech_path=Path("services/agent-core/agent_core/speech.py")
speech_source=speech_path.read_bytes()
tree=ast.parse(speech_source)
error=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="SpeechUnavailable")
client=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="SpeechClient")
synth=next(n for n in client.body if isinstance(n,ast.FunctionDef) and n.name=="synthesize")
g={"urllib":SimpleNamespace(error=urllib.error),"json":json,"logger":logging.getLogger("in-memory-review")}
exec(compile(ast.Module(body=[error,synth],type_ignores=[]),"<actual-speech-classification>","exec"),g)
out=[]
for status in (400,503):
 def fail(*args,**kwargs):raise urllib.error.HTTPError("http://synthetic.invalid",status,"synthetic",None,None)
 g["_post_json"]=fail
 try:
  g["synthesize"](SimpleNamespace(base_url="http://synthetic.invalid",synth_timeout=1,invalidate_health=lambda:None),original)
 except g["SpeechUnavailable"] as exc:out.append({"status":status,"retryable":exc.retryable})
assert out==[{"status":400,"retryable":False},{"status":503,"retryable":True}]
print(json.dumps({"trace_sha256":hashlib.sha256(trace_path.read_bytes()).hexdigest(),"source_sha256":hashlib.sha256(source).hexdigest(),"line":node.lineno,"speech_sha256":hashlib.sha256(speech_source).hexdigest(),"print_cases":cases,"http_classification":out,"no_network_gpu_process_calls":True},ensure_ascii=False,indent=2))
```

### 故障后快照、恢复代际与尚未闭合的验收

只读故障后私有 identity 元数据：采集开始 2026-10-07T16:12:19.230971Z，status=captured、identity_stable/same_physical_file/watermarks_equal 均 true，事件水位 7631、快照 SHA256 `66e6093312de2d0286b9f642c1503586ab686dc9198eaa56e6f5bd918e327930`。同一时刻 Core PID 5836 的 speechPending=true、available=false；TTS PID 23396 phase=loading、synthCount=0。这些健康端点先后读取，不是跨进程原子快照；不能把该时点 loading 与稍后 23396 seq3 的编码异常压成同一瞬间或矛盾结果。

主执行者随后报告通过正常 Alt+F4 结束旧 Godot/Core/TTS，16:13 UTC 由正式链重新启动；本实例没有操作窗口或探测进程，因此**正常退出/新 PID 启动及可用性恢复属于主执行者现场证据，未由本实例重新执行验收**。新链应单列 PID+启动时间、诊断版本、近期合成输入/回执，避免把 5836 的旧 pending、23396 的旧失败或旧请求缓存归为新链结果。已有 successful action ledger 与文本答案也不等于失败答案已经完整播完；原 trace 的 human_audio=not individually confirmed 必须保留，不能借用此前闲置提醒的“听到且清楚”。

追加只读恢复证据：tts-recovered-short.json 的 avatar-chat-242243 分属新 Core23404/TTS30624；Core seq40、47 两片 speech.receipt 均 failed=false/interrupted=false，seq51 speech.completed，文件仍标 human_audio=not individually confirmed。这证明新代际普通中文链路的播放回执恢复；不证明旧含✅答案已播完、编码条件改变或故障修复。

限定结论：所审提取器修订可用于其登记范围的诊断；连接器脚本静态检查未发现越界业务写入，但运行和清理结果仍分列取证。TTS 的日志编码首异常及 503 重试传播得到现场栈和独立内存反事实支持，业务修复与修复后完整播放尚未发生。覆盖逐项复核见同目录 COVERAGE_REVIEW.md/JSON，不能用本节的单个 Gmail 读取或闲置提醒升级其他工具和分支。


## B01与隔离反例证据的独立复核（RC02、R2-RC14–17）

本节只读四份既有证据和实现；未操作桌面、浏览器、Core、MCP、TTS、模型或网络。唯一新执行是从指定main.py提取一个条件表达式和一条字符串赋值的纯内存AST对照，不导入或调用Core。先向主执行者报告下述反例，再写本节。

### [MEDIUM] R2-I09：无待办的“继续”也注入“仍待确认”，不能把伪待办单独归给模型

精确代码：services/agent-core/agent_core/main.py:1490条件是“pending非空，或者task存在且text匹配继续”；:1494给这两种状态无区别地赋值confirm_note：“既有操作仍待确认，本条消息没有授予执行权限。保留所有待办；确认必须绑定展示的参数版本。” :1538将confirm_note放入extra_parts，:1542传给harness.build_messages，harness.py:173再加入system正文。存在task不保证存在待办，此分支没有用pending再次保护该文本。

本次实际输入条件全部有证据：browser-group1-trace.json:23832，Core23404 seq1242，request avatar-chat-1798932，text="继续"、before.task.id=avatar-chat-1226122、before.pending_head=null。seq1249请求发出；seq1252原始模型content随后称browser_find待确认，tool_calls=null；seq1254适配为空数组，seq1268最终仍pending_head=null，calls_used=6/18、rounds_used=7/9。因此适配器没有丢弃真实提案可以成立；**“伪待办首次语义偏离只在模型输出”不成立：宿主此前已经构造不实的待确认状态提示。**

独立纯内存实际对照取生产main.py字节，SHA256 e64a26e426b1cf3c00447f2dc39fc775241114498e1c257ebdd86e3e66d3d3f5，与edge-counterfactuals-01所记源hash相同。只编译:1490条件和:1494赋值：
- pending=[]、task存在、text="继续"：进入分支，生成上述待确认提示。
- pending=[合成action]、task存在、text="继续"：生成完全相同提示，这是有待办的正常对照。
- pending=[]、task存在、text="R2新的任务"：该分支不进入，confirm_note保持空。

此对照证明宿主状态描述错误，不证明该字符串单独足以诱发当前具体输出；任务历史、其他system段落、模型选择仍可共同影响。原ROOT_CAUSES.md:8的“无待办确认重建task/cache”是另一个已证分支；这里是“无待办继续保留task却注入待确认提示”，不得混为同一个触发器。建议主执行将:23的首次偏离边界修正并保留模型raw证据；不要先改提示词后重新跑一次成功就宣称根因消失。

以下是已验证的零外部调用复现正文（从源AST提取，不执行Core初始化）：

```python
import ast,hashlib,json,re
from pathlib import Path
p=Path("C:/Users/26052/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/anime-agent-mvp/services/agent-core/agent_core/main.py")
raw=p.read_bytes()
tree=ast.parse(raw)
handler=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=="_handle_chat_locked")
branch=next(n for n in ast.walk(handler) if isinstance(n,ast.If) and n.lineno==1490)
assignment=next(n for n in branch.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="confirm_note" for t in n.targets))
test=compile(ast.Expression(body=branch.test),str(p),"eval")
body=compile(ast.Module(body=[assignment],type_ignores=[]),str(p),"exec")
cases=[]
for label,pending,task,text in [("continue_without_pending",[],{"id":"R2-task"},"继续"),("continue_with_pending",[{"id":"R2-action"}],{"id":"R2-task"},"继续"),("new_without_pending",[],{"id":"R2-task"},"R2新的任务")]:
 ns={"re":re,"pending":pending,"task":task,"text":text,"confirm_note":""}
 selected=bool(eval(test,ns))
 if selected:exec(body,ns)
 cases.append({"case":label,"selected":selected,"confirm_note":ns["confirm_note"]})
print(json.dumps({"source_sha256":hashlib.sha256(raw).hexdigest(),"branch_line":branch.lineno,"assignment_line":assignment.lineno,"isolated_condition_and_assignment_only":True,"cases":cases},ensure_ascii=False))
d=json.loads(Path("docs/assessments/root-cause-audit/round-02/evidence/browser-group1-trace.json").read_text(encoding="utf-8"))
for r in d["records"]:
 if r.get("trace",{}).get("request_id")=="avatar-chat-1798932" and r["stage"]=="input":
  print(json.dumps({"input_seq":r["seq"],"text":r["data"]["text"],"task":r["data"]["before"]["task"]["id"],"pending":r["data"]["before"]["pending_head"]},ensure_ascii=False))

```

### B01对照的其他反例与计数范围

- browser-group1-state.json是8个会话360–367的事务快照摘录，46条消息、512事件、9个actions，http_attempts_observed=43；它不是会话366/B01专属切片。browser-group1-trace.json只选8个明确request，1274记录，13个唯一exchange的request/response一一配对，5个mcp.raw.out。43、9不能用于B01调用次数/成功率。task.calls_used还包括提案、去重回执，不等于远端执行次数。
- 单步CF不是完整成功：1986553的seq1318产生browser_find提案，seq1335无工具总结返回未闭合JSON且finish_reason=stop；seq1341格式fallback，seq1352原生待办仍正确存在。此样本说明“提出真实动作”与“可展示答复解析”应分别验收；它不定位旧单个左花括号的首次来源。
- 2081817的seq1417真实find返回2匹配；seq1423原始content前文说已执行，JSON reply却说等待执行。seq1428解析器选择JSON reply并舍弃前文，delivery沿用该reply。因此矛盾已存在raw输出，但“parse完全未改变内容”不准确。解析器按既有合同选择reply，尚不能据此把状态误报的最初产生归给parser。
- seq1121页面求值读回title="R2 合成审计页面 V3"、starColor="rgb(204, 0, 0)"及auditState.width/height=1024/768；numericValue其实是全页innerText，并非独立数值字段。find后的模型把h1“R2 合成画面 V3”说成页面标题，不能把其自然语言总结全部判正确。
- navigate seq419只返回snapshot文件链接；独立snapshot seq904确实含完整YAML正文，所以“当前浏览器始终只能拿链接”已被反例否定。但这不实现独立resources/read，也不证明其他resource工具正文可达。
- evaluate中的hover="未悬停"、networkCount=0、clicks全0、multi=[]证明当时页面初态；不是hover、network、click、多选能力成功。B01没有hover/console工具执行，console的2 errors只是摘要，不知道两条具体内容，不能据此判定全部来自故意合成error。

### context/hash确证范围与缺口

失败的seq1249与单步seq1316均发105工具，工具名含browser_find，tools_sha256同为f8aad7d1c0222c04702a63df333343ab26dbb2f79c00f3ce20926fddc06c5c5a。这排除这两次未暴露该工具的解释；不表示105工具都测过。四个tools_count=0请求是待确认后调用complete的总结路径，不能与工具能力轮混在一起计算模型拒绝使用工具的比例。

两次消息完全不同：seq1249的system长度8825、messages_bytes=22236、messages_sha256=0877ec8f7a013d5c8bfe9af597e347079e01e7a52b0652bdd0818d69dd1366bf；seq1316为3282/16244/67327b8e6e1873a7c9b8411c9562268af3fcde642502cac178a17069668fc6c8，消息shape数量12→14。新任务还重建task/cache并重置预算，继承同会话旧历史，不能称唯一变量是“单步措辞”或“告诉模型用工具”。

round02_observer.py:122–134记录的是解析后messages的规范JSON hash/bytes和role/keys/content长度，不是可还原正文，也不是整份HTTP字节hash。整组hash不同只能证明不相等，不能定位哪个system子段有错误，不能证明没有global memory或某条回执已按正确语义发送。source+输入足以复现I09分支，但本报告没有从私有wire正文反解hash，也未打开全局记忆。

response的raw_bytes_sha256关联原始响应字节，而公开payload经过私有reasoning过滤和导出路径/邮箱脱敏，不能对公开payload重新json.dumps后宣称匹配原字节hash。trace sources的prefix_sha256仅绑定各私有日志完整行前缀（导出器:19–27），不是完整日志终态或选中1274记录的hash。公开导出文件自身hash另列；未重新读取私有前缀来冒称完成了完整字节校验。

若主执行需要更强归因，可给task_context、confirm_note、合成receipt、召回计数分别记录来源/规范hash/长度，R2明确合成段落可白名单保留；禁止因本缺口自动记录完整私有记忆或reasoning。首先复现宿主纯函数分支即可，不需要外部模型追加花费。

### R2-RC14–17及四项诊断修订的限定复核

| 项目 | 可支持的因果结论 | 不可扩大之处 |
|---|---|---|
| RC14 / edge read-mixed-utf8 | 正常首字节41得到next_offset65535并保留甲；只改ff后65536、甲变3个替代字符。实际read_file的首个UnicodeDecodeError分支解释差异。 | 仅已有坏UTF-8且合法多字节字符跨页的输入；不推翻有效UTF-8跨页正常控制。 |
| RC15 / quoted-path | 同白名单和其余参数，无空格目录一次mock且argv正确；带空格目录0次、basename r2误拒。 | subprocess全mock，证明分词拒绝，不证明真实可执行文件启动、权限或超时终止。 |
| RC16 / null与类型 | 12个实际方法AST适配观察及5个parser观察保留了None字符串、空content、数字字符串、ProviderError/AttributeError差异；正常字符串控制存在。 | 脚本自定义异常类与TRANSPORT_ERRORS=(OSError,)替身，未测试网络错误分类；不是供应商全协议验证，也不证明本轮真实模型发过null。reply空串转格式提示与null不同。 |
| RC17 / replace失败 | local-branches-01:208保留返回错误、原目标未变且六字节tmp残留。实现tools.py:261–265写tmp后replace异常直接返回，与现象吻合。 | matched=true只表示观察判据符合，不能说write_file自行清理、崩溃安全/全部原子性通过或文件系统真实PermissionError全部等价。 |

主执行报告独立Python reviewer提出的四项修订已在运行前处理；本实例源码复核：
1. local_branches.py:23、edge_counterfactuals.py:29在agent_core导入前设sys.dont_write_bytecode=True；随后核对module.__file__.resolve与所选实现路径。这样避免本次导入新增业务pyc且拒绝错包；不应称它测了真实Core内存代码/SQLite句柄身份。两证据所列tools/storage（edge另含harness/main）源hash与本实例只读生产路径字节一致。
2. local_branches.py:167–175在sweep后重查会话、25条A消息及B唯一正文；local-branches-01:491保存listed_after、messages_a=25、B正文。修复了只看sweep前列表无法判断误删的盲区。
3. :130–146补ok False、错误标记、nonzero返回码和stderr、成功argv、完整kwargs（shell=False、timeout=30、capture_output/text=True）语义断言。此次输出29条matched并不等于29项能力全部PASS。截断断言仍以startswith/存在“截断”判断，但本实例只读实际输出精确等于4000个R加既定后缀，未为这点重跑。
4. :91–99保存replace失败后的tmp名/大小并标明清理责任属于独立harness；因此temporary_objects_cleaned仅表示TemporaryDirectory生命周期结束，不能归功于write_file。该修订将真实缺陷保留为RC17，没有用清理掩盖它。

edge脚本SHA256 1bc98737569cc8cd401693e584687ac247e16d31379217397489b7a57139ffde与edge输出内script_sha256相同。当前local脚本SHA256 0eb6f9072e05e9b6906adf64c9300124d537de85246487889e0dff57b00b3f0f，但local输出没有script_sha256：可确认其新增字段和当前源码相符，不能仅凭现在的hash证明运行时脚本逐字节身份。无需因此重跑已确定业务用例；若另有运行命令/脚本归档由主执行关联，后续诊断再记录执行时hash。

本节文件hash：browser-group1-trace=87b8043bf3b892956e087d7a30fde2df88c31bcfaa3ccdd7a11dc20c5b4f3c61；browser-group1-state=4282c7407c5d3a1a90d36d32f44025f2d17c3d1456aa31161e8fd41021f402f0；edge-counterfactuals-01=9cf356c6e33c3ee31b802f951d80f64bd6bf7144748ca91dff2504977bdb2f5d；local-branches-01=89b9a31ded3c9e74649788ee4dd8609cabfb68424e20037d4fd1549848824893。人工听感仍按文件not confirmed保留。

主执行随后提供round02_continuation_counterfactual.py，SHA256 975b8615d6e13ab88de4bb1010d3e644c25f243e0240df0cc75fc874af8fa3b1。本实例逐行只读审查：结构筛选唯一elif、要求literal note、仅eval已审条件且禁用builtins，五合成case排除approve/decline/edit前置分支；只读源和x模式写新报告，无Core导入/数据库/网络。无新增代码发现，APPROVE仅限这个诊断脚本；主执行负责运行。false_pending_statement依赖当前已审note的含义，未来若更改状态文案不能原样当通用修复验收器。

## 历史气泡与实时气泡时间差的限定只读审查

### [MEDIUM] R2-I10候选：历史截取UTC时分，实时使用本地墙钟

主执行者报告：正常重启恢复会话368后，旧回复显示17:26/17:28，新实时输入显示01:44，本地为UTC+8，真实间隔约18分钟。本实例没有查看桌面、读取该会话的私人数据库或重启Godot；以下结论是**已查明的代码路径差异，可静态解释观察，但该两条具体消息的逐行身份仍依赖主执行现场证据**。

确切路径：
1. services/agent-core/agent_core/storage.py:64把messages.created_at默认设为SQLite CURRENT_TIMESTAMP（UTC）；:232–234写消息不显式传created_at，采用此默认值。:210–217的load_history将原字段字符串原样作为createdAt，不转本地时区。
2. main.py:2044–2062处理chat.history.request并发送messages；Godot runtime.gd:743–745转到interaction_ui.on_chat_history。interaction_ui.gd:163调用_short_time(createdAt)，:1146–1149只对长度>=16的字符串取substr(11,5)。注释“取时分即可”省略了时区转换；:1046–1054把该文字原样放入气泡。
3. 实时用户输入在interaction_ui.gd:1335调用add_message；实时assistant在runtime.gd:733–735也调用它。add_message的interaction_ui.gd:177取Time.get_time_string_from_system().substr(0,5)，即当前本地墙钟，不使用该消息的createdAt或服务器event.timestamp。两条入口传到同一_append_bubble，却采用不同时间基准。
4. 会话列表卡片另走interaction_ui.gd:735–737，先把UTC更新时间加_tz_bias_sec再格式化；:665–668定义本地偏移。所以“回忆列表卡片已做UTC→local”不能反证聊天气泡没有混用。verify_session_ui.gd:113–138只查日期分组/搜索等，不断言气泡时间；test_storage.py:117–124只查createdAt存在，不验证时区显示。

最小合成反例与正常对照（本实例仅字符/日期推演，未运行Godot）：
- 历史createdAt="2026-10-07 17:26:00"，当前实现_short_time必给17:26；UTC+8对应的本地时间应为2026-10-08 01:26。新输入01:44距它18分钟；17:28那条对应01:28，距新输入16分钟。日期跨日被仅显示HH:mm掩盖。
- 同一瞬间2026-10-07 17:44 UTC的消息，实时在UTC+8应标01:44；保存后重新加载历史会取17:44。该设计可在受控Godot时间替身/纯合成history中检验，无需私人数据库或真实模型。
- 正常对照时区UTC+0，两入口都可能显示17:44，缺陷暂不显现；不是证明所有时区都正确。短createdAt返回空，长度>=16的非法字符串也会机械截取，这只是格式校验边界，不能把已有24个非法事件时间列直接归为本气泡缺陷。

因此无需假定旧消息真的相差8小时、恢复了错误历史、系统时钟跳变或SQLite发生新损坏，就已有充分的显示层机制解释。也不能仅凭这个静态机制断定现场两条具体记录肯定来自UTC默认值：旧导入数据/人工写入的timestamp可能采用别的格式；须由主执行已有消息身份/createdAt记录对齐，不能猜私人内容。实时使用渲染/接收时刻而历史使用存储时刻还允许额外处理延迟，两者差值不能一律当固定8小时。

被审生产磁盘文件与审计副本相同：interaction_ui.gd SHA256 00f8c9e1f4ee0de019835cf0592f2b1fab4bf09ae228dff6157842bdbc552401；runtime.gd 0ad46f150734814e1de2e7deb12799dfd9637cbdff041a80ce5f6ae715519295；storage.py 91450c232cacdd05d7fb7835e5ee58812da024d0d446b4580905ff59b64fc06b。仅证明读取到的磁盘实现，没有重新鉴定当前Godot内存/导出包。业务代码未改。若后续修复，应让历史与实时采用同一明确时区合同，不能只给历史字符串硬加8小时而忽略日期、其他时区和格式。

### I09主执行复现与反例的适用边界补记

continuation-counterfactual-01.json已由主执行运行5个合成case：无pending+继续/go on为两个false_pending_statement，真实pending+继续为正常对照，无task/普通新任务不进入。文件SHA256 a496c461ac06b03359c5b97797bb24e374cf6cf3149d38ef5c0f2ca92d2cbadb，内嵌source/script hash分别与前节生产源码及已审975b8615…脚本一致。ROOT_CAUSES.md:23–30已修正“唯一首次偏离在模型”的说法，并保留多变量对照限制；这是反例处置完成，未修业务缺陷。

B02另有反例，不能用I09统包：browser-group2-trace.json中request avatar-chat-3514020的input seq2384是“确认”、已有真实console_messages待办并绑定票据；seq2398原始回答在info执行成功后又声称level=error待确认，tool_calls=null，seq2414 pending_head=null。该请求走main.py:1471–1477的approve真实回执分支，不是:1490–1494无待办继续分支。I09不应被描述为所有伪待办的充分解释；这轮后续错误仍需按原始响应、任务/历史上下文及交付分别归因。以上仅查既有导出，未追加模型调用。

### 时间观察归属与未启用分类续记

主执行随后明确补充：同一恢复会话面板的历史17:26与新输入“我在”01:44已由其现场截图观察确认。本实例只读定位的UTC截取/本地实时格式足以解释该显示组合；具体记录createdAt与渲染身份尚未由本实例读取，保留“静态机制+主执行现场观察”层次，不升级为本实例亲测，也不与数据库结构异常合并归因。

原10项未启用/未实现及NI-open_app、AD03正式factory未装配reload_config的限定结论，见COVERAGE_REVIEW.md“未启用与未实现项的分类闭合”。分类可闭合不计功能成功；其中VO05最新Core代际需引用既有health/启动事件禁用回执，不为验收打开监听。NI06已有Tauri代码、NI07已有交付模板、AD03已有类级重载实现，这三个“有代码但未启用/未认证”的反例均保留，不能泛化写成无实现。

新增wiring诊断脚本79767bd4…的只读审查与主执行7项隔离结果也已记录于覆盖审查；生产main为v3 overlay代际7af0c89c…，factory规范AST与审计副本一致。此处没有重新审查或批准完整observer-v3，也没有现场换key、查询窗口或启动服务。初审仍开放，本节没有新增整体批准。

## 本次 Review Summary

编号 R2-I01–I10 共10组MEDIUM：3组既有覆盖/评测问题、I09宿主状态提示错误及I10时间显示候选仍开放，5组诊断问题按上述范围闭合；不把关闭诊断阻断计为总体审计通过。I10已定位代码差异，具体现场消息身份仍由主执行者对齐。

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 5 open / 5 closed | includes I10 static display candidate; live attribution pending |
| LOW | 0 | pass |

Verdict: APPROVE（仅限上述 hash 的受控诊断代码候选）— 现场安装、复现与恢复仍由主执行者验收；总体初审仍开放，未给出总体批准。
