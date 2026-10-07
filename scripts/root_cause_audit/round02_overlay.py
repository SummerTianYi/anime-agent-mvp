"""Install/remove temporary gated diagnostics; preserve exact entry bytes.

Caller must normally close the formal Godot session before apply/restore.
No business decisions, prompts, configuration values or assets are changed.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sha = lambda content: hashlib.sha256(content).hexdigest()

def atomic_write(path, content):
    temporary = path.with_name(path.name + ".r2-" + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
p = argparse.ArgumentParser()
p.add_argument("mode", choices=("apply", "restore"))
p.add_argument("--production", type=Path, required=True)
p.add_argument("--tts", type=Path, required=True)
p.add_argument("--private", type=Path, required=True)
p.add_argument("--observer", type=Path, help="Reviewed diagnostic version; defaults to original v2")
a = p.parse_args()
a.private = a.private.resolve()
manifest_path = a.private / "overlay-manifest.json"
control = a.private / "control.json"
if a.mode == "apply":
    if manifest_path.exists():
        raise SystemExit("Overlay manifest exists; refusing duplicate installation")
    observer = (a.observer or ROOT / "scripts/root_cause_audit/round02_observer.py").read_bytes()
    ast.parse(observer)
    deployment = json.loads((ROOT / "docs/assessments/root-cause-audit/round-02/evidence/deployment-entry.json").read_text(encoding="utf-8"))
    targets = [("core", a.production / "services/agent-core/agent_core/main.py", "install_core"),
               ("tts", a.tts / "scripts/tts_server.py", "install_tts")]
    prepared = []
    for component, entry, install in targets:
        entry = entry.resolve()
        original = entry.read_bytes()
        if component == "core" and sha(original) != deployment["files"]["services/agent-core/agent_core/main.py"]["sha256"]:
            raise SystemExit("Core changed since entry manifest; refusing overlay")
        sidecar = entry.parent / "_round02_observer.py"
        if sidecar.exists():
            raise SystemExit("Observer target already exists")
        marker = b'if __name__ == "__main__":'
        if original.count(marker) != 1:
            raise SystemExit("Unexpected entry structure")
        hook = ("# Temporary R2 audit observation: gated, removable, outcome-preserving.\n"
                "try:\n"
                "    from pathlib import Path as _r2_Path\n"
                f"    if _r2_Path({str(control)!r}).is_file():\n"
                "        import importlib.util as _r2_import\n"
                f"        _r2_spec = _r2_import.spec_from_file_location('_r2_observer', {str(sidecar)!r})\n"
                "        _r2_module = _r2_import.module_from_spec(_r2_spec)\n"
                "        _r2_spec.loader.exec_module(_r2_module)\n"
                f"        _r2_module.{install}(sys.modules[__name__], {str(a.private)!r})\n"
                "except Exception:\n"
                "    try:\n"
                "        print('ROUND02_OBSERVER_INSTALL_FAILED', file=sys.stderr, flush=True)\n"
                "    except Exception:\n"
                "        pass\n\n").encode("utf-8")
        patched = original.replace(marker, hook + marker)
        ast.parse(patched)
        backup = a.private / (component + "-entry-before.py")
        if backup.exists():
            raise SystemExit("Backup already exists")
        prepared.append((entry, original, patched, backup, sidecar, component))
    record = {"utc": datetime.now(timezone.utc).isoformat(), "observer_sha256": sha(observer), "files": []}
    for entry, original, patched, backup, sidecar, component in prepared:
        atomic_write(backup, original)
        record["files"].append({"component": component, "entry": str(entry), "backup": str(backup),
                                "sidecar": str(sidecar), "before": sha(original), "after": sha(patched)})
    atomic_write(manifest_path, json.dumps(record, indent=2).encode("utf-8"))
    for entry, original, patched, backup, sidecar, component in prepared:
        atomic_write(sidecar, observer)
        atomic_write(entry, patched)
    control.write_text(json.dumps({"enabled": True, "expires_epoch": time.time()+21600}), encoding="utf-8")
    print(json.dumps({"installed": [x["component"] for x in record["files"]], "observer_sha256": record["observer_sha256"]}))
else:
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    control.write_text('{"enabled":false}', encoding="utf-8")
    for item in record["files"]:
        if sha(Path(item["entry"]).read_bytes()) not in {item["before"], item["after"]}:
            raise SystemExit("Entry changed outside overlay; restoration refused")
        if sha(Path(item["backup"]).read_bytes()) != item["before"]:
            raise SystemExit("Backup checksum mismatch")
        sidecar = Path(item["sidecar"])
        if sidecar.parent.resolve() != Path(item["entry"]).parent.resolve() or sidecar.name != "_round02_observer.py":
            raise SystemExit("Invalid registered observer target")
        if sidecar.exists() and sha(sidecar.read_bytes()) != record["observer_sha256"]:
            raise SystemExit("Observer changed; restoration refused")
    for item in record["files"]:
        atomic_write(Path(item["entry"]), Path(item["backup"]).read_bytes())
        Path(item["sidecar"]).unlink(missing_ok=True)
    restored = {"utc": datetime.now(timezone.utc).isoformat(), "restored": [{"component": x["component"], "sha256": sha(Path(x["entry"]).read_bytes())} for x in record["files"]]}
    with (a.private / "overlay-restored.json").open("x", encoding="utf-8") as target:
        json.dump(restored, target, indent=2)
    print(json.dumps(restored))
