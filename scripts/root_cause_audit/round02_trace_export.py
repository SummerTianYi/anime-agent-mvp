"""Export explicitly reviewed R2 request traces. Does not auto-approve privacy.

Run only after inspecting the selected synthetic input, model output and tools.
The underlying private log prefix stays available with hash+byte count.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument("--private", type=Path, required=True)
p.add_argument("--requests", nargs="+", required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--gap", action="append", default=[])
a = p.parse_args()
selected, sources = [], []
for path in sorted(a.private.glob("trace-*.jsonl")):
    raw = path.read_bytes()
    # A concurrent append can leave one incomplete last record. Keep a complete
    # immutable prefix; don't confuse prefix evidence with a whole-file hash.
    raw = raw[:raw.rfind(b"\n")+1]
    rows = [json.loads(line) for line in raw.splitlines()]
    accepted = [row for row in rows if row.get("trace",{}).get("request_id") in a.requests]
    if accepted:
        sources.append({"name":path.name,"prefix_bytes":len(raw),"prefix_sha256":hashlib.sha256(raw).hexdigest()})
        for row in accepted:
            if row["stage"] == "model.http.request":
                tools = row["data"].get("body",{}).pop("tools",[])
                row["data"]["tools_count"] = len(tools)
                row["data"]["tools_sha256"] = hashlib.sha256(json.dumps(tools,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                row["data"]["tool_names"] = [tool.get("function",tool).get("name") for tool in tools]
            selected.append(row)
report = {"schema":"r2-reviewed-trace-v1","layer":"current Godot task, diagnostic observation; not a synthetic replacement Core",
          "requests":a.requests,"sources":sources,"known_gaps":a.gap,"human_audio":"not individually confirmed", "records":sorted(selected,key=lambda row:(row["epoch"],row["pid"],row["seq"]))}
def sanitize(value):
    if isinstance(value,dict):
        return {key:sanitize(item) for key,item in value.items()}
    if isinstance(value,list):
        return [sanitize(item) for item in value]
    if not isinstance(value,str):
        return value
    for prefix in ("C:/Users/26052/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/", "D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/"):
        value = value.replace(prefix+"anime-agent-mvp", "{PRODUCTION}").replace(prefix+"tianyi-tts", "{TTS}")
        value = value.replace((prefix+"anime-agent-mvp").replace("/", "\\"), "{PRODUCTION}").replace((prefix+"tianyi-tts").replace("/", "\\"), "{TTS}")
    value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "OWNER_TEST_MAILBOX", value)
    return value
with a.output.open("x",encoding="utf-8") as target:
    json.dump(sanitize(report),target,ensure_ascii=False,indent=2)
print(json.dumps({"requests":a.requests,"records":len(selected),"stages":sorted({row["stage"] for row in selected}),"known_gaps":a.gap}))
