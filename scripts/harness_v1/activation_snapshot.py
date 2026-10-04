"""Read-only, sanitized proof of the authorized desktop candidate activation."""
import argparse
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument("--production", type=Path, required=True)
p.add_argument("--runtime-sha", required=True)
p.add_argument("--record", default="activation.json")
a = p.parse_args()
opener = build_opener(ProxyHandler({}))
def get(path):
    with opener.open("http://127.0.0.1:8765" + path, timeout=15) as response:
        return json.load(response)
health, live = get("/health"), get("/health/live")
paths = sorted((ROOT / "services/agent-core/agent_core").glob("*.py"))
paths += [ROOT / "apps/avatar-runtime" / name for name in ("runtime.gd", "interaction_ui.gd")]
files = {}
for source in paths:
    relative = source.relative_to(ROOT).as_posix()
    deployed = a.production / relative
    files[relative] = dict(candidate=hashlib.sha256(source.read_bytes()).hexdigest(),
                           deployed=hashlib.sha256(deployed.read_bytes()).hexdigest())
config = {}
allowed = {"LLM_PROVIDER", "ANIME_AGENT_VOICE_INPUT_MODE", "ANIME_AGENT_WAKE_WORD", "ANIME_AGENT_IDLE_THRESHOLD"}
for line in (a.production / ".env").read_text(encoding="utf-8-sig").splitlines():
    key, sep, value = line.partition("=")
    if sep and key in allowed:
        config[key] = value.strip()
tree = ast.parse((a.production / "services/agent-core/agent_core/harness.py").read_text(encoding="utf-8"))
parts = {n.targets[0].id: n.value.value for n in tree.body
         if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant)}
prompt = parts["ROLE_PROMPT"] + "\n\n" + parts["RUNTIME_CONTRACT"]
record = dict(checked_utc=datetime.now(timezone.utc).isoformat(), runtime_source_sha=a.runtime_sha,
    prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(), config=config,
    core_pid=live["pid"], health={key: health[key] for key in ("status", "llm", "roles", "wake", "tools")},
    tts={key: health["tts"][key] for key in ("enabled", "available", "playbackProtocol")},
    file_hashes=files, files_match=all(v["candidate"] == v["deployed"] for v in files.values()),
    human_voice_test="pending", human_effort_test="pending", human_real_600s_idle_test="pending",
    data_boundary="No chat, memory contents, credentials or model/voice assets read; only source hashes and health.")
assert Path(a.record).name == a.record and a.record.endswith(".json")
out = ROOT / "docs/assessments/harness-v1/evidence" / a.record
assert not out.exists(), "Preserve earlier activation evidence; select a new record for a later activation"
out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: record[k] for k in ("runtime_source_sha", "core_pid", "health", "tts", "files_match")}, ensure_ascii=False))
raise SystemExit(not record["files_match"] or not health["roles"]["avatar"] or health["wake"]["running"])
