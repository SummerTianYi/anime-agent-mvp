"""One-shot, text-only, interleaved official-DS experiment. No server or WebSocket is started."""
import argparse
import asyncio
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import runpy
import sys
import threading
import time
import urllib.error
import urllib.request
from unittest.mock import patch

from design import (BASE, HERE, PINS, ROOT, URL, audit_design, build, canonical, digest, git,
                    read, schedule)
from isolated_checks import sandbox


def append(path, record):
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def deny_redirect(self, req, fp, code, msg, headers, newurl):
    raise urllib.error.HTTPError(req.full_url, code, "Redirect blocked", headers, fp)


class Capture:
    def __init__(self, core, box, frozen, bodies):
        self.core = core
        self.box = box
        self.frozen = frozen
        self.bodies = bodies
        self.original = core.provider._request
        self.build_native = core.harness.build_messages
        self.parse_native = core.harness.parse_reply
        self.send_native = core.hub.send_roles
        self.number = 0
        self.transport = threading.local()
        self.violations = []

    def stop(self, reason):
        self.violations.append(reason)
        raise RuntimeError(reason)

    def fence(self, name, args):
        if name in {"socket.connect", "http.client.connect", "urllib.Request", "http.client.send"}:
            if not getattr(self.transport, "allowed", False):
                self.stop("network outside reserved official request")
            if name == "urllib.Request" and (args[0] != URL or args[3] != "POST"):
                self.stop("unregistered HTTP destination or method")
            if name == "socket.connect" and args[1][1] in (8765, 8770):
                self.stop("desktop service port")
            if name == "http.client.send" and bytes(args[1]).startswith(b"POST "):
                if self.transport.sent:
                    self.stop("second HTTP dispatch on one reservation")
                self.transport.sent = True
        if name in {"socket.bind", "subprocess.Popen", "os.startfile", "os.system"}:
            self.stop("unexpected service, subprocess or desktop action")
        if name == "sqlite3.connect" and not Path(args[0]).resolve().is_relative_to(self.box):
            self.stop("database outside synthetic directory")

    def prepare(self, item, number):
        self.item, self.slot = item, number
        self.sent = False
        self.bubbles, self.parsed, self.errors = [], [], []
        self.state, self.overhead_ns, self.source, self.first = None, None, None, None
        self.result = None

    def assemble(self, history, user_text, extra_system="", request_session_title=False):
        if self.core.chat_channels.lane.get() != "companion" or self.source is not None:
            self.stop("more than one or non-companion harness invocation")
        self.source, self.first = copy.deepcopy(history), request_session_title
        messages, self.state, self.overhead_ns = build(self.build_native, self.item["arm"], history, user_text,
                                                        extra_system, request_session_title)
        return messages

    def request(self, req):
        body = json.loads(req.data)
        key = self.item["scene"] + "-" + self.item["arm"]
        if (self.sent or self.slot != self.number + 1 or self.slot > 24 or self.violations
                or req.full_url != URL or req.get_method() != "POST"
                or digest(canonical(body)) != self.bodies[key]):
            self.stop("duplicate, excess or non-preregistered request")
        # Exactly one live process owns the lease. Durable reservation precedes all HTTP I/O.
        self.sent, self.number = True, self.slot
        append(self.box / "requests.jsonl", dict(n=self.slot, phase="request", **self.item,
               body=body, body_sha256=self.bodies[key], pins=PINS, code=self.frozen))
        started = time.monotonic()
        self.transport.allowed, self.transport.sent = True, False
        result = dict(n=self.slot, phase="result")
        try:
            wire = self.original(req)
            payload = json.loads(wire)
            result.update(response_id=payload.get("id"), model=payload.get("model"), usage=payload.get("usage"),
                          choices=[{"finish_reason": c.get("finish_reason"),
                                    "message": {k: v for k, v in c["message"].items()
                                                if k in {"content", "role", "refusal", "tool_calls"}}}
                                   for c in payload["choices"]])
            if (not self.transport.sent or result["model"] != body["model"] or len(result["choices"]) != 1
                    or result["choices"][0]["message"].get("tool_calls")):
                self.stop("unexpected official response")
            return wire
        except Exception as exc:
            result.update(error=type(exc).__name__, status=getattr(exc, "code", None))
            # A failed attempt ends this run. Raising outside TRANSPORT_ERRORS suppresses provider retries.
            raise RuntimeError("official exchange failed; stop") from None
        finally:
            self.transport.allowed = False
            result.update(http_post=self.transport.sent, seconds=round(time.monotonic()-started, 6))
            append(self.box / "requests.jsonl", result)
            self.result = result

    def parse(self, raw):
        parsed = self.parse_native(raw)
        self.parsed.append({"input": raw, "parsed": asdict(parsed)})
        return parsed

    async def observe(self, roles, event):
        if event["type"] == "chat.response":
            self.bubbles.append({"roles": sorted(roles), "event": copy.deepcopy(event)})
        elif event["type"] == "core.error":
            self.errors.append(event["type"])
        return await self.send_native(roles, event)

    async def no_tools(self, *args, **kwargs):
        self.stop("unexpected operational dispatch")

    async def turn(self, scene):
        core = self.core
        core.memory.close()
        core.memory = core.MemoryStore(self.box / "data" / str(self.slot))
        sid = core.memory.create_session()["id"]
        for i, row in enumerate(scene["history"]):
            core.memory.add_message(row["role"], row["content"], f"history-{i//2}", sid)
        before = core.memory.load_messages(100, sid)
        assert before == scene["history"] and not core.memory.recall_facts(sid)
        started = time.monotonic()
        failure = None
        try:
            await core.handle_chat(scene["current"], "target", sid, effort="deep")
            await asyncio.sleep(0)
            if (self.errors or self.violations or self.result is None or self.result.get("error")
                    or len(self.parsed) != 1 or len(self.bubbles) != 1
                    or self.bubbles[0]["event"]["channel"] != "companion" or core.hub.client_count):
                self.stop("incomplete or unexpected delivery")
            assert core.memory.load_messages(100, sid)[:len(before)] == before
        except Exception as exc:
            failure = type(exc).__name__
            raise
        finally:
            append(self.box / "dialogues.jsonl", dict(n=self.slot, **self.item, code=self.frozen,
                   source_history=before, current=scene["current"], model_history=self.source,
                   first=self.first, state=self.state, parsed=self.parsed, bubbles=self.bubbles,
                   error=failure, core_errors=self.errors, violations=list(self.violations),
                   projection_ns=self.overhead_ns, turn_seconds=round(time.monotonic()-started, 6)))


async def run(args, bodies, profile):
    # The event loop already exists before installing the no-listener fence on Windows.
    sandbox(args.box)
    os.environ.update(profile)
    os.environ["ANIME_AGENT_TOOLS"] = "0"
    from agent_core import main as core
    assert (core.provider.name, core.provider.model, core.provider.completion_url) == (
        "deepseek", "deepseek-flash", URL)
    assert not core.TTS_ENABLED and core.wake_listener is None and core.VOICE_INPUT_MODE == "manual"
    assert not core.mcp_host.tool_entries() and not core.hub.client_count and not core.TOOLS_ENABLED
    assert core.memory.path.resolve().is_relative_to(args.box) and not core.voice_recorder.recording
    observer = Capture(core, args.box, args.frozen, bodies)
    core.provider._request = observer.request
    core.provider.complete_with_tools = observer.no_tools
    core._execute_authorized_tool = observer.no_tools
    core.harness.build_messages, core.harness.parse_reply = observer.assemble, observer.parse
    core.hub.send_roles = observer.observe
    scenes = read("scenes.json")
    order = schedule()
    sys.addaudithook(observer.fence)
    error = None
    try:
        with patch.object(urllib.request.HTTPRedirectHandler, "redirect_request", deny_redirect):
            for n, item in enumerate(order, 1):
                observer.prepare(item, n)
                await observer.turn(scenes[item["scene"]])
                print(f"slot {n}/24 recorded", flush=True)
    except Exception as exc:
        error = type(exc).__name__
    finally:
        core.memory.close()
        append(args.box / "run.jsonl", dict(code=args.frozen, reserved=observer.number,
               missing=list(range(observer.number + 1, 25)), stop=error, isolation_violations=observer.violations,
               clients=core.hub.client_count, tts_enabled=core.TTS_ENABLED, wake_started=bool(core.wake_listener),
               recording=core.voice_recorder.recording, lifespan_started=False, effect_tools=core.TOOLS_ENABLED,
               close="memory closed; no server started"))
    if error:
        raise SystemExit("Stopped; preserve every row and unfilled slot")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen", required=True)
    p.add_argument("--ds-env", type=Path, required=True)
    p.add_argument("--box", type=Path, required=True)
    args = p.parse_args()
    args.box = args.box.resolve()
    if args.box.is_relative_to(ROOT) or args.box.exists():
        p.error("A new private directory outside the checkout is required")
    if git("rev-parse", "HEAD") != args.frozen or git("status", "--porcelain"):
        p.error("A clean pre-registered revision is required")
    assert git("rev-parse", args.frozen + "^") == BASE
    bodies = audit_design()
    assert bodies == read("request-pins.json")
    # Reuse the prior experiment's allowlisted selector for the configured official adapter.
    profile = runpy.run_path(str(HERE.parent / "companion-platform/evaluate.py"))["public_config"](args.ds_env)
    common = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    lease = common / ("companion-p0-ablation-" + BASE[:12] + ".reserved")
    with lease.open("x", encoding="ascii") as stream:
        stream.write(args.frozen + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    args.box.mkdir(parents=True, exist_ok=False)
    asyncio.run(run(args, bodies, profile))


if __name__ == "__main__":
    main()
