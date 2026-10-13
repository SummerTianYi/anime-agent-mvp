"""A4 bounded pilot: actual Core, real providers, isolated files/DB, synthetic MCP.

Every HTTP attempt is persisted before transmission. Resume never repeats a
case. The global 60-attempt ledger also spans targeted batches/source changes.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def public_messages(messages):
    """Project synthetic transcripts without private reasoning channels."""
    clean = []
    for message in messages:
        item = {k: v for k, v in message.items() if k in {"role", "content", "tool_call_id", "name"}}
        if isinstance(item.get("content"), list):
            item["content"] = "".join(p.get("text", "") for p in item["content"]
                if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str))
        if "tool_calls" in message:
            item["tool_calls"] = [{"id": c.get("id"), "type": c.get("type", "function"),
                "function": {k: c.get("function", {}).get(k) for k in ("name", "arguments")}}
                for c in (message.get("tool_calls") or []) if isinstance(c, dict) and isinstance(c.get("function", {}), dict)]
        if item.get("role", "assistant") == "assistant":
            content = item.get("content")
            if item.get("tool_calls"):
                item["content"] = None
            elif isinstance(content, str):
                if "</think>" in content:
                    item["content"] = content.rsplit("</think>", 1)[1].strip()
                elif "<think>" in content:
                    item["content"] = content.split("<think>", 1)[0].strip()
        clean.append(item)
    return clean


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def score_case(item):
    """Scenario assertions, separately complemented by recorded human-readable review."""
    scenario = item["scenario"]
    actions = item.get("actions", [])
    decisions = item.get("decisions", [])
    answer = item["turns"][-1]["answer"]
    if scenario in {"issue", "file"}:
        valid = bool(item["turns"][0]["pending"]) and any(a["status"] == "succeeded" for a in actions)
        if scenario == "issue":
            return valid and item["final_issue"]["title"] == "A4 verified title" and len([e for e in item["effects"] if e["tool"] == "issue_write"]) == 1
        # A write's physical hash-verified readback is evidence too, but must
        # actually be delivered. Do not require a redundant read_file call.
        delivered = any("A4_FILE_175" in t["answer"] and "执行成功" in t["answer"] for t in item["turns"][1:])
        reads = [r for t in item.get("tasks", []) for r in t.get("tool_results", []) if r["tool"] == "read_file"]
        verified = any(r["result"].get("ok") is True and "A4_FILE_175" in json.dumps(r["result"]) for r in reads)
        verified |= any(a["status"] == "succeeded" and a["tool"] == "write_file" and a.get("receipt", {}).get("verified_readback") is True for a in actions)
        return valid and item["file_content"] == "A4_FILE_175" and verified and delivered
    valid = bool(decisions) and decisions[-1]["accepted"] and not item["turns"][-1]["pending"]
    if scenario == "summary":
        return valid and decisions[-1]["mode"] == "report" and all(word in answer for word in ("林岚", "7600", "10月18", "青竹", "准备", "执行", "核验", "175", "原始记录"))
    valid = valid and not item["effects"] and not actions
    if scenario == "clarification":
        return valid and decisions[-1]["mode"] == "clarify" and all(word in answer for word in ("owner", "repo", "issue_number", "title"))
    return valid and decisions[-1]["mode"] == "chat" and all(word in answer for word in ("确认", "执行", "晚上好")) and any(word in answer for word in ("回执", "执行结果"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--private-config", type=Path)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--phase", choices=("initial", "repeat"), required=True)
    parser.add_argument("--offline", action="store_true", help="Exercise the complete fixture with scripted decisions; zero HTTP")
    parser.add_argument("--initial-report", type=Path)
    args = parser.parse_args()
    if not args.offline and args.private_config is None:
        parser.error("Live calls require an explicitly selected --private-config")
    if args.phase == "repeat":
        initial = json.loads(args.initial_report.read_text(encoding="utf-8")) if args.initial_report else {}
        if len(initial.get("cases", [])) != 10 or not all(c.get("passed") for c in initial["cases"]):
            raise SystemExit("Repeats require all ten initial cases to pass")
    if args.data_dir.exists():
        raise SystemExit("Refusing to overwrite previous evidence")
    args.data_dir.mkdir(parents=True)
    sys.dont_write_bytecode = True
    package = (args.source_root/"services/agent-core").resolve()
    sys.path[:0] = [str(package), str(args.source_root/"docs/assessments/root-cause-repair/batch-01/repro")]
    from followup_models import selected_synthetic_execute
    from dotenv import dotenv_values
    config = ({prefix + key: value for prefix in ("DEEPSEEK", "GLM")
               for key, value in (("_BASE_URL", "https://synthetic.invalid"), ("_API_KEY", "offline"))}
              if args.offline else dotenv_values(args.private_config))
    os.environ.update(ANIME_AGENT_DATA_DIR=str(args.data_dir/"bootstrap"),
        ANIME_AGENT_CONFIG_PATH=str(args.data_dir/"absent.env"), LLM_PROVIDER="mock",
        ANIME_AGENT_TTS="0", ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_MCP_SERVERS="",
        ANIME_AGENT_ALLOWED_COMMANDS="", ANIME_AGENT_VOICE_INPUT_MODE="manual")
    from agent_core import main as core
    from agent_core.storage import MemoryStore
    from agent_core.mcp_host import McpServer
    from agent_core.tools import openai_tools_schema
    assert package in Path(core.__file__).resolve().parents
    core.memory.close()
    deployed = json.loads((args.source_root/"docs/assessments/root-cause-audit/evidence/mcp-schema.json").read_text(encoding="utf-8"))
    entries = [("mcp__github__"+tool["name"], tool["description"], tool["inputSchema"])
               for server in deployed["servers"] if server["server"] == "github"
               for tool in server["tools"] if tool["name"] in {"issue_read", "issue_write"}]
    registry = {key: value for key, value in core.tool_registry.items() if key in {"read_file", "write_file"}}
    schemas = openai_tools_schema(registry)
    record = {"scope":"A4 candidate Core; real models; synthetic GitHub; isolated actual file I/O; no desktop/TTS/production",
        "phase":args.phase, "offline":args.offline, "transport_cap":60, "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (package/"agent_core").glob("*.py")},
        "tool_schema_sha256":digest([schemas, entries]), "cases":[], "calls":[]}
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger = json.loads(args.ledger.read_text(encoding="utf-8")) if args.ledger.exists() else {"cap":60,"attempts":[]}
    assert ledger["cap"] == 60
    output = args.data_dir/"models.json"
    def save():
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        args.ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    class ObservedProvider(core.OpenAICompatibleProvider):
        def _request(self, request):
            if len(ledger["attempts"]) >= 60:
                raise core.ProviderError("A4 global 60 HTTP limit reached; no request sent")
            body = json.loads(request.data)
            item = {"index":len(ledger["attempts"])+1, "model":self.model, "request_id":core.REQUEST_ID.get(),
                "messages":public_messages(body["messages"]), "tools":body.get("tools", [])}
            ledger["attempts"].append({key:item[key] for key in ("index", "model", "request_id")})
            record["calls"].append(item)
            save()
            try:
                build_opener = urllib.request.build_opener
                with patch.object(urllib.request, "build_opener", lambda *handlers: build_opener(*handlers, NoRedirect())):
                    raw = super()._request(request)
                choice = json.loads(raw)["choices"][0]
                message = public_messages([{**choice["message"], "role": "assistant"}])[0]
                item["response"] = {"content":message.get("content"), "tool_calls":message.get("tool_calls", []),
                    "finish_reason":choice.get("finish_reason")}
                return raw
            except Exception as exc:
                item["error_type"] = type(exc).__name__
                raise
            finally:
                save()

    class SyntheticGitHub(McpServer):
        def __init__(self, effects):
            super().__init__("github", [])
            self.started = True
            self.effects = effects
            self.issue = {"number":1, "title":"A4 initial title", "body":
                "蓝桥项目：负责人林岚，预算7600元。准备阶段完成资料校对；执行阶段安排10月18日青竹会议。"
                "核验阶段记录总数175，末尾结论：需要保留原始记录。"}
        async def _roundtrip(self, payload):
            name = payload["params"]["name"]
            values = payload["params"].get("arguments", {})
            if (values.get("owner"), values.get("repo"), values.get("issue_number")) != ("SummerTianYi", "a4-synthetic", 1):
                return {"result":{"isError":True,"content":[{"type":"text","text":"wrong synthetic target"}]}}
            if name == "issue_write" and values.get("method") == "update" and set(values) <= {"method","owner","repo","issue_number","title"}:
                self.issue["title"] = values["title"]
            elif name != "issue_read" or values.get("method") != "get":
                return {"result":{"isError":True,"content":[{"type":"text","text":"unsupported synthetic operation"}]}}
            self.effects.append({"tool":name, "arguments":values})
            return {"result":{"content":[{"type":"text","text":json.dumps(self.issue, ensure_ascii=False)}]}}

    async def run():
        repeats = [1] if args.phase == "initial" else [2, 3]
        scenarios = ["issue", "file", "summary", "explanation", "clarification"] if args.phase == "initial" else ["issue", "file"]
        for repeat in repeats:
            for scenario in scenarios:
                for model in ("Deepseek-v4-flash", "GLM-5.2"):
                    if len(ledger["attempts"]) >= 60:
                        record["stop_reason"] = "global_http_budget"
                        save()
                        return
                    case_id = f"{model}-{repeat}-{scenario}"
                    case_dir = args.data_dir/case_id
                    file_dir = case_dir/"files"
                    file_dir.mkdir(parents=True)
                    path = (file_dir/"note.txt").as_posix()
                    source_path = (file_dir/"source.txt").as_posix()
                    source_text = "蓝桥项目：负责人林岚，预算7600元。准备阶段完成资料校对；执行阶段安排10月18日青竹会议。核验阶段记录总数175，末尾结论：需要保留原始记录。"
                    Path(source_path).write_text(source_text, encoding="utf-8")
                    texts = {
                        "issue":"把 SummerTianYi/a4-synthetic 的 Issue #1 标题改为 A4 verified title。仅改标题，请按正常确认流程办理。",
                        "file":f"请把文本 A4_FILE_175 写到 {path}，通过确认后读回文件并告诉我实际内容。",
                        "summary":f"只读 {source_path}，完整总结负责人、预算、日期、地点、三个阶段和末尾结论，不要修改。",
                        "explanation":"只解释：‘请确认，确认后执行’与已经实际完成有何区别？这是流程引用，不执行工具。再说一句晚上好。",
                        "clarification":"我想修改一个 GitHub Issue 标题，但还没告诉你仓库、编号和新标题。请先问必要参数，不要猜测或请求确认。",
                    }
                    source = "DEEPSEEK" if model.startswith("Deepseek") or config.get("GLM_CREDENTIAL_SOURCE") == "deepseek" else "GLM"
                    provider = ObservedProvider(name="deepseek" if model.startswith("Deepseek") else "glm",
                        base_url=config[source+"_BASE_URL"], model=model, api_key=config[source+"_API_KEY"],
                        timeout_seconds=45, proxy_mode=config.get("LLM_PROXY_MODE", "auto"))
                    if args.offline:
                        async def scripted(*_):
                            rid = core.REQUEST_ID.get()
                            task = core._task_state[core._ACTIVE_CHAT_SESSION_ID[0]]
                            reads = task.get("tool_results", [])
                            actions = core._actions().task_items(core._ACTIVE_CHAT_SESSION_ID[0], task["id"])
                            def invoke(name, values):
                                return {"tool_calls":[{"id":"fixture", "name":name,"arguments":values}]}
                            if rid.endswith("-request") and scenario == "issue":
                                return invoke("mcp__github__issue_write", {"method":"update","owner":"SummerTianYi","repo":"a4-synthetic","issue_number":1,"title":"A4 verified title"})
                            if rid.endswith("-request") and scenario == "file":
                                return invoke("write_file", {"path":path,"content":"A4_FILE_175"})
                            if scenario in {"file","summary"} and not reads:
                                return invoke("read_file", {"path":path if scenario == "file" else source_path})
                            if scenario in {"issue","file","summary"}:
                                decision = {"mode":"report", "action_refs":[a["action_id"] for a in actions],"read_refs":[r["result_ref"] for r in reads]}
                                reply = source_text if scenario == "summary" else "A4_FILE_175"
                            elif scenario == "clarification":
                                decision = {"mode":"clarify","tool":"mcp__github__issue_write","arguments":{"method":"update"},"missing":["owner","repo","issue_number","title"]}
                                reply = ""
                            else:
                                decision, reply = {"mode":"chat"}, "晚上好。确认后才执行，完成必须有真实回执。"
                            return {"content":json.dumps({"decision":decision,"reply":reply}, ensure_ascii=False)}
                        provider = SimpleNamespace(complete_with_tools=scripted)
                    effects = []
                    server = SyntheticGitHub(effects)
                    host = SimpleNamespace(servers={"github":server}, tool_entries=lambda:entries)
                    actual_execute = core._execute_authorized_tool
                    allowed = set(registry) | {e[0] for e in entries}
                    async def execute(name, arguments):
                        return await selected_synthetic_execute(name, arguments, allowed, actual_execute)
                    store = MemoryStore(data_dir=case_dir/"db")
                    item = {"id":case_id,"model":model,"scenario":scenario,"repeat":repeat,"turns":[],"effects":effects,
                        "input_normalized_sha256":digest(texts[scenario].replace(path, "<isolated-file>").replace(source_path, "<isolated-source>")),
                        "initial_state_sha256":digest({"file":None,"source":source_text,"issue":server.issue}),"effort":"standard"}
                    record["cases"].append(item)
                    start = len(record["calls"])
                    with patch.dict(os.environ, {"ANIME_AGENT_WRITE_ROOTS":str(file_dir), "ANIME_AGENT_TOOLS_ROOTS":str(file_dir)}), patch.multiple(core,
                        memory=store, provider=provider, mcp_host=host, tools_schema=schemas, tool_registry=registry,
                        _execute_authorized_tool=execute, hub=SimpleNamespace(send_roles=AsyncMock(), role_count=lambda *_:0),
                        broadcast_state=AsyncMock(), broadcast_behavior=AsyncMock(), _spawn=lambda c:c.close(),
                        _action_ledger=None, _task_state={}, _result_pages={}, _pending_writes={}, _shown_confirmations={}, chat_lock=asyncio.Lock()):
                        sid = store.create_session()["id"]
                        item["session_id"] = sid
                        async def turn(text, suffix):
                            rid = case_id+"-"+suffix
                            await core.handle_chat(text, rid, sid, effort="standard")
                            item["turns"].append({"input":text,"request_id":rid,"answer":store.load_messages(100,sid)[-1]["content"],
                                "pending":[core._actions().ticket(a) for a in core._sync_pending(sid)]})
                            save()
                        try:
                            await turn(texts[scenario], "request")
                            if scenario in {"issue", "file"}:
                                await turn("确认", "confirm")
                                await turn("确认", "confirm-next-or-empty")
                            item["actions"] = list(core._actions().records.values())
                            item["tasks"] = list(core._task_state.values())
                            item["final_issue"] = server.issue
                            item["file_content"] = Path(path).read_text(encoding="utf-8") if Path(path).is_file() else None
                            decisions = store.connection.execute("SELECT payload FROM events WHERE event_type='task.decision'").fetchall()
                            item["decisions"] = [json.loads(row[0]) for row in decisions]
                            item["passed"] = score_case(item)
                        except Exception as exc:
                            item["runner_error"] = type(exc).__name__
                            item["passed"] = False
                        finally:
                            item["transport_count"] = len(record["calls"])-start
                            store.close()
                        reopened = MemoryStore(data_dir=case_dir/"db")
                        item["reopened_messages"] = reopened.load_messages(100,sid)
                        reopened.close()
                        item["reopened_ok"] = len(item["reopened_messages"]) == 2*len(item["turns"])
                    save()
                    print(json.dumps({k:item.get(k) for k in ("id","passed","transport_count","runner_error","reopened_ok")}), flush=True)
                # Both models get one identical scenario before deciding whether
                # to stop expansion. Existing failures are never replaced.
                if args.phase == "repeat" and not all(c["passed"] for c in record["cases"][-2:]):
                    record["stop_reason"] = "first_pair_failure; diagnose before expanding sample"
                    save()
                    return
    asyncio.run(run())
    record["actual_transports"] = len(record["calls"])
    record["global_transports"] = len(ledger["attempts"])
    save()


if __name__ == "__main__":
    main()
