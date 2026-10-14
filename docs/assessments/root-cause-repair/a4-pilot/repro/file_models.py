"""Reusable file-task protocol through Core.handle_chat; provider chosen by config.

Reuses the A4 runner's transport projection and redirect protection. Each run
owns a fresh persistent sandbox. An explicit supplement links a new bounded
ledger to the immutable original 30-attempt ledger and interrupted case.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import urllib.request
from unittest.mock import AsyncMock, patch

from models import NoRedirect, digest, public_messages


CAP = 30
PROTOCOLS = {"file": "file-write-confirm-read-v1", "issue": "issue-title-confirm-read-v1",
             "email": "email-send-confirm-receipt-v1"}
REQUIRED_CHECKS = ("no_preconfirm_effect", "real_proposal", "correct_write", "actual_read", "receipt_bound",
                   "complete_delivery", "no_duplicate_write", "truthful_progress", "history_reopened",
                   "ledger_reopened", "reads_reopened", "source_unchanged")
SAMPLES = {
    1: ("delivery note.txt", "第一行：合成记录青竹 175\n第二行：7月12日，长度3cm"),
    2: ("different-蓝桥.txt", "蓝桥记录：42kg，普通Disco\n核验尾行：蓝色小鸟73921"),
    3: ("third sample.md", "## 合成温度 20℃\n完整末行：READY 902，10月18日"),
}


def source_hashes(package):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (package / "agent_core").glob("*.py")}


def runner_hashes():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("file_models.py", "models.py")}


def protocol_runner_hashes(scenario):
    hashes = runner_hashes()
    if scenario in {"issue", "email"}:
        name = scenario + "_model_case.py"
        hashes[name] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        fixture = Path(__file__).resolve().parents[5] / f"services/agent-core/tests/{scenario}_fixture.py"
        hashes[fixture.name] = hashlib.sha256(fixture.read_bytes()).hexdigest()
        schema = Path(__file__).resolve().parents[5] / "docs/assessments/root-cause-audit/evidence/mcp-schema.json"
        hashes["mcp-schema.json"] = hashlib.sha256(schema.read_bytes()).hexdigest()
    return hashes


def validate_issue_ledger(args, ledger):
    """The new protocol uses one existing-format ledger, including expansion."""
    if [a.get("index") for a in ledger["attempts"]] != list(range(1, len(ledger["attempts"]) + 1)):
        raise RuntimeError("Non-contiguous Issue HTTP ledger")
    if args.variant > 1 and not args.offline:
        reports = [json.loads(p.read_text(encoding="utf-8")) for p in args.initial_report]
        if ({(r.get("provider"), r.get("model")) for r in reports} !=
                {("deepseek", "Deepseek-v4-flash"), ("glm", "GLM-5.2")}):
            raise RuntimeError("Expansion needs the two requested providers and models")
        for report in reports:
            if not report.get("calls") or report.get("ledger_path") != str(args.ledger):
                raise RuntimeError("Initial results must belong to this shared Issue ledger")
            if any({k: c[k] for k in ("index", "model", "request_id")} not in ledger["attempts"] for c in report["calls"]):
                raise RuntimeError("Initial HTTP attempts missing from shared Issue ledger")


def read_connection(path):
    # Only connection fields are selected; never load private runtime settings
    # into Core or include credentials/endpoint URLs in evidence.
    from dotenv import dotenv_values
    import io
    allowed = {f"{prefix}_{suffix}" for prefix in ("DEEPSEEK", "GLM")
               for suffix in ("BASE_URL", "MODEL", "API_KEY")} | {"GLM_CREDENTIAL_SOURCE", "LLM_PROXY_MODE"}
    with path.open(encoding="utf-8-sig") as stream:
        selected = "\n".join(line.rstrip() for line in stream if line.split("=", 1)[0].strip() in allowed)
    return {k: v for k, v in dotenv_values(stream=io.StringIO(selected), interpolate=False).items() if v is not None}


def score(item):
    checks = item["checks"]
    item["passed"] = all(checks.get(key) is True for key in REQUIRED_CHECKS) and not item.get("exception")
    if item["passed"]:
        item["failure_category"] = None
    elif any(c.get("error_type") for c in item["calls"]) or any(e.get("outcome") in {"failed", "deadline_exceeded"} for e in item.get("transport", [])):
        item["failure_category"] = "connection_or_protocol"
    elif any(not checks.get(k, False) for k in ("no_preconfirm_effect", "no_duplicate_write", "receipt_bound")):
        item["failure_category"] = "permission_or_receipt"
    else:
        item["failure_category"] = "proposal_or_task"


def supplement_budget(args, hashes):
    """Authorize only the referenced frozen case; never reuse its task state."""
    if args.prior_ledger is None and args.supplement_of is None:
        if args.http_budget != (40 if getattr(args, "scenario", "file") in {"issue", "email"} else CAP):
            raise SystemExit("A non-default HTTP budget requires both supplement references")
        return None, None
    if getattr(args, "scenario", "file") != "file":
        raise SystemExit("File supplement references cannot fund another protocol")
    if args.prior_ledger is None or args.supplement_of is None or not 1 <= args.http_budget <= 8:
        raise SystemExit("Supplement requires prior ledger, interrupted case and 1..8 HTTP attempts")
    args.prior_ledger = args.prior_ledger.resolve()
    args.supplement_of = args.supplement_of.resolve()
    if args.ledger in {args.prior_ledger, args.supplement_of} or args.ledger.exists():
        raise SystemExit("Supplement needs a new ledger; prior evidence is immutable")
    prior_bytes, case_bytes = args.prior_ledger.read_bytes(), args.supplement_of.read_bytes()
    prior, case = json.loads(prior_bytes), json.loads(case_bytes)
    if (prior.get("cap") != CAP or [a.get("index") for a in prior.get("attempts", [])] != list(range(1, CAP + 1))
            or case.get("passed") is not False or case.get("offline") is not False
            or case.get("shared_http_attempts") != CAP or case.get("source_sha256") != hashes
            or case.get("variant") != args.variant or case.get("provider") != args.provider
            or case.get("checks", {}).get("real_proposal") is not True
            or case.get("checks", {}).get("correct_write") is not True
            or case.get("checks", {}).get("actual_read") is not False
            or not case.get("calls")
            or any({k: c[k] for k in ("index", "model", "request_id")} not in prior["attempts"] for c in case["calls"])):
        raise SystemExit("Supplement does not match the exhausted ledger and frozen interrupted case")
    link = {"prior_ledger": str(args.prior_ledger), "prior_ledger_sha256": hashlib.sha256(prior_bytes).hexdigest(),
            "prior_attempts": CAP, "interrupted_case": str(args.supplement_of),
            "interrupted_case_sha256": hashlib.sha256(case_bytes).hexdigest(),
            "original_runner_sha256": case["runner_sha256"], "additional_cap": args.http_budget,
            "cumulative_cap": CAP + args.http_budget}
    return {"cap": args.http_budget, "prior_attempts": CAP, "supplement": link, "attempts": []}, case


def claim_supplement(args):
    if args.reference_case is None or args.offline:
        return
    # The original ledger remains read-only. An exclusive adjacent claim binds
    # this single authorized supplement even if a caller selects another ledger.
    claim = args.prior_ledger.with_name(args.prior_ledger.name + ".supplement-claim.json")
    with claim.open("x", encoding="utf-8") as stream:
        json.dump({"ledger": str(args.ledger), "data_dir": str(args.data_dir),
                   **args.supplement_ledger["supplement"]}, stream, ensure_ascii=False, indent=2)
    args.supplement_ledger["supplement"]["claim"] = str(claim)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--private-config", type=Path)
    parser.add_argument("--provider", choices=("deepseek", "glm"), default="deepseek")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--variant", type=int, choices=SAMPLES, default=1)
    parser.add_argument("--scenario", choices=("file", "issue", "email"), default="file")
    parser.add_argument("--initial-report", type=Path, action="append", default=[])
    parser.add_argument("--http-budget", type=int)
    parser.add_argument("--prior-ledger", type=Path)
    parser.add_argument("--supplement-of", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.http_budget is None:
        args.http_budget = 40 if args.scenario in {"issue", "email"} else CAP
    if args.scenario in {"issue", "email"} and args.variant > 2:
        parser.error("Issue and Email protocols have only two variants")
    if not args.offline and args.private_config is None:
        parser.error("Live verification requires an explicitly selected connection config")
    args.source_root = args.source_root.resolve()
    args.data_dir = args.data_dir.resolve()
    args.ledger = args.ledger.resolve()
    if args.data_dir.exists():
        raise SystemExit("Refusing to overwrite previous evidence")
    package = args.source_root / "services/agent-core"
    hashes = source_hashes(package)
    args.supplement_ledger, args.reference_case = supplement_budget(args, hashes)
    if args.variant > 1 and not args.offline and args.reference_case is None:
        initial = [json.loads(p.read_text(encoding="utf-8")) for p in args.initial_report]
        if (len(initial) != 2 or not all(r.get("passed") and not r.get("offline") and r.get("variant") == 1
                                       and r.get("source_sha256") == hashes and r.get("runner_sha256") == protocol_runner_hashes(args.scenario)
                                       and r.get("protocol") == PROTOCOLS[args.scenario] for r in initial)
                or len({r["model"] for r in initial}) != 2
                or len({r["input_normalized_sha256"] for r in initial}) != 1
                or len({digest(r.get("budget")) for r in initial}) != 1
                or len({r.get("initial_state_sha256") for r in initial}) != 1
                or len({r["tool_schema_sha256"] for r in initial}) != 1):
            raise SystemExit("Expansion requires both equivalent initial cases passing on this source")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(package))
    connection = {} if args.offline else read_connection(args.private_config)
    args.data_dir.mkdir(parents=True)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = args.ledger.with_suffix(args.ledger.suffix + ".lock")
    # Concurrent processes may not each spend the same last request slot.
    with lock_path.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        if args.reference_case is not None and args.ledger.exists():
            raise SystemExit("A supplement already started; do not run a second task")
        claim_supplement(args)
        return run(args, package, hashes, connection)
    finally:
        lock_path.unlink()


def run(args, package, hashes, connection):
    config_path = args.data_dir / "isolated.env"
    config_path.write_text("LLM_PROVIDER=mock\n", encoding="utf-8")
    for key in list(os.environ):
        if key.startswith(("ANIME_AGENT_", "DEEPSEEK_", "GLM_", "STEPFUN_")):
            os.environ.pop(key)
    os.environ.update(ANIME_AGENT_DATA_DIR=str(args.data_dir / "bootstrap"),
        ANIME_AGENT_CONFIG_PATH=str(config_path), LLM_PROVIDER="mock", ANIME_AGENT_TTS="0",
        ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_ALLOWED_COMMANDS="",
        ANIME_AGENT_VOICE_INPUT_MODE="manual")

    def audit(event, values):
        if event == "sqlite3.connect":
            path = Path(str(values[0])).resolve()
            if not path.is_relative_to(args.data_dir):
                raise RuntimeError("Non-isolated database blocked before access")
        if event == "open" and isinstance(values[0], (str, bytes)):
            path = Path(os.fsdecode(values[0])).resolve()
            mode, flags = values[1:3]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
            if writing and not path.is_relative_to(args.data_dir) and path != args.ledger:
                raise RuntimeError("Non-isolated write blocked")
            if path.name.endswith(".env") and path != config_path:
                raise RuntimeError("Private runtime config blocked")
        if event in {"subprocess.Popen", "os.system"} or (args.offline and event.startswith("socket.")):
            raise RuntimeError("External I/O forbidden in this fixture")

    # Windows asyncio creates its internal socket pair during loop creation;
    # initialize that plumbing before forbidding every later offline socket.
    loop = asyncio.new_event_loop()
    sys.addaudithook(audit)
    from agent_core import main as core
    from agent_core.actions import ActionLedger
    from agent_core.storage import MemoryStore
    from agent_core.tools import openai_tools_schema
    if not Path(core.__file__).resolve().is_relative_to(package) or core.ENV_PATH.resolve() != config_path:
        raise RuntimeError("Core source/config isolation mismatch")
    core.memory.close()
    registry = {k: v for k, v in core.tool_registry.items() if k in {"write_file", "read_file"}}
    schemas = openai_tools_schema(registry)
    issue_case = None
    if args.scenario == "issue":
        sys.path.insert(0, str(package / "tests"))
        from issue_model_case import IssueCase
        issue_case = IssueCase(args, core)
        schemas = issue_case.schemas
    elif args.scenario == "email":
        sys.path.insert(0, str(package / "tests"))
        from email_model_case import EmailCase
        issue_case = EmailCase(args, core)
        schemas = issue_case.schemas
    ledger = args.supplement_ledger or (json.loads(args.ledger.read_text(encoding="utf-8")) if args.ledger.exists() else {"cap": args.http_budget, "attempts": []})
    if ledger.get("cap") != args.http_budget or not isinstance(ledger.get("attempts"), list) or len(ledger["attempts"]) > args.http_budget:
        raise RuntimeError("Invalid shared request ledger")
    if issue_case:
        validate_issue_ledger(args, ledger)
    if issue_case and not args.offline and ledger["cap"] - len(ledger["attempts"]) < 18:
        raise RuntimeError("Reserve 18 HTTP slots for a complete six-round case including transport retries")
    output = args.data_dir / (args.scenario + "-model.json")
    record = {"protocol": PROTOCOLS[args.scenario], "offline": args.offline, "variant": args.variant,
        "source_sha256": hashes, "runner_sha256": protocol_runner_hashes(args.scenario), "tool_schema_sha256": digest(schemas), "provider": args.provider,
        "budget": {"max_steps": 6, "max_calls": 12, "corrections": 1, "timeout_seconds": 45},
        "initial_state_sha256": digest({"target_file": None, "messages": [], "actions": []}),
        "transport_cap": ledger["cap"], "calls": [], "turns": [], "effects": [], "checks": {}, "transport": []}
    if args.reference_case is not None:
        record["supplement"] = ledger["supplement"]
    if issue_case:
        record["ledger_path"] = str(args.ledger)
    mutex = threading.RLock()

    def save():
        with mutex:
            output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            # Save prior to network dispatch. Interrupted evidence never refills
            # quota; the exclusive process lock prevents competing writers.
            args.ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    class ObservedProvider(core.OpenAICompatibleProvider):
        def _request(self, request):
            with mutex:
                if len(ledger["attempts"]) >= ledger["cap"]:
                    raise core.ProviderError("Shared HTTP attempt limit reached; no request sent")
                body = json.loads(request.data)
                item = {"index": ledger.get("prior_attempts", 0) + len(ledger["attempts"]) + 1, "model": self.model,
                        "request_id": core.REQUEST_ID.get(), "messages": public_messages(body["messages"]),
                        "tools": body.get("tools", [])}
                ledger["attempts"].append({k: item[k] for k in ("index", "model", "request_id")})
                record["calls"].append(item)
                save()
            try:
                build_opener = urllib.request.build_opener
                with patch.object(urllib.request, "build_opener", lambda *handlers: build_opener(*handlers, NoRedirect())):
                    raw = super()._request(request)
                choice = json.loads(raw)["choices"][0]
                message = public_messages([{**choice["message"], "role": "assistant"}])[0]
                item["response"] = {"content": message.get("content"), "tool_calls": message.get("tool_calls", []),
                                    "finish_reason": choice.get("finish_reason")}
                return raw
            except Exception as exc:
                item["error_type"] = type(exc).__name__
                raise
            finally:
                save()

    if args.offline:
        record["model"] = "controlled-provider"
    else:
        with patch.dict(os.environ, connection):
            base_url, model, api_key = core._provider_config(args.provider)
        if not api_key or not model or not base_url.startswith("https://"):
            raise RuntimeError("Missing or unsupported connection config; no request sent")
        if issue_case and model != {"deepseek": "Deepseek-v4-flash", "glm": "GLM-5.2"}[args.provider]:
            raise RuntimeError("Configured model is not the requested Issue verification model; no request sent")
        if args.reference_case is not None and model != args.reference_case["model"]:
            raise RuntimeError("Supplement model differs from the referenced case; no request sent")
        record["model"] = model
        live_provider = ObservedProvider(name=args.provider, base_url=base_url, model=model, api_key=api_key,
            timeout_seconds=45, proxy_mode=connection.get("LLM_PROXY_MODE", "auto"),
            on_transport_event=lambda event: record["transport"].append({k: v for k, v in event.items() if k != "host"}))
    filename, content = SAMPLES[args.variant]
    file_dir = args.data_dir / "files"
    file_dir.mkdir()
    path = file_dir / filename
    text = f"请创建文件 {path.as_posix()}，写入后实际读取该文件并展示完整内容。内容如下（两行，末尾无换行）：\n{content}"
    record["input_normalized_sha256"] = digest(text.replace(path.as_posix(), "<isolated-file>"))
    record["expected"] = {"path": str(path), "content": content, "sha256": hashlib.sha256(content.encode()).hexdigest()}
    if issue_case:
        record.update(issue_case.metadata())
    if args.reference_case is not None:
        keys = ("budget", "initial_state_sha256", "tool_schema_sha256", "input_normalized_sha256")
        if any(record[k] != args.reference_case[k] for k in keys):
            raise RuntimeError("Supplement changed the task, schema, budget or initial state; no request sent")

    async def exercise():
        store = MemoryStore(data_dir=args.data_dir / "db")
        original_execute = core._execute_authorized_tool

        async def execute(name, arguments):
            if name not in registry:
                raise RuntimeError("Unselected tool blocked")
            record["effects"].append({"tool": name, "arguments": dict(arguments), "request_id": core.REQUEST_ID.get()})
            return await original_execute(name, arguments)

        async def scripted(*_):
            task = core._task_state[core._ACTIVE_CHAT_SESSION_ID[0]]
            actions = core._actions().task_items(core._ACTIVE_CHAT_SESSION_ID[0], task["id"])
            reads = task.get("tool_results", [])
            if not actions:
                return {"tool_calls": [{"id": "controlled-write", "name": "write_file", "arguments": {"path": str(path), "content": content}}]}
            if not reads:
                return {"tool_calls": [{"id": "controlled-read", "name": "read_file", "arguments": {"path": str(path)}}]}
            return {"content": json.dumps({"decision": {"mode": "report", "action_refs": [a["action_id"] for a in actions],
                "read_refs": [r["result_ref"] for r in reads]}, "reply": "模型摘要不替代原文"}, ensure_ascii=False)}

        try:
            with ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ, {"ANIME_AGENT_WRITE_ROOTS": str(file_dir), "ANIME_AGENT_TOOLS_ROOTS": str(file_dir)}))
                stack.enter_context(patch.multiple(core, memory=store,
                    provider=SimpleNamespace(complete_with_tools=scripted) if args.offline else live_provider,
                    tools_schema=schemas, tool_registry=registry,
                    mcp_host=SimpleNamespace(tool_entries=lambda: []), _execute_authorized_tool=execute,
                    hub=SimpleNamespace(send_roles=AsyncMock(), role_count=lambda *_: 0), broadcast_state=AsyncMock(),
                    broadcast_behavior=AsyncMock(), _spawn=lambda c: c.close(), _action_ledger=None, _task_state={},
                    _result_pages={}, _pending_writes={}, _shown_confirmations={}, chat_lock=asyncio.Lock()))
                sid = store.create_session()["id"]
                record["session_id"] = sid

                async def turn(user, suffix):
                    rid = f"file-{args.variant}-{suffix}"
                    await core.handle_chat(user, rid, sid, effort="standard")
                    record["turns"].append({"input": user, "request_id": rid, "answer": store.load_messages(100, sid)[-1]["content"],
                        "pending": [core._actions().ticket(a) for a in core._sync_pending(sid)]})
                    save()

                await turn(text, "request")
                pending = core._sync_pending(sid)
                checks = record["checks"]
                checks["no_preconfirm_effect"] = not path.exists() and not any(e["tool"] == "write_file" for e in record["effects"])
                checks["real_proposal"] = len(pending) == 1 and pending[0]["tool"] == "write_file" and Path(pending[0]["arguments"].get("path", "")).resolve() == path and pending[0]["arguments"].get("content") == content and pending[0]["arguments"].get("mode", "overwrite") == "overwrite"
                if checks["real_proposal"] and checks["no_preconfirm_effect"]:
                    await turn("确认", "confirm")
                record["actions"] = list(core._actions().records.values())
                record["tasks"] = list(core._task_state.values())
                reads = [r for t in record["tasks"] for r in t.get("tool_results", []) if r["tool"] == "read_file"]
                checks["correct_write"] = path.is_file() and path.read_bytes() == content.encode("utf-8")
                checks["actual_read"] = any(r["result"].get("ok") is True and r["result"].get("content") == content and r["result"].get("truncated") is False and Path(r["arguments"].get("path", "")).resolve() == path and r.get("after_actions") for r in reads)
                checks["receipt_bound"] = all(a["session_id"] == sid and a["task_id"] == "file-" + str(args.variant) + "-request" for a in record["actions"]) and all(r["session_id"] == sid for r in reads)
                checks["complete_delivery"] = len(record["turns"]) == 2 and "文件任务已完成" in record["turns"][1]["answer"] and content in record["turns"][1]["answer"]
                writes_before = sum(e["tool"] == "write_file" for e in record["effects"])
                calls_before = len(record["calls"])
                if not core._sync_pending(sid):
                    await turn("确认", "duplicate")
                checks["no_duplicate_write"] = writes_before <= 1 and sum(e["tool"] == "write_file" for e in record["effects"]) == writes_before and len(record["calls"]) == calls_before
                await turn("刚才那个任务现在怎么样？", "status")
                answer = record["turns"][-1]["answer"]
                checks["truthful_progress"] = len(record["calls"]) == calls_before and (("执行成功" in answer) if checks["correct_write"] else ("执行成功" not in answer))
                record["messages"] = public_messages(store.load_messages(100, sid))
                rows = store.connection.execute("SELECT event_type,payload FROM events WHERE event_type IN ('tool.result','task.decision','chat.delivery') ORDER BY id").fetchall()
                record["events"] = [{"type": r[0], "payload": json.loads(r[1])} for r in rows]
        except Exception as exc:
            record["exception"] = type(exc).__name__
        finally:
            store.close()
        reopened = MemoryStore(data_dir=args.data_dir / "db")
        try:
            record["checks"]["history_reopened"] = bool(record.get("messages")) and public_messages(reopened.load_messages(100, record["session_id"])) == record.get("messages")
            record["checks"]["ledger_reopened"] = list(ActionLedger(reopened.connection).records.values()) == record.get("actions")
            rows = reopened.connection.execute("SELECT payload FROM events WHERE event_type='tool.result' ORDER BY id").fetchall()
            expected_reads = [r for t in record.get("tasks", []) for r in t.get("tool_results", [])]
            record["checks"]["reads_reopened"] = bool(expected_reads) and any(r["tool"] == "read_file" for r in expected_reads) and [json.loads(r[0]) for r in rows] == expected_reads
        finally:
            reopened.close()

    try:
        loop.run_until_complete(issue_case.exercise(record, None if args.offline else live_provider, save) if issue_case else exercise())
    finally:
        # A timed-out HTTP worker can finish later. Keep the ledger lock and
        # event loop alive until its final telemetry has been saved.
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()
    record["checks"]["source_unchanged"] = (source_hashes(package) == hashes
        and protocol_runner_hashes(args.scenario) == record["runner_sha256"])
    record["http_attempts"] = len(record["calls"])
    record["shared_http_attempts"] = len(ledger["attempts"])
    record["cumulative_http_attempts"] = ledger.get("prior_attempts", 0) + len(ledger["attempts"])
    if args.reference_case is not None:
        record["prior_evidence_unchanged"] = (
            hashlib.sha256(args.prior_ledger.read_bytes()).hexdigest() == record["supplement"]["prior_ledger_sha256"]
            and hashlib.sha256(args.supplement_of.read_bytes()).hexdigest() == record["supplement"]["interrupted_case_sha256"])
        if not record["prior_evidence_unchanged"]:
            record["exception"] = "PriorEvidenceChanged"
    if issue_case:
        issue_case.score(record)
    else:
        score(record)
    save()
    print(json.dumps({k: record[k] for k in ("model", "variant", "passed", "failure_category", "checks", "http_attempts", "shared_http_attempts")}, ensure_ascii=False))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
