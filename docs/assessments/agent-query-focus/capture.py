"""Capture actual Core synthesis messages or replay final model content, entirely offline."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "agent-query-delivery"))
from checks import isolate, offline


async def capture(args):
    isolate(args.state)
    offline(args.state)
    sys.path.insert(0, str(args.repo / "services/agent-core"))
    from agent_core import main as core
    from agent_core.harness import ACTIVE_PROMPT_OVERRIDE

    assert core.provider.name == "mock" and core.memory.path.resolve().is_relative_to(args.state)
    assert hashlib.sha256(ACTIVE_PROMPT_OVERRIDE.encode()).hexdigest() == "714ae650ce060f0a645f2fa1055878790438a5e93566ceda18a3ecbdc9d9c9f6"
    recorded = json.loads(args.results.read_text("utf8")) if args.results else []
    rows = []
    for case in json.loads((HERE / "cases.json").read_text("utf8")):
        items = [r for r in recorded if r["case"] == case["id"] and r["phase"] == args.phase and r.get("content")]
        for sample in items if args.results else [{}]:
            sid = core.memory.create_session()["id"]
            rid = case["id"] + sample.get("provider", "")
            transport = AsyncMock(return_value={"ok": True, "as_of": case["as_of"], "sources": case["sources"]})
            provider = AsyncMock(return_value=sample.get("content", '{"reply":"测试用答复。","emotion":"happy","gesture":"wave"}'))
            with (patch.dict(os.environ, {"TAVILY_API_KEY":"offline"}), patch.object(core, "_execute_authorized_tool", transport),
                  patch.object(core.provider, "complete", provider), patch.object(core.hub, "send_roles", new_callable=AsyncMock) as hub,
                  patch.object(core.hub, "role_count", return_value=1), patch.object(core, "TTS_ENABLED", True),
                  patch.object(core, "_maybe_speak_think_filler", new_callable=AsyncMock),
                  patch.object(core, "_speak_reply", new_callable=AsyncMock) as speak):
                await core.handle_chat(case["question"], rid, sid)
                await asyncio.sleep(0)
            assert provider.await_count == 1 and transport.await_count == 1
            events = [c.args[1] for c in hub.await_args_list]
            response, = [e for e in events if e["type"] == "chat.response" and e["channel"] == "task"]
            messages = provider.await_args.args[0]
            digest = hashlib.sha256(json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            row = {"case": case["id"], "phase": args.phase, "prompt_sha256":digest, "search_arguments":transport.await_args.args[1]}
            if sample:
                assert digest == sample["prompt_sha256"]
                row.update(provider=sample["provider"], **{k:response[k] for k in ("text","emotion","emotion_intensity","gesture")},
                           commands=[e["event"] for e in events if e["type"]=="avatar.command"],
                           tts=[c.args[0] for c in speak.await_args_list])
            else:
                row["messages"] = messages
            rows.append(row)
    args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf8")
    print(args.phase, "captured", len(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before","after"))
    for name in ("repo","state","output"):
        parser.add_argument(name, type=lambda p:Path(p).resolve())
    parser.add_argument("--results", type=Path)
    asyncio.run(capture(parser.parse_args()))
