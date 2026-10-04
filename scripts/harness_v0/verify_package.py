"""Read-only candidate integrity checks. Never contacts providers or Core."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess

from .prepare import sha
from .runner import PACKAGE, REPO, replay, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-env", type=Path, help="Optional read-only local secret comparison; values never printed")
    args = parser.parse_args()
    verify()
    summary = replay()
    rows = [json.loads(s) for s in (PACKAGE / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    cases = json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]
    assert {(r["model_tag"], r["case_id"], r["repeat"]) for r in rows} == {
        (model, c["id"], repetition) for model in ("ds", "glm") for c in cases for repetition in (1, 2, 3)}
    ledger = json.loads((PACKAGE / "evidence/http-accounting.json").read_text(encoding="utf-8"))["reserved_wire_attempts"]
    http = []
    for row in rows:
        ev = json.loads((PACKAGE / row["evidence_path"]).read_text(encoding="utf-8"))
        assert len(ev.get("http", [])) == row["http_calls"]
        if not row["attempted"]:
            assert row["verdict"] == "BLOCKED" and row["http_calls"] == 0
        ids = {t["request_id"] for t in ev.get("turns", [])}
        for entry in ev.get("http", []):
            assert entry["request_id"] in ids
            assert entry["request_body"]["model"] == row["model_configuration"]["model"]
            if entry["status"] == 200:
                assert entry["response_body"]["model"] == row["model_configuration"]["model"]
            http.append({"sequence": entry["global_http_sequence"], "trial_id": row["trial_id"]})
        for action in ev.get("executions", []):
            assert action["request_id"] in ids
            if action.get("authorized_by"):
                assert any(t["request_id"] == action["authorized_by"] and t["kind"] == "confirmation" and t["confirms_action_id"] for t in ev["turns"])
    assert sorted(http, key=lambda h: h["sequence"]) == ledger
    assert len(http) <= 900
    checked = []
    for path in (REPO / "scripts/harness_v0").glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"))
        checked.append(path.relative_to(REPO).as_posix())
    file_paths = [p for p in PACKAGE.rglob("*") if p.is_file()]
    secret_count = 0
    if args.private_env:
        from dotenv import dotenv_values
        secrets = [v for k, v in dotenv_values(args.private_env).items() if v and len(v) >= 12 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", k)]
        scan_paths = file_paths + list((REPO / "scripts/harness_v0").glob("*.py"))
        for path in scan_paths:
            content = path.read_text(encoding="utf-8")
            assert not any(value in content for value in secrets), "Secret detected; content withheld"
        secret_count = len(secrets)
    assert all(p.stat().st_size < 50 * 1024 * 1024 for p in file_paths)
    assert not any(p.suffix in {"sqlite3", ".db", ".wav", ".mp4", ".env"} for p in file_paths)
    for path in (PACKAGE / "evidence").rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[CD]:[\\/]+(?:Users|UserData)", text), "Unsanitized local path: " + path.name
    for probe in json.loads((PACKAGE / "evidence/offline-audit/summary.json").read_text(encoding="utf-8"))["probes"]:
        assert sha((PACKAGE / probe["evidence"]).read_bytes()) == probe["sha256"]
    proc = subprocess.run(["git", "diff", "--check"], cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout
    print(json.dumps({"package_integrity": "PASS", "matrix_rows": len(rows), "actual_http": len(http),
          "secret_values_compared_without_disclosure": secret_count, "syntax_checked": checked,
          "package_bytes": sum(p.stat().st_size for p in file_paths), "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
