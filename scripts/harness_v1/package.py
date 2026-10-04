"""Privacy-only packaging, append-only batch aggregation and offline verification.

Run only after batches have completed. Does not contact models or production.
Original failures/grades remain intact; path redaction has before/after hashes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from scripts.harness_v0.prepare import dump, sha
from .grader import grade

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/assessments/harness-v1"


def redact(value, changes, trail=""):
    if isinstance(value, dict):
        return {k: redact(v, changes, trail + "/" + k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, changes, trail + "/" + str(i)) for i, v in enumerate(value)]
    if not isinstance(value, str):
        return value
    revised = re.sub(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/]+[\\/]+AppData[\\/]+Local[\\/]+Temp[\\/]+tianyi-v1-eval-[^\\/]+[\\/]+[^\\/]+[\\/]+fixtures", "{ROOT}", value)
    for source in (str(ROOT), ROOT.as_posix()):
        revised = revised.replace(source, "{SOURCE}")
    revised = re.sub(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/]+[\\/]+AppData[\\/]+Local[\\/]+Programs[\\/]+Python[\\/]+Python\d+", "{PYTHON}", revised)
    if revised != value:
        changes.append(dict(pointer=trail, before_sha256=sha(value), after_sha256=sha(revised)))
    return revised


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def summarize(items):
    return {tag: dict(cases=len({x["case_id"] for x in items if x["model_tag"] == tag}),
        actual_runs=sum(x.get("attempted", True) for x in items if x["model_tag"] == tag),
        verdicts=dict(Counter(x["verdict"] for x in items if x["model_tag"] == tag)),
        http_calls=sum(x["http_calls"] for x in items if x["model_tag"] == tag)) for tag in ("ds", "glm")}


def main(mode):
    cases = {c["id"]: c for c in json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]}
    merged, summaries, provenance = [], {}, {}
    # Reject an unfinished batch before changing any earlier evidence file.
    for batch in (PACKAGE / "batches").iterdir():
        if batch.is_dir():
            registration = json.loads((batch / "registration.json").read_text(encoding="utf-8"))
            assert (batch / "summary.json").exists(), "Batch still running"
            assert len(rows(batch / "results.jsonl")) == len(registration["slots"]), "Incomplete batch"
    for batch in sorted((PACKAGE / "batches").iterdir()):
        if not batch.is_dir():
            continue
        registration = json.loads((batch / "registration.json").read_text(encoding="utf-8"))
        items = rows(batch / "results.jsonl")
        assert (batch / "summary.json").exists(), "Batch still running"
        assert len(items) == len(registration["slots"]), "Incomplete batch"
        assert sha((PACKAGE / "cases.json").read_bytes()) == registration["versions"]["case_sha256"]
        assert sha((PACKAGE / "shared-prompt.txt").read_bytes()) == registration["versions"]["current_prompt_sha256"]
        original_results = (batch / "results.jsonl").read_bytes()
        redactions = []
        for row in items:
            path = PACKAGE / row["evidence_path"]
            assert sha(path.read_bytes()) == row["evidence_sha256"]
            ev = json.loads(path.read_text(encoding="utf-8"))
            original_grade = grade(cases[row["case_id"]], ev)
            assert original_grade["verdict"] == row["verdict"] and original_grade["reasons"] == row["reasons"]
            if mode == "finalize":
                changes = []
                revised = redact(ev, changes)
                if changes:
                    assert original_grade == grade(cases[row["case_id"]], revised), "Privacy redaction must not change grading"
                    before = sha(path.read_bytes())
                    dump(path, revised)
                    row["pre_packaging_evidence_sha256"] = before
                    row["evidence_sha256"] = sha(path.read_bytes())
                    redactions.append(dict(path=row["evidence_path"], before_sha256=before,
                        after_sha256=row["evidence_sha256"], changes=changes, grade_unchanged=True))
            merged.append(row)
        if redactions:
            report = batch / "redaction.json"
            assert not report.exists(), "Redaction already archived"
            (batch / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in items), encoding="utf-8")
            dump(report, dict(results_before_sha256=sha(original_results), results_after_sha256=sha((batch / "results.jsonl").read_bytes()), records=redactions, purpose="privacy-only; no score/criterion modification"))
        summaries[batch.name] = summarize(items)
        runtime = {k: v for k, v in registration["versions"]["files"].items() if k.startswith(("services/agent-core/agent_core/", "apps/avatar-runtime/"))}
        matches = []
        for commit in ("d5394ac336ef0fd2587e0dc0bd4bb0a50be79470", "e7cf5aa54860067e7be409c7ab41e4fbc33bc42b", "0129076f60a5e1bab719b541e44eb939ae8f128b", "a33c1c21d5d7b8288e35ae1bdda448ce8dd1e903", "e111184c759cd1cbb5230b2f210a65d3575f36d3", "c212cba3622f6f2a7f008c6a8ad01e4f585a097b"):
            if all(sha(subprocess.check_output(["git", "show", commit+":"+k], cwd=ROOT)) == v for k, v in runtime.items()):
                matches.append(commit)
        assert matches, "Frozen runtime must map to committed source"
        provenance[batch.name] = dict(runtime_matching_commits=matches, prompt_sha256=registration["versions"]["current_prompt_sha256"], case_sha256=registration["versions"]["case_sha256"])
    accounting = json.loads((PACKAGE / "http-accounting.json").read_text(encoding="utf-8"))
    assert sum(r["http_calls"] for r in merged) == accounting["http_calls"] <= accounting["cap"]
    assert len({r["trial_id"] for r in merged}) == len(merged)
    aggregate = dict(batches=summaries, provenance=provenance, http_calls=accounting["http_calls"], formal_acceptance=False)
    if mode == "finalize":
        unit_redactions = []
        for path in sorted((PACKAGE / "evidence/unit").glob("*.json")):
            old = json.loads(path.read_text(encoding="utf-8")); changes = []
            revised = redact(old, changes)
            if changes:
                before = sha(path.read_bytes()); dump(path, revised)
                unit_redactions.append(dict(path=path.relative_to(PACKAGE).as_posix(), before_sha256=before, after_sha256=sha(path.read_bytes()), changes=changes, assertions_unchanged=True))
        if unit_redactions:
            path = PACKAGE / "evidence/unit-redaction.json"
            assert not path.exists()
            dump(path, unit_redactions)
        (PACKAGE / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in merged), encoding="utf-8")
        dump(PACKAGE / "summary.json", aggregate)
    else:
        assert rows(PACKAGE / "results.jsonl") == merged
        assert json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8")) == aggregate
    print(json.dumps(dict(rows=len(merged), summaries=summaries, provenance=provenance, http_calls=accounting["http_calls"], verified=True), ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("mode", choices=["finalize", "verify"])
    main(parser.parse_args().mode)
