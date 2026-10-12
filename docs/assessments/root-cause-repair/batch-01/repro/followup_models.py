"""Fixed background model sample: actual candidate Core, isolated persistent data.

No listeners, desktop, speech, production histories or real connector calls.
Credentials come from an explicitly selected private dotenv file. Only synthetic
messages/content/tool calls/finish reasons are exported, never reasoning or keys.
Existing output directories are refused so first failures cannot be overwritten.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


def public_messages(messages):
    """Project the transcript; provider raw messages can include private reasoning."""
    output = []
    for message in messages:
        clean = {key: message[key] for key in ("role", "content", "tool_call_id", "name") if key in message}
        if isinstance(clean.get("content"), list):
            clean["content"] = [{"type": "text", "text": part.get("text", "")}
                                for part in clean["content"] if isinstance(part, dict) and part.get("type") == "text"]
        if "tool_calls" in message:
            clean["tool_calls"] = [
                {"id": call.get("id"), "type": call.get("type", "function"),
                 "function": {key: call.get("function", {}).get(key) for key in ("name", "arguments")}}
                for call in message["tool_calls"] or []]
        output.append(clean)
    return output


async def selected_synthetic_execute(name, arguments, allowed, execute):
    """Hiding tools from the schema is not an execution sandbox."""
    if name not in allowed:
        return {"ok": False, "outcome": "failed", "error": "工具不在本次隔离合成测试白名单内，未执行"}
    return await execute(name, arguments)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--private-config", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true", help="Append only missing cases; never retry an existing case")
    args = parser.parse_args()
    if not args.resume and (args.data_dir.exists() or args.output.exists()):
        raise SystemExit("Refusing to replace an earlier run")
    args.data_dir.mkdir(parents=True, exist_ok=args.resume)
    sys.dont_write_bytecode = True
    package = args.source_root / "services/agent-core"
    sys.path.insert(0, str(package))
    from dotenv import dotenv_values
    config = dotenv_values(args.private_config)
    os.environ.update(ANIME_AGENT_DATA_DIR=str(args.data_dir / "bootstrap"),
        ANIME_AGENT_CONFIG_PATH=str(args.data_dir / "absent.env"), LLM_PROVIDER="mock",
        ANIME_AGENT_TTS="0", ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_MCP_SERVERS="",
        ANIME_AGENT_ALLOWED_COMMANDS="", ANIME_AGENT_WRITE_ROOTS=str(args.data_dir),
        ANIME_AGENT_TOOLS_ROOTS=str(args.data_dir), ANIME_AGENT_VOICE_INPUT_MODE="manual")
    from agent_core import main as core
    from agent_core.storage import MemoryStore
    from agent_core.mcp_host import McpServer
    if package.resolve() not in Path(core.__file__).resolve().parents:
        raise RuntimeError("Wrong candidate import")
    core.memory.close()
    schema_path = args.source_root / "docs/assessments/root-cause-audit/evidence/mcp-schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    names = {"github": {"issue_write", "issue_read"}, "gmail": {"search_emails", "read_email"}}
    entries = [("mcp__"+server["server"]+"__"+tool["name"], tool["description"], tool["inputSchema"])
               for server in schema["servers"] for tool in server["tools"]
               if tool["name"] in names.get(server["server"], set())]
    record = {"scope": "background actual Core + real models + synthetic MCP; no Godot/TTS/real service acceptance",
              "schema_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (package / "agent_core").glob("*.py")},
              "fixed_repeats": 3, "transport_cap": 96, "calls": [], "cases": []}
    if args.resume:
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        if previous["source_sha256"] != record["source_sha256"] or previous["schema_sha256"] != record["schema_sha256"]:
            raise SystemExit("Resume requires identical candidate source and schema")
        record = previous
        record.setdefault("resume_notes", []).append(
            "Stopped to harden capture and executor isolation; every existing case retained without retry")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    class ObservedProvider(core.OpenAICompatibleProvider):
        def _request(self, request):
            if len(record["calls"]) >= record["transport_cap"]:
                raise RuntimeError("Fixed transport cap reached")
            body = json.loads(request.data)
            item = {"index": len(record["calls"])+1, "model": self.model,
                    "request_id": core.REQUEST_ID.get(), "messages": public_messages(body["messages"]),
                    "tools": body.get("tools", [])}
            record["calls"].append(item)
            save()
            try:
                raw = super()._request(request)
                payload = json.loads(raw)
                choice = payload["choices"][0]
                message = choice["message"]
                public = public_messages([message])[0]
                item["response"] = {"content": public.get("content"),
                                    "tool_calls": public.get("tool_calls"),
                                    "finish_reason": choice.get("finish_reason")}
                item["usage"] = payload.get("usage", {})
                return raw
            except Exception as exc:
                item["error_type"] = type(exc).__name__
                raise
            finally:
                save()
    class StubServer(McpServer):
        def __init__(self, name, effects):
            super().__init__(name, [])
            self.started = True
            self.effects = effects
        async def _roundtrip(self, payload):
            name = payload["params"]["name"]
            arguments = payload["params"].get("arguments", {})
            self.effects.append({"server": self.name, "tool": name, "arguments": arguments})
            if name == "issue_write":
                text = json.dumps({"id": 1, "number": 1, "title": arguments.get("title"),
                                   "url": "https://example.invalid/synthetic/issues/1"})
            elif name == "issue_read":
                text = json.dumps({"number": 1, "title": "FOLLOWUP fixture", "body": "合成材料：总数175。"})
            elif name == "search_emails":
                text = ""
            else:
                text = "Error: Invalid id value"
            return {"result": {"content": [{"type": "text", "text": text}]}}

    scenarios = [
        ("operation", "【B01-FOLLOWUP】文件已经写入，Issue也已读取，不要重复这两项。现在仅调用 GitHub issue_write，method=update，owner=SummerTianYi，repo=tianyi-audit-round02-20261007，issue_number=1，只将标题更新为 [B01-FOLLOWUP] synthetic title。先提出真实待确认操作。"),
        ("explanation", "【B01-FOLLOWUP】只解释：天依说‘请确认，确认后执行’与已经真的执行有什么区别？这是流程引用，不要执行任何工具。然后说一句晚上好。"),
        ("clarification", "【B01-FOLLOWUP】我想修改一个 GitHub Issue 的标题，但还没告诉你仓库、Issue编号和新标题。先问我必须补充哪些参数，不要猜测，也不要提出操作确认。"),
    ]
    async def run():
        for repeat in range(1, 4):
            for model in ("Deepseek-v4-flash", "GLM-5.2"):
                source = "DEEPSEEK" if model.startswith("Deepseek") or config.get("GLM_CREDENTIAL_SOURCE") == "deepseek" else "GLM"
                model_provider = ObservedProvider(name="deepseek" if model.startswith("Deepseek") else "glm",
                    base_url=config[source+"_BASE_URL"], model=model, api_key=config[source+"_API_KEY"],
                    timeout_seconds=45, proxy_mode=config.get("LLM_PROXY_MODE", "auto"))
                for scenario, text in scenarios:
                    case_id = f"{model}-{repeat}-{scenario}"
                    if any(case["id"] == case_id for case in record["cases"]):
                        continue
                    store = MemoryStore(data_dir=args.data_dir / case_id)
                    effects = []
                    servers = {name: StubServer(name, effects) for name in names}
                    fake_host = SimpleNamespace(servers=servers, tool_entries=lambda: entries)
                    actual_execute = core._execute_authorized_tool
                    async def isolated_execute(name, arguments):
                        return await selected_synthetic_execute(name, arguments, {entry[0] for entry in entries}, actual_execute)
                    with patch.multiple(core, memory=store, provider=model_provider, mcp_host=fake_host,
                         tools_schema=[], tool_registry={}, _execute_authorized_tool=isolated_execute,
                         hub=SimpleNamespace(send_roles=AsyncMock(), role_count=lambda *_: 0),
                         broadcast_state=AsyncMock(), broadcast_behavior=AsyncMock(),
                         _spawn=lambda coro: coro.close(), _action_ledger=None, _task_state={}, _result_pages={},
                         _pending_writes={}, _shown_confirmations={}, chat_lock=asyncio.Lock()):
                        sid = store.create_session()["id"]
                        start = len(record["calls"])
                        item = {"id": case_id, "model": model, "repeat": repeat, "scenario": scenario,
                                "session_id": sid, "effort": "standard", "turns": [], "effects": effects}
                        record["cases"].append(item)
                        async def turn(user_text, suffix):
                            rid = case_id+"-"+suffix
                            await core.handle_chat(user_text, rid, sid, effort="standard")
                            messages = store.load_messages(100, sid)
                            item["turns"].append({"request_id": rid, "input": user_text,
                                "answer": messages[-1]["content"],
                                "pending": [core._actions().ticket(a) for a in core._sync_pending(sid)]})
                            save()
                        try:
                            await turn(text, "request")
                            if scenario == "operation":
                                # One explicit confirmation also tests no-ticket rejection.
                                await turn("确认", "confirm")
                                await turn("确认", "confirm-again")
                            item["actions"] = list(core._actions().records.values())
                            item["tasks"] = list(core._task_state.values())
                            item["transport_count"] = len(record["calls"]) - start
                        except Exception as exc:
                            item["runner_error"] = type(exc).__name__
                        finally:
                            store.close()
                        reopened = MemoryStore(data_dir=args.data_dir / case_id)
                        item["reopened_messages"] = reopened.load_messages(100, sid)
                        reopened.close()
                        save()
                        print(json.dumps({"case": case_id, "calls": item.get("transport_count"),
                                          "effects": len(effects), "runner_error": item.get("runner_error")}), flush=True)
    asyncio.run(run())
    record["actual_transports"] = len(record["calls"])
    save()


if __name__ == "__main__":
    main()
