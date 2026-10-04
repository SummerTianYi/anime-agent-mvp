"""Codex evaluation-only isolated Core. No HTTP listener, lifespan, voice or UI.

Production logic is loaded from a verified source snapshot. Only I/O endpoints,
event observers and HTTP accounting are replaced, never authorization or loops.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import time
import urllib.error

from scripts.harness_v0.budget import BudgetExceeded, reserve
from scripts.harness_v0.prepare import dump, sha


def safe_confirmation(case, pending, root):
    """A fixture Manager approves only the exact allowed target and content."""
    name, args = pending.get("tool", ""), pending.get("arguments", {})
    if name == "write_file":
        path = Path(str(args.get("path", ""))).resolve()
        if not path.is_relative_to(root.resolve()):
            return False
        wanted = case["expected"].get("files_equal", {}).get(path.relative_to(root.resolve()).as_posix())
        return wanted is not None and str(args.get("content", "")).strip() == wanted.strip()
    if name.endswith("__send_email"):
        allowed = case.get("authorized_send_attempts", case["expected"].get("outbox", []))
        return any(all(args.get(k) == v for k, v in item.items()) for item in allowed)
    if name.endswith("__create_issue"):
        return args.get("owner") == "fixture-owner" and args.get("repo") == "fixture-repo" and any(
            all(args.get(k) == v for k, v in item.items()) for item in case["expected"].get("issues", []))
    return name in {"mcp__gmail__search_emails", "mcp__gmail__read_email", "mcp__github__get_file_contents"}


def sanitize(value, replacements, key):
    if isinstance(value, dict):
        return {k: ({"redacted_reasoning_sha256": sha(str(v)), "characters": len(str(v))}
                    if k in {"reasoning_content", "reasoning", "thinking"} and v else sanitize(v, replacements, key))
                for k, v in value.items() if k.lower() not in {"authorization", "api_key", "cookie"}}
    if isinstance(value, list):
        return [sanitize(v, replacements, key) for v in value]
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new).replace(old.replace("/", "\\\\"), new).replace(old.replace("/", "\\"), new)
        if key:
            value = value.replace(key, "[SECRET-REMOVED]")
    return value


async def run(job):
    case, tag, trial = job["case"], job["model_tag"], job["trial_id"]
    work = Path(job["trial_dir"]).resolve()
    root = work / "fixtures"
    root.mkdir(parents=True, exist_ok=False)
    for name, value in case["initial_fixture"]["files"].items():
        path = root / name
        assert path.resolve().is_relative_to(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    state_file = work / "connector-state.json"
    dump(state_file, copy.deepcopy(case["initial_fixture"]))
    # Deliberately never load the user's configuration inside Core. The parent
    # passes a single credential in its process environment, not in artifacts.
    key = os.environ.pop("HARNESS_MODEL_KEY", "")
    for k in list(os.environ):
        if k.startswith(("ANIME_AGENT_", "GLM_", "DEEPSEEK_", "LLM_", "STEPFUN_", "QWEN_")):
            del os.environ[k]
    os.environ.update({"ANIME_AGENT_CONFIG_PATH": str(work / "no-production.env"),
        "ANIME_AGENT_DATA_DIR": str(work / "db"), "ANIME_AGENT_TTS": "0", "ANIME_AGENT_WAKE_WORD": "0",
        "ANIME_AGENT_MCP_SERVERS": "", "ANIME_AGENT_ALLOWED_COMMANDS": "",
        "ANIME_AGENT_TOOLS_ROOTS": str(root), "ANIME_AGENT_WRITE_ROOTS": str(root),
        "LLM_PROVIDER": "mock", "AGENT_CORE_PORT": "0"})
    sys.path.insert(0, job["source_path"])
    import agent_core.main as core
    from agent_core.mcp_host import McpServer
    from agent_core.provider_http import REQUEST_ID
    assert not core.TTS_ENABLED and core.ENV_PATH == work / "no-production.env"
    store = core.memory
    core._actions()
    evidence = {"trial_id": trial, "case_id": case["id"], "model_tag": tag,
                "layer": "real-model/isolated-current-core/local-files-and-sqlite/controlled-stdio-mcp",
                "turns": [], "events": [], "attempts": [], "executions": [], "http": [], "transport": [],
                "source_manifest": job["versions"], "model_configuration": job["model"],
                "external_services_tested": False, "isolation_interventions": []}
    calibration = job.get("calibration_responses")
    if calibration is not None:
        evidence["layer"] = "simulated-model/calibration-only"
    current = {"request_id": "", "authorized_by": None}

    def snapshot():
        state = json.loads(state_file.read_text(encoding="utf-8"))
        database = {table: [dict(row) for row in store.connection.execute("SELECT * FROM " + table)]
                    for table in ("messages", "facts", "events", "sessions", "harness_actions")}
        return {"files": {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8", errors="replace")
                          for p in sorted(root.rglob("*")) if p.is_file()},
                "outbox": state["mail"]["outbox"], "issues": state["github"]["issues"],
                "facts": database["facts"], "database": database, "connector_state": state}

    class Hub:
        client_count = 0
        def role_count(self, role): return 0
        async def send_roles(self, roles, payload):
            evidence["events"].append({**copy.deepcopy(payload), "observer_request_id": current["request_id"]})

    core.hub = Hub()
    original_execute, original_run = core.execute_tool, core.run_tool
    original_authorized = core._execute_authorized_tool
    async def authorized(name, args):
        action = next((a for a in core._actions().records.values() if a["status"] == "executing"
                       and a["tool"] == name and a["arguments"] == args), None)
        current["native_action"] = copy.deepcopy(action)
        try:
            return await original_authorized(name,args)
        finally:
            current["native_action"] = None
    core._execute_authorized_tool = authorized

    async def execute(registry, name, arguments):
        args = arguments if isinstance(arguments, dict) else {}
        kind = "mutation" if name in {"write_file", "run_command"} else "read"
        denied = False
        if name in {"read_file", "write_file", "list_dir"}:
            candidate = Path(str(args.get("path", "")))
            denied = not candidate.is_absolute() or not candidate.resolve().is_relative_to(root)
        if name in {"run_command", "screenshot", "clipboard_read", "active_window"} or denied:
            result = {"ok": False, "error": "HARNESS_ISOLATION: host/private I/O disabled; synthetic fixtures only"}
            evidence["isolation_interventions"].append({"request_id": current["request_id"], "tool": name,
                                                        "arguments": args})
        elif name == "get_time":
            result = {"ok": True, "local_time": "2026-10-04 12:00:00", "weekday": "日", "utc_offset": "+0800"}
        else:
            result = await original_execute(registry, name, args)
        evidence["executions"].append({"execution_id": trial + "-exec-" + str(len(evidence["executions"]) + 1),
            "request_id": current["request_id"], "authorized_by": current["authorized_by"], "native_action": copy.deepcopy(current.get("native_action")), "kind": kind,
            "tool": name, "arguments": copy.deepcopy(args), "result": copy.deepcopy(result)})
        return result

    async def tool(name, args):
        evidence["attempts"].append({"request_id": current["request_id"], "tool": name, "arguments": copy.deepcopy(args)})
        return await original_run(name, args)

    core.execute_tool, core.run_tool = execute, tool
    # Seed fixtures directly: exercising memory promotion here would change the
    # specified initial state (near-duplicate seed facts can supersede each other).
    for fact in case["initial_fixture"]["facts"]:
        store.connection.execute("INSERT INTO facts(scope,content,status,source_request_id) VALUES ('global',?,'confirmed','fixture')", (fact,))
    store.connection.commit()
    servers = []
    for domain in ("gmail", "github"):
        server = McpServer(domain, [sys.executable, job["fixture_script"], str(state_file), domain])
        await server.start()
        original_call = server.call
        async def mcp_call(name, args, original_call=original_call, domain=domain):
            receipt = await original_call(name, args)
            evidence["executions"].append({"execution_id": trial + "-exec-" + str(len(evidence["executions"]) + 1),
                "request_id": current["request_id"], "authorized_by": current["authorized_by"], "native_action": copy.deepcopy(current.get("native_action")),
                "kind": "mutation" if name in {"send_email", "create_issue"} else "read",
                "tool": f"mcp__{domain}__{name}", "arguments": copy.deepcopy(args), "result": copy.deepcopy(receipt)})
            return receipt
        server.call = mcp_call
        core.mcp_host.servers[domain] = server
        servers.append(server)
    config = job["model"]
    provider = core.OpenAICompatibleProvider(name="deepseek" if tag == "ds" else "glm",
        base_url=config["base_url"], model=config["model"], api_key=key,
        timeout_seconds=config["timeout_seconds"], proxy_mode=config["proxy_mode"],
        on_transport_event=lambda e: evidence["transport"].append(e))
    real_request = provider._request

    def request(req):
        if req.full_url != config["base_url"].rstrip("/") + "/chat/completions":
            raise RuntimeError("Unregistered provider URL")
        serial = reserve(job["budget_path"], trial)
        entry = {"global_http_sequence": serial, "request_id": REQUEST_ID.get(), "url": req.full_url,
                 "request_body": json.loads(req.data), "status": None}
        evidence["http"].append(entry)
        start = time.monotonic()
        try:
            if calibration is None:
                response = real_request(req)
            else:
                assert calibration, "Calibration script exhausted"
                message = calibration.pop(0)
                if "tool_calls" in message:
                    for call in message["tool_calls"]:
                        call["function"]["arguments"] = call["function"]["arguments"].replace("{ROOT}", root.as_posix())
                response = json.dumps({"model": config["model"], "choices": [{"message": message}]}).encode("utf-8")
                entry["simulated"] = True
            entry.update(status=200, response_body=json.loads(response))
            return response
        except urllib.error.HTTPError as exc:
            entry.update(status=exc.code, error_type=type(exc).__name__)
            raise
        except Exception as exc:
            entry.update(error_type=type(exc).__name__)
            raise
        finally:
            entry["elapsed_ms"] = round((time.monotonic() - start) * 1000)

    provider._request = request
    core.provider = provider
    session = store.latest_session_id()

    def pending():
        value = copy.deepcopy(core._pending_writes.get(session))
        if value:
            identity = json.dumps([session, value["tool"], value["arguments"]], sort_keys=True, ensure_ascii=False)
            value["observer_action_id"] = trial + "-action-" + sha(identity)[:12]
        return value

    async def turn(text, kind="user", confirms=None):
        if len(evidence["turns"]) >= 6:
            raise BudgetExceeded("trial_turn_limit")
        rid = trial + "-turn-" + str(len(evidence["turns"]) + 1)
        current.update(request_id=rid, authorized_by=rid if kind == "confirmation" else None)
        row = {"request_id": rid, "session_id": session, "kind": kind, "text": text,
               "pending_before": pending(), "confirms_action_id": confirms}
        evidence["turns"].append(row)
        try:
            ticket = {k: row["pending_before"][k] for k in ("action_id","revision","args_hash")} if kind == "confirmation" and row["pending_before"] else None
            await core.handle_chat(text, rid, conversation_id=session, effort=case["effort"], confirmation=ticket)
        finally:
            row["pending_after"] = pending()
            row["state_after"] = snapshot()

    evidence["before"] = snapshot()
    started = time.monotonic()
    try:
        async with asyncio.timeout(240):
            for step in case["steps"]:
                if step.get("new_session"):
                    session = store.create_session("合成跨会话测试")["id"]
                await turn(step["text"].replace("{ROOT}", root.as_posix()))
                seen = set()
                for _ in range(step.get("auto_confirm", 0)):
                    action = pending()
                    if not action:
                        break
                    if action["observer_action_id"] in seen:
                        evidence["auto_confirmation_stop"] = "same action remains pending"
                        break
                    if not safe_confirmation(case, action, root):
                        evidence["auto_confirmation_stop"] = "pending parameters outside frozen authorization"
                        break
                    seen.add(action["observer_action_id"])
                    await turn("确认", "confirmation", action["observer_action_id"])
    except BudgetExceeded as exc:
        evidence["task_limit"] = str(exc)
        if str(exc) == "global_http_limit":
            evidence["blocked"] = str(exc)
    except TimeoutError:
        evidence["task_limit"] = "trial_wall_time_limit"
    except Exception as exc:
        evidence["application_exception"] = {"type": type(exc).__name__, "message": str(exc)[:300]}
    finally:
        evidence["after"] = snapshot()
        evidence["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        last_failure = next((e for e in reversed(evidence["events"]) if e.get("type") == "core.error"), None)
        if last_failure:
            evidence["blocked"] = "provider_or_gateway_unavailable"
        evidence["final_contract_valid"] = False
        for entry in reversed(evidence["http"]):
            body = entry.get("response_body", {})
            try:
                message = body["choices"][0]["message"]
                if message.get("tool_calls"):
                    continue
                raw = json.loads(message["content"])
                evidence["final_contract_valid"] = isinstance(raw.get("reply"), str) and bool(raw.get("emotion")) and bool(raw.get("gesture"))
                break
            except (KeyError, TypeError, ValueError, IndexError):
                continue
        for server in servers:
            await server.stop()
            if server.process:
                await server.process.wait()
        store.close()
    replacements = [(root.as_posix(), "{ROOT}"), (work.as_posix(), "{TRIAL}"),
                    (job["source_path"], "{SOURCE}"), (str(Path.home()).replace("\\", "/"), "{HOME}")]
    return sanitize(evidence, replacements, key)


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = asyncio.run(run(job))
    dump(Path(job["output"]), result)


if __name__ == "__main__":
    main()
