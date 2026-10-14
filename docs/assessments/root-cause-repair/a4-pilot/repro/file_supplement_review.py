"""Independent offline supplement probes; no Core import or real HTTP dispatch."""
from __future__ import annotations

import argparse
import ast
import copy
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import file_runner_review as prior_review


ROOT = Path(__file__).resolve().parents[5]
RUNNER = Path(__file__).with_name("file_models.py")
EVIDENCE = RUNNER.parent.parent / "evidence"
FREEZE = "87ca47420d2a441368684778a3ffc79e7fb849e9"
PRIOR_LEDGER = EVIDENCE / "file-http-ledger.json"
PRIOR_CASE = EVIDENCE / "file-live-glm-3-release.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def dump_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def node(tree: ast.AST, name: str) -> ast.AST:
    return next(item for item in ast.walk(tree)
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and item.name == name)


def arguments(directory: Path, label: str = "case") -> SimpleNamespace:
    return SimpleNamespace(source_root=ROOT, private_config=directory / "never-read.env",
        provider="glm", variant=3, http_budget=8, prior_ledger=PRIOR_LEDGER,
        supplement_of=PRIOR_CASE, ledger=directory / f"{label}-ledger.json",
        data_dir=directory / label, offline=False, initial_report=[])


def budget_probes(tree: ast.AST, directory: Path, case: dict) -> list[dict]:
    namespace = {"CAP": 30, "json": json, "hashlib": hashlib, "Path": Path}
    authorize = prior_review.extract(tree, "supplement_budget", namespace)
    hashes = case["source_sha256"]
    results = []
    args = arguments(directory)
    ledger, linked = authorize(args, hashes)
    results.append({"case": "bounded_linked_supplement", "passed": ledger["cap"] == 8
        and ledger["prior_attempts"] == 30 and ledger["attempts"] == [] and linked == case
        and ledger["supplement"]["prior_ledger_sha256"] == sha(PRIOR_LEDGER)
        and ledger["supplement"]["interrupted_case_sha256"] == sha(PRIOR_CASE)})
    variants = [
        ("budget_above_eight", {"http_budget": 9}),
        ("budget_zero", {"http_budget": 0}),
        ("missing_prior", {"prior_ledger": None}),
        ("missing_case", {"supplement_of": None}),
        ("wrong_provider", {"provider": "deepseek"}),
        ("wrong_variant", {"variant": 2}),
        ("overwrite_prior_ledger", {"ledger": PRIOR_LEDGER}),
        ("overwrite_old_case", {"ledger": PRIOR_CASE}),
    ]
    for label, changes in variants:
        candidate = arguments(directory, label)
        vars(candidate).update(changes)
        try:
            authorize(candidate, hashes)
        except SystemExit as exc:
            results.append({"case": label, "passed": True, "rejection": str(exc)})
        else:
            results.append({"case": label, "passed": False})
    existing = directory / "existing-ledger.json"
    dump_new(existing, ledger)
    candidate = arguments(directory, "reuse")
    candidate.ledger = existing
    try:
        authorize(candidate, hashes)
    except SystemExit:
        results.append({"case": "existing_supplement_rejected", "passed": True})
    else:
        results.append({"case": "existing_supplement_rejected", "passed": False})
    for label, key, value in (("wrong_source", "source_sha256", {}),
                              ("already_passed", "passed", True),
                              ("offline_reference", "offline", True),
                              ("not_exhausted", "shared_http_attempts", 29)):
        invalid = copy.deepcopy(case)
        invalid[key] = value
        path = directory / f"{label}.json"
        dump_new(path, invalid)
        candidate = arguments(directory, label)
        candidate.supplement_of = path
        try:
            authorize(candidate, hashes)
        except SystemExit:
            results.append({"case": label, "passed": True})
        else:
            results.append({"case": label, "passed": False})
    return results


def observer_probes(tree: ast.AST, projection: object) -> list[dict]:
    dispatches = []
    saves = []

    class Parent:
        model = "synthetic-model"

        def _request(self, request: object) -> bytes:
            dispatches.append(len(dispatches) + 1)
            return prior_review.response()

    ledger = {"cap": 8, "prior_attempts": 30, "attempts": []}
    observer = prior_review.make_observer(tree, projection, Parent, ledger,
        {"calls": []}, lambda: saves.append(len(ledger["attempts"])))
    rejected = False
    for _ in range(9):
        try:
            observer._request(prior_review.synthetic_request())
        except RuntimeError:
            rejected = True
    return [{"case": "eighth_allowed_ninth_blocked_at_cumulative_38",
        "passed": len(dispatches) == 8 and rejected
        and [a["index"] for a in ledger["attempts"]] == list(range(31, 39)),
        "in_memory_dispatches": len(dispatches), "indices": [a["index"] for a in ledger["attempts"]],
        "save_counts": saves}]


def repeat_entry_probe(tree: ast.AST, directory: Path, case: dict) -> dict:
    """Exercise exact main preflight twice with two paths and a fake run body."""
    prior_copy = directory / "repeat-original-ledger.json"
    case_copy = directory / "repeat-interrupted-case.json"
    dump_new(prior_copy, json.loads(PRIOR_LEDGER.read_text(encoding="utf-8")))
    dump_new(case_copy, case)
    calls = []

    def fake_run(args: SimpleNamespace, *_: object) -> int:
        calls.append(str(args.ledger))
        record = args.supplement_ledger
        record["attempts"] = [{"index": i, "model": "synthetic", "request_id": "fixture"}
                              for i in range(31, 39)]
        dump_new(args.ledger, record)
        return 0

    namespace = {"__doc__": "Synthetic supplement entry test", "argparse": argparse,
        "Path": Path, "CAP": 30, "SAMPLES": {1: None, 2: None, 3: None}, "sys": sys,
        "os": os, "json": json, "hashlib": hashlib,
        "source_hashes": lambda _: case["source_sha256"],
        "read_connection": lambda _: {}, "run": fake_run}
    for helper in ("supplement_budget", "claim_supplement", "main"):
        prior_review.extract(tree, helper, namespace)
    failures = []
    for label in ("repeat-first", "repeat-second"):
        args = arguments(directory, label)
        args.prior_ledger, args.supplement_of = prior_copy, case_copy
        with patch.object(argparse.ArgumentParser, "parse_args", return_value=args):
            try:
                namespace["main"]()
            except (SystemExit, FileExistsError) as exc:
                failures.append(str(exc))
    return {"case": "second_supplement_cannot_reset_budget_by_changing_ledger",
        "passed": len(calls) == 1, "accepted_run_count": len(calls),
        "synthetic_cumulative_attempts": 30 + 8 * len(calls), "rejections": failures,
        "real_http_attempts": 0}


def equivalence_probes(tree: ast.AST, original: ast.AST) -> list[dict]:
    names = ("score", "exercise", "audit", "read_connection")
    return [{"case": f"unchanged_{name}_ast", "passed": ast.dump(node(tree, name))
             == ast.dump(node(original, name))} for name in names]


def contract_probes(tree: ast.AST, case: dict) -> list[dict]:
    """Execute the new model and task equivalence guards without a Provider."""
    gates = []
    for item in ast.walk(tree):
        if isinstance(item, ast.If) and any(isinstance(part, ast.Raise) for part in item.body):
            wording = ast.unparse(item)
            if "Supplement model differs" in wording or "Supplement changed the task" in wording:
                gates.append(item)
    keys = ("budget", "initial_state_sha256", "tool_schema_sha256", "input_normalized_sha256")
    results = []
    for changed in (None, "model", *keys):
        record = copy.deepcopy(case)
        namespace = {"args": SimpleNamespace(reference_case=case), "model": case["model"],
                     "record": record, "keys": keys}
        if changed == "model":
            namespace["model"] = "wrong-model"
        elif changed is not None:
            record[changed] = "synthetic mismatch"
        rejected = False
        try:
            for gate in gates:
                exec(compile(ast.fix_missing_locations(ast.Module(body=[gate], type_ignores=[])),
                             str(RUNNER), "exec"), namespace)
        except RuntimeError:
            rejected = True
        results.append({"case": f"contract_guard_{changed or 'unchanged'}",
                        "passed": len(gates) == 2 and rejected is (changed is not None)})
    return results


def live_delivery_probes(record: dict) -> tuple[list[dict], Path]:
    """Check the synthetic output and receipt chain without importing Core."""
    target = Path(record["expected"]["path"]).resolve()
    permitted = Path("D:/TianyiRepair/file-supplement-20261014").resolve()
    if not target.is_relative_to(permitted):
        raise ValueError("Live evidence target is outside the authorized synthetic directory")
    body = record["expected"]["content"]
    target_hash = sha(target)
    actions = record["actions"]
    reads = [item for task in record["tasks"] for item in task.get("tool_results", [])
             if item["tool"] == "read_file"]
    valid_actions = [item for item in actions if item["tool"] == "write_file"
        and item["status"] == "succeeded" and item["arguments"]["content"] == body
        and Path(item["arguments"]["path"]).resolve() == target
        and item["receipt"]["sha256"] == target_hash
        and item["session_id"] == record["session_id"] and item["task_id"] == "file-3-request"]
    valid_reads = [item for item in reads if item["result"].get("ok") is True
        and item["result"].get("content") == body and item["result"].get("truncated") is False
        and Path(item["arguments"]["path"]).resolve() == target
        and item["session_id"] == record["session_id"] and item["task_id"] == "file-3-request"
        and any(action["action_id"] in item.get("after_actions", []) for action in valid_actions)]
    effects = record["effects"]
    turns = record["turns"]
    checks = [{"case": "live_exact_bytes_and_success_receipt", "passed": len(valid_actions) == 1
        and target.read_bytes() == body.encode("utf-8") and target_hash == record["expected"]["sha256"],
        "actual_file_sha256": target_hash},
        {"case": "live_independent_read_bound_after_write", "passed": bool(valid_reads),
         "bound_reads": len(valid_reads)},
        {"case": "live_normal_confirmation_full_delivery_and_no_rewrite",
         "passed": len(turns) == 4 and [item["input"] for item in turns[1:]]
         == ["确认", "确认", "刚才那个任务现在怎么样？"] and body in turns[1]["answer"]
         and "文件任务已完成" in turns[1]["answer"]
         and sum(item["tool"] == "write_file" for item in effects) == 1
         and sum(item["tool"] == "read_file" for item in effects) >= 1
         and bool(turns[0]["pending"]) and not turns[1]["pending"]}]
    return checks, target.parent.parent / "db" / "anime-agent.sqlite3"


def database_probes(record: dict, path: Path) -> list[dict]:
    """Read only the completed, isolated model-run database and retain its hash."""
    before = sha(path)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        messages = [{"role": role, "content": content} for role, content in connection.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (record["session_id"],))]
        actions = [json.loads(row[0]) for row in connection.execute(
            "SELECT payload FROM harness_actions WHERE session_id = ?", (record["session_id"],))]
        events = [{"type": kind, "payload": json.loads(payload)} for kind, payload in connection.execute(
            "SELECT event_type, payload FROM events WHERE event_type IN "
            "('tool.result','task.decision','chat.delivery') ORDER BY id")]
    return [{"case": "live_readonly_database_reopen_matches_messages_actions_events",
             "passed": messages == record["messages"] and actions == record["actions"]
             and events == record["events"] and any(item["type"] == "tool.result" for item in events)
             and before == sha(path), "database_sha256_before": before,
             "database_sha256_after": sha(path), "message_count": len(messages),
             "action_count": len(actions), "event_count": len(events)}]


def live_review(args: argparse.Namespace) -> int:
    record = json.loads(args.live_report.read_text(encoding="utf-8"))
    ledger = json.loads(args.live_ledger.read_text(encoding="utf-8"))
    previous = json.loads(PRIOR_CASE.read_text(encoding="utf-8"))
    offline = json.loads((EVIDENCE / "file-supplement-review-offline.json").read_text(encoding="utf-8"))
    runner_path = RUNNER.relative_to(ROOT).as_posix()
    diff_hash = hashlib.sha256(git("diff", FREEZE, "--", runner_path)).hexdigest()
    calls = record["calls"]
    link = record["supplement"]
    claim = json.loads(Path(link["claim"]).read_text(encoding="utf-8"))
    required = ("no_preconfirm_effect", "real_proposal", "correct_write", "actual_read",
                "receipt_bound", "complete_delivery", "no_duplicate_write", "truthful_progress",
                "history_reopened", "ledger_reopened", "reads_reopened", "source_unchanged")
    checks = [{"case": "live_single_glm_variant3_all_original_assertions",
        "passed": record["passed"] is True and not record.get("exception")
        and record["offline"] is False and record["provider"] == "glm" and record["variant"] == 3
        and record["model"] == previous["model"]
        and all(record["checks"].get(key) is True for key in required)},
        {"case": "live_contract_and_business_frozen", "passed": all(record[key] == previous[key]
         for key in ("protocol", "budget", "initial_state_sha256", "input_normalized_sha256",
                     "tool_schema_sha256", "source_sha256"))
         and record["expected"]["content"] == previous["expected"]["content"]
         and record["source_sha256"] == {path.name: sha(path) for path in prior_review.CORE_DIR.glob("*.py")}
         and not git("diff", FREEZE, "--", "services/agent-core", "apps/avatar-runtime")},
        {"case": "live_runner_bound_to_independent_offline_review",
         "passed": offline["passed"] is True and diff_hash == offline["runner_diff_sha256"]
         and record["runner_sha256"] == {name: sha(RUNNER.with_name(name))
                                       for name in ("file_models.py", "models.py")}},
        {"case": "live_original_30_plus_bounded_additional_attempts",
         "passed": 1 <= len(calls) <= 8 and ledger["cap"] == record["transport_cap"] == 8
         and ledger["prior_attempts"] == 30 and ledger["supplement"] == link
         and [item["index"] for item in calls] == list(range(31, 31 + len(calls)))
         and ledger["attempts"] == [{key: item[key] for key in ("index", "model", "request_id")}
                                    for item in calls]
         and record["http_attempts"] == record["shared_http_attempts"] == len(calls)
         and record["cumulative_http_attempts"] == 30 + len(calls),
         "additional_attempts": len(calls), "cumulative_attempts": 30 + len(calls)},
        {"case": "live_claim_and_original_evidence_immutable",
         "passed": link["prior_ledger_sha256"] == sha(PRIOR_LEDGER)
         and link["interrupted_case_sha256"] == sha(PRIOR_CASE)
         and record["prior_evidence_unchanged"] is True
         and Path(claim["ledger"]).resolve() == args.live_ledger.resolve()
         and claim["prior_ledger_sha256"] == sha(PRIOR_LEDGER)
         and claim["interrupted_case_sha256"] == sha(PRIOR_CASE)}]
    delivery, database = live_delivery_probes(record)
    checks += delivery + database_probes(record, database)
    result = {"scope": "Independent read-only verification of the one new live model report and synthetic artifacts",
        "frozen_commit": FREEZE, "runner_diff_sha256": diff_hash,
        "real_http_attempts_by_reviewer": 0, "reviewed_report_sha256": sha(args.live_report),
        "reviewed_ledger_sha256": sha(args.live_ledger), "checks": checks,
        "passed": all(item["passed"] for item in checks)}
    dump_new(args.output, result)
    print(json.dumps({"passed": result["passed"], "checks": checks,
                      "evidence": str(args.output)}, ensure_ascii=False))
    return 0 if result["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--live-report", type=Path)
    parser.add_argument("--live-ledger", type=Path)
    args = parser.parse_args()
    args.data_dir = args.data_dir.resolve()
    args.output = args.output.resolve()
    if args.data_dir.exists() or args.output.exists():
        raise SystemExit("Refusing to overwrite independent review evidence")
    args.data_dir.mkdir(parents=True)
    if args.live_report is not None or args.live_ledger is not None:
        if args.live_report is None or args.live_ledger is None:
            parser.error("Live review requires both report and ledger")
        return live_review(args)
    case = json.loads(PRIOR_CASE.read_text(encoding="utf-8"))
    before = {str(path.relative_to(ROOT)): sha(path) for path in (RUNNER, PRIOR_CASE, PRIOR_LEDGER)}
    runner_path = RUNNER.relative_to(ROOT).as_posix()
    diff = git("diff", FREEZE, "--", runner_path)
    frozen_source = git("show", f"{FREEZE}:{runner_path}").decode("utf-8")
    business_diff = git("diff", FREEZE, "--", "services/agent-core", "apps/avatar-runtime")
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    original = ast.parse(frozen_source)
    projection = prior_review.load_module("supplement_projection", RUNNER.with_name("models.py"))
    transport = prior_review.load_module("supplement_transport", prior_review.CORE_DIR / "provider_http.py")
    loop = prior_review.asyncio.new_event_loop()
    cleanup_loop = prior_review.asyncio.new_event_loop()
    with patch.object(socket.socket, "connect", side_effect=AssertionError("No network")), \
            patch.object(socket, "create_connection", side_effect=AssertionError("No network")):
        checks = equivalence_probes(tree, original) + budget_probes(tree, args.data_dir, case)
        checks += observer_probes(tree, projection) + prior_review.dispatch_probes(tree, projection)
        checks += prior_review.isolation_probes(tree, args.data_dir)
        checks += prior_review.grader_probes(tree)
        checks += contract_probes(tree, case)
        try:
            checks.append(loop.run_until_complete(prior_review.retry_probe(tree, projection, transport)))
        finally:
            loop.run_until_complete(loop.shutdown_default_executor())
            loop.close()
        checks.append(prior_review.late_save_probe(tree, projection, transport, args.data_dir, cleanup_loop))
        checks.append(repeat_entry_probe(tree, args.data_dir, case))
    after = {str(path.relative_to(ROOT)): sha(path) for path in (RUNNER, PRIOR_CASE, PRIOR_LEDGER)}
    business_hashes = {path.name: sha(path) for path in prior_review.CORE_DIR.glob("*.py")}
    checks.append({"case": "business_frozen_and_prior_evidence_immutable",
                   "passed": not business_diff and before == after and business_hashes == case["source_sha256"]})
    record = {"scope": "AST and synthetic in-memory HTTP only; no Core/private config/production database",
        "frozen_commit": FREEZE, "runner_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "source_sha256_before": before, "source_sha256_after": after,
        "real_http_attempts": 0, "checks": checks,
        "static_tools_available": [name for name in ("ruff", "mypy", "pylint", "black")
                                   if importlib.util.find_spec(name) is not None],
        "passed": all(check["passed"] for check in checks)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dump_new(args.output, record)
    print(json.dumps({"passed": record["passed"], "checks": len(checks),
        "failures": [check for check in checks if not check["passed"]],
        "runner_diff_sha256": record["runner_diff_sha256"], "evidence": str(args.output)}, ensure_ascii=False))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
