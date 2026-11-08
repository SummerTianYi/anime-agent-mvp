"""Replay two actual candidate bubbles through the candidate speech path and an isolated visible Godot."""
import argparse
import asyncio
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

from evaluate import HERE, platform


def get(port, endpoint="/health"):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
        f"http://127.0.0.1:{port}{endpoint}", timeout=4
    ) as response:
        return json.load(response)


def readiness():
    h, side = get(8765), get(8770)
    mem = (ctypes.c_ulonglong * 8)()
    ctypes.cast(mem, ctypes.POINTER(ctypes.c_ulong))[0] = 64
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
        raise ctypes.WinError()
    gpu = int(subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free",
        "--format=csv,noheader,nounits"], text=True).splitlines()[0])
    if (not h["tts"]["available"] or h["tts"]["speechPending"] or h.get("status") != "ok"
            or not side["ok"] or side.get("phase") != "ready" or mem[2] < 800 * 1024**2 or gpu < 1100):
        raise RuntimeError("Shared service busy/unavailable or insufficient headroom")


async def run(args):
    from uvicorn import Config, Server
    args.phase = "archive"  # Offline synthetic DS configuration; all model dispatch is forbidden below.
    readiness()
    core, _ = platform.start_core(args)
    def forbid(*unused, **kwargs):
        raise AssertionError("Audition may not call a Provider")
    core.provider._request = forbid
    core.TTS_ENABLED = True
    assert core.speech_client.base_url == "http://127.0.0.1:8770" and core.speech_client.probe_health()
    assert core.speech_manager.lookahead == 1
    sources = (args.repo / "apps/avatar-runtime")
    for name in ("runtime.gd", "interaction_ui.gd", "speech_output.gd", "main.tscn"):
        normal = lambda b: b.replace(b"\r\n", b"\n")
        if normal((args.project / name).read_bytes()) != normal((sources / name).read_bytes()):
            raise RuntimeError("Isolated avatar source mismatch")
    if 'config/use_custom_user_dir=true' not in (args.project / "project.godot").read_text(encoding="utf-8"):
        raise RuntimeError("Isolated Godot user directory required")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = Server(Config(core.app, lifespan="off", log_level="error", access_log=False))
    serve = asyncio.create_task(server.serve(sockets=[sock]))
    while not server.started:
        await asyncio.sleep(.05)
    rows = {x["id"]: x for x in platform.read_lines(args.dialogues)}
    sid = core.memory.create_session()["id"]
    env = dict(os.environ, AGENT_CORE_WS_URL=f"ws://127.0.0.1:{port}/ws",
               ANIME_AGENT_CANVAS_MODE="compact", ANIME_AGENT_SPEECH_GAIN_DB="5",
               COMPANION_AUDITION_STATE=str(args.state))
    engine = subprocess.Popen([str(args.godot), "--path", str(args.project), "--script", str(HERE / "voice_window.gd"),
                               "--log-file", str(args.state / "godot.log")], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = []
    try:
        async with asyncio.timeout(32):
            while core.hub.role_count("avatar") != 1:
                if engine.poll() is not None:
                    raise RuntimeError("Isolated avatar exited")
                await asyncio.sleep(.1)
        await asyncio.sleep(.6)
        await core.hub.send_roles({"avatar"}, core.event("session.switched", conversationId=sid, title="合成试听"))
        for tag in ("after-space-1-1", "after-light-3"):
            row = rows[tag]
            bubble, speech = row["bubbles"][0], row["tts_entry"][0]
            assert speech["text"] == bubble["text"]
            rid = speech["request"]
            reply = core.AgentReply(reply=bubble["text"], emotion=bubble["emotion"],
                                   emotion_intensity=bubble["emotion_intensity"], gesture=bubble["gesture"])
            if get(8765)["tts"]["speechPending"]:
                raise RuntimeError("Formal speech started; stop the audition")
            await core._present(reply, sid, rid, "companion")
            async with asyncio.timeout(70):
                while True:
                    events = [(r[0], json.loads(r[1])) for r in core.memory.connection.execute(
                        "SELECT event_type,payload FROM events WHERE event_type IN ('speech.completed','speech.receipt','speech.unavailable')")]
                    if any(k == "speech.unavailable" and v.get("request_id") == rid for k,v in events):
                        raise RuntimeError("Synthesis unavailable")
                    done = next((v for k,v in events if k == "speech.completed" and v.get("request_id") == rid), None)
                    if done:
                        break
                    await asyncio.sleep(.15)
            receipts = [v for k,v in events if k == "speech.receipt" and v.get("utteranceId") == done["utteranceId"]]
            assert receipts and all(not v.get("interrupted") and v.get("endedAtMs",0) > v.get("startedAtMs",0) for v in receipts)
            report.append({"turn":tag, "tts_text":speech["text"], "receipts":receipts})
            platform.save(args.state / "audio.json", report)
            await asyncio.sleep(.8)
    finally:
        (args.state / "finished").touch()
        try:
            await asyncio.to_thread(engine.wait, 12)
        except subprocess.TimeoutExpired:
            engine.terminate()  # Only the child created above.
            await asyncio.to_thread(engine.wait, 8)
        server.should_exit = True
        await serve
        core.memory.close()
    if engine.returncode != 0:
        raise RuntimeError("See private isolated Godot result")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("repo", "state", "godot", "project", "dialogues"):
        p.add_argument("--"+arg, type=Path, required=True)
    a = p.parse_args()
    a.repo, a.state = a.repo.resolve(), a.state.resolve()
    if (not (a.state / "synthetic-only").is_file() or a.state.is_relative_to(a.repo)
            or any(x.name != "synthetic-only" for x in a.state.iterdir())):
        p.error("Use an empty, marked private directory")
    asyncio.run(run(a))
