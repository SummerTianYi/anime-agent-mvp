from __future__ import annotations

import concurrent.futures
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("ANIME_AGENT_WAKE_WORD", "0")
os.environ.setdefault("ANIME_AGENT_FAREWELL_PRECACHE", "0")

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
        for name in ('provider', 'memory', 'tools_schema', 'TTS_ENABLED', 'speech_client', 'speech_manager', 'wake_listener', 'voice_recorder'):
            self.addCleanup(setattr, core, name, getattr(core, name))
        quiet = patch.object(core.proactive_policy, 'allow', return_value=(False, 'test-isolation'))
        quiet.start()
        self.addCleanup(quiet.stop)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        store = MemoryStore(data_dir=Path(self._tmp.name))
        self.addCleanup(store.close)
        core.provider = ScriptedProvider("你好呀，我是洛天依。")
        core.memory = store
        core.tools_schema = []
        core.TTS_ENABLED = True
        self.speech_client = FakeSpeechClient()
        core.speech_client = self.speech_client
        core.speech_manager = SpeechManager(
            self.speech_client,
            on_speak=core._broadcast_speak,
            on_interrupt=core._broadcast_speech_stop,
        )

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

        ws.send_json({"type": "speech.finished", "utteranceId": speak["utteranceId"], "playbackId": speak["playbackId"]})
        tail = _collect_until(ws, "agent.state", match={"state": "idle"})
        self.assertNotIn("avatar.speech.stop", [e.get("type") for e in tail])
        self.assertEqual(self.speech_client.synth_count, 1)


    def test_transient_negative_health_does_not_drop_reply(self) -> None:
        self.speech_client.is_healthy = lambda: False
        self.test_tts_chat_flow_speaks_and_settles()

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

    def test_new_chat_message_interrupts_current_playback(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "session.new"})
        switched = _collect_until(ws, "session.switched")[-1]
        session_id = int(switched["conversationId"])

        ws.send_json({"type": "chat.message", "messageId": "m3", "text": "讲个长故事", "conversationId": session_id})
        events = _collect_until(ws, "avatar.speak")
        speak = events[-1]

        # m4 lands while m3 is still playing; playback must stop at once,
        # before the new reply is even synthesized
        ws.send_json({"type": "chat.message", "messageId": "m4", "text": "换个话题", "conversationId": session_id})
        stop = _collect_until(ws, "avatar.speech.stop")[-1]
        self.assertEqual(stop["utteranceId"], speak["utteranceId"])
        self.assertEqual(stop["reason"], "new-message")
        response = _collect_until(ws, "chat.response", match={"request_id": "m4"}, limit=60)[-1]
        self.assertTrue(response["text"])

    def test_speech_finished_unknown_id_is_ignored(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "speech.finished", "utteranceId": "utt-nonexistent"})
        ws.send_json({"type": "ping"})
        evt = _recv(ws)
        self.assertEqual(evt.get("type"), "pong")
        self.assertIsNone(core.speech_manager.current)

    def test_stale_or_ui_receipt_cannot_complete_avatar_playback(self) -> None:
        client, ws = self._connect()
        ws.send_json({'type':'chat.message','messageId':'receipt-test','text':'测试'})
        speak = _collect_until(ws, 'avatar.speak')[-1]
        with client.websocket_connect('/ws') as ui:
            ui.send_json({'type':'client.hello','role':'ui'})
            _collect_until(ui,'client.ready')
            ui.send_json({'type':'speech.finished','utteranceId':speak['utteranceId'],'playbackId':speak['playbackId']})
            ui.send_json({'type':'ping'})
            _collect_until(ui,'pong')
            self.assertIsNotNone(core.speech_manager.current)
            self.assertFalse(core.speech_manager.current.done.is_set())
        for playback in ({}, {'playbackId':'obsolete-attempt'}):
            ws.send_json({'type':'speech.finished','utteranceId':speak['utteranceId'],**playback})
            ws.send_json({'type':'ping'})
            _collect_until(ws,'pong')
            self.assertFalse(core.speech_manager.current.done.is_set())
        ws.send_json({'type':'speech.finished','utteranceId':speak['utteranceId'],'playbackId':speak['playbackId']})
        _collect_until(ws,'agent.state',match={'state':'idle'})

    def test_load_failure_retries_with_new_playback_id(self) -> None:
        _client, ws = self._connect()
        ws.send_json({'type':'chat.message','messageId':'failed-load','text':'测试'})
        speak = _collect_until(ws,'avatar.speak')[-1]
        ws.send_json({'type':'speech.failed','utteranceId':speak['utteranceId'],'playbackId':speak['playbackId']})
        retry = _collect_until(ws,'avatar.speak')[-1]
        self.assertEqual(retry['utteranceId'],speak['utteranceId'])
        self.assertNotEqual(retry['playbackId'],speak['playbackId'])
        ws.send_json({'type':'speech.finished','utteranceId':retry['utteranceId'],'playbackId':retry['playbackId']})
        _collect_until(ws,'agent.state',match={'state':'idle'})
        self.assertEqual(self.speech_client.synth_count,2)

    def test_uncertain_failure_only_resends_the_existing_playback_id(self) -> None:
        _client, ws = self._connect()
        core.speech_manager.completion_grace_seconds = .12
        ws.send_json({'type':'chat.message','messageId':'unknown-playback','text':'测试'})
        first = _collect_until(ws, 'avatar.speak')[-1]
        ids = {k: first[k] for k in ('utteranceId','playbackId')}
        for details in ({'error':'unknown'}, {'error':'audio-load-failed','startedAtMs':123}):
            ws.send_json({'type':'speech.failed', **ids, **details})
            resend = _collect_until(ws, 'avatar.speak')[-1]
            self.assertEqual(resend['playbackId'], first['playbackId'])
        ws.send_json({'type':'speech.finished', **ids})
        _collect_until(ws,'agent.state',match={'state':'idle'})
        self.assertEqual(self.speech_client.synth_count, 1)


if __name__ == "__main__":
    unittest.main()
