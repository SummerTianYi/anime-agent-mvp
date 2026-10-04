"""Codex: offline supplement audit and matrix summary; no model or Core calls."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

from .gateway_probe import BATCH
from .prepare import dump, git, sha
from .resume_batch import read_rows, replay
from .runner import PACKAGE, REPO, replay as replay_original


def statistics(rows):
    return {tag: {"case_count": len({r["case_id"] for r in rows if r["model_tag"] == tag}),
            "actual_runs": sum(r["attempted"] for r in rows if r["model_tag"] == tag),
            "actual_cases": len({r["case_id"] for r in rows if r["model_tag"] == tag and r["attempted"]}),
            "verdicts": {v: sum(r["model_tag"] == tag and r["verdict"] == v for r in rows)
                         for v in ("PASS", "PARTIAL", "FAIL", "BLOCKED")},
            "http_calls": sum(r["http_calls"] for r in rows if r["model_tag"] == tag)} for tag in ("ds", "glm")}


def collect(output, progress=False):
    old = read_rows(PACKAGE / "results.jsonl")
    new = read_rows(output / "results.jsonl")
    by_parent = {r["parent_trial_id"]: r for r in new}
    resolved = [by_parent.get(r["trial_id"], r) if r["verdict"] == "BLOCKED" else r for r in old]
    report = {"original": statistics(old), "supplement": statistics(new),
              "logical_slots_latest_blocked_attempt": statistics(resolved),
              "all_actual_attempts": statistics([r for r in old + new if r["attempted"]]),
              "supplement_rows": len(new), "total_logical_slots": len(resolved)}
    if progress:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    replay_original()
    replay(output)
    # Exact original package bytes, not just scores, must survive supplementation.
    parent = "c310a6775f5f20b7617e5f5b219c892d20e8d5b7"
    names = git(REPO, "ls-tree", "-r", "--name-only", parent, "docs/assessments/harness-v0", "scripts/harness_v0").decode().splitlines()
    for name in names:
        if name.endswith("REPORT.md"):
            continue  # Only the top-level report may add a pointer to the new batch.
        assert (REPO / name).read_bytes() == git(REPO, "show", parent + ":" + name), "Original changed: " + name
    report["original_files_byte_identical"] = len(names) - 1
    ledger = json.loads((output / "http-accounting.json").read_text(encoding="utf-8"))
    wire = []
    details = []
    quality_flags = []
    for row in new:
        ev = json.loads((output / row["evidence_path"]).read_text(encoding="utf-8"))
        ids = {s["request_id"] for s in ev["turns"]}
        for h in ev["http"]:
            assert h["request_id"] in ids
            assert h["request_body"]["model"] == row["model_configuration"]["model"]
            if h["status"] == 200:
                assert h["response_body"]["model"] == row["model_configuration"]["model"]
            wire.append({"sequence": h["global_http_sequence"], "trial_id": row["trial_id"]})
        for action in ev.get("executions", []):
            assert action["request_id"] in ids
            if action.get("authorized_by"):
                assert any(s["request_id"] == action["authorized_by"] and s["kind"] == "confirmation" and s["confirms_action_id"] for s in ev["turns"])
        assert ev["grade"]["verdict"] == row["verdict"]
        if row["attempted"] and (not ev.get("final_contract_valid") or ev.get("isolation_interventions") or ev.get("task_limit")):
            quality_flags.append({"trial_id": row["trial_id"], "verdict_unchanged": row["verdict"],
                 "final_contract_valid": ev.get("final_contract_valid"), "task_limit": ev.get("task_limit"),
                 "isolation_interventions": ev.get("isolation_interventions", []), "evidence": row["evidence_path"]})
        details.append({"trial_id": row["trial_id"], "case_id": row["case_id"], "model_tag": row["model_tag"],
                        "verdict": row["verdict"], "reasons": row["reasons"], "evidence": row["evidence_path"],
                        "final": ev["grade"]["final_delivery"], "blocked": ev.get("blocked"),
                        "http_statuses": [h["status"] for h in ev["http"]]})
    assert sorted(wire, key=lambda h: h["sequence"]) == ledger["reserved_wire_attempts"]
    report["http_statuses"] = {tag: dict(Counter(code for d in details if d["model_tag"] == tag for code in d["http_statuses"])) for tag in ("ds", "glm")}
    report["cumulative_http_with_probes"] = ledger["cumulative_calls"]
    report["gateway_probe_calls"] = ledger["probe_calls"]
    report["wire_ledger_and_association"] = "PASS"
    case_specs = json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]
    report["case_results"] = [{"case_id": case["id"], "title": case["title"],
        **{tag: [{"repeat": r["repeat"], "verdict": r["verdict"], "trial_id": r["trial_id"],
                  "evidence": r["evidence_path"] if r.get("batch_id") else "../../" + r["evidence_path"]}
                 for r in resolved if r["case_id"] == case["id"] and r["model_tag"] == tag]
           for tag in ("ds", "glm")}} for case in case_specs]
    for path in output.rglob("*.json"):
        content = path.read_text(encoding="utf-8")
        assert not re.search(r"[CD]:[\\/]+(?:Users|UserData)", content), "Host path in: " + path.name
        assert path.stat().st_size < 50 * 1024 * 1024
    selftest = subprocess.run([sys.executable, "-m", "unittest", "scripts.harness_v0.test_resume", "-v"],
                             cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    assert selftest.returncode == 0
    dump(output / "selftest.json", {"exit_code": 0, "command": "python -m unittest scripts.harness_v0.test_resume -v",
         "stdout": selftest.stdout, "stderr": selftest.stderr, "http_calls": 0,
         "pre_live_development": "Initial error-body-replay test failed: assigning HTTPError.fp did not rewind cached read. Reconstructed equivalent HTTPError with BytesIO, then all 6 passed before live continuation; no test criterion removed."})
    dump(output / "summary.json", report)
    dump(output / "deliveries.json", details)
    dump(output / "quality-flags.json", {"purpose": "Supplementary review; never changes frozen scores", "flags": quality_flags})
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=BATCH)
    p.add_argument("--progress", action="store_true")
    p.add_argument("--private-env", type=Path)
    args = p.parse_args()
    collect(args.output, args.progress)
    if args.private_env and not args.progress:
        from dotenv import dotenv_values
        secrets = [v for k, v in dotenv_values(args.private_env).items() if v and len(v) >= 12 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", k)]
        paths = [p for p in PACKAGE.rglob("*") if p.is_file()] + list((REPO / "scripts/harness_v0").glob("*.py"))
        for path in paths:
            assert not any(s in path.read_text(encoding="utf-8") for s in secrets), "Secret detected; content withheld"
        print("SECRET_SCAN_PASS", len(secrets), "values compared without disclosure")


if __name__ == "__main__":
    main()
