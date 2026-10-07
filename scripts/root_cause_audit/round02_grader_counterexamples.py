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
