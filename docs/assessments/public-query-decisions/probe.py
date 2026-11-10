"""Capture the actual decision messages or replay responses through an isolated Core and ledger."""
import argparse
import asyncio
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "agent-query-delivery"))
from checks import isolate, offline


class TrialDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 10)


def fingerprint(messages, tools):
    payload = json.dumps([messages, tools], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


async def run(args):
    isolate(args.state)
    offline(args.state)
    sys.path.insert(0, str(args.repo / "services/agent-core"))
    from agent_core import main as core, provider_response
    from agent_core.permissions import ASK, PermissionEngine, PolicyRule
    core.public_search.date = TrialDate
    assert Path(core.__file__).resolve().is_relative_to(args.repo)
    assert core.provider.name == "mock" and not core.TTS_ENABLED
    assert core.memory.path.resolve().is_relative_to(args.state)
    samples = json.loads(args.responses.read_text("utf8")) if args.responses else []
    output = []
    for case in json.loads((HERE / "cases.json").read_text("utf8")):
        rows = [r for r in samples if r["case"] == case["id"]] if args.responses else [{}]
        for sample in rows:
            sid = core.memory.create_session()["id"]
            book = core._actions()
            original = None
            mail = None
            seeded = {"subject":"F1", "fields":["积分榜"], "year":2026}
            if case["seed"]:
                original = book.propose(sid, "initial", "seed", core.public_search.TOOL, seeded)
                original.update(intent="请查一下今年 F1 的车手积分榜。", public_scope=seeded)
                book.save(original)
            if case["mail"]:
                mail = book.propose(sid, "unrelated", "mail", "mcp__gmail__send_email",
                                    {"to":["sample@example.org"], "body":"独立模拟待办"})
            await core._publish_pending(sid)
            decisions, dispatches, http_bodies = [], [], []
            gate = PermissionEngine()
            if case["policy"] == "ask":
                gate.rules.insert(0, PolicyRule("fixture-ask", core.public_search.TOOL, "user", ASK))

            async def propose(messages, tools):
                digest = fingerprint(messages, tools)
                decisions.append({"hash":digest, "messages":messages, "tools":tools})
                if sample.get("message"):
                    assert sample["prompt_sha256"] == digest
                    return provider_response.openai({"choices":[{"message":sample["message"]}]})
                return {"content":"", "tool_calls":[]}

            async def dispatch(name, arguments):
                assert name == core.public_search.TOOL, name
                dispatches.append(arguments)
                return core.public_search.search(arguments)

            def open_search(request, timeout):
                http_bodies.append(json.loads(request.data))
                response = MagicMock()
                response.__enter__.return_value.read.return_value = b'{"results":[]}'
                return response

            with (patch.dict(os.environ, {"TAVILY_API_KEY":"synthetic-fixture"}),
                  patch.object(core, "permission_engine", gate),
                  patch.object(core.hub, "send_roles", new_callable=AsyncMock),
                  patch.object(core, "_execute_authorized_tool", side_effect=dispatch),
                  patch.object(core.provider, "complete_with_tools", side_effect=propose, create=True),
                  patch.object(core.provider, "complete", new_callable=AsyncMock,
                               return_value='{"reply":"隔离测试回复。"}'),
                  patch("urllib.request.build_opener") as opener):
                opener.return_value.open.side_effect = open_search
                await core.handle_chat(case["text"], "target", sid)
                await asyncio.sleep(0)
                pending = [r for r in book.pending(sid) if r["tool"] == core.public_search.TOOL and r is not original]
                answer = core.memory.load_messages(20, sid)[-1]["content"]
                actual = {"old":original["status"] if original else None, "dispatched":list(dispatches),
                          "new_pending":[r["arguments"] for r in pending]}
                def scopes(items):
                    return [[a["subject"], *a["fields"]] for a in items]
                normalized = {**actual, "dispatched":scopes(actual["dispatched"]), "new_pending":scopes(actual["new_pending"])}
                checks = {"target":normalized==case["expected"], "other_ticket":not mail or mail["status"]=="awaiting_confirmation"}
                row = {"case":case["id"], "actual":actual, "http":list(http_bodies), "reply":answer, "checks":checks}
                if original and case["expected"]["old"] == "cancelled":
                    count = len(dispatches)
                    await core.handle_chat("确认", "old-confirm", sid, confirmation=book.ticket(original))
                    row["old_confirmation_dispatches"] = dispatches[count:]
                    checks["old_confirmation_inert"] = count == len(dispatches)
                if case["id"]=="switch":
                    count = len(dispatches)
                    if len(pending)==1:
                        await core.handle_chat("确认", "new-confirm", sid, confirmation=book.ticket(pending[0]))
                        await core.handle_chat("确认", "new-repeat", sid, confirmation=book.ticket(pending[0]))
                    row["after_new_confirmation"] = dispatches[count:]
                    checks["new_once"] = scopes(dispatches[count:])==[["英超","积分榜"]]
                row["passed"] = all(checks.values())
                if args.responses:
                    calls=(sample.get("message") or {}).get("tool_calls") or []
                    try:
                        mode=json.loads(calls[0]["function"]["arguments"])["mode"]
                    except (ValueError,TypeError,KeyError,IndexError):
                        mode=None
                    checks["native_mode"] = mode == case["expected_mode"] and len(calls)==1
                    checks["valid_proposal"] = not core.memory.connection.execute(
                        "SELECT 1 FROM events WHERE event_type='public.proposal.invalid' AND json_extract(payload,'$.session_id')=?",
                        (sid,)).fetchone()
                    row.update(provider=sample["provider"], model_response=sample.get("outcome"),
                               proposal_input=decisions[0]["hash"] if decisions else None)
                    row["passed"] = all(checks.values()) and sample.get("outcome")=="received"
                elif args.capture:
                    assert len(decisions)==1, case["id"]
                    row= {"case":case["id"], **decisions[0]}
                output.append(row)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    print([(r["case"],r.get("provider",""),r.get("passed")) for r in output])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("repo", "state", "output"):
        parser.add_argument(arg, type=lambda v: Path(v).resolve())
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--responses", type=Path)
    asyncio.run(run(parser.parse_args()))
