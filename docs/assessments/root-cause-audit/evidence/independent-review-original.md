# Independent fresh-context review — Sagan

Read-only review, no business changes. Original returned findings; response/verification tracked separately.

集中结论：**RC02/RC03 的宿主机制已由隔离反例证实；RC01 的数据异常成立，但“包重定向→WAL→损坏→任务失败”因果链尚未闭合。** 新增 desktop-11/12 又反驳了“无待办后任务必然无法恢复”，并证实交付缺口不只影响只读工具。

本轮未修改文件，未调用真实连接器、UI、模型或私库。

## 一、RC01：异常证据成立，损坏来源与任务因果仍待验证

### 已证实与不能扩大之处

[ROOT_CAUSES.md:3](../../../../docs/assessments/root-cause-audit/ROOT_CAUSES.md:3) 对应证据中：

- `quick_check` 确实报告 `Tree 4 page 4 cell 14: Rowid 672 out of order`。
- **严格说，被独立证明异常的是所检查的数据库视图／副本。** 当前 [inventory.py:20](../../../../scripts/root_cause_audit/inventory.py:20) 通过 `db_connect` 获得复制视图，再运行检查；缺少源文件身份与一致快照证明时，“活动原库已由这次检查直接证明损坏”仍偏强。
- 同名路径数据不同支持“数据身份分裂”，不单独证明 Windows 包重定向就是损坏原因。
- `events` 中角色名、请求 ID 占据异常列是另一类逻辑异常。错误写入／恢复映射也是替代解释，不能直接认定为上述 B-tree 异常造成。
- `runtime-start` 的水位为7016、最后 MCP 启动6990／10月4日；`inventory-start` 为6444／10月7日。没有统一数据身份前不能按事件 ID 拼接成一条时间线。
- 磁盘源码哈希不证明进程正在执行该版本；`runtime-start` 缺进程创建时间，注明 `psutil unavailable`。

### 快照校验的两个已复现反例

位置：[probe.py:39](../../../../scripts/root_cause_audit/probe.py:39)。

1. **迟到 WAL**：首次检查 WAL 不存在，随后出现；末次校验只遍历首次存在的文件，不会发现新 WAL。
2. **A→B→A**：首次源哈希为A，复制取得B，末次源又是A；前后源哈希一致，但目标副本不同。代码没有校验目标哈希。

我用模拟文件系统执行原 `db_connect`，两种情况均被接受。这**否定校验的充分性，不证明现场实际发生过这两种竞态，也不证明复制导致了损坏**。

最小逻辑复现：

```python
from hashlib import sha256
h = lambda b: sha256(b).hexdigest()

# 迟到 WAL：对应 probe.py 末次只遍历 before 的键。
source = {"": b"MAIN"}
before = {k: h(v) for k, v in source.items()}
copied = dict(source)
source["-wal"] = b"NEW COMMITTED WAL"
assert before == {k: h(source[k]) for k in before}
assert "-wal" not in copied

# A→B→A：前后源哈希相等不保证复制内容。
source = b"A"
before = h(source)
source = b"B"
copied = source
source = b"A"
assert before == h(source)
assert copied != source
```

另外两处取证漏洞：

- [probe.py:124](../../../../scripts/root_cause_audit/probe.py:124)：显式 `--request` 先加入 `allowed`，但事件关联 ID 随后又从实际消息重建。**消息行缺失时，仅带 request_id 的事件仍会漏掉**；不能据此断言没有 HTTP 调用。
- `probe.py:129` 用字符串比较时间。下面的错误时间值也会入选：

```python
import sqlite3
db = sqlite3.connect(":memory:")
assert db.execute(
    "select ? >= ?",
    ("avatar-chat-1735379", "2026-10-07 11:01:00")
).fetchone()[0] == 1

allowed = {"explicit-request"}
messages = []  # 该消息行未进入快照
ids = {m["request_id"] for m in messages}
assert "explicit-request" not in ids
```

## 二、RC02：文字待办为空成立，“上下文全部丢失”过强

### 现场反例及新对照

| 场景 | 可核对事实 | 判定 |
|---|---|---|
| RA-F01，desktop-03 | 两次 `read_file` 成功记录；助手汇总200元／5人后口头询问写入；`actions=[]` | 没有形成原生待办 |
| desktop-04 | 用户“确认”后，回复先称已写入、又承认未读未写；仍无动作 | 虚报／自相矛盾未被交付层拦住 |
| RA-F02，desktop-05 | 用户明确要求调用工具、等待宿主卡，助手仍用文字模拟卡；`actions=[]` | 不只是用户指令不明确 |
| RA-G02C，desktop-10，会话350 | 明确 `issue_write(method=create)`，仍文字待确认、`actions=[]` | 新会话也复现；削弱“仅旧会话污染”解释 |
| desktop-11/12 | 第一次“确认”才产生真正待办；第二次“确认”获得创建成功回执 | **反驳“重建 task 后原任务必然不可恢复”** |

新会话证据：[desktop-10.json:14](../../../../docs/assessments/root-cause-audit/evidence/desktop-10.json:14)。

### 已证实机制

- [agent_loop.py:107](../../../../services/agent-core/agent_core/agent_loop.py:107)：没有 `tool_calls` 就接受文字并结束该循环；不会把“待确认操作”文字转成动作。
- [main.py:1337](../../../../services/agent-core/agent_core/main.py:1337)：真正待办由 `book.propose` 建立，不由自然语言建立。
- [main.py:1466](../../../../services/agent-core/agent_core/main.py:1466)：无 pending 时，“确认”不进入确认执行分支。
- `main.py:1495–1509`：创建新 task，`intent="确认"`，替换 `ResultPages`，调用计数从零开始。
- **但 `main.py:1504` 仍加载聊天历史，`harness.py:177–193` 保留原请求和助手摘要。**

执行原任务状态语句的隔离结果：

| 无待办时输入 | task | 既有调用计数 | 旧结果引用 | 原请求与助手摘要 |
|---|---|---:|---|---|
| 确认 | 重建，intent＝确认 | 2→0 | 丢失 | 仍在 |
| 继续 | 保留 | 2→2 | 保留 | 仍在 |

所以应表述为：**任务身份、预算与工具结果缓存连续性丢失；不等于所有聊天上下文消失。**

当前没有原始 wire，不能断言现场首偏离一定来自模型而非网关／适配器。`desktop-03..05` 也没有成功读取的完整参数、正文及目标文件前后哈希；“没有写入动作证据”和“独立检查目标文件确实不存在”应分开。

### V1 既有反例已排除“必须依赖当前损坏库”

[REVIEW.md:46](../../../../docs/assessments/harness-v1/REVIEW.md:46) 所指原证据：

- `repair-01-ds-M05-r1`：原始 HTTP 响应就只有“先准备发送请求”，`tool_calls:null`；attempts、executions、actions均为空，使用隔离夹具、未测试真实外部服务。
- `repair-01-ds-M04-r1`：第三轮真实请求正文仍含 `new@example.invalid`，模型却再次索要地址。**信息在请求中但未被使用**，不能解释成信息必然没传入。

## 三、RC03：成功回执与有效交付之间确有缺口

### RA-G01 不是缺正文，也不是纯 UI 渲染问题

[desktop-06.json](../../../../docs/assessments/root-cause-audit/evidence/desktop-06.json) 中：

- 原生待办、确认、成功回执均存在。
- 回执包装7354字符；其中 README 正文7001字符，已与 `d3ed6d68…:README.md` 完全比对一致。
- 保存的助手消息1274本身就是 `{`，不只是屏幕显示异常。

机制：

- [harness.py:275](../../../../services/agent-core/agent_core/harness.py:275)：fallback只检测若干带引号的字段名；裸 `{` 原样通过。
- 合法 JSON `{"reply":"{"}` 也得到 `{`。因此不能仅凭最终字符判定“原始 JSON 被截断”。
- [main.py:864](../../../../services/agent-core/agent_core/main.py:864)：成功且未归类为变更操作时，直接返回 fallback。
- `main.py:858` 的600字符详情裁剪，在这条分支根本没有作为最终回复返回，不能解释 `{`。
- [grader.py:50](../../../../scripts/harness_v1/grader.py:50) 的 `display_is_not_raw_json` 也会让 `{` 通过。**只是该检查误通过，不代表整个用例会通过。**

### 新增：`issue_write` 确认存在变更分类遗漏

[desktop-12.json](../../../../docs/assessments/root-cause-audit/evidence/desktop-12.json) 记录成功回执 `id=5744447898`、`…/issues/1`，但最终仅表示“这就执行”。

离线实测：

| 工具／method | 是否保留“这就执行”原文 |
|---|---|
| `issue_write / create` | 是 |
| `issue_write / update` | 是 |
| `issue_write / read` | 是，但这是**非法参数负对照** |
| `issue_read / get` | 是，合法读取对照 |
| `write_file` 成功控制组 | 否，返回执行记录 |

`issue_write` schema只有 `create/update`，不能把 `read` 描述为真实支持的操作。代码完全没有读取 method，工具名也不命中六种字符串，因此**误归入“不需要回执覆盖”的分支已证实**，不再只是“可能”。

这是交付分类缺陷，不是授权绕过；本次没有发出任何真实创建请求。

## 四、可直接运行的核心最小复现

在[仓库根目录](<SOURCE>)用独立 Python 执行；只读源码，使用 `-I -B`，不导入 Core、不创建文件。下面先验证解析、空动作和交付，再验证任务重置。

```python
import ast, asyncio, json, re, sys, types
from pathlib import Path
from types import SimpleNamespace as NS

core = Path.cwd() / "services/agent-core/agent_core"

def load_isolated(name):
    tree = ast.parse((core / f"{name}.py").read_text(encoding="utf-8"))
    # harness 的歌曲库不参与本测试；其余保留原定义。
    tree.body = [
        n for n in tree.body
        if not (isinstance(n, ast.ImportFrom) and n.level)
    ]
    mod = types.ModuleType("audit_" + name)
    sys.modules[mod.__name__] = mod
    exec(compile(tree, name, "exec"), mod.__dict__)
    return mod

H = load_isolated("harness")
L = load_isolated("agent_loop")
P = load_isolated("result_pages")
tree = ast.parse((core / "main.py").read_text(encoding="utf-8"))

# 只提取交付函数，不执行 main.py 顶层。
fn = next(n for n in tree.body
          if isinstance(n, ast.FunctionDef)
          and n.name == "_receipt_delivery")
rows = []
book = NS(records={}, task_items=lambda *_: list(rows),
          cancel=lambda *_: [], context=lambda *_: [])
ns = dict(json=json, re=re, _actions=lambda: book)
exec(compile(ast.Module(body=[fn], type_ignores=[]), "receipt", "exec"), ns)
deliver = ns["_receipt_delivery"]

assert H.CharacterHarness.parse_reply("{").reply == "{"
assert H.CharacterHarness.parse_reply('{"reply":"{"}').reply == "{"

# 空动作既不生成待办，也不纠正口头完成声明。
for text in ("待确认操作：write_file", "已经写入了"):
    assert deliver(1, {"id": "t"}, text) == text

class Provider:
    async def complete_with_tools(self, *_):
        return {"content": "待确认操作：write_file", "tool_calls": []}

async def forbidden(*_):
    raise AssertionError("不应调用 executor")

result = asyncio.run(L.run_agent_loop(
    Provider(), [], [{"type": "function"}], forbidden))
assert result.steps == []
assert result.text == "待确认操作：write_file"

# succeeded-only ledger；read 是故意的非法参数负对照。
for tool, method in [
    ("mcp__github__get_file_contents", ""),
    ("mcp__github__issue_write", "create"),
    ("mcp__github__issue_write", "read"),
    ("mcp__github__issue_read", "get"),
]:
    rows[:] = [dict(
        action_id="a", session_id=1, task_id="t",
        tool=tool, arguments={"method": method},
        status="succeeded",
        receipt={"ok": True, "output": "FULL_RESULT"},
    )]
    for fallback in ("{", "我这就执行"):
        assert deliver(1, {"id": "t"}, fallback) == fallback

# 有效变更控制组，证明并非所有成功动作都直接放行 fallback。
rows[0]["tool"] = "write_file"
rows[0]["arguments"] = {"path": "synthetic.txt"}
assert "执行成功" in deliver(1, {"id": "t"}, "{")
rows.clear()

# 冻结 HEAD acc7bd4 的原任务状态语句；不执行其余 Core。
handler = next(n for n in tree.body
               if isinstance(n, ast.AsyncFunctionDef)
               and n.name == "_handle_chat_locked")
assert handler.lineno == 1449
probe = ast.parse("async def state_probe():\n    pass").body[0]
probe.body = [
    n for n in handler.body[0].body if 1463 <= n.lineno <= 1511
] + ast.parse("return task_context, conversation_history").body

history = [
    {"role": "user", "content": "读取两文件并写入汇总"},
    {"role": "assistant", "content": "200元，5人；请确认写入"},
]
ns.update(
    ResultPages=P.ResultPages, session_id=1, request_id="confirm-turn",
    preempted=None, confirmation=None, _sync_pending=lambda _: [],
    MAX_HISTORY_MESSAGES=20, effort=None,
    resolve_effort=lambda _: "standard",
    EFFORT_LEVELS={"standard": {"max_steps": 6, "max_calls": 12}},
    memory=NS(load_messages=lambda *_: history, add_event=lambda *_: None),
)
exec(compile(ast.fix_missing_locations(
    ast.Module(body=[probe], type_ignores=[])), "state", "exec"), ns)

for text in ("确认", "继续"):
    pages = P.ResultPages()
    ref = pages.pack({"ok": True, "output": "X" * 3000})["ref"]
    ns.update(
        text=text,
        _task_state={1: dict(id="old", intent="读取两文件并写入汇总",
                            blocked=False, calls_used=2)},
        _result_pages={1: pages},
    )
    context, kept = asyncio.run(ns["state_probe"]())
    task = ns["_task_state"][1]
    cached = ref in ns["_result_pages"][1].items
    expected = ("确认", 0, False) if text == "确认" else (
        "读取两文件并写入汇总", 2, True)
    assert (task["intent"], task["calls_used"], cached) == expected

    harness = H.CharacterHarness(
        NS(search=lambda _: [], format_context=lambda _: ""))
    messages = harness.build_messages(kept, text, context)
    assert any("读取两文件并写入汇总" in m["content"] for m in messages)
    assert any("200元，5人" in m["content"] for m in messages)

print("RC02_RC03_COUNTEREXAMPLES_PASS")
```

## 五、coverage 200项：可确认缺口，而非数量推论

逐名比较提供的 MCP schema与清单：94个名称没有漏项、没有额外项。**这只证明对该份 schema 的工具名登记完整。**

[现有清单](../../../../docs/assessments/root-cause-audit/COVERAGE.md) 已有 PE03、TA06、LC03等，不能说解析、连续性、数据身份整项遗漏。可以确认的是：

| 缺口 | 已有相邻项 | 尚未明确形成的判别用例／验收条件 |
|---|---|---|
| **取证器自身可靠性未列为审查对象** | EV01是旧 grader；ME01／LC03检查数据 | 迟到WAL、A→B→A、目标哈希、缺消息但有请求事件、畸形时间过滤 |
| **成功动作→实质答案的交付合同不足** | PE03解析、TA05失败、TA08正文 | 全成功账本＋`{`／“这就执行”；合法JSON中的无效reply；结果完整但未回答任务 |
| **按 method 分派的变更语义未展开** | 每个 MCP 工具一行 | `issue_write(create/update)`、`pull_request_review_write`的多个变更方法，而非只看工具名 |
| **无待办确认的状态交叉项未展开** | TA06泛称确认／续办 | pending有／无 × 确认／继续 × task／budget／缓存／历史各自是否保留 |
| **协议成功与业务失败未细分** | TA05及 MCP共享回执 | 缺省／false／true `isError`、错误正文、顶层error；失败原因是否交付 |
| **文本内容触发的TTS确定性故障未列出** | TT01／TT02／TT05 | emoji×stdout编码；相同错误按HTTP503或200包装；重试／重启是否重复同一失败输入 |

另有证据回填缺口：本次读取的清单仍未把 desktop-10..12、RA-M01及新增TTS反例关联到相应状态。它是工作稿，不能把“待验证”算通过，也不能把尚未回填误称为已有验证。

## 六、尾部核验：TTS编码链高置信，但不是全部链路已独立证明

[tts-encoding-counterfactual.json](../../../../docs/assessments/root-cause-audit/evidence/tts-encoding-counterfactual.json) 支持该假设；我独立确认了：

1. 用主仓真实分片函数重算消息1282，13个分片完全一致，第二片确为含📌的标题。
2. 内存输出流中，`gbk/errors=surrogateescape` 打印📌、😊失败；UTF-8成功，普通中文两者成功。
3. [speech.py:156](../../../../services/agent-core/agent_core/speech.py:156) 仅按状态码把所有HTTP503标为可重试。同一合成错误若返回HTTP200＋`ok:false`，则不可重试——已用模拟HTTP错误对照。
4. 同请求 `avatar-chat-5937548` 的 `speech.recovering` 为11:44:45，`speech.unavailable` 为11:47:45，正好180秒；符合 [speech.py:344](../../../../services/agent-core/agent_core/speech.py:344) 的恢复截止逻辑。

最小编码反例：

```python
import io

for encoding in ("gbk", "utf-8"):
    for text in ("你好。", "📌 待确认动作", "谢谢你😊。"):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(
            raw, encoding=encoding,
            errors="surrogateescape", write_through=True)
        try:
            print("实际输入的目标文本:", text, file=stream)
            outcome = "printed"
        except UnicodeEncodeError:
            outcome = "UnicodeEncodeError"
        finally:
            stream.detach()
        print(encoding, ascii(text), outcome)
```

仍需保留的反驳／边界：

- 我没有读取安装私库或重新执行其中844行AST；该部分依主执行者提供的来源哈希与重放记录。这里独立证明的是等价打印机制。
- 子进程默认GBK不等于 live TTS stdout必然GBK；环境变量、显式 `reconfigure` 等仍是可区分条件。
- 四份日志各三条、共12条错误，与“三次失败触发恢复”吻合，但这份摘要没有完整请求／分片／PID创建时间关联，不能仅凭摘要把12次逐一归到同一分片并闭合每次重启。
- 主仓看护确实对 `failed/stalled` 连续检查后重启；服务端“三次失败→failed”的阈值本轮没有进入私库独立核验。
- 同会话之后两个请求又有 `speech.completed`，也不支持“整个语音系统一直不可用”。

因此，**“本次含emoji文本触发输出编码错误，503分类使确定性故障进入重复恢复”是高置信解释；live编码、具体抛错栈及逐次重启关联仍是证据缺口。** 它不能解释早先的空待办、`{`或Issue成功后未交付，更不能外推成全部语音问题的根因。
