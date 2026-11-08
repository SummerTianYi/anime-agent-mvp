"""Wake -> official Flash wire format -> V1 chat -> two Godot playback receipts.

Pass a marked disposable avatar project with an isolated Godot user directory.
The microphone, transcription, model HTTP response and TTS waveform are synthetic.
"""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
from unittest.mock import patch
import wave


async def verify(godot, fixture, data):
    import numpy as np
    import uvicorn
    from agent_core import main as core

    project = fixture / "apps/avatar-runtime"
    if not (fixture / ".farewell-test-fixture").is_file():
        raise ValueError("A disposable avatar fixture is required")
    settings = (project / "project.godot").read_text(encoding="utf-8")
    if "config/use_custom_user_dir=true" not in settings or 'config/custom_user_dir_name="TianyiCodex' not in settings:
        raise ValueError("Use a separate TianyiCodex-prefixed user directory in the fixture")
    for name in ("runtime.gd", "speech_output.gd", "interaction_ui.gd"):
        if (project / name).read_text(encoding="utf-8") != (ROOT / "apps/avatar-runtime" / name).read_text(encoding="utf-8"):
            raise ValueError(f"Fixture differs from this checkout: {name}")
    assert core.memory.path.resolve().is_relative_to(data)
    wav = data / "tone.wav"
    with wave.open(str(wav), "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "none"))
        out.writeframes(b"".join(struct.pack("<h", round(3000 * math.sin(i / 8))) for i in range(4000)))

    phrase, answer = "今天一起听歌吧", "好呀。"
    spoken, requests = [], []
    ds = core.OpenAICompatibleProvider(name="deepseek", base_url="https://api.deepseek.com",
                                       model="deepseek-flash", api_key="fixture", timeout_seconds=1)

    def respond(request):
        assert request.full_url == "https://api.deepseek.com/chat/completions"
        body = json.loads(request.data)
        assert body["model"] == "deepseek-flash" and body["thinking"] == {"type": "disabled"}
        assert body["tools"] and body["messages"][-1]["content"] == phrase
        assert any(m["role"] == "system" and "洛天依" in m["content"] for m in body["messages"])
        requests.append(body["model"])
        content = json.dumps({"reply": answer, "emotion": "happy", "gesture": "none"})
        return json.dumps({"choices": [{"message": {"role": "assistant", "content": content}}]}).encode()

    def synthesize(text, _speed):
        spoken.append(text)
        return {"audioPath": str(wav), "sampleRate": 16000, "durationMs": 250}

    def capture(_token, *, on_ready):
        assert on_ready()
        return b"fixture command"

    def completions():
        rows = core.memory.connection.execute("SELECT payload FROM events WHERE event_type='speech.completed' ORDER BY id")
        return [json.loads(row[0]) for row in rows]

    history_ready = asyncio.Event()
    send = core.hub.send

    async def observe_send(socket_client, payload):
        await send(socket_client, payload)
        if payload["type"] == "chat.history.response" and core.hub.role_of(socket_client) == "avatar":
            history_ready.set()

    async def wait_for(test):
        async with asyncio.timeout(40):
            while not test():
                await asyncio.sleep(.05)

    # The server owns this ephemeral socket until shutdown.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        assert port not in (8765, 8770)
        server = uvicorn.Server(uvicorn.Config(core.app, log_level="warning"))
        task = asyncio.create_task(server.serve(sockets=[listener]))
        avatar = None
        try:
            await wait_for(lambda: server.started)
            addr = f"ws://127.0.0.1:{port}/ws"
            env = dict(os.environ, AGENT_CORE_WS_URL=addr, ANIME_AGENT_SPEECH_GAIN_DB="5")
            with (data / "avatar.log").open("wb") as log, patch.object(core.hub, "send", observe_send):
                # The production scene intentionally quits after its headless preview.
                avatar = await asyncio.create_subprocess_exec(str(godot), "--audio-driver", "Dummy",
                    "--max-fps", "30", "--resolution", "160x160", "--position", "-4000,-4000",
                    "--path", str(project), env=env, stdout=log, stderr=log)
                # Opening the initial history invalidates older voice captures.
                await asyncio.wait_for(history_ready.wait(), 40)
                with patch.object(core, "VOICE_INPUT_MODE", "wake"), patch.object(core, "TTS_ENABLED", True), \
                        patch.object(core, "provider", ds), patch.object(ds, "_request", respond), \
                        patch.object(core, "transcribe_wav", side_effect=["嗨天依", phrase]), \
                        patch.object(core, "capture_utterance", capture), patch.object(core.speech_manager.client, "synthesize", synthesize):
                    await core.handle_wake_word(np.ones(1600, dtype=np.float32))
                    try:
                        await wait_for(lambda: len(completions()) >= 2)
                    except TimeoutError as exc:
                        recent = core.memory.connection.execute(
                            "SELECT event_type, payload FROM events ORDER BY id DESC LIMIT 12").fetchall()
                        raise AssertionError((spoken, requests, [tuple(row) for row in recent])) from exc
                rows = completions()
                assert requests == ["deepseek-flash"] and spoken == ["我在，请讲。", answer]
                assert len(rows) == 2 and len({r["utteranceId"] for r in rows}) == 2
                assert len({r["request_id"] for r in rows}) == 1 and rows[0]["request_id"].startswith("wake-")
                history = core.memory.load_messages(4, core.memory.latest_session_id())
                assert [(m["role"], m["content"]) for m in history] == [("user", phrase), ("assistant", answer)]
        finally:
            if avatar is not None and avatar.returncode is None:
                avatar.terminate()
                await avatar.wait()
            server.should_exit = True
            await asyncio.wait_for(task, 10)
    logs = (data / "avatar.log").read_text(encoding="utf-8", errors="replace")
    config = next(json.loads(line.split("GODOT_SPEECH_OUTPUT_READY ",1)[1]) for line in logs.splitlines()
                  if "GODOT_SPEECH_OUTPUT_READY " in line)
    assert config["bus"] == "TianyiSpeech" and config["gainDb"] == 5 and config["limiterEnabled"]
    print("DESKTOP_FOUR_OK requests=1 external=0 speech_completed=2 voice_gain_db=5 limiter=on")


ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "services/agent-core"))
    with tempfile.TemporaryDirectory(prefix="tianyi-four-") as tmp:
        overrides = {k: v for k,v in os.environ.items() if not k.startswith(
            ("ANIME_AGENT_", "AGENT_CORE_", "LLM_", "GLM_", "DEEPSEEK_", "STEPFUN_", "TTS_SERVICE_"))}
        overrides.update(ANIME_AGENT_CONFIG_PATH=str(Path(tmp)/"absent.env"), ANIME_AGENT_DATA_DIR=tmp,
            LLM_PROVIDER="mock", ANIME_AGENT_VOICE_INPUT_MODE="manual", ANIME_AGENT_WAKE_WORD="0",
            ANIME_AGENT_TTS="0", ANIME_AGENT_TTS_NARRATE="0", ANIME_AGENT_FAREWELL_PRECACHE="0",
            ANIME_AGENT_IDLE_THRESHOLD="0", ANIME_AGENT_MCP_SERVERS="", TTS_SERVICE_URL="http://127.0.0.1:1")
        def network_guard(event, args):
            if event == "socket.connect" and isinstance(args[1], tuple):
                host, port = args[1][:2]
                if host not in {"127.0.0.1", "::1", "localhost"} or port in (8765, 8770):
                    raise RuntimeError("External or desktop service access blocked")
        sys.addaudithook(network_guard)
        with patch.dict(os.environ, overrides, clear=True):
            from agent_core import main as core
            try:
                asyncio.run(verify(args.godot.resolve(), args.fixture.resolve(), Path(tmp).resolve()))
            finally:
                core.memory.close()
