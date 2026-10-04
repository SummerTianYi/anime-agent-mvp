"""Codex Harness V0 controller. Replay grading is offline; live needs explicit key file."""
import argparse
from collections import Counter
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from .budget import initialize
from .grader import grade
from .prepare import capture, dump, materialize, sha

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "docs/assessments/harness-v0"
FROZEN = ["docs/assessments/harness-v0/cases.json", "scripts/model_cert.py", *[
    "scripts/harness_v0/" + name for name in
    ("grader.py", "worker.py", "budget.py", "fixture_mcp.py", "prepare.py", "runner.py", "test_calibration.py")]]


def verify(package=PACKAGE):
    frozen = json.loads((package / "freeze.json").read_text(encoding="utf-8"))
    for name, digest in frozen["files"].items():
        assert sha((REPO / name).read_bytes()) == digest, "Frozen evaluator/case changed: " + name
    return frozen


def freeze():
    assert not (PACKAGE / "results.jsonl").exists(), "Do not replace scored cases"
    test = subprocess.run([sys.executable, "-m", "unittest", "scripts.harness_v0.test_calibration", "-v"],
                          cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    dump(PACKAGE / "evidence/calibration/selftest.json", {"exit_code": test.returncode,
         "command": "python -m unittest scripts.harness_v0.test_calibration -v", "stdout": test.stdout, "stderr": test.stderr})
    if test.returncode:
        raise RuntimeError(test.stderr)
    manifest = json.loads((PACKAGE / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))
    result = {"version": "v0.1", "policy": "append/version changes; preserve all first outcomes",
              "files": {name: sha((REPO / name).read_bytes()) for name in FROZEN},
              "source_tree_sha256": manifest["source_tree_sha256"],
              "current_prompt_sha256": manifest["current_prompt_sha256"],
              "candidate_prompt_active": False}
    dump(PACKAGE / "freeze.json", result)
    print("CALIBRATED_AND_FROZEN", result["files"]["docs/assessments/harness-v0/cases.json"])


def replay(package=PACKAGE):
    verify(package)
    cases = {c["id"]: c for c in json.loads((package / "cases.json").read_text(encoding="utf-8"))["cases"]}
    summary = {}
    rows = [json.loads(x) for x in (package / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    identities = [(r["model_tag"], r["case_id"], r["repeat"]) for r in rows]
    assert len(identities) == len(set(identities))
    for row in rows:
        path = package / row["evidence_path"]
        assert sha(path.read_bytes()) == row["evidence_sha256"]
        ev = json.loads(path.read_text(encoding="utf-8"))
        actual = grade(cases[row["case_id"]], ev)
        assert actual["verdict"] == row["verdict"] and actual["reasons"] == row["reasons"], row["trial_id"]
    for tag in ("ds", "glm"):
        group = [r for r in rows if r["model_tag"] == tag]
        summary[tag] = {"cases": len({r["case_id"] for r in group}), "scheduled": len(group),
                        "actual_runs": sum(r["attempted"] for r in group),
                        "verdicts": dict(Counter(r["verdict"] for r in group)),
                        "http_calls": sum(r["http_calls"] for r in group)}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def live(env_path, output):
    from dotenv import dotenv_values
    frozen = verify()
    manifest = json.loads((PACKAGE / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))
    spec = json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))
    values = dotenv_values(env_path)
    assert values.get("DEEPSEEK_API_KEY"), "Credential missing"
    # No guessed aliases or accidental account/model change between freeze/run.
    for tag, variable in (("ds", "DEEPSEEK_MODEL"), ("glm", "GLM_MODEL")):
        assert values.get(variable) == manifest["models"][tag]["model"]
        assert values.get("DEEPSEEK_BASE_URL", "").rstrip("/") == manifest["models"][tag]["base_url"]
    assert values.get("GLM_CREDENTIAL_SOURCE") == "deepseek"
    output.mkdir(parents=True, exist_ok=True)
    results = output / "results.jsonl"
    assert not results.exists(), "Append-only evidence: choose a NEW output directory for another run"
    # Reproduction output is independent; never overwrite the committed V0 scores.
    if output != PACKAGE:
        for name in ("cases.json", "freeze.json"):
            (output / name).write_bytes((PACKAGE / name).read_bytes())
    stopped = {}
    consecutive = {"ds": 0, "glm": 0}
    versions = {"source_sha": manifest["source_sha"], "source_tree_sha256": manifest["source_tree_sha256"],
                "current_prompt_sha256": manifest["current_prompt_sha256"],
                "case_sha256": frozen["files"]["docs/assessments/harness-v0/cases.json"],
                "evaluator_sha256": sha((PACKAGE / "freeze.json").read_bytes())}
    with tempfile.TemporaryDirectory(prefix="tianyi-harness-v0-") as temporary:
        temp = Path(temporary)
        source = materialize(REPO, PACKAGE, temp / "source")
        budget = temp / "http-budget.sqlite3"
        initialize(budget, spec["budget"]["hard_http_limit"])
        env = os.environ.copy()
        env.update(HARNESS_MODEL_KEY=values["DEEPSEEK_API_KEY"], PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

        def one(case, repetition, tag):
            trial = f"{tag}-{case['id']}-r{repetition}"
            start = time.monotonic()
            if tag in stopped:
                ev = {"trial_id": trial, "blocked": stopped[tag], "turns": [], "events": [], "executions": [],
                      "before": {"files": case["initial_fixture"]["files"]},
                      "after": {"files": case["initial_fixture"]["files"]}, "http": [], "attempted": False}
            else:
                trial_dir = temp / trial
                trial_dir.mkdir()
                job = {"case": case, "model_tag": tag, "trial_id": trial, "trial_dir": str(trial_dir),
                    "source_path": str(source), "model": manifest["models"][tag], "versions": versions,
                    "budget_path": str(budget), "fixture_script": str(REPO / "scripts/harness_v0/fixture_mcp.py"),
                    "output": str(trial_dir / "output.json")}
                dump(trial_dir / "job.json", job)
                process = subprocess.run([sys.executable, "-m", "scripts.harness_v0.worker", str(trial_dir / "job.json")],
                    cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300)
                if process.returncode or not Path(job["output"]).exists():
                    # Evaluation infrastructure failure is not a model-capability score.
                    ev = {"trial_id": trial, "blocked": "evaluation_worker_failed", "turns": [], "events": [],
                        "before": {"files": case["initial_fixture"]["files"]},
                        "after": {"files": case["initial_fixture"]["files"]}, "http": [],
                        "worker_error": process.stderr[-6000:].replace(str(temp), "{TEMP}"), "attempted": True}
                    stopped[tag] = "evaluation_worker_failed"
                else:
                    ev = json.loads(Path(job["output"]).read_text(encoding="utf-8"))
                    ev["attempted"] = True
                codes = [h.get("status") for h in ev["http"]]
                consecutive[tag] = consecutive[tag] + 1 if ev.get("blocked") else 0
                if any(c in {401, 403, 429} for c in codes) or consecutive[tag] >= 3 or ev.get("blocked") == "global_http_limit":
                    stopped[tag] = "external_auth_quota_or_repeated_unavailability"
            result = grade(case, ev)
            ev["grade"] = result
            path = output / f"evidence/runs/{trial}.json"
            assert not path.exists()
            dump(path, ev)
            with closing(sqlite3.connect(budget)) as db:
                calls = db.execute("SELECT COUNT(*) FROM calls WHERE trial=?", (trial,)).fetchone()[0]
            return {"trial_id": trial, "model_tag": tag, "case_id": case["id"], "repeat": repetition,
                "model_configuration": manifest["models"][tag], **versions,
                "layer": "real-model/isolated-current-core/controlled-stdio-mcp", "attempted": ev["attempted"],
                "verdict": result["verdict"], "reasons": result["reasons"], "elapsed_ms": ev.get("elapsed_ms", round((time.monotonic()-start)*1000)),
                "http_calls": calls, "evidence_path": path.relative_to(output).as_posix(),
                "evidence_sha256": sha(path.read_bytes()), "external_services_tested": False}

        with ThreadPoolExecutor(max_workers=2) as pool, results.open("x", encoding="utf-8") as sink:
            for case in spec["cases"]:
                for repetition in range(1, 4):
                    futures = [pool.submit(one, case, repetition, tag) for tag in ("ds", "glm")]
                    for future in futures:
                        row = future.result()
                        sink.write(json.dumps(row, ensure_ascii=False) + "\n")
                        sink.flush()
                        print(row["trial_id"], row["verdict"], "HTTP", row["http_calls"], flush=True)
        with closing(sqlite3.connect(budget)) as db:
            dump(output / "evidence/http-accounting.json", {"cap": 900,
                 "reserved_wire_attempts": [dict(zip(("sequence", "trial_id"), row)) for row in db.execute("SELECT * FROM calls ORDER BY id")]})
    replay(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("capture", "freeze", "run", "replay"))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output", type=Path, default=PACKAGE)
    args = parser.parse_args()
    if args.operation == "capture":
        assert args.source and args.env_file
        manifest = capture(args.source, PACKAGE, args.env_file)
        print("CAPTURED", manifest["source_tree_sha256"], manifest["current_prompt_sha256"])
    elif args.operation == "freeze":
        freeze()
    elif args.operation == "run":
        assert args.env_file
        live(args.env_file, args.output.resolve())
    else:
        replay(args.output.resolve())


if __name__ == "__main__":
    main()
