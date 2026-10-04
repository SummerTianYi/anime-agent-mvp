"""One-time packaging redaction of clipped temporary path titles, not regrading.

The frozen worker already removes full paths. Core's fallback session title can
clip a path BEFORE that removal, leaving C:/Users or C:/Users/2. Preserve changes
and old hashes, assert the frozen grades stay exactly identical.
"""
import json
import re
import sys
from pathlib import Path

from .grader import grade
from .prepare import dump, sha
from .runner import PACKAGE, verify


def clean(value, trail="", changes=None):
    if isinstance(value, dict):
        return {k: clean(v, trail + "/" + k, changes) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v, trail + "/" + str(i), changes) for i, v in enumerate(value)]
    if isinstance(value, str):
        new = value.replace("C:/Users/2", "{TEMP_PREFIX}").replace("C:/Users", "{TEMP_PREFIX}")
        new = re.sub(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/]+[\\/]+AppData[\\/]+Local[\\/]+Temp[\\/]+(?:tianyi-harness-v0|harness-calibration|harness-offline-audit)-[^\\/]+[\\/]+[^\\/]+[\\/]+fixtures", "{ROOT}", new)
        if new != value:
            changes.append({"json_pointer": trail, "before_sha256": sha(value), "after_sha256": sha(new),
                            "reason": "synthetic temporary path in automatic title or multiply JSON-escaped receipt"})
        return new
    return value


def main():
    verify()
    if "--offline" in sys.argv:
        return offline()
    report = PACKAGE / "evidence/redaction-nested-manifest.json"
    assert not report.exists(), "Redaction already archived"
    cases = {c["id"]: c for c in json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]}
    results = PACKAGE / "results.jsonl"
    original = results.read_bytes()
    rows = [json.loads(x) for x in original.decode("utf-8").splitlines()]
    records = []
    for row in rows:
        path = PACKAGE / row["evidence_path"]
        old_hash = sha(path.read_bytes())
        ev = json.loads(path.read_text(encoding="utf-8"))
        changes = []
        revised = clean(ev, changes=changes)
        if changes:
            before, after = grade(cases[row["case_id"]], ev), grade(cases[row["case_id"]], revised)
            assert before == after, "Packaging must not alter scoring"
            dump(path, revised)
            row["evidence_sha256"] = sha(path.read_bytes())
            row.setdefault("pre_packaging_evidence_sha256", old_hash)
            records.append({"evidence_path": row["evidence_path"], "before_sha256": old_hash,
                            "after_sha256": row["evidence_sha256"], "changes": changes, "grade_unchanged": True})
    # No score fields change; the original SHA and exact per-field redaction are
    # retained, while only the publishable sanitized evidence is committed.
    results.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    dump(report, {"reason": "packaging privacy-only redaction; not case/criteria/version change",
         "results_before_sha256": sha(original), "results_after_sha256": sha(results.read_bytes()),
         "all_scores_unchanged": True, "records": records})
    print("REDACTED_TITLE_PREFIXES", len(records), "SCORES_UNCHANGED")


def offline():
    report = PACKAGE / "evidence/redaction-offline-manifest.json"
    assert not report.exists()
    records = []
    cases = {c["id"]: c for c in json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]}
    summary_path = PACKAGE / "evidence/offline-audit/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    for directory in ("calibration", "offline-audit"):
        for path in (PACKAGE / "evidence" / directory).glob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8")); changes = []
            revised = clean(value, changes=changes)
            if not changes:
                continue
            old_hash = sha(path.read_bytes())
            if value.get("case_id"):
                assert grade(cases[value["case_id"]], value) == grade(cases[value["case_id"]], revised)
            dump(path, revised)
            relative = path.relative_to(PACKAGE).as_posix()
            records.append({"evidence_path": relative, "before_sha256": old_hash, "after_sha256": sha(path.read_bytes()), "changes": changes, "grade_unchanged": True})
            for probe in summary["probes"]:
                if probe["evidence"] == relative:
                    probe["pre_packaging_sha256"] = probe["sha256"]
                    probe["sha256"] = sha(path.read_bytes())
    dump(summary_path, summary)
    dump(report, {"records": records, "real_http_calls": 0, "all_scores_unchanged": True})
    print("OFFLINE_REDACTION", len(records))


if __name__ == "__main__":
    main()
