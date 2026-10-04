"""Codex: append-only supplement of first-batch BLOCKED slots; frozen V0 scoring."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from .budget import initialize
from .gateway_probe import BATCH, credentials
from .grader import grade
from .prepare import dump, materialize, sha
from .redact_titles import clean
from .runner import PACKAGE, REPO, verify


def blocked_slots(rows):
    identities = [(r["model_tag"], r["case_id"], r["repeat"]) for r in rows]
    assert len(identities) == len(set(identities)), "Duplicate original logical slot"
    return [r for r in rows if r["verdict"] == "BLOCKED"]


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def accounting(path, output, probe_calls):
    with closing(sqlite3.connect(path)) as db:
        calls = [dict(zip(("sequence", "trial_id"), row)) for row in db.execute("SELECT * FROM calls ORDER BY id")]
    dump(output / "http-accounting.json", {"cumulative_cap": 900, "original_http_calls": 66,
         "probe_calls": probe_calls, "batch_wire_cap": 834 - probe_calls,
         "reserved_wire_attempts": calls, "cumulative_calls": 66 + probe_calls + len(calls)})
    return Counter(row["trial_id"] for row in calls)


def run(env_file, output):
    frozen = verify()
    key, models = credentials(env_file)
    original = read_rows(PACKAGE / "results.jsonl")
    slots = blocked_slots(original)
    assert len(slots) == 138 and sum(r["http_calls"] for r in original) == 66
    probe = json.loads((output / "gateway-probes.json").read_text(encoding="utf-8"))
    assert probe["all_passed"] and probe["http_calls"] == 2, "Both gateway probes must pass first"
    cases = {c["id"]: c for c in json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]}
    baseline = json.loads((PACKAGE / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))
    results = output / "results.jsonl"
    registration = output / "registration.json"
    assert not results.exists() and not registration.exists(), "Use a NEW batch; never overwrite attempts"
    versions = {k: baseline[k] for k in ("source_sha", "source_tree_sha256", "current_prompt_sha256")}
    versions.update(case_sha256=frozen["files"]["docs/assessments/harness-v0/cases.json"],
                    evaluator_sha256=sha((PACKAGE / "freeze.json").read_bytes()))
    dump(registration, {"registered_utc": datetime.now(timezone.utc).isoformat(),
         "parent_candidate_sha": "c310a6775f5f20b7617e5f5b219c892d20e8d5b7", **versions,
         "original_results_sha256": sha((PACKAGE / "results.jsonl").read_bytes()),
         "plan_sha256": sha((output / "PLAN.md").read_bytes()),
         "gateway_probes_sha256": sha((output / "gateway-probes.json").read_bytes()),
         "new_driver_sha256": {name: sha((REPO / "scripts/harness_v0" / name).read_bytes())
                               for name in ("resume_batch.py", "resume_worker.py", "gateway_probe.py")},
         "slots": [r["trial_id"] for r in slots], "models": models, "cumulative_http_cap": 900,
         "candidate_prompt_active": False, "scheduling_only": "serialized; 2s min wire gap; stop both on 401/403/429"})
    stopped = None
    consecutive = 0
    with tempfile.TemporaryDirectory(prefix="tianyi-harness-v0-") as temporary:
        temp = Path(temporary)
        source = materialize(REPO, PACKAGE, temp / "source")
        budget = temp / "http-budget.sqlite3"
        initialize(budget, 834 - probe["http_calls"])
        env = os.environ.copy()
        env.update(HARNESS_MODEL_KEY=key, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        with results.open("x", encoding="utf-8") as sink:
            for old in slots:
                trial = "resume01-" + old["trial_id"]
                case, tag = cases[old["case_id"]], old["model_tag"]
                started = time.monotonic()
                if stopped:
                    ev = {"trial_id": trial, "case_id": case["id"], "blocked": stopped, "attempted": False,
                          "turns": [], "events": [], "executions": [], "http": [],
                          "before": {"files": case["initial_fixture"]["files"]},
                          "after": {"files": case["initial_fixture"]["files"]}}
                else:
                    work = temp / trial
                    work.mkdir()
                    job = {"case": case, "model_tag": tag, "trial_id": trial, "trial_dir": str(work),
                           "source_path": str(source), "model": models[tag], "versions": versions,
                           "budget_path": str(budget), "fixture_script": str(REPO / "scripts/harness_v0/fixture_mcp.py"),
                           "output": str(work / "output.json")}
                    dump(work / "job.json", job)
                    process = subprocess.run([sys.executable, "-m", "scripts.harness_v0.resume_worker", str(work / "job.json")],
                        cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300)
                    if process.returncode or not Path(job["output"]).exists():
                        # Stop on infrastructure failure; do not publish raw stderr containing host paths.
                        ev = {"trial_id": trial, "blocked": "evaluation_worker_failed", "attempted": True,
                              "turns": [], "events": [], "executions": [], "http": [],
                              "before": {"files": case["initial_fixture"]["files"]},
                              "after": {"files": case["initial_fixture"]["files"]},
                              "worker_exit_code": process.returncode, "stderr_sha256": sha(process.stderr)}
                        stopped = "evaluation_worker_failed"
                    else:
                        ev = json.loads(Path(job["output"]).read_text(encoding="utf-8"))
                        ev["attempted"] = True
                    consecutive = consecutive + 1 if ev.get("blocked") else 0
                    if ev.get("wire_gate", {}).get("halted_status") or consecutive >= 3 or ev.get("blocked") == "global_http_limit":
                        stopped = ev.get("blocked", "repeated_unavailability")
                scored = grade(case, ev)
                changes = []
                revised = clean(ev, changes=changes)
                assert grade(case, revised) == scored, "Redaction cannot change scores"
                revised.update(grade=scored, parent_trial_id=old["trial_id"], batch_id=output.name,
                               redaction_changes=changes, pre_packaging_logical_sha256=sha(json.dumps(ev, ensure_ascii=False)))
                path = output / "evidence" / (trial + ".json")
                assert not path.exists()
                dump(path, revised)
                counts = accounting(budget, output, probe["http_calls"])
                row = {"trial_id": trial, "parent_trial_id": old["trial_id"], "batch_id": output.name,
                       "model_tag": tag, "case_id": case["id"], "repeat": old["repeat"], **versions,
                       "model_configuration": models[tag], "layer": "real-model/isolated-current-core/controlled-stdio-mcp",
                       "attempted": ev["attempted"], "verdict": scored["verdict"], "reasons": scored["reasons"],
                       "elapsed_ms": ev.get("elapsed_ms", round((time.monotonic()-started)*1000)),
                       "http_calls": counts[trial], "evidence_path": path.relative_to(output).as_posix(),
                       "evidence_sha256": sha(path.read_bytes()), "external_services_tested": False}
                sink.write(json.dumps(row, ensure_ascii=False) + "\n")
                sink.flush()
                print(trial, row["verdict"], "HTTP", row["http_calls"], "reason", row["reasons"], flush=True)
                if not stopped:
                    time.sleep(2)
    replay(output)


def replay(output):
    verify()
    reg = json.loads((output / "registration.json").read_text(encoding="utf-8"))
    assert reg["original_results_sha256"] == sha((PACKAGE / "results.jsonl").read_bytes())
    for name, digest in reg["new_driver_sha256"].items():
        assert sha((REPO / "scripts/harness_v0" / name).read_bytes()) == digest, name
    assert reg["plan_sha256"] == sha((output / "PLAN.md").read_bytes())
    assert reg["gateway_probes_sha256"] == sha((output / "gateway-probes.json").read_bytes())
    cases = {c["id"]: c for c in json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]}
    rows = read_rows(output / "results.jsonl")
    assert [r["parent_trial_id"] for r in rows] == reg["slots"]
    ledger = json.loads((output / "http-accounting.json").read_text(encoding="utf-8"))
    counts = Counter(r["trial_id"] for r in ledger["reserved_wire_attempts"])
    for row in rows:
        path = output / row["evidence_path"]
        assert sha(path.read_bytes()) == row["evidence_sha256"]
        ev = json.loads(path.read_text(encoding="utf-8"))
        score = grade(cases[row["case_id"]], ev)
        assert score["verdict"] == row["verdict"] and score["reasons"] == row["reasons"], row["trial_id"]
        assert counts[row["trial_id"]] == row["http_calls"] == len(ev["http"])
    assert ledger["cumulative_calls"] == 68 + sum(r["http_calls"] for r in rows) <= 900
    summary = {tag: {"scheduled": sum(r["model_tag"] == tag for r in rows),
               "actual_runs": sum(r["attempted"] for r in rows if r["model_tag"] == tag),
               "verdicts": dict(Counter(r["verdict"] for r in rows if r["model_tag"] == tag)),
               "http_calls": sum(r["http_calls"] for r in rows if r["model_tag"] == tag)} for tag in ("ds", "glm")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=("run", "replay"))
    p.add_argument("--env-file", type=Path)
    p.add_argument("--output", type=Path, default=BATCH)
    args = p.parse_args()
    if args.operation == "run":
        assert args.env_file
        run(args.env_file, args.output)
    else:
        replay(args.output)


if __name__ == "__main__":
    main()
