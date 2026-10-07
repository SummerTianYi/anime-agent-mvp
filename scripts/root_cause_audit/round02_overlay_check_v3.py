"""Check v3 overlay install/restore on verified entry backups in a temp tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source_manifest = json.loads((args.baseline / "overlay-manifest.json").read_text(encoding="utf-8"))
    before = {item["component"]: item["before"] for item in source_manifest["files"]}
    originals = {name: (args.baseline / f"{name}-entry-before.py").read_bytes() for name in ("core", "tts")}
    assert all(sha(body) == before[name] for name, body in originals.items())
    observer = root / "scripts/root_cause_audit/round02_observer_v3.py"
    checks = []
    with tempfile.TemporaryDirectory(prefix="r2-v3-overlay-") as temporary:
        temp = Path(temporary)
        production, tts, private = temp / "production", temp / "tts", temp / "private"
        private.mkdir()
        entries = {"core": production / "services/agent-core/agent_core/main.py", "tts": tts / "scripts/tts_server.py"}
        for name, path in entries.items():
            path.parent.mkdir(parents=True)
            path.write_bytes(originals[name])
        command = [sys.executable, "-B", str(root / "scripts/root_cause_audit/round02_overlay.py")]
        parameters = ["--production", str(production), "--tts", str(tts), "--private", str(private), "--observer", str(observer)]
        subprocess.run(command + ["apply"] + parameters, capture_output=True, check=True)
        manifest = json.loads((private / "overlay-manifest.json").read_text(encoding="utf-8"))
        assert manifest["observer_sha256"] == sha(observer.read_bytes())
        assert all((path.parent / "_round02_observer.py").read_bytes() == observer.read_bytes() for path in entries.values())
        checks.append("explicit v3 observer installed with exact manifest/sidecar identity")
        changed = {name: path.read_bytes() for name, path in entries.items()}
        for name, body in changed.items():
            assert body != originals[name]
            compile(body, str(entries[name]), "exec")
        duplicate = subprocess.run(command + ["apply"] + parameters, capture_output=True)
        assert duplicate.returncode != 0 and b"Overlay manifest exists" in duplicate.stderr
        assert all(path.read_bytes() == changed[name] for name, path in entries.items())
        checks.append("duplicate apply rejected without changing entries")
        # Simulate interrupted restoration after one entry returned to baseline.
        entries["core"].write_bytes(originals["core"])
        subprocess.run(command + ["restore"] + parameters, capture_output=True, check=True)
        assert all(path.read_bytes() == originals[name] for name, path in entries.items())
        assert all(not (path.parent / "_round02_observer.py").exists() for path in entries.values())
        assert json.loads((private / "control.json").read_text())["enabled"] is False
        checks.append("mixed before/after entries restore exact bytes, remove sidecars and disable control")
    report = {"layer": "temporary copies only, no runtime launched", "ok": True, "checks": checks,
              "source_entry_hashes": before, "observer_sha256": sha(observer.read_bytes()),
              "overlay_sha256": sha((root / "scripts/root_cause_audit/round02_overlay.py").read_bytes()),
              "script_sha256": sha(Path(__file__).read_bytes())}
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
