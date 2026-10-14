"""Offline probes of the current file runner's actual observer and lifecycle AST.

No Core import, private configuration, model, socket, service, or production DB
is used. HTTP responses below are in-memory fixtures, not live model evidence.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
from contextvars import ContextVar
from email.message import Message
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
from types import SimpleNamespace
import urllib.error
import urllib.request
import urllib.response
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[5]
RUNNER = Path(__file__).with_name("file_models.py")
CORE_DIR = ROOT / "services/agent-core/agent_core"


def extract(tree: ast.AST, name: str, namespace: dict):
    node = next(node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name)
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(module, str(RUNNER), "exec"), namespace)
    return namespace[name]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def hashes() -> dict[str, str]:
    files = list(CORE_DIR.glob("*.py")) + [RUNNER, Path(__file__).with_name("models.py"),
             ROOT / "services/agent-core/tests/test_file_task.py", Path(__file__)]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files}


def response() -> bytes:
    return json.dumps({"choices": [{"message": {"content": "synthetic result"},
                                    "finish_reason": "stop"}]}).encode()


def make_observer(tree, projection, parent, ledger, record, save):
    namespace = {"core": SimpleNamespace(OpenAICompatibleProvider=parent,
        ProviderError=RuntimeError, REQUEST_ID=ContextVar("file-review-request", default="synthetic")),
        "CAP": 30, "mutex": threading.RLock(), "ledger": ledger, "record": record,
        "public_messages": projection.public_messages, "NoRedirect": projection.NoRedirect,
        "json": json, "urllib": urllib, "patch": patch, "save": save, "time": time}
    return extract(tree, "ObservedProvider", namespace)()


def synthetic_request():
    return urllib.request.Request("http://synthetic.invalid/start",
                                  data=b'{"messages":[{"role":"user","content":"fixture"}]}')


def grader_probes(tree) -> list[dict]:
    namespace = {"json": json, "hashlib": hashlib, "Path": Path}
    # Keep any module constants needed by a strengthened grader.
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            try:
                exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                             str(RUNNER), "exec"), namespace)
            except NameError:
                continue
    score = extract(tree, "score", namespace)
    partial = {"checks": {"source_unchanged": True}, "calls": []}
    score(partial)
    required = ("no_preconfirm_effect", "real_proposal", "correct_write", "actual_read",
                "receipt_bound", "complete_delivery", "no_duplicate_write", "truthful_progress",
                "history_reopened", "ledger_reopened", "reads_reopened", "source_unchanged")
    checks = dict.fromkeys(required, True)
    expected_read = {"tool": "read_file", "session_id": 2, "task_id": "file-1-request",
                     "result_ref": "file-1-request:read:1", "after_actions": ["action-1"],
                     "arguments": {"path": "synthetic.txt"},
                     "result": {"ok": True, "content": "expected", "truncated": False}}
    empty_events = {"checks": checks, "calls": [], "events": [],
                    "tasks": [{"tool_results": [expected_read]}]}
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "reads_reopened" for target in node.targets))
    ns = {"record": empty_events, "rows": [], "json": json, "reads": [expected_read]}
    for assignment in ast.walk(tree):
        if isinstance(assignment, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id == "expected_reads" for target in assignment.targets):
            exec(compile(ast.fix_missing_locations(ast.Module(body=[assignment], type_ignores=[])),
                         str(RUNNER), "exec"), ns)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 str(RUNNER), "exec"), ns)
    score(empty_events)
    return [{"case": "incomplete_check_set_rejected", "passed": not partial["passed"],
             "grader_accepted_partial": partial["passed"]},
            {"case": "missing_persisted_read_rejected", "passed": not empty_events["passed"],
             "grader_accepted_no_read_events": empty_events["passed"],
             "read_reopen_check": checks["reads_reopened"],
             "fault": "tool.result events missing both before and after reopen; in-memory read exists"}]


def isolation_probes(tree, directory) -> list[dict]:
    config_path = directory / "synthetic.env"
    config_path.write_text("DEEPSEEK_MODEL=synthetic-ds\nGLM_MODEL=synthetic-glm\n"
                           "GLM_CREDENTIAL_SOURCE=deepseek\nLLM_PROXY_MODE=direct\n"
                           "ANIME_AGENT_DATA_DIR=untrusted-fixture\nLLM_PROVIDER=glm\n"
                           "ANIME_AGENT_TTS=1\nSTEPFUN_MODEL=unselected\n", encoding="utf-8")
    selected = extract(tree, "read_connection", {})(config_path)
    projection_ok = selected == {"DEEPSEEK_MODEL": "synthetic-ds", "GLM_MODEL": "synthetic-glm",
                                "GLM_CREDENTIAL_SOURCE": "deepseek", "LLM_PROXY_MODE": "direct"}
    directory = directory.resolve()
    args = SimpleNamespace(data_dir=directory, ledger=directory / "ledger.json", offline=True, scenario="file")
    audit = extract(tree, "audit", {"Path": Path, "os": os, "args": args,
                                    "config_path": config_path.resolve()})
    sentinel = directory.parent / "outside-synthetic"
    blocked = []
    for name, event, values in (
            ("external_database", "sqlite3.connect", (str(sentinel / "example.sqlite3"),)),
            ("other_config", "open", (str(sentinel / "private.env"), "r", 0)),
            ("external_write", "open", (str(sentinel / "write.txt"), "w", os.O_WRONLY)),
            ("offline_socket", "socket.connect", (None, ("synthetic.invalid", 80))),
            ("subprocess", "subprocess.Popen", ("synthetic",))):
        try:
            audit(event, values)
        except RuntimeError:
            blocked.append(name)
    audit("sqlite3.connect", (str(directory / "allowed.sqlite3"),))
    audit("open", (str(config_path.resolve()), "r", 0))
    return [{"case": "connection_fields_only", "passed": projection_ok},
            {"case": "isolation_guard_rejects_fallback_io", "passed": len(blocked) == 5,
             "blocked": blocked, "actual_external_io": 0}]


def literal_probes() -> list[dict]:
    subject = load_module("file_review_literal", CORE_DIR / "file_task.py")
    if not hasattr(subject, "literal_content_error"):
        return []
    delivery = load_module("file_review_delivery", CORE_DIR / "task_delivery.py")
    body = " 第一行：7月12日 3cm\n第二行：普通Disco 20℃\n"
    text = "请创建文件 synthetic.txt，写入后读取。内容如下（两行）：\n" + body
    arguments = {"path": "synthetic.txt", "content": body}
    positive = subject.literal_content_error(text, "write_file", arguments) == ""
    changed = {**arguments, "content": body.strip()}
    before = dict(changed)
    rejected = subject.literal_content_error(text, "write_file", changed)
    main_tree = ast.parse((CORE_DIR / "main.py").read_text(encoding="utf-8"))
    calls = []

    def literal(*values):
        calls.append(values[1])
        return subject.literal_content_error(*values)

    namespace = {"validate_proposal": delivery.validate_proposal, "literal_content_error": literal,
                 "edited_file_request": subject.edited_file_request,
                 "text": text, "file_turn": True, "file_request": True,
                 "task": {"file_delivery": True, "file_request_text": text, "intent": text},
                 "schemas": {"write_file": {"type": "object", "required": ["path", "content"],
                     "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}}
    validate = extract(main_tree, "check_proposal", namespace)
    errors = [validate("write_file", value) for value in (None, [], {"path": "x", "content": 5})]
    schema_first = all(isinstance(error, str) and error for error in errors) and not calls
    namespace["task"]["file_delivery"] = False
    untouched = validate("write_file", changed) == "" and not calls
    namespace["task"]["file_delivery"] = True
    namespace.update(text="继续", file_turn=False, file_request=False)
    bound = bool(validate("write_file", changed)) and validate("write_file", arguments) == ""
    namespace["task"]["file_request_text"] = "内容如下：新版正文"
    revised = validate("write_file", {**arguments, "content": "新版正文"}) == ""
    revised = revised and bool(validate("write_file", arguments))
    namespace["task"]["file_request_text"] = text
    namespace.update(intent="edit", text="取消旧的，把文件路径改成 renamed.txt，正文不变，仍然写入后读取完整内容",
                     file_request=True)
    edit = next(node for node in ast.walk(main_tree) if isinstance(node, ast.If)
                and ast.unparse(node.test) == "intent == 'edit'")
    exec(compile(ast.fix_missing_locations(ast.Module(body=[edit], type_ignores=[])),
                 str(CORE_DIR / "main.py"), "exec"), namespace)
    path_only_bound = bool(validate("write_file", changed)) and validate("write_file", arguments) == ""
    new_literal = "取消旧的，改成新版。内容如下：新正文"
    rewrite = "取消旧的，改成新版，仍然写入后读取完整内容"
    edit_modes = (subject.edited_file_request(text, new_literal) == new_literal
                  and subject.edited_file_request(text, rewrite) == rewrite
                  and subject.edited_file_request(text, "文件名改为 renamed.txt") == text)
    correction_checks = []
    for status in ("cancelled", "failed", "unknown", "pending"):
        budget_task = {"blocked": False, "corrections_used": 0}
        correction = extract(main_tree, "take_correction", {
            "task": budget_task, "request_id": "edit-probe", "intent": "edit",
            "file_turn": True,
            "book": SimpleNamespace(records={"old": {"action_id": "old", "status": status}}),
            "delivery_actions": ["old"]})
        first, second = correction(), correction()
        correction_checks.append(first is (status == "cancelled") and second is False
                                 and budget_task["corrections_used"] == int(status == "cancelled"))
    non_file_task = {"blocked": False, "corrections_used": 0}
    non_file_correction = extract(main_tree, "take_correction", {
        "task": non_file_task, "request_id": "non-file-edit", "intent": "edit", "file_turn": False,
        "book": SimpleNamespace(records={"old": {"action_id": "old", "status": "cancelled"}}),
        "delivery_actions": ["old"]})
    non_file_unchanged = non_file_correction() is False and non_file_task["corrections_used"] == 0
    differences = []
    for expected, actual, index in (("ABC", "", 0), ("ABC", "AB", 2), ("AB", "ABC", 2),
                                    ("第一行：" + "甲" * 40, "第二行：" + "乙" * 40, 1)):
        candidate = {"content": actual}
        message = subject.literal_content_error("内容如下：" + expected, "write_file", candidate)
        differences.append(isinstance(message, str) and f"第{index + 1}个字符" in message
                           and repr(expected[index:index + 24]) in message
                           and repr(actual[index:index + 24]) in message
                           and candidate == {"content": actual})
    return [{"case": "literal_bytes_preserved_without_argument_synthesis",
             "passed": positive and isinstance(rejected, str) and bool(rejected) and changed == before},
            {"case": "literal_gate_schema_first_and_task_scope_only",
             "passed": schema_first and untouched and bound and revised},
            {"case": "path_only_edit_preserves_literal_body_constraint", "passed": path_only_bound and edit_modes},
            {"case": "edit_cancelled_revision_uses_one_existing_correction_only",
             "passed": all(correction_checks)},
            {"case": "non_file_edit_has_no_cancelled_correction_exception", "passed": non_file_unchanged},
            {"case": "literal_difference_offsets_and_bounded_snippets", "passed": all(differences)}]


def dispatch_probes(tree, projection) -> list[dict]:
    dispatches = []

    class InMemoryHTTP(urllib.request.HTTPHandler):
        def http_open(self, request):
            dispatches.append(request.get_method())
            headers = Message()
            headers["Location"] = "http://synthetic.invalid/redirected"
            result = urllib.response.addinfourl(io.BytesIO(b""), headers, request.full_url, 302)
            result.msg = "synthetic"
            return result

    class Parent:
        model = "synthetic-model"

        def _request(self, request):
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), InMemoryHTTP())
            with opener.open(request) as result:
                return result.read()

    ledger = {"cap": 30, "attempts": [{"index": i} for i in range(1, 30)]}
    record = {"calls": []}
    saves = []
    observed = make_observer(tree, projection, Parent, ledger, record,
                             lambda: saves.append(len(ledger["attempts"])))
    blocked = []
    for _ in range(2):
        try:
            observed._request(synthetic_request())
        except (urllib.error.HTTPError, RuntimeError) as exc:
            blocked.append(type(exc).__name__)
    redirect_ok = len(dispatches) == 1 and len(ledger["attempts"]) == 30 and len(blocked) == 2
    results = [{"case": "redirect_and_hard_cap", "passed": redirect_ok,
                "dispatches_in_memory": len(dispatches), "attempts": len(ledger["attempts"]),
                "blocked": blocked, "save_counts": saves}]
    before = len(dispatches)

    def failing_save():
        raise OSError("synthetic persistence failure")

    observed = make_observer(tree, projection, Parent, {"cap": 30, "attempts": []},
                             {"calls": []}, failing_save)
    try:
        observed._request(synthetic_request())
    except OSError:
        pass
    results.append({"case": "persistence_failure_blocks_dispatch", "passed": len(dispatches) == before})
    return results


async def retry_probe(tree, projection, transport) -> dict:
    dispatched = []

    class Parent:
        model = "synthetic-model"

        def _request(self, request):
            dispatched.append(len(dispatched) + 1)
            if len(dispatched) < 3:
                raise ConnectionResetError("synthetic transient failure")
            return response()

    ledger, record = {"cap": 30, "attempts": []}, {"calls": []}
    observer = make_observer(tree, projection, Parent, ledger, record, lambda: None)
    result = await transport.ModelHttpTransport().send(observer._request, synthetic_request(),
        name="synthetic", route="direct", timeout=3, refresh=lambda _: None)
    return {"case": "all_retries_counted", "passed": result == response()
            and len(dispatched) == len(ledger["attempts"]) == 3,
            "dispatches_in_memory": len(dispatched), "attempts": len(ledger["attempts"])}


def late_save_probe(tree, projection, transport, directory, loop) -> dict:
    """Execute the runner's exact loop cleanup with an uncancellable fake worker."""
    entered, release, saved = threading.Event(), threading.Event(), threading.Event()
    ledger_path, output = directory / "late-ledger.json", directory / "late-report.json"
    ledger, record = {"cap": 30, "attempts": []}, {"calls": []}
    namespace = {"mutex": threading.RLock(), "output": output, "record": record,
                 "ledger": ledger, "args": SimpleNamespace(ledger=ledger_path), "json": json}
    exact_save = extract(tree, "save", namespace)

    def save():
        exact_save()
        if release.is_set():
            saved.set()

    class Parent:
        model = "synthetic-model"

        def _request(self, request):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("fixture release missing")
            return response()

    observer = make_observer(tree, projection, Parent, ledger, record, save)

    async def exercise():
        try:
            await transport.ModelHttpTransport().send(observer._request, synthetic_request(),
                name="synthetic", route="direct", timeout=0.03, refresh=lambda _: None)
        except TimeoutError:
            pass

    cleanup = next(node for node in ast.walk(tree) if isinstance(node, ast.Try)
                   and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                           and n.func.attr == "run_until_complete" for n in ast.walk(node)))
    cleanup_code = ast.fix_missing_locations(ast.Module(body=[cleanup], type_ignores=[]))
    result = {}
    try:
        # Newer fixes wait for the worker inside cleanup. A timer bounds that
        # wait, preserving the same proof: the second writer only starts after
        # the runner actually returns from its unchanged cleanup code.
        timer = threading.Timer(0.15, release.set)
        timer.start()
        exec(compile(cleanup_code, str(RUNNER), "exec"), {"loop": loop, "exercise": exercise})
        cleanup_returned_with_worker_pending = entered.is_set() and not saved.is_set()
        newer = json.loads(ledger_path.read_text(encoding="utf-8"))
        newer["attempts"].append({"index": 2, "model": "second-process", "request_id": "next"})
        ledger_path.write_text(json.dumps(newer), encoding="utf-8")
        release.set()
        worker_saved = saved.wait(2)
        final = json.loads(ledger_path.read_text(encoding="utf-8"))
        result = {"case": "no_late_worker_ledger_rollback",
                  "passed": len(final["attempts"]) == 2,
                  "cleanup_returned_with_worker_pending": cleanup_returned_with_worker_pending,
                  "late_worker_saved": worker_saved, "before_late_save": 2,
                  "final_attempt_count": len(final["attempts"]),
                  "cleanup_source": ast.unparse(cleanup)}
    finally:
        release.set()
        timer.join()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.data_dir.exists():
        raise SystemExit("Refusing to overwrite previous evidence")
    args.data_dir.mkdir(parents=True)
    before = hashes()
    sys.dont_write_bytecode = True
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    projection = load_module("file_review_projection", RUNNER.with_name("models.py"))
    transport = load_module("file_review_transport", CORE_DIR / "provider_http.py")
    retry_loop, cleanup_loop = asyncio.new_event_loop(), asyncio.new_event_loop()
    # Only already-initialized asyncio internal socketpairs exist. Every test
    # dispatch uses in-memory handlers; any accidental socket use is rejected.
    with patch.object(socket.socket, "connect", side_effect=AssertionError("No network")), \
            patch.object(socket, "create_connection", side_effect=AssertionError("No network")):
        results = grader_probes(tree) + isolation_probes(tree, args.data_dir) + literal_probes() + dispatch_probes(tree, projection)
        try:
            results.append(retry_loop.run_until_complete(retry_probe(tree, projection, transport)))
        finally:
            retry_loop.run_until_complete(retry_loop.shutdown_default_executor())
            retry_loop.close()
        results.append(late_save_probe(tree, projection, transport, args.data_dir, cleanup_loop))
    report = {"scope": "offline AST probes and in-memory transport only; no Core/private config/real HTTP",
              "real_http_attempts": 0, "source_sha256_before": before,
              "source_sha256_after": hashes(), "checks": results,
              "static_tools_available": [],
              "passed": all(item["passed"] for item in results) and before == hashes()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"passed": report["passed"], "checks": results, "evidence": str(args.output)},
                     ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
