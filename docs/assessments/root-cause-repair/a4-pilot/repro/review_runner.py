"""Independent offline A4 review probes; no real network or production data.

Extract the current runner's grader/observer AST unchanged so counterexamples
exercise its code. All fixtures and HTTP responses are synthetic. Output is
exclusive-create and contains booleans/metadata, never provider reasoning text.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
from contextlib import closing
from contextvars import ContextVar
from email.message import Message
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import urllib.request
import urllib.response
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[5]
RUNNER = Path(__file__).with_name("models.py")
CORE_DIR = ROOT / "services/agent-core/agent_core"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def extract(tree: ast.AST, name: str, namespace: dict):
    node = next(n for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == name)
    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(code, str(RUNNER), "exec"), namespace)
    return namespace[name]


def grade_probe(tree: ast.AST, decision: dict, scenario: str, answer: str) -> dict:
    item = {"scenario": scenario, "effects": [], "turns": [{"answer": answer, "pending": []}],
            "decisions": [decision], "actions": [], "tasks": [], "file_content": None}
    if any(isinstance(n, ast.FunctionDef) and n.name == "score_case" for n in tree.body):
        score_case = extract(tree, "score_case", {"json": json})
        return {"scenario": scenario, "grader_passed": bool(score_case(item))}
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.If) and n.orelse
                and n.body and isinstance(n.body[0], ast.Assign)
                and any(ast.unparse(t) == "item['passed']" for t in n.body[0].targets))
    namespace = {"item": item, "scenario": scenario, "effects": [], "json": json,
                 "core": SimpleNamespace(_sync_pending=lambda _: []), "sid": 1}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 str(RUNNER), "exec"), namespace)
    return {"scenario": scenario, "grader_passed": bool(item["passed"])}


def transport_probe(tree: ast.AST, public_messages) -> dict:
    """Run urllib's genuine redirect machinery with an in-memory HTTP handler."""
    attempts = []
    network = []
    response = json.dumps({"choices": [{"message": {"content": "synthetic"},
                                        "finish_reason": "stop"}]}).encode()

    class InMemoryHTTP(urllib.request.HTTPHandler):
        def http_open(self, request):
            network.append(request.get_method())
            headers = Message()
            if len(network) == 1:
                headers["Location"] = "http://synthetic.invalid/redirected"
                status, data = 302, b""
            else:
                status, data = 200, response
            result = urllib.response.addinfourl(io.BytesIO(data), headers, request.full_url, status)
            result.msg = "synthetic"
            return result

    class ParentProvider:
        model = "synthetic-model"

        def _request(self, request):
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), InMemoryHTTP())
            with opener.open(request) as result:
                return result.read()

    ledger = {"cap": 60, "attempts": [{"index": i} for i in range(1, 60)]}
    record = {"calls": []}
    namespace = {"core": SimpleNamespace(OpenAICompatibleProvider=ParentProvider,
                                          ProviderError=RuntimeError, REQUEST_ID=ContextVar("request", default="synthetic")),
                 "ledger": ledger, "record": record, "public_messages": public_messages,
                 "json": json, "urllib": urllib, "patch": patch,
                 "save": lambda: attempts.append(len(ledger["attempts"]))}
    if any(isinstance(n, ast.ClassDef) and n.name == "NoRedirect" for n in tree.body):
        extract(tree, "NoRedirect", namespace)
    observer = extract(tree, "ObservedProvider", namespace)()
    request = urllib.request.Request("http://synthetic.invalid/start",
                                     data=b'{"messages": [{"role": "user", "content": "synthetic"}]}')
    blocked = False
    try:
        observer._request(request)
    except (RuntimeError, urllib.error.HTTPError):
        blocked = True
    return {"prior_attempts": 59, "observed_ledger_count": len(ledger["attempts"]),
            "http_dispatches_in_memory": len(network), "blocked": blocked,
            "cap_would_be_exceeded": 59 + len(network) > 60}


def core_probes() -> list[dict]:
    """Use the actual entry point with synthetic providers and a fresh SQLite DB."""
    with tempfile.TemporaryDirectory(prefix="a4-review-") as temporary, asyncio.Runner() as runner:
        runner.get_loop()  # Windows creates its internal wakeup socketpair here.
        isolated = Path(temporary)
        environment = {"ANIME_AGENT_DATA_DIR": str(isolated / "bootstrap"),
                       "ANIME_AGENT_CONFIG_PATH": str(isolated / "absent.env"),
                       "LLM_PROVIDER": "mock", "ANIME_AGENT_TTS": "0",
                       "ANIME_AGENT_WAKE_WORD": "0", "ANIME_AGENT_MCP_SERVERS": "",
                       "ANIME_AGENT_ALLOWED_COMMANDS": "", "ANIME_AGENT_VOICE_INPUT_MODE": "manual",
                       "ANIME_AGENT_WRITE_ROOTS": str(isolated), "ANIME_AGENT_TOOLS_ROOTS": str(isolated)}
        with patch.dict(os.environ, environment), patch.object(socket.socket, "connect", side_effect=AssertionError("Real network prohibited")), patch.object(
                socket, "create_connection", side_effect=AssertionError("Real network prohibited")):
            sys.path.insert(0, str(CORE_DIR.parent))
            from agent_core import main as core
            from agent_core.storage import MemoryStore
            core.memory.close()

            async def run() -> list[dict]:
                results = []
                for name in ("invalid_mode", "exhausted_budget"):
                    store = MemoryStore(data_dir=isolated / name)
                    provider = SimpleNamespace(complete=AsyncMock(return_value='{"decision":{"mode":[]},"reply":"synthetic"}'))
                    try:
                        with patch.multiple(core, memory=store, provider=provider,
                                mcp_host=SimpleNamespace(tool_entries=lambda: []), tools_schema=[],
                                hub=SimpleNamespace(send_roles=AsyncMock(), role_count=lambda *_: 0),
                                broadcast_state=AsyncMock(), broadcast_behavior=AsyncMock(), _spawn=lambda c: c.close(),
                                _action_ledger=None, _task_state={}, _result_pages={}, _pending_writes={},
                                _shown_confirmations={}, chat_lock=asyncio.Lock()):
                            sid = store.create_session()["id"]
                            core._actions()
                            core._task_state[sid] = {"id": name, "intent": "synthetic", "blocked": False,
                                "budget": {"max_steps": 0 if name == "exhausted_budget" else 6, "max_calls": 12},
                                "rounds_used": 0, "calls_used": 0}
                            exception = None
                            try:
                                await core.handle_chat("继续", name, sid, effort="standard")
                            except TypeError as exc:
                                exception = type(exc).__name__
                            messages = store.load_messages(100, sid)
                            assistant = [m for m in messages if m["role"] == "assistant"]
                            results.append({"case": name, "exception_type": exception,
                                            "assistant_count": len(assistant),
                                            "assistant_nonempty": bool(assistant and assistant[-1]["content"]),
                                            "provider_calls": provider.complete.await_count})
                    finally:
                        store.close()
                return results
            return runner.run(run())


def public_export_probe(private_run: Path, public_dir: Path, subject) -> dict:
    """Independently inspect the existing public projection and synthetic DBs."""
    raw = private_run.read_bytes()
    historical = json.loads(raw)
    public = json.loads((public_dir / "models-initial.json").read_bytes())
    manifest = json.loads((public_dir / "manifest.json").read_bytes())
    forbidden_keys = []
    marker_paths = []

    def inspect(value, path="root"):
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = path + "." + key
                if key.lower() in {"reasoning", "reasoning_content", "thinking", "analysis"}:
                    forbidden_keys.append(child_path)
                inspect(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect(child, f"{path}[{index}]")
        elif isinstance(value, str) and re.search(r"<\s*/?\s*(?:think|thinking|analysis|reasoning)\b", value, re.I):
            marker_paths.append(path)

    inspect(public)
    actual_sources = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in CORE_DIR.glob("*.py")}
    first_cases = {case["id"]: case for case in historical["cases"]}
    final_cases = {case["id"]: case for case in public["cases"]}
    histories = {entry["case"]: entry for entry in manifest["history"]}
    database_results = []
    for case_id, case in first_cases.items():
        db = (private_run.parent / case_id / "db/anime-agent.sqlite3").resolve()
        db.relative_to(private_run.parent.resolve())
        before_hash = hashlib.sha256(db.read_bytes()).hexdigest()
        with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id",
                                      (case["session_id"],)).fetchall()
        expected = [{"role": message["role"], "content": message["content"]} for message in case["reopened_messages"]]
        database_results.append({"case": case_id, "same_as_first_reopen": [dict(row) for row in rows] == expected,
                                 "manifest_count_matches": histories[case_id]["messages"] == len(rows),
                                 "manifest_hash_matches": histories[case_id]["db_sha256"] == before_hash,
                                 "database_bytes_unchanged": hashlib.sha256(db.read_bytes()).hexdigest() == before_hash})
    report = {
        "forbidden_reasoning_field_paths": forbidden_keys, "reasoning_marker_paths": marker_paths,
        "source_hashes_match": actual_sources == manifest["final_business_sha256"],
        "source_file_count": len(actual_sources),
        "original_source_hashes_preserved": historical["source_sha256"] == public["source_sha256"] == manifest["first_live_business_sha256"],
        "historical_hash_matches_publication": hashlib.sha256(raw).hexdigest() == public["publication"]["original_private_sha256"],
        "historical_bytes_unchanged": private_run.read_bytes() == raw,
        "same_cases": first_cases.keys() == final_cases.keys(),
        "first_scores_preserved": all(case["passed"] == final_cases[case_id]["passed"] == final_cases[case_id]["first_score_preserved"]
                                      for case_id, case in first_cases.items()),
        "first_pass_count": sum(case["passed"] for case in first_cases.values()),
        "final_assertion_rescore_matches": all(bool(subject.score_case(first_cases[case_id])) == case["rescored_final_assertions"]
                                               for case_id, case in final_cases.items()),
        "projected_reopened_messages_match": all(subject.public_messages(first_cases[case_id]["reopened_messages"]) == case["reopened_messages"]
                                                 for case_id, case in final_cases.items()),
        "observed_entry_count": len(public["calls"]),
        "wire_count_claim_limited": "not instrumented" in public["publication"]["count_caveat"],
        "live_run_is_final_source": public["publication"]["live_run_is_final_source"],
        "database_checks": database_results,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--historical", type=Path)
    parser.add_argument("--core-probes", action="store_true")
    parser.add_argument("--public-evidence", type=Path)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    decision_module = load_module("a4_review_delivery", CORE_DIR / "task_delivery.py")
    loop = load_module("a4_review_loop", CORE_DIR / "agent_loop.py")
    helper_path = ROOT / "docs/assessments/root-cause-repair/batch-01/repro/followup_models.py"
    helper = load_module("a4_review_helper", helper_path)
    runner_module = load_module("a4_review_runner_subject", RUNNER)
    projector = getattr(runner_module, "public_messages", helper.public_messages)
    report = {"scope": "independent offline synthetic review; no real HTTP/production DB/services",
              "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (RUNNER, CORE_DIR / "task_delivery.py", CORE_DIR / "agent_loop.py",
                                          CORE_DIR / "main.py", CORE_DIR / "harness.py")},
              "probes": {}}
    probes = report["probes"]
    mode_results = []
    for mode in ([], {}):
        try:
            result = decision_module.validate_decision(json.dumps({"decision": {"mode": mode}, "reply": "synthetic"}),
                task={"id": "task"}, session_id=1, request_id="r", actions=[], schemas={})
            mode_results.append({"input_type": type(mode).__name__, "handled": True,
                                 "rejected": bool(result.error)})
        except TypeError as exc:
            mode_results.append({"input_type": type(mode).__name__, "handled": False,
                                 "exception_type": type(exc).__name__})
    probes["invalid_mode"] = mode_results
    probes["clarification_accepts_chat"] = grade_probe(tree, {"accepted": True, "mode": "chat"}, "clarification", "晚上好。")
    probes["explanation_accepts_irrelevant_chat"] = grade_probe(tree, {"accepted": True, "mode": "chat"}, "explanation", "蓝天。")
    probes["summary_missing_date_and_stages"] = grade_probe(tree, {"accepted": True, "mode": "report"}, "summary", "林岚 7600 青竹 175 原始记录")
    marker = "SYNTHETIC_REASONING_MARKER"
    projections = {
        "embedded_marker": {"role": "assistant", "content": f"<think>{marker}</think>{{\"reply\":\"synthetic\"}}"},
        "unclosed_marker": {"role": "assistant", "content": f"<think>{marker}"},
        "missing_role_marker": {"content": f"<think>{marker}</think>{{\"reply\":\"synthetic\"}}"},
        "content_array_marker": {"role": "assistant", "content": [{"type": "reasoning", "text": marker}, {"type": "text", "text": "synthetic"}]},
        "tool_call_marker": {"role": "assistant", "content": None, "tool_calls": [{"id": "synthetic", "type": "function",
            "reasoning": marker, "function": {"name": "synthetic", "arguments": "{}", "reasoning": marker}}]},
    }
    probes["content_projection"] = {key + "_preserved": marker in json.dumps(projector([value]))
                                    for key, value in projections.items()}
    with patch.object(socket.socket, "connect", side_effect=AssertionError("Real network prohibited")), patch.object(
            socket, "create_connection", side_effect=AssertionError("Real network prohibited")):
        probes["redirect_count"] = transport_probe(tree, projector)
    probes["positive_grader_controls"] = [
        grade_probe(tree, {"accepted": True, "mode": "clarify"}, "clarification", "请补充owner repo issue_number title"),
        grade_probe(tree, {"accepted": True, "mode": "chat"}, "explanation", "晚上好。确认后才能执行；已经完成需要真实回执。"),
        grade_probe(tree, {"accepted": True, "mode": "report"}, "summary", "林岚预算7600；准备校对，执行10月18日在青竹会议，核验175，保留原始记录。"),
    ]

    async def exhausted_probe():
        return await loop.run_agent_loop(SimpleNamespace(), [], [], None, max_steps=0,
                                         validate_final=lambda _: "invalid")
    exhausted = asyncio.run(exhausted_probe())
    probes["exhausted_delivery"] = {"host_delivery": exhausted.host_delivery,
                                   "hit_step_limit": exhausted.hit_step_limit,
                                   "nonempty_loop_text": bool(exhausted.text)}
    if args.core_probes:
        probes["actual_core_entry"] = core_probes()
    if args.historical:
        history = json.loads(args.historical.read_text(encoding="utf-8"))
        calls = history.get("calls", [])
        call_keys = sorted({key for call in calls for key in call})
        response_keys = sorted({key for call in calls for key in call.get("response", {})})
        history_meta = {"case_count": len(history.get("cases", [])),
                        "call_count": len(calls), "call_field_names": call_keys,
                        "response_field_names": response_keys,
                        "raw_file_sha256": hashlib.sha256(args.historical.read_bytes()).hexdigest(),
                        "redirect_history_recorded": any("redirect" in key.lower() for key in call_keys + response_keys),
                        "wire_dispatch_count_proven": False,
                        "count_limit": "Saved calls prove observer _request entries only; no per-dispatch/redirect telemetry was recorded.",
                        "cases": []}
        for case in history.get("cases", []):
            history_meta["cases"].append({key: case.get(key) for key in (
                "id", "scenario", "passed", "transport_count", "reopened_ok", "input_normalized_sha256", "initial_state_sha256")})
        probes["historical_metadata_only"] = history_meta
        if args.public_evidence:
            probes["public_export"] = public_export_probe(args.historical, args.public_evidence, runner_module)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "probe_count": len(probes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
