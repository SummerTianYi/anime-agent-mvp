"""Run matched companion histories through handle_chat and the existing official DS transport."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import msvcrt
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / "companion-platform"
spec = importlib.util.spec_from_file_location("platform_evidence", PRIOR / "evaluate.py")
platform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform)
SCENES = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
BASE = "371fc7e1e492c24fb0462d53696563488d2866c1"
PRODUCT = ("agent_core/conversation_context.py", "agent_core/main.py", "agent_core/harness.py")


def sources(repo):
    rev = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    hashes = {p: hashlib.sha256((repo / "services/agent-core" / p).read_bytes()).hexdigest()
              for p in PRODUCT}
    return rev, hashes


def fixed_inputs(case):
    if "archive" in case:
        row = next(x for x in platform.read_lines(PRIOR / "dialogues.jsonl") if x["id"] == case["archive"])
        return row["history_before"], [row["user"]]
    return [{"role": role, "content": t} for pair in case["history"]
            for role, t in zip(("user", "assistant"), pair)], [case["user"]]


async def run(args):
    core, prompt = platform.start_core(args)
    git_rev, hashes = sources(args.repo)
    if args.phase == "before" and git_rev != BASE:
        raise ValueError("Expected the fixed candidate baseline")
    wire = platform.Wire(core, args, prompt)
    tts = []

    async def capture(text, request_id, *unused, **kw):
        tts.append({"request": request_id, "text": text})
        return True

    # Only the speech sink is observed here. Actual audible playback is a separate check.
    core._speak_reply = capture
    core.TTS_ENABLED = True
    core.hub.role_count = lambda role: int(role == "avatar")
    groups = [(f"{name}-{attempt}", *fixed_inputs(case))
              for attempt in (1, 2) for name, case in SCENES["fixed"].items()]
    if args.phase == "after":
        groups.extend((name, [], steps) for name, steps in SCENES["continuous"].items())
    ledger = args.output / "dialogues.jsonl"
    for group, history, steps in groups:
        box = args.state / (args.phase + "-" + group)
        box.mkdir()  # Never silently rerun an existing group or spend a second request for it.
        core.memory.close()
        core.memory = core.MemoryStore(box)
        sid = core.memory.create_session()["id"]
        core._action_ledger = None
        core._task_state.clear()
        core._actions()
        n = 0
        for h in history:
            n += h["role"] == "user"
            core.memory.add_message(h["role"], h["content"], f"history-{n}", sid)
        for i, text in enumerate(steps, 1):
            if sum(x["phase"] == "request" for x in platform.read_lines(wire.path)) >= args.ceiling:
                return
            tag = f"{args.phase}-{group}-{i}"
            rid = f"sample-{group}-{i}"
            wire.tag = tag
            wire.messages.clear()
            wire.parsed.clear()
            wire.effects.clear()
            tts.clear()
            prior = core.memory.load_messages(30, sid)
            started = time.monotonic()
            try:
                await core.handle_chat(text, rid, sid, effort="deep")
                await asyncio.sleep(0)
            finally:
                bubbles = [{k: v for k, v in event.items() if k != "timestamp"}
                           for event in wire.messages if event["type"] == "chat.response"]
                errors = [ev.get("message") for ev in wire.messages if ev["type"] == "core.error"]
                platform.append(ledger, dict(id=tag, code=git_rev, source_sha256=hashes, user=text,
                    history_before=prior, parsed=wire.parsed, bubbles=bubbles, tts_entry=tts, errors=errors,
                    blocked_external_calls=wire.effects, seconds=round(time.monotonic()-started, 3)))
                print(tag, len(bubbles), len(errors), flush=True)
            if errors or wire.effects:
                raise RuntimeError("Unexpected error or operation. Preserve evidence and investigate.")
    core.memory.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--ds-env", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--phase", choices=("before", "after"), required=True)
    args = p.parse_args()
    args.repo, args.state = args.repo.resolve(), args.state.resolve()
    if (args.state.is_relative_to(HERE.parents[2]) or args.state.is_relative_to(args.repo)
            or not (args.state / "synthetic-only").is_file()):
        p.error("Use a marked private synthetic directory outside both repositories")
    args.ceiling = 32
    args.output = args.state / "evidence"
    args.output.mkdir(exist_ok=True)
    # Both revisions use this same lock, journal and transport-side 32-request check.
    with (args.state / "runner.lock").open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        asyncio.run(run(args))
