# Codex: reproduce independent Sagan counterexamples; source-only AST, no Core startup.
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
