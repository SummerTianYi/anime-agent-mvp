"""Offline integrity checks for the published experiment. Does not rate companion quality."""
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2] / "services/agent-core/agent_core"
rows = lambda p: [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()]
digest = lambda text: hashlib.sha256(text.encode()).hexdigest()
canonical = lambda obj: json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
wire = rows(folder / "requests.jsonl")
turns = rows(folder / "dialogues.jsonl")
spec = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
baseline = "371fc7e1e492c24fb0462d53696563488d2866c1"
candidate = "0b951016f395fc353844831dd86f37217c3f3ae5"
req = {i["turn"]: i for i in wire if i["phase"] == "request"}
res = {i["turn"]: i for i in wire if i["phase"] == "result"}
dialogs = {t["id"]: t for t in turns}
expected = {f"{phase}-{n}-{a}-1" for phase in ("before","after") for n in spec["fixed"] for a in (1,2)}
expected.update(f"after-{n}-{i}" for n in spec["continuous"] for i in range(1,7))
assert len(wire) == 56 and len(turns) == 28 and set(req) == set(res) == set(dialogs) == expected
assert [r["n"] for r in wire if r["phase"] == "request"] == list(range(1,29))

def literal(file, key):
    return next(ast.literal_eval(n.value) for n in ast.parse((CORE/file).read_bytes()).body
                if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id == key)

active = literal("harness.py", "ROLE_PROMPT") + "\n\n" + literal("harness.py", "RUNTIME_CONTRACT")
guide = literal("conversation_context.py", "COMPANION_TURN_GUIDANCE")
assert digest(active) == "714ae650ce060f0a645f2fa1055878790438a5e93566ceda18a3ecbdc9d9c9f6"
assert active == (HERE.parent/"companion-v1.2/SYSTEM_PROMPT.txt").read_text(encoding="utf-8").rstrip("\n")
for key,row in dialogs.items():
    b, result = req[key]["body"], res[key]
    assert req[key]["n"] == result["n"] and not result.get("error")
    assert digest(canonical(b)) == req[key]["body_sha256"]
    assert b["model"] == result["model"] == "deepseek-flash" and b["thinking"] == {"type":"disabled"}
    assert "tools" not in b and len(result["choices"]) == 1
    assert b["messages"][0]["content"].startswith(active)
    assert (guide in b["messages"][0]["content"]) == key.startswith("after-")
    assert b["messages"][-1] == {"role":"user","content":row["user"]}
    assert len(row["parsed"]) == len(row["bubbles"]) == len(row["tts_entry"]) == 1
    raw = result["choices"][0]["message"]["content"]
    assert raw == row["parsed"][0]["input"] and not row["parsed"][0]["parsed"]["parse_failed"]
    assert row["bubbles"][0]["text"] == row["parsed"][0]["parsed"]["reply"] == row["tts_entry"][0]["text"]
    assert row["bubbles"][0]["channel"] == "companion" and row["bubbles"][0]["request_id"] == row["tts_entry"][0]["request"]
    assert not row["errors"] and not row["blocked_external_calls"]
    assert row["code"] == (candidate if key.startswith("after-") else baseline)
    if key.startswith("after-"):
        for name, sha in row["source_sha256"].items():
            content = (CORE.parent / name).read_bytes()
            assert sha in {hashlib.sha256(content).hexdigest(), hashlib.sha256(content.replace(b"\r\n",b"\n")).hexdigest()}
for name in spec["fixed"]:
    for i in (1,2):
        before, after = f"before-{name}-{i}-1", f"after-{name}-{i}-1"
        assert dialogs[before]["history_before"] == dialogs[after]["history_before"]
        # Reconstruct the baseline payload by removing precisely the one known system addition.
        b = json.loads(json.dumps(req[after]["body"]))
        b["messages"][0]["content"] = b["messages"][0]["content"].replace("\n\n"+guide, "", 1)
        assert b == req[before]["body"]
        assert req[before]["body"] == req[f"before-{name}-1-1"]["body"]
for name,inputs in spec["continuous"].items():
    hist = []
    for i, user in enumerate(inputs, 1):
        row = dialogs[f"after-{name}-{i}"]
        assert row["history_before"] == hist and row["user"] == user
        hist.extend([{"role":"user","content":user},{"role":"assistant","content":row["bubbles"][0]["text"]}])
print(json.dumps({"turns":28,"http":len(req),"matched_pairs":8,"six_turn_sessions":2,"raw_bubble_tts_agreement":28,
    "input_tokens":sum(r["usage"]["prompt_tokens"] for r in res.values()),
    "output_tokens":sum(r["usage"]["completion_tokens"] for r in res.values()),
    "http_seconds":round(sum(r["seconds"] for r in res.values()),3),
    "role_sha256":digest(literal("harness.py","ROLE_PROMPT")), "runtime_sha256":digest(literal("harness.py","RUNTIME_CONTRACT")),
    "active_sha256":digest(active), "strategy_sha256":digest(guide), "strategy_characters":len(guide)},indent=2))
