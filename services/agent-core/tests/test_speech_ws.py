from __future__ import annotations

import concurrent.futures
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANIME_AGENT_WAKE_WORD", "0")

from fastapi.testclient import TestClient

from agent_core import main as core
from agent_core.speech import SpeechManager
from agent_core.storage import MemoryStore


class ScriptedProvider:
    name = "scripted"

    def __init__(self, reply_text: str) -> None:
        self.reply_text = reply_text

    async def complete(self, messages) -> str:
        payload = {
            "reply": self.reply_text,
            "emotion": "happy",
            "emotion_intensity": 0.5,
            "gesture": "none",
            "memory_candidate": None,
        }
        return json.dumps(payload, ensure_ascii=False)


class FakeSpeechClient:
    def __init__(self) -> None:
        self.synth_count = 0

    def is_healthy(self) -> bool:
        return True

    def synthesize(self, text: str, speed: float = 1.0) -> dict:
        self.synth_count += 1
        return {"audioPath": "C:/nonexistent/spool.wav", "durationMs": 50, "sampleRate": 32000}


def _recv(ws, timeout: float = 10.0):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(ws.receive_json).result(timeout=timeout)


def _collect_until(ws, stop_type: str, match: dict | None = None, limit: int = 30):
    seen = []
    for _ in range(limit):
        evt = _recv(ws)
        seen.append(evt)
        if evt.get("type") == stop_type and (
            match is None or all(evt.get(k) == v for k, v in match.items())
        ):
            return seen
    raise AssertionError(f"event {stop_type} {match or ''} never arrived; saw {[e.get('type') for e in seen]}")


class SpeechWSTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        store = MemoryStore(data_dir=Path(self._tmp.name))
        self.addCleanup(store.close)
        core.provider = ScriptedProvider("你好呀，我是洛天依。")
        self.addCleanup(setattr, core, "provider", core.provider)
        core.memory = store
        self.addCleanup(setattr, core, "memory", core.memory)
        core.tools_schema = []
        self.addCleanup(setattr, core, "tools_schema", core.tools_schema)
        core.TTS_ENABLED = True
        self.addCleanup(setattr, core, "TTS_ENABLED", False)
        self.speech_client = FakeSpeechClient()
        core.speech_client = self.speech_client
        self.addCleanup(setattr, core, "speech_client", core.speech_client)
        core.speech_manager = SpeechManager(
            self.speech_client,
            on_speak=core._broadcast_speak,
            on_interrupt=core._broadcast_speech_stop,
        )
        self.addCleanup(setattr, core, "speech_manager", core.speech_manager)

    def _connect(self):
        client = TestClient(core.app)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        ws = client.websocket_connect("/ws")
        self.addCleanup(ws.__exit__, None, None, None)
        ws.__enter__()
        ws.send_json({"type": "client.hello", "role": "avatar"})
        _collect_until(ws, "client.ready")
        return client, ws

    def test_tts_chat_flow_speaks_and_settles(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "session.new"})
        switched = _collect_until(ws, "session.switched")[-1]
        session_id = int(switched["conversationId"])

        ws.send_json({"type": "chat.message", "messageId": "m1", "text": "你好", "conversationId": session_id})
        events = _collect_until(ws, "agent.state", match={"state": "speaking"})
        speak = next(e for e in events if e.get("type") == "avatar.speak")
        self.assertEqual(speak["text"], "你好呀，我是洛天依。")
        self.assertTrue(speak["utteranceId"])
        self.assertEqual(speak["durationMs"], 50)
        speaking = next(e for e in events if e.get("type") == "agent.state" and e.get("state") == "speaking")
        self.assertEqual(speaking["request_id"], "m1")

        ws.send_json({"type": "speech.finished", "utteranceId": speak["utteranceId"]})
        tail = _collect_until(ws, "agent.state", match={"state": "idle"})
        self.assertNotIn("avatar.speech.stop", [e.get("type") for e in tail])
        self.assertEqual(self.speech_client.synth_count, 1)


    def test_voice_start_interrupts_speech(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "session.new"})
        switched = _collect_until(ws, "session.switched")[-1]
        session_id = int(switched["conversationId"])

        ws.send_json({"type": "chat.message", "messageId": "m2", "text": "讲个长故事", "conversationId": session_id})
        events = _collect_until(ws, "avatar.speak")
        speak = events[-1]
        self.assertEqual(speak["text"], "你好呀，我是洛天依。")

        ws.send_json({"type": "voice.start"})
        stop = _collect_until(ws, "avatar.speech.stop")[-1]
        self.assertEqual(stop["utteranceId"], speak["utteranceId"])
        self.assertEqual(stop["reason"], "voice")
        tail = _collect_until(ws, "agent.state", match={"state": "idle"})
        self.assertTrue(tail)
        self.assertEqual(self.speech_client.synth_count, 1)

    def test_speech_finished_unknown_id_is_ignored(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "speech.finished", "utteranceId": "utt-nonexistent"})
        ws.send_json({"type": "ping"})
        evt = _recv(ws)
        self.assertEqual(evt.get("type"), "pong")
        self.assertIsNone(core.speech_manager.current)


if __name__ == "__main__":
    unittest.main()
