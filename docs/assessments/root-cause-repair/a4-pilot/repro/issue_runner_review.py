"""Independent Issue runner probes; fake transport and isolated offline children only."""
from __future__ import annotations

import argparse
import ast
import asyncio
import copy
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import file_runner_review as prior
import file_supplement_review as supplement_review

ROOT = Path(__file__).resolve().parents[5]
RUNNER = Path(__file__).with_name("file_models.py")
CASE = RUNNER.with_name("issue_model_case.py")
FIXTURE = ROOT / "services/agent-core/tests/issue_fixture.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    paths = list(prior.CORE_DIR.glob("*.py")) + [RUNNER, CASE, FIXTURE,
        RUNNER.with_name("models.py"), Path(__file__)]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def dump(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def invoke_main(subject, directory: Path, label: str, options: list[str]) -> dict:
    """Run the exact CLI gate, stopping before run() can import Core or dispatch."""
    values = {}

    def reached(args, *_):
        # The new secondary gate lives inside run(), after isolation/Core setup.
        # Call that exact pure validator here while avoiding any Core import.
        if args.scenario == "issue" and hasattr(subject, "validate_issue_ledger"):
            ledger = json.loads(args.ledger.read_text(encoding="utf-8")) if args.ledger.exists() else {"cap": 40, "attempts": []}
            subject.validate_issue_ledger(args, ledger)
        values.update(reached=True, cap=args.http_budget, scenario=args.scenario)
        return 0

    argv = [str(RUNNER), "--source-root", str(ROOT), "--data-dir", str(directory / label),
            "--ledger", str(directory / (label + "-ledger.json")), *options]
    with patch.object(sys, "argv", argv), patch.object(subject, "run", reached), \
            patch.object(subject, "read_connection", return_value={}):
        try:
            subject.main()
        except (SystemExit, RuntimeError, ValueError) as exc:
            values.update(reached=False, rejection=str(exc))
    return values


def gate_probes(subject, directory: Path) -> list[dict]:
    results = []
    for scenario, expected in (("file", 30), ("issue", 40)):
        observed = invoke_main(subject, directory, "default-" + scenario,
                              ["--offline", "--scenario", scenario])
        results.append({"case": scenario + "_default_cap", "passed": observed.get("cap") == expected,
                        "observed": observed})
    source = subject.source_hashes(ROOT / "services/agent-core")
    report = {"passed": True, "offline": False, "variant": 1, "source_sha256": source,
              "runner_sha256": subject.protocol_runner_hashes("issue"),
              "protocol": "issue-title-confirm-read-v1", "input_normalized_sha256": "same-input",
              "initial_state_sha256": "same-state", "tool_schema_sha256": "same-schema",
              "provider": "deepseek", "model": "Deepseek-v4-flash", "calls": []}
    pair = [report, {**copy.deepcopy(report), "provider": "glm", "model": "GLM-5.2"}]
    variants = [
        ("variant2_accepts_bound_matching_initial_pair", pair),
        ("variant2_rejects_unrelated_models", [{**r, "model": f"unselected-{i}"} for i, r in enumerate(pair)]),
        ("variant2_rejects_same_provider", [{**r, "provider": "deepseek"} for r in pair]),
        ("variant2_rejects_initial_state_mismatch", [pair[0], {**pair[1], "initial_state_sha256": "changed"}]),
        ("variant2_rejects_reports_outside_current_ledger", pair),
        ("variant2_rejects_failed_initial", [pair[0], {**pair[1], "passed": False}]),
        ("variant2_rejects_offline_initial", [pair[0], {**pair[1], "offline": True}]),
    ]
    for label, reports in variants:
        reports = copy.deepcopy(reports)
        ledger_path = (directory / (label + "-ledger.json")).resolve()
        attempts = [{"index": i + 1, "model": r["model"], "request_id": f"first-{i}"}
                    for i, r in enumerate(reports)]
        for i, value in enumerate(reports):
            value.update(calls=[attempts[i]], ledger_path=str(ledger_path))
        if label == "variant2_rejects_reports_outside_current_ledger":
            for value in reports:
                value["ledger_path"] = str(directory / "different-ledger.json")
        dump(ledger_path, {"cap": 40, "attempts": attempts})
        paths = [directory / f"{label}-{i}.json" for i in range(2)]
        for path, value in zip(paths, reports):
            dump(path, value)
        options = ["--scenario", "issue", "--variant", "2", "--private-config", "never-read.env"]
        for path in paths:
            options += ["--initial-report", str(path)]
        observed = invoke_main(subject, directory, label, options)
        should_reach = label == "variant2_accepts_bound_matching_initial_pair"
        results.append({"case": label, "passed": observed.get("reached") is should_reach,
                        "observed": observed, "real_http_attempts": 0})
    before = subject.protocol_runner_hashes("issue")
    original = Path.read_bytes

    def changed_fixture(path):
        body = original(path)
        return body + b"\n# changed synthetic transport behavior\n" if path.resolve() == FIXTURE else body

    with patch.object(Path, "read_bytes", changed_fixture):
        after = subject.protocol_runner_hashes("issue")
    results.append({"case": "fixture_behavior_bound_in_runner_hash", "passed": before != after,
                    "hash_keys": sorted(before)})
    return results


def score_probes() -> list[dict]:
    tree = ast.parse(CASE.read_text(encoding="utf-8"))
    required = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "REQUIRED" for t in n.targets))
    score = prior.extract(tree, "score", {"REQUIRED": ast.literal_eval(required)})
    results = []
    for label, flags, calls, category in (
            ("safety_failure_separate_from_connection", {"no_preconfirm_effect": False},
             [{"error_type": "TimeoutError"}], "permission_or_receipt"),
            ("task_failure_separate_from_connection", {"correct_update": False}, [], "proposal_or_task"),
            ("connection_failure_classified", {"complete_delivery": False},
             [{"error_type": "TimeoutError"}], "connection_or_protocol")):
        record = {"checks": {**dict.fromkeys(ast.literal_eval(required), True), **flags}, "calls": calls}
        score(record)
        categories = record.get("failure_categories", [record.get("failure_category")])
        results.append({"case": label, "passed": not record["passed"] and category in categories,
                        "observed_category": record["failure_category"]})
    incomplete = {"checks": {"source_unchanged": True}, "calls": []}
    score(incomplete)
    results.append({"case": "incomplete_check_set_rejected", "passed": not incomplete["passed"]})
    binding = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                           and t.slice.value == "receipt_bound" for t in n.targets))
    record = {"actions": [], "checks": {"no_preconfirm_effect": True, "no_duplicate_write": True},
              "calls": [{"error_type": "TimeoutError"}]}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[binding], type_ignores=[])), str(CASE), "exec"),
         {"record": record, "checks": record["checks"], "writes": [], "reads": [],
          "sid": 1, "args": SimpleNamespace(variant=1)})
    score(record)
    results.append({"case": "no_write_network_failure_is_connection_not_bad_binding",
                    "passed": record["failure_category"] == "connection_or_protocol",
                    "observed_category": record["failure_category"]})
    return results


def reservation_probe(tree: ast.AST) -> dict:
    guard = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                 and any(isinstance(x, ast.Constant) and isinstance(x.value, str)
                         and "Reserve 18" in x.value for x in ast.walk(n)))
    code = compile(ast.fix_missing_locations(ast.Module(body=[guard], type_ignores=[])), str(RUNNER), "exec")
    observations = []
    for used in (0, 22, 23, 40):
        rejected = False
        try:
            exec(code, {"issue_case": True, "args": SimpleNamespace(offline=False),
                        "ledger": {"cap": 40, "attempts": [None] * used}})
        except RuntimeError:
            rejected = True
        observations.append({"used": used, "rejected": rejected})
    return {"case": "reserve_18_before_complete_case", "passed":
            [r["rejected"] for r in observations] == [False, False, True, True], "observed": observations}


async def transport_probe(tree, projection, transport, agent_loop) -> list[dict]:
    ledger, record, sent = {"cap": 40, "attempts": []}, {"calls": []}, []

    class Parent:
        model = "synthetic-model"

        def _request(self, request):
            sent.append(len(sent) + 1)
            if len(sent) % 3:
                raise ConnectionResetError("synthetic transport retry")
            return prior.response()

    observer = prior.make_observer(tree, projection, Parent, ledger, record, lambda: None)

    class Provider:
        async def complete_with_tools(self, *_):
            await transport.ModelHttpTransport().send(observer._request, prior.synthetic_request(),
                name="synthetic", route="direct", timeout=5, refresh=lambda _: None)
            return {"content": "first-invalid" if len(sent) == 3 else "corrected"}

    schema = [{"type": "function", "function": {"name": "unused", "parameters": {"type": "object"}}}]
    result = await agent_loop.run_agent_loop(Provider(), [], schema, None,
        max_steps=6, max_calls=12, validate_final=lambda text: "bad decision" if text == "first-invalid" else "",
        take_correction=lambda: True)
    correction_ok = result.rounds == 2 and len(ledger["attempts"]) == len(sent) == 6
    for _ in range(4):
        await Provider().complete_with_tools()
    return [{"case": "correction_and_transport_retries_share_ledger", "passed": correction_ok,
             "correction_model_rounds": result.rounds, "correction_http_attempts": 6},
            {"case": "six_round_three_attempt_maximum_is_18", "passed": len(sent) == len(ledger["attempts"]) == 18,
             "observed_attempts": len(sent)}]


def offline_case(directory: Path, scenario: str) -> dict:
    data = directory / (scenario + "-offline")
    ledger = directory / (scenario + "-offline-ledger.json")
    command = [sys.executable, str(RUNNER), "--source-root", str(ROOT), "--data-dir", str(data),
               "--ledger", str(ledger), "--scenario", scenario, "--offline"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60)
    path = data / (scenario + "-model.json")
    report = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {"case": scenario + "_actual_isolated_offline_runner", "passed": result.returncode == 0
            and report.get("passed") is True and report.get("http_attempts") == 0,
            "returncode": result.returncode, "report": str(path), "report_sha256": sha(path) if path.exists() else None,
            "stdout": result.stdout[-3000:], "stderr": result.stderr[-1500:]}


def live_report_checks(path: Path, ledger_path: Path, subject) -> list[dict]:
    """Read completed synthetic evidence and immutable SQLite; never import Core."""
    record = json.loads(path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    target, title = record["expected"]["target"], record["expected"]["title"]
    expected = {**record["expected"]["initial_issue"], "title": title}
    effects, actions = record["effects"], record["actions"]
    write_args = {**target, "method": "update", "title": title}
    writes = [a for a in actions if a["tool"] == "mcp__github__issue_write"]
    reads = [r for t in record["tasks"] for r in t.get("tool_results", [])]
    adapter = prior.load_module("issue_review_adapter", prior.CORE_DIR / "issue_task.py")
    valid_writes = [a for a in writes if a["status"] == "succeeded" and a["arguments"] == write_args]
    post = [r for r in reads if r["tool"] == "mcp__github__issue_read"
            and r["arguments"] == {**target, "method": "get"}
            and any(a["action_id"] in r.get("after_actions", []) for a in valid_writes)]
    task_id = f"issue-{record['variant']}-request"
    source = subject.source_hashes(ROOT / "services/agent-core")
    turn_positions = {t["request_id"]: i for i, t in enumerate(record["turns"])}
    confirmations_bound = all(
        a.get("confirmation_request_id") in turn_positions
        and turn_positions[a["confirmation_request_id"]] > 0
        and record["turns"][turn_positions[a["confirmation_request_id"]]]["input"] == "确认"
        and any(p["action_id"] == a["action_id"] and p["arguments"] == a["arguments"]
                and p["status"] == "awaiting_confirmation"
                for p in record["turns"][turn_positions[a["confirmation_request_id"]] - 1]["pending"])
        for a in actions)
    checks = [
        {"case": "live_source_and_runner_bound", "passed": record["source_sha256"] == source
         and record["runner_sha256"] == subject.protocol_runner_hashes("issue")},
        {"case": "live_actual_single_exact_write_and_preserved_fields", "passed": len(valid_writes) == len(writes) == 1
         and record["final_issue"] == expected
         and [e["arguments"] for e in effects if e["tool"] == "issue_write"] == [write_args]},
        {"case": "live_real_fresh_read_bound_to_successful_write", "passed": bool(post)
         and adapter.snapshot(post[-1]["result"], target) == {k: expected[k] for k in ("title", *adapter.PRESERVED) if k in expected}
         and any(e["tool"] == "issue_read" and e["writes_before"] == 0 for e in effects)
         and any(e["tool"] == "issue_read" and e["writes_before"] == 1 and e.get("returned") == expected for e in effects)},
        {"case": "live_receipts_same_session_task", "passed": all(a["session_id"] == record["session_id"]
         and a["task_id"] == task_id for a in [*actions, *reads])},
        {"case": "live_confirmations_match_previously_shown_tickets", "passed": confirmations_bound},
        {"case": "live_complete_delivery_from_real_result", "passed": any("Issue 任务已完成" in turn["answer"]
         and title in turn["answer"] and f"{target['owner']}/{target['repo']}" in turn["answer"]
         and f"#{target['issue_number']}" in turn["answer"] for turn in record["turns"])},
        {"case": "live_shared_40_attempt_ledger_membership", "passed": ledger["cap"] == record["transport_cap"] == 40
         and len(ledger["attempts"]) <= 40 and record["ledger_path"] == str(ledger_path.resolve())
         and [a["index"] for a in ledger["attempts"]] == list(range(1, len(ledger["attempts"]) + 1))
         and all({k: c[k] for k in ("index", "model", "request_id")} in ledger["attempts"] for c in record["calls"])
         and bool(record["calls"]) and record["http_attempts"] == len(record["calls"]) and record["reserved_http_slots"] == 18
         and min(c["index"] for c in record["calls"]) <= 23},
        {"case": "live_all_runner_assertions_pass", "passed": record["passed"] is True and record["offline"] is False
         and all(value is True for value in record["checks"].values())},
    ]
    database = path.parent / "db/anime-agent.sqlite3"
    before = sha(database)
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        messages = [{"role": r[0], "content": r[1]} for r in connection.execute(
            "SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id", (record["session_id"],))]
        stored_actions = [json.loads(r[0]) for r in connection.execute(
            "SELECT payload FROM harness_actions WHERE session_id=?", (record["session_id"],))]
        stored_events = [{"type": r[0], "payload": json.loads(r[1])} for r in connection.execute(
            "SELECT event_type,payload FROM events WHERE event_type IN ('tool.result','task.decision','chat.delivery') ORDER BY id")]
    checks.append({"case": "live_readonly_database_matches_all_evidence", "passed": messages == record["messages"]
                   and stored_actions == actions and stored_events == record["events"] and sha(database) == before,
                   "database_sha256": before})
    for check in checks:
        check["report"] = str(path)
    return checks


def failed_report_checks(path: Path, ledger_path: Path, subject) -> list[dict]:
    """Verify an unchanged failed case; evidence validity does not make the task pass."""
    record = json.loads(path.read_text(encoding="utf-8"))
    shared = {"live_source_and_runner_bound", "live_receipts_same_session_task",
              "live_confirmations_match_previously_shown_tickets",
              "live_shared_40_attempt_ledger_membership", "live_readonly_database_matches_all_evidence"}
    checks = [c for c in live_report_checks(path, ledger_path, subject) if c["case"] in shared]
    initial, target = record["expected"]["initial_issue"], record["expected"]["target"]
    effects, actions, calls = record["effects"], record["actions"], record["calls"]
    reads = [r for task in record["tasks"] for r in task.get("tool_results", [])]
    checks += [
        {"case": "failed_case_remains_failed_for_connection", "passed": record["passed"] is False
         and record["offline"] is False and record["failure_category"] == "connection_or_protocol"
         and all(record["checks"].get(k) is False for k in
                 ("real_proposal", "correct_update", "fresh_read", "complete_delivery"))},
        {"case": "failed_case_no_write_proposal_effect_or_state_change", "passed": record["final_issue"] == initial
         and len(effects) == 1 and effects[0]["tool"] == "issue_read" and effects[0]["writes_before"] == 0
         and effects[0]["arguments"] == {**target, "method": "get"} and effects[0]["returned"] == initial
         and all(a["tool"] == "mcp__github__issue_read" for a in actions)
         and len(reads) == 1 and not reads[0].get("after_actions")},
        {"case": "failed_case_timeout_after_preread_before_update", "passed": bool(calls)
         and calls[-1].get("error_type") == "TimeoutError" and bool(reads)
         and reads[0]["result_ref"] in json.dumps(calls[-1]["messages"])
         and any(e.get("outcome") == "deadline_exceeded" and e.get("category") == "timeout"
                 and e["request_id"] == calls[-1]["request_id"] for e in record["transport"])},
        {"case": "failed_case_no_false_completion_or_duplicate_request", "passed": all(
            "Issue 任务已完成" not in t["answer"] for t in record["turns"])
         and any("Issue 任务尚未完成" in t["answer"] for t in record["turns"])
         and not any(c["request_id"].endswith(("-duplicate", "-status")) for c in calls)
         and all(record["checks"].get(k) is True for k in ("no_preconfirm_effect", "no_duplicate_write", "receipt_bound"))},
    ]
    for check in checks:
        check["report"] = str(path)
    return checks


def aggregate_live_checks(reports: list[dict], subject) -> list[dict]:
    """Check comparable contracts and the successful case with a late model timeout."""
    expected_budget = {"max_steps": 6, "max_calls": 12, "corrections": 1, "timeout_seconds": 45}
    checks = [{"case": "live_all_calls_use_same_captured_tool_schema", "passed":
               len({r["tool_schema_sha256"] for r in reports}) == 1
               and all(subject.digest(c["tools"]) == r["tool_schema_sha256"]
                       and {t["function"]["name"] for t in c["tools"]} ==
                       {"mcp__github__issue_read", "mcp__github__issue_write"}
                       for r in reports for c in r["calls"])},
              {"case": "live_fixed_budgets_and_true_initial_state", "passed":
               all(r["budget"] == expected_budget and r["initial_state_sha256"] == subject.digest(
                   {"issue": r["expected"]["initial_issue"], "messages": [], "actions": []})
                   and r["input_normalized_sha256"] == subject.digest(r["turns"][0]["input"])
                   for r in reports)},
              {"case": "live_same_variant_models_have_equivalent_contracts", "passed": all(
                  len({subject.digest(r[k]) for r in reports if r["variant"] == variant}) == 1
                  for variant in {r["variant"] for r in reports}
                  for k in ("input_normalized_sha256", "initial_state_sha256", "expected", "budget"))}]
    for report in reports:
        timeouts = [c for c in report["calls"] if c.get("error_type") == "TimeoutError"]
        if not report["passed"] or not timeouts:
            continue
        results = [r for t in report["tasks"] for r in t.get("tool_results", []) if r.get("after_actions")]
        events = report["events"]
        confirmed = bool(results)
        for call in timeouts:
            matches = [r for r in results if r["request_id"] == call["request_id"]
                       and r["result_ref"] in json.dumps(call["messages"])]
            result_positions = [i for i, e in enumerate(events) if e["type"] == "tool.result"
                                and any(e["payload"].get("result_ref") == r["result_ref"] for r in matches)]
            delivery_positions = [i for i, e in enumerate(events) if e["type"] == "chat.delivery"
                                  and e["payload"].get("request_id") == call["request_id"]]
            confirmed &= bool(matches and result_positions and delivery_positions)
            confirmed &= bool(result_positions and delivery_positions
                              and max(result_positions) < min(delivery_positions))
        checks.append({"case": "successful_task_timeout_occurred_after_persisted_fresh_read",
                       "passed": confirmed, "model": report["model"], "variant": report["variant"],
                       "timeout_http_indices": [c["index"] for c in timeouts]})
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--live-report", type=Path, action="append", default=[])
    parser.add_argument("--failed-report", type=Path, action="append", default=[])
    parser.add_argument("--live-ledger", type=Path)
    args = parser.parse_args()
    if args.data_dir.exists() or args.output.exists():
        raise SystemExit("Refusing to overwrite independent review evidence")
    args.data_dir.mkdir(parents=True)
    sys.dont_write_bytecode = True
    before = source_hashes()
    subject = prior.load_module("issue_review_subject", RUNNER)
    if args.live_report or args.failed_report:
        if args.live_ledger is None:
            parser.error("Live review requires --live-ledger")
        if args.live_ledger.with_suffix(args.live_ledger.suffix + ".lock").exists():
            raise SystemExit("Shared ledger is still running; do not freeze an intermediate hash")
        report_paths = args.live_report + args.failed_report
        report_hashes = {str(path): sha(path) for path in report_paths}
        ledger_hash = sha(args.live_ledger)
        checks = [check for path in args.live_report
                  for check in live_report_checks(path.resolve(), args.live_ledger, subject)]
        checks += [check for path in args.failed_report
                   for check in failed_report_checks(path.resolve(), args.live_ledger, subject)]
        checks.append({"case": "reviewed_reports_unchanged", "passed": report_hashes ==
                       {str(path): sha(path) for path in report_paths}})
        checks.append({"case": "reviewed_ledger_frozen", "passed": ledger_hash == sha(args.live_ledger)
                       and not args.live_ledger.with_suffix(args.live_ledger.suffix + ".lock").exists()})
        reports = [json.loads(path.read_text(encoding="utf-8")) for path in report_paths]
        checks += aggregate_live_checks(reports, subject)
        ledger = json.loads(args.live_ledger.read_text(encoding="utf-8"))
        projected = sorted([{k: c[k] for k in ("index", "model", "request_id")}
                            for r in reports for c in r["calls"]], key=lambda c: c["index"])
        checks.append({"case": "reviewed_reports_cover_entire_shared_ledger", "passed": projected == ledger["attempts"]})
        if len(reports) == 4:
            initial = [r for r in reports if r["variant"] == 1]
            expansion = [r for r in reports if r["variant"] == 2]
            checks.append({"case": "two_models_two_variants_initial_pair_passed_before_expansion",
                           "passed": {(r["provider"], r["variant"]) for r in reports} ==
                           {(p, v) for p in ("deepseek", "glm") for v in (1, 2)}
                           and all(r["passed"] is True for r in initial)
                           and max(c["index"] for r in initial for c in r["calls"]) <
                           min(c["index"] for r in expansion for c in r["calls"])})
        verified = all(c["passed"] for c in checks) and before == source_hashes()
        evidence = {"scope": "read-only independent live synthetic evidence review; no model calls",
                    "real_http_attempts_by_reviewer": 0, "source_sha256": before,
                    "report_sha256": report_hashes, "ledger_sha256": ledger_hash,
                    "checks": checks, "evidence_verified": verified, "passed": verified,
                    "all_tasks_passed": all(r["passed"] is True for r in reports),
                    "task_results": [{k: r[k] for k in ("provider", "model", "variant", "passed", "failure_category", "http_attempts")}
                                     for r in reports]}
        dump(args.output, evidence)
        print(json.dumps({"passed": evidence["passed"], "checks": len(checks),
                          "failures": [c for c in checks if not c["passed"]]}, ensure_ascii=False))
        return 0 if evidence["passed"] else 1
    projection = prior.load_module("issue_review_projection", RUNNER.with_name("models.py"))
    transport = prior.load_module("issue_review_transport", prior.CORE_DIR / "provider_http.py")
    agent_loop = prior.load_module("issue_review_loop", prior.CORE_DIR / "agent_loop.py")
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    loop = asyncio.new_event_loop()
    with patch.object(socket.socket, "connect", side_effect=AssertionError("No network")), \
            patch.object(socket, "create_connection", side_effect=AssertionError("No network")):
        checks = gate_probes(subject, args.data_dir) + score_probes() + [reservation_probe(tree)]
        checks += prior.isolation_probes(tree, args.data_dir) + prior.dispatch_probes(tree, projection)
        previous = json.loads(supplement_review.PRIOR_CASE.read_text(encoding="utf-8"))
        checks += supplement_review.budget_probes(tree, args.data_dir, previous)
        try:
            checks += loop.run_until_complete(transport_probe(tree, projection, transport, agent_loop))
        finally:
            loop.run_until_complete(loop.shutdown_default_executor())
            loop.close()
    checks += [offline_case(args.data_dir, scenario) for scenario in ("file", "issue")]
    after = source_hashes()
    checks.append({"case": "reviewed_source_unchanged_during_review", "passed": before == after})
    record = {"scope": "independent actual CLI gates, actual observer/transport, actual isolated offline runner",
              "real_http_attempts": 0, "source_sha256_before": before, "source_sha256_after": after,
              "static_tools_available": [name for name in ("ruff", "mypy", "black", "pylint")
                                         if importlib.util.find_spec(name) is not None],
              "checks": checks, "passed": all(c["passed"] for c in checks)}
    dump(args.output, record)
    print(json.dumps({"passed": record["passed"], "checks": len(checks),
                      "failures": [c for c in checks if not c["passed"]]}, ensure_ascii=False))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
