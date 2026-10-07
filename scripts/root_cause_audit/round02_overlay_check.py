"""Exercise exact byte restoration on copies, without launching any runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument("--production", type=Path, required=True)
p.add_argument("--tts", type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix="r2-overlay-copy-") as tmp:
    temp = Path(tmp).resolve()
    production, tts, private = temp/"production", temp/"tts", temp/"private"
    private.mkdir()
    original = {}
    for source, dest in [(a.production/"services/agent-core/agent_core/main.py", production/"services/agent-core/agent_core/main.py"),
                         (a.tts/"scripts/tts_server.py", tts/"scripts/tts_server.py")]:
        dest.parent.mkdir(parents=True)
        original[dest] = source.read_bytes()
        dest.write_bytes(original[dest])
    command = [sys.executable, str(root/"scripts/root_cause_audit/round02_overlay.py")]
    parameters = ["--production",str(production),"--tts",str(tts),"--private",str(private)]
    applied = subprocess.run(command+["apply"]+parameters, capture_output=True, check=True, text=True)
    assert all(path.read_bytes() != body for path,body in original.items())
    for path in original:
        compile(path.read_bytes(), str(path), "exec")
    restored = subprocess.run(command+["restore"]+parameters, capture_output=True, check=True, text=True)
    assert all(path.read_bytes() == body for path,body in original.items())
    assert all(not (path.parent/"_round02_observer.py").exists() for path in original)
    assert json.loads((private/"control.json").read_text())["enabled"] is False
    report = {"layer":"isolated file copies; real runtime not launched", "ok":True,
              "checks":["apply changes only copied entries and observer files","patched entries compile","restore returns exact original bytes","observer removed","control disabled"],
              "original_hashes":[hashlib.sha256(body).hexdigest() for body in original.values()]}
with (root/"docs/assessments/root-cause-audit/round-02/evidence/overlay-check.json").open("x",encoding="utf-8") as output:
    json.dump(report,output,ensure_ascii=False,indent=2)
print(json.dumps(report))
