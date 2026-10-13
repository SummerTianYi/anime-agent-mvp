"""Replay only the historical cross-turn pending counterexample, offline.

Reuses the existing independent fixture's in-memory DB and I/O audit guard.
No direct Core import occurs outside that fixture. Refuses evidence overwrite.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest


def acceptance_checks(cases):
    turns = cases[0].get("turns", []) if len(cases) == 1 else []
    status = turns[-1] if len(turns) == 2 else {}
    return {
        "two_real_chat_turns": len(turns) == 2,
        "no_hidden_exception": bool(turns) and all("exception" not in turn for turn in turns),
        "pending_answer_delivered": "待确认，尚未执行" in status.get("reply", ""),
        "pending_action_preserved": bool(status.get("actions")) and all(
            item["status"] == "awaiting_confirmation" for item in status.get("actions", [])),
        "query_did_not_call_model_or_executor": status.get("model_calls") == 0
            and status.get("plain_model_calls") == 0 and status.get("effects") == [],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite evidence")
    root = args.source_root.resolve()
    sys.dont_write_bytecode = True
    os.environ["HARNESS_REVIEW_CORE_ROOT"] = str(root / "services/agent-core")
    sys.path.insert(0, str(root / "services/agent-core/tests"))
    import test_harness_v1_review as fixture
    if fixture.CORE_ROOT.resolve() != root / "services/agent-core":
        raise SystemExit("Fixture source root mismatch")
    path = Path(__file__).with_name("independent.py")
    spec = importlib.util.spec_from_file_location("pending_historical_repro", path)
    repro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repro)
    before = repro.hashes(root)
    suite = unittest.TestSuite(case for case in repro.build_suite(fixture.IndependentReviewTests)
        if case._testMethodName == "test_pending_task_cannot_be_relabelled_completed_on_later_turn")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = repro.hashes(root)
    checks = acceptance_checks(repro.CASES)
    passed = result.wasSuccessful() and before == after and result.testsRun == 1 and all(checks.values())
    record = {"tests": result.testsRun, "passed": passed, "failures": len(result.failures),
        "errors": len(result.errors), "source_sha256": after, "source_stable": before == after,
        "actual_core_root": str(fixture.CORE_ROOT.resolve()), "acceptance_checks": checks,
        "cases": repro.CASES, "real_model_calls": 0, "external_calls": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: record[k] for k in ("tests", "passed", "failures", "errors", "source_stable")}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
