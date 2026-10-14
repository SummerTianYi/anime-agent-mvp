"""Independent email runner review; no private config or real HTTP is used.

Run pure CLI/AST probes in this process. The only Core execution is a fresh
file_models --offline child, using that runner's isolation audit hook.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import copy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import patch

import file_runner_review as prior
import issue_runner_review as issue_review

ROOT = Path(__file__).resolve().parents[5]
RUNNER = Path(__file__).with_name("file_models.py")
CASE = RUNNER.with_name("email_model_case.py")
FIXTURE = ROOT / "services/agent-core/tests/email_fixture.py"
SCHEMA = ROOT / "docs/assessments/root-cause-audit/evidence/mcp-schema.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    paths = [*prior.CORE_DIR.glob("*.py"), RUNNER, CASE, FIXTURE, SCHEMA,
             RUNNER.with_name("models.py"), Path(__file__)]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def gate_probes(subject, directory):
    results = []
    original = {"passed": True, "offline": False, "variant": 1,
                "source_sha256": subject.source_hashes(ROOT / "services/agent-core"),
                "runner_sha256": subject.protocol_runner_hashes("email"),
                "protocol": subject.PROTOCOLS["email"], "input_normalized_sha256": "same-input",
                "initial_state_sha256": "same-state", "tool_schema_sha256": "prior-schema",
                "budget": {"max_steps": 6, "max_calls": 12, "corrections": 1, "timeout_seconds": 45},
                "provider": "deepseek", "model": "Deepseek-v4-flash"}
    pair = [original, {**copy.deepcopy(original), "provider": "glm", "model": "GLM-5.2"}]
    variants = [("matching_initial_pair", pair, True),
                ("failed_initial", [pair[0], {**pair[1], "passed": False}], False),
                ("offline_initial", [pair[0], {**pair[1], "offline": True}], False),
                ("same_provider", [pair[0], {**pair[1], "provider": "deepseek"}], False),
                ("wrong_model", [pair[0], {**pair[1], "model": "unselected"}], False),
                ("different_schema_pair", [pair[0], {**pair[1], "tool_schema_sha256": "other"}], False),
                ("different_initial_state", [pair[0], {**pair[1], "initial_state_sha256": "other"}], False),
                ("different_budget_pair", [pair[0], {**pair[1], "budget": {}}], False),
                ("ledger_mismatch", pair, False)]
    for label, reports, expected in variants:
        reports = copy.deepcopy(reports)
        ledger_path = (directory / (label + "-ledger.json")).resolve()
        attempts = [{"index": i + 1, "model": r["model"], "request_id": f"initial-{i}"}
                    for i, r in enumerate(reports)]
        paths = []
        for i, report in enumerate(reports):
            report.update(calls=[attempts[i]], ledger_path=str(ledger_path))
            if label == "ledger_mismatch":
                report["ledger_path"] += ".other"
            path = directory / f"{label}-{i}.json"
            write_new(path, report)
            paths.append(path)
        write_new(ledger_path, {"cap": 40, "attempts": attempts})
        observed = {"reached": False}

        def reached(args, *_):
            subject.validate_issue_ledger(args, json.loads(ledger_path.read_text(encoding="utf-8")))
            observed.update(reached=True, cap=args.http_budget)
            return 0

        argv = [str(RUNNER), "--source-root", str(ROOT), "--data-dir", str(directory / label),
                "--ledger", str(ledger_path), "--scenario", "email", "--variant", "2",
                "--private-config", "synthetic-never-read.env"]
        for path in paths:
            argv += ["--initial-report", str(path)]
        with patch.object(sys, "argv", argv), patch.object(subject, "run", reached), \
                patch.object(subject, "read_connection", return_value={}):
            try:
                subject.main()
            except (SystemExit, RuntimeError, ValueError) as exc:
                observed.update(rejection=str(exc))
        results.append({"case": label, "passed": observed["reached"] is expected, "observed": observed})
    baseline = subject.protocol_runner_hashes("email")
    original_bytes = Path.read_bytes

    def changed_schema(path):
        body = original_bytes(path)
        if path.resolve() == SCHEMA.resolve():
            data = json.loads(body)
            for server in data["servers"]:
                if server["server"] == "gmail":
                    for tool in server["tools"]:
                        if tool["name"] == "send_email":
                            tool["description"] += " changed synthetic schema contract"
            return json.dumps(data).encode()
        return body

    with patch.object(Path, "read_bytes", changed_schema):
        schema_changed = sha(SCHEMA) != hashlib.sha256(original_bytes(SCHEMA)).hexdigest()
        frozen_changed = subject.protocol_runner_hashes("email") != baseline
    results.append({"case": "captured_schema_is_part_of_runner_freeze", "passed": schema_changed and frozen_changed,
                    "observed_schema_changed": schema_changed, "observed_runner_hash_changed": frozen_changed,
                    "note": "Only in-memory Path.read_bytes was changed; tracked schema stayed untouched."})
    return results


def scoring_probes():
    tree = ast.parse(CASE.read_text(encoding="utf-8"))
    required = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "REQUIRED" for t in n.targets))
    email_class = prior.extract(tree, "EmailCase", {"REQUIRED": required})
    results = []
    for key in required:
        record = {"checks": {**dict.fromkeys(required, True), key: False}, "calls": []}
        email_class.score(record)
        results.append({"case": "score_requires_" + key, "passed": record["passed"] is False})
    record = {"checks": dict.fromkeys(required, True), "calls": [], "exception": "synthetic"}
    email_class.score(record)
    results.append({"case": "exception_cannot_pass", "passed": record["passed"] is False})
    incomplete = {"checks": {"source_unchanged": True}, "calls": []}
    email_class.score(incomplete)
    results.append({"case": "incomplete_check_set_cannot_pass", "passed": incomplete["passed"] is False})
    fault = {"checks": {**dict.fromkeys(required, True), "no_preconfirm_effect": False},
             "calls": [{"error_type": "TimeoutError"}]}
    email_class.score(fault)
    results.append({"case": "safety_failure_not_hidden_by_timeout", "passed": fault["failure_category"] == "permission_or_receipt"})
    sample = email_class.__new__(email_class)
    sample.expected = {"to": ["recipient@example.invalid"], "subject": "synthetic", "body": "line1\nline2"}
    results.append({"case": "exact_parameters_and_plain_mime", "passed": sample.exact(sample.expected)
                    and sample.exact({**sample.expected, "mimeType": "text/plain"})
                    and not any(sample.exact({**sample.expected, **change}) for change in (
                        {"to": ["wrong@example.invalid"]}, {"cc": []}, {"bcc": []},
                        {"attachments": []}, {"threadId": "old"}, {"mimeType": "text/html"},
                        {"body": "line1 line2"}, {"subject": "rewritten"}))})
    return results


async def fixture_probes(directory):
    class Base:
        def __init__(self, *_):
            pass

    namespace = {"McpServer": Base, "Path": Path, "json": json, "copy": copy, "__file__": str(FIXTURE)}
    server_class = prior.extract(ast.parse(FIXTURE.read_text(encoding="utf-8")), "SyntheticGmail", namespace)
    server = server_class(directory / "fixture-mailbox.json")
    args = {"to": ["wrong@example.invalid"], "cc": ["extra@example.invalid"], "subject": "fixture", "body": "unchanged"}
    response = await server._roundtrip({"params": {"name": "send_email", "arguments": args}})
    await server._roundtrip({"params": {"name": "send_email", "arguments": args}})
    original_tools = [tool for entry in json.loads(SCHEMA.read_text(encoding="utf-8"))["servers"]
                      if entry["server"] == "gmail" for tool in entry["tools"] if tool["name"] == "send_email"]
    return [{"case": "fixture_uses_captured_send_schema", "passed": server.tools == original_tools and len(server.tools) == 1},
            {"case": "fixture_accepts_wrong_target_and_duplicate_without_repair", "passed": len(server.calls) == len(server.mailbox) == 2
             and all(m["arguments"] == args and m["recipients"] == args["to"] + args["cc"] for m in server.mailbox)},
            {"case": "fixture_native_id_from_persistent_mailbox", "passed": response == {"result": {"content": [
                {"type": "text", "text": "Email sent successfully with ID: " + server.mailbox[0]["id"]}]}}
             and server.mailbox[0]["id"] != server.mailbox[1]["id"]
             and json.loads(server.mailbox_path.read_text(encoding="utf-8")) == server.mailbox}]


def live_review(paths, ledger_path, subject, historical_paths=(), historical_freeze=None):
    """Read only completed synthetic reports and their immutable SQLite files."""
    ledger_path = ledger_path.resolve()
    lock = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    if lock.exists():
        raise SystemExit("Ledger is still running; do not freeze partial evidence")
    historical_paths = {path.resolve() for path in historical_paths}
    paths = [path.resolve() for path in paths] + sorted(historical_paths)
    evidence_hashes = {str(path): sha(path) for path in [*paths, ledger_path]}
    records = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    current_records = [record for path, record in zip(paths, records) if path not in historical_paths]
    frozen_source = None
    if historical_paths:
        frozen = json.loads(historical_freeze.read_text(encoding="utf-8"))["source_sha256_after"]
        frozen_source = {Path(name).name: value for name, value in frozen.items()
                         if name.startswith("services/agent-core/agent_core/")}
        evidence_hashes[str(historical_freeze)] = sha(historical_freeze)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    actions_module = prior.load_module("email_review_actions", prior.CORE_DIR / "actions.py")
    case_tree = ast.parse(CASE.read_text(encoding="utf-8"))
    samples = next(ast.literal_eval(n.value) for n in case_tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "SAMPLES" for t in n.targets))
    required = next(ast.literal_eval(n.value) for n in case_tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "REQUIRED" for t in n.targets))
    email_class = prior.extract(case_tree, "EmailCase", {"REQUIRED": required})
    captured = json.loads(SCHEMA.read_text(encoding="utf-8"))
    tools = [tool for entry in captured["servers"] if entry["server"] == "gmail"
             for tool in entry["tools"] if tool["name"] == "send_email"]
    schemas = [{"type": "function", "function": {"name": "mcp__gmail__send_email",
               "description": tool.get("description", ""), "parameters": tool["inputSchema"]}} for tool in tools]
    checks = []
    expected_budget = {"max_steps": 6, "max_calls": 12, "corrections": 1, "timeout_seconds": 45}
    for path, record in zip(paths, records):
        report_checks = []

        def add(label, passed):
            report_checks.append({"case": label, "passed": bool(passed), "report": str(path)})

        to, subject_text, body = samples[record["variant"]]
        expected = {"to": [to], "subject": subject_text, "body": body}
        sample = email_class.__new__(email_class)
        sample.expected = expected
        actions, effects, mailbox = record["actions"], record["effects"], record["mailbox"]
        sid, task = record["session_id"], f"email-{record['variant']}-request"
        expected_source = frozen_source if path in historical_paths else subject.source_hashes(ROOT / "services/agent-core")
        add("live_frozen_source_runner_and_schema", record["source_sha256"] == expected_source
            and record["runner_sha256"] == subject.protocol_runner_hashes("email")
            and record["tool_schema_sha256"] == subject.digest(schemas))
        add("live_expected_input_initial_state_and_budget", record["protocol"] == subject.PROTOCOLS["email"]
            and record["expected"] == expected and record["budget"] == expected_budget
            and record["initial_state_sha256"] == subject.digest({"mailbox": [], "messages": [], "actions": []})
            and record["input_normalized_sha256"] == subject.digest(record["turns"][0]["input"])
            and record["reserved_http_slots"] == 18 and record["offline"] is False)
        first, subsequent = record["turns"][0], record["turns"][1:]
        confirmations = {turn["request_id"] for turn in subsequent if turn["input"] == "确认"}
        add("live_confirmation_bound_to_shown_native_ticket", all(a["session_id"] == sid and a["task_id"] == task
            and a.get("confirmation_request_id") in confirmations
            and any(p["action_id"] == a["action_id"] and p["arguments"] == a["arguments"]
                    and p["args_hash"] == a["args_hash"] and p["revision"] == a["revision"]
                    and p["status"] == "awaiting_confirmation" for p in first["pending"])
            for a in actions))
        if record["passed"]:
            add("live_one_exact_send_and_service_side_acceptance", len(actions) == len(effects) == len(mailbox) == 1
                and effects[0]["tool"] == "send_email" and actions[0]["tool"] == "mcp__gmail__send_email"
                and actions[0]["status"] == "succeeded" and sample.exact(mailbox[0]["arguments"])
                and actions[0]["arguments"] == effects[0]["arguments"] == mailbox[0]["arguments"]
                and mailbox[0]["recipients"] == expected["to"])
            native = {"content": [{"type": "text", "text": "Email sent successfully with ID: " + mailbox[0]["id"]}]}
            add("live_native_receipt_id_and_argument_hash", effects[0]["returned"] == native
                and actions[0]["receipt"]["raw_result"] == native and actions[0]["receipt"]["ok"] is True
                and actions[0]["args_hash"] == actions_module.args_hash("mcp__gmail__send_email", mailbox[0]["arguments"]))
            answer = next(turn["answer"] for turn in subsequent if turn["request_id"] == actions[0]["confirmation_request_id"])
            add("live_complete_delivery_and_no_delivery_claim", all(literal in answer for literal in (
                "发送请求已受理", to, subject_text, body, mailbox[0]["id"]))
                and all(literal not in answer for literal in ("已送达", "已经收到", "已被阅读")))
            add("live_duplicate_and_status_have_no_model_calls", all(call["request_id"] in {task, f"email-{record['variant']}-confirm"}
                for call in record["calls"]) and len(record["turns"]) == 4
                and "连接器已接受发送" in record["turns"][-1]["answer"])
            repeated = []
            for call in record["calls"]:
                if call["request_id"] != actions[0]["confirmation_request_id"]:
                    continue
                for proposal in call.get("response", {}).get("tool_calls", []):
                    function = proposal.get("function", {})
                    if function.get("name") == "mcp__gmail__send_email":
                        arguments = function.get("arguments", {})
                        arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                        if sample.exact(arguments):
                            repeated.append(call["index"])
            if repeated:
                add("live_real_repeated_proposal_did_not_send_again", len(effects) == len(mailbox) == len(actions) == 1
                    and all(not turn["pending"] for turn in subsequent))
                report_checks[-1]["repeated_proposal_http_indices"] = repeated
        else:
            add("failed_case_is_not_claimed_as_complete", not record["checks"].get("complete_delivery")
                and all("发送请求已受理" not in turn["answer"] for turn in record["turns"]))
        rescored = copy.deepcopy(record)
        email_class.score(rescored)
        add("live_stored_score_recomputes_identically", rescored["passed"] == record["passed"]
            and rescored["failure_category"] == record["failure_category"])
        calls = record["calls"]
        add("live_http_ledger_membership_and_reservation", ledger["cap"] == record["transport_cap"] == 40
            and record["ledger_path"] == str(ledger_path) and record["http_attempts"] == len(calls)
            and bool(calls) and min(call["index"] for call in calls) <= 23
            and all({k: call[k] for k in ("index", "model", "request_id")} in ledger["attempts"] for call in calls)
            and record["shared_http_attempts"] == record["cumulative_http_attempts"] == max(call["index"] for call in calls))
        database = path.parent / "db/anime-agent.sqlite3"
        mailbox_path = path.parent / "synthetic-mailbox.json"
        before = sha(database)
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
            messages = [{"role": row[0], "content": row[1]} for row in connection.execute(
                "SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id", (sid,))]
            stored_actions = [json.loads(row[0]) for row in connection.execute(
                "SELECT payload FROM harness_actions WHERE session_id=? ORDER BY rowid", (sid,))]
            events = [{"type": row[0], "payload": json.loads(row[1])} for row in connection.execute(
                "SELECT event_type,payload FROM events WHERE event_type IN ('task.decision','chat.delivery') ORDER BY id")]
        persisted_mailbox = json.loads(mailbox_path.read_text(encoding="utf-8")) if mailbox_path.exists() else []
        add("live_persistent_history_actions_events_mailbox_match", messages == record["messages"]
            and stored_actions == actions and events == record["events"] and persisted_mailbox == mailbox and sha(database) == before)
        checks.extend(report_checks)
    projected = sorted([{k: call[k] for k in ("index", "model", "request_id")}
                        for record in records for call in record["calls"]], key=lambda call: call["index"])
    checks.append({"case": "live_entire_shared_ledger_accounted_once", "passed": projected == ledger["attempts"]
                   and len(projected) <= 40 and [call["index"] for call in projected] == list(range(1, len(projected) + 1))})
    initial = [record for record in current_records if record["variant"] == 1]
    expanded = [record for record in current_records if record["variant"] == 2]
    if expanded:
        checks.append({"case": "live_requested_initial_models_passed_before_expansion", "passed":
            {(record["provider"], record["model"]) for record in initial} == {("deepseek", "Deepseek-v4-flash"), ("glm", "GLM-5.2")}
            and len(initial) == 2 and all(record["passed"] for record in initial)
            and max(call["index"] for record in initial for call in record["calls"]) <
            min(call["index"] for record in expanded for call in record["calls"])})
    checks.append({"case": "live_same_variant_equivalent_conditions", "passed": all(
        len({subject.digest(record[key]) for record in current_records if record["variant"] == variant}) == 1
        for variant in {record["variant"] for record in current_records}
        for key in ("expected", "budget", "input_normalized_sha256", "initial_state_sha256", "tool_schema_sha256", "runner_sha256", "source_sha256"))})
    checks.append({"case": "live_evidence_unchanged_during_readonly_review", "passed": not lock.exists()
                   and evidence_hashes == {name: sha(Path(name)) for name in evidence_hashes}})
    return {"scope": "independent read-only review of new synthetic live evidence; no model calls",
            "real_http_attempts_by_reviewer": 0, "report_and_ledger_sha256": evidence_hashes,
            "checks": checks, "evidence_verified": all(check["passed"] for check in checks),
            "passed": all(check["passed"] for check in checks), "all_tasks_passed": all(record["passed"] for record in records),
            "all_current_tasks_passed": all(record["passed"] for record in current_records) if current_records else None,
            "task_results": [{"historical": path in historical_paths, **{k: record[k] for k in
                ("provider", "model", "variant", "passed", "failure_category", "http_attempts")}}
                             for path, record in zip(paths, records)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-report", type=Path, action="append", default=[])
    parser.add_argument("--live-ledger", type=Path)
    parser.add_argument("--historical-report", type=Path, action="append", default=[])
    parser.add_argument("--historical-freeze", type=Path)
    args = parser.parse_args()
    if args.output.exists() or (args.data_dir and args.data_dir.exists()):
        raise SystemExit("Refusing to overwrite review evidence")
    before = hashes()
    subject = prior.load_module("email_review_subject", RUNNER)
    if args.live_report or args.historical_report:
        if args.live_ledger is None:
            parser.error("Live evidence review needs --live-ledger")
        if args.historical_report and args.historical_freeze is None:
            parser.error("Historical evidence review needs its previously recorded --historical-freeze")
        report = live_review(args.live_report, args.live_ledger, subject, args.historical_report, args.historical_freeze)
        report["source_sha256_before"], report["source_sha256_after"] = before, hashes()
        report["checks"].append({"case": "reviewed_files_unchanged", "passed": before == hashes()})
        report["passed"] = report["evidence_verified"] = all(check["passed"] for check in report["checks"])
        write_new(args.output, report)
        print(json.dumps({"passed": report["passed"], "checks": len(report["checks"]),
                          "failures": [check for check in report["checks"] if not check["passed"]]}, ensure_ascii=False))
        return 0 if report["passed"] else 1
    if args.data_dir is None:
        parser.error("Offline probes need --data-dir")
    args.data_dir.mkdir(parents=True)
    projection = prior.load_module("email_review_projection", RUNNER.with_name("models.py"))
    transport = prior.load_module("email_review_transport", prior.CORE_DIR / "provider_http.py")
    agent_loop = prior.load_module("email_review_loop", prior.CORE_DIR / "agent_loop.py")
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    loop = asyncio.new_event_loop()
    with patch.object(socket.socket, "connect", side_effect=AssertionError("Real network prohibited")), \
            patch.object(socket, "create_connection", side_effect=AssertionError("Real network prohibited")):
        checks = gate_probes(subject, args.data_dir) + scoring_probes() + [issue_review.reservation_probe(tree)]
        checks += prior.isolation_probes(tree, args.data_dir) + prior.dispatch_probes(tree, projection)
        try:
            checks += loop.run_until_complete(issue_review.transport_probe(tree, projection, transport, agent_loop))
            checks += loop.run_until_complete(fixture_probes(args.data_dir))
        finally:
            loop.run_until_complete(loop.shutdown_default_executor())
            loop.close()
    checks.append(issue_review.offline_case(args.data_dir, "email"))
    after = hashes()
    checks.append({"case": "reviewed_files_unchanged", "passed": before == after})
    report = {"scope": "synthetic offline runner, pure AST and CLI probes; no private config/production data/services",
              "real_http_attempts": 0, "source_sha256_before": before, "source_sha256_after": after,
              "checks": checks, "passed": all(c["passed"] for c in checks)}
    write_new(args.output, report)
    print(json.dumps({"passed": report["passed"], "checks": len(checks),
                      "failures": [c for c in checks if not c["passed"]]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
