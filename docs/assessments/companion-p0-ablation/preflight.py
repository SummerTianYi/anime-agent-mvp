"""Offline integration checks only. Fixture text is never published as model evidence."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
from urllib.request import Request

from design import PARAMS, URL, audit_design, canonical, expected, read, rows, schedule
from evaluate import Capture
from isolated_checks import offline_fence, sandbox


async def run(box):
    from agent_core import main as core
    bodies = audit_design()
    # Real provider construction/HTTP encoding, with an offline payload sink before any network.
    core.provider = core.OpenAICompatibleProvider(name="deepseek", base_url="https://api.deepseek.com",
        model=PARAMS["model"], api_key="offline-fixture", timeout_seconds=2)
    observer = Capture(core, box, "offline", bodies)
    def sink(req):
        body = json.loads(req.data)
        assert req.full_url == URL
        assert body == expected(scenes[observer.item["scene"]], observer.item["arm"])[0]
        observer.result = {"fixture": True}
        return json.dumps({"choices": [{"message": {"content": '{"reply":"离线夹具。需要哪一种？"}'}}]}).encode()
    core.provider._request = sink
    core.provider.complete_with_tools = observer.no_tools
    core._execute_authorized_tool = observer.no_tools
    core.harness.build_messages, core.harness.parse_reply = observer.assemble, observer.parse
    core.hub.send_roles = observer.observe
    scenes = read("scenes.json")
    for n, item in enumerate(schedule(), 1):
        observer.prepare(item, n)
        await observer.turn(scenes[item["scene"]])
        assert observer.bubbles[0]["event"]["text"] == "离线夹具。需要哪一种？"
        assert not observer.first
    # Exercise rejection after a transport failure, a repeat of the same slot, and a 25th attempt.
    plan = schedule()
    item = plan[0]
    req = Request(URL, data=canonical(expected(scenes[item["scene"]], item["arm"])[0]).encode())
    observer.original = lambda _: (_ for _ in ()).throw(ConnectionResetError())
    observer.prepare(item, 1)
    for action in ("failure", "duplicate", "limit"):
        if action == "limit":
            observer.prepare(item, 25)
            observer.number = 24
            observer.violations.clear()
        try:
            observer.request(req)
        except RuntimeError:
            pass
        else:
            raise AssertionError("isolation/ceiling did not stop " + action)
    ledger = rows(box / "requests.jsonl")
    assert [r["phase"] for r in ledger] == ["request", "result"] and ledger[1]["error"] == "ConnectionResetError"
    core.memory.close()
    print("OFFLINE_ONLY: 24 exact handle_chat payloads; original questions delivered; failure/duplicate/limit guards passed")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="companion-offline-", dir=sys.argv[1]) as private:
        box = Path(private).resolve()
        sandbox(box)
        offline_fence(box)
        asyncio.run(run(box))
