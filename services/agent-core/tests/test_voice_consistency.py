"""Wake re-arm ordering, voice refractory window, and reply text normalization."""
from __future__ import annotations

import asyncio
import os
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

os.environ.setdefault("ANIME_AGENT_WAKE_WORD", "0")

from agent_core import main as core
from agent_core.speech import SpeechManager
from agent_core.storage import MemoryStore
from agent_core.voice import VoiceError
from agent_core.voice_text import normalize_voice_text
try:
    from test_speech_ws import FakeSpeechClient, ScriptedProvider, _collect_until
except ImportError:  # module-path execution: fall back to package-relative import
    from tests.test_speech_ws import FakeSpeechClient, ScriptedProvider, _collect_until


def _run(coro):
    return asyncio.run(coro)


class NormalizeTests(unittest.TestCase):
    def test_date_day_becomes_colloquial_hao(self) -> None:
        self.assertEqual(normalize_voice_text("生日是7月12日。"), "生日是7月12号。")

    def test_units_and_titles_are_spoken_forms(self) -> None:
        normalized = normalize_voice_text("身高156cm，来首普通Disco，今天30°C。")
        self.assertIn("156厘米", normalized)
        self.assertIn("普通迪斯科", normalized)
        self.assertIn("30度", normalized)

    def test_plain_text_untouched(self) -> None:
        self.assertEqual(normalize_voice_text("你好呀，今天天气真好。"), "你好呀，今天天气真好。")


class ReplyNormalizationWSTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        store = MemoryStore(data_dir=Path(self._tmp.name))
        self.addCleanup(store.close)
        core.provider = ScriptedProvider("你好呀，我是洛天依，生日是7月12日，身高156cm。")
        self.addCleanup(setattr, core, "provider", core.provider)
        core.memory = store
        self.addCleanup(setattr, core, "memory", core.memory)
        core.tools_schema = []
        self.addCleanup(setattr, core, "tools_schema", core.tools_schema)
        core.TTS_ENABLED = True
        self.addCleanup(setattr, core, "TTS_ENABLED", False)
        speech_client = FakeSpeechClient()
        core.speech_client = speech_client
        self.addCleanup(setattr, core, "speech_client", core.speech_client)
        core.speech_manager = SpeechManager(
            speech_client,
            on_speak=core._broadcast_speak,
            on_interrupt=core._broadcast_speech_stop,
        )
        self.addCleanup(setattr, core, "speech_manager", core.speech_manager)

    def test_displayed_and_spoken_text_stay_identical(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(core.app)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        ws = client.websocket_connect("/ws")
        self.addCleanup(ws.__exit__, None, None, None)
        ws.__enter__()
        ws.send_json({"type": "client.hello", "role": "avatar"})
        _collect_until(ws, "client.ready")

        ws.send_json({"type": "session.new"})
        switched = _collect_until(ws, "session.switched")[-1]
        session_id = int(switched["conversationId"])

        ws.send_json(
            {"type": "chat.message", "messageId": "m1", "text": "你好", "conversationId": session_id}
        )
        events = _collect_until(ws, "avatar.speak")
        response = next(e for e in events if e.get("type") == "chat.response")
        speak = events[-1]
        self.assertIn("7月12号", response["text"])
        self.assertIn("156厘米", response["text"])
        self.assertEqual(speak["text"], response["text"])


class FakeWakeListener:
    def __init__(self) -> None:
        self.paused = False
        self.pause_count = 0
        self.resume_count = 0

    def pause(self) -> None:
        self.paused = True
        self.pause_count += 1

    def resume(self) -> None:
        self.paused = False
        self.resume_count += 1


class FakeRecorder:
    """Hermetic stand-in for the mic-backed recorder (no real audio device)."""

    def __init__(self) -> None:
        self.started = False

    @property
    def recording(self) -> bool:
        return self.started

    def start(self) -> None:
        self.started = True

    def stop(self) -> bytes:
        if not self.started:
            raise VoiceError("当前没有正在进行的录音")
        self.started = False
        return b"fake-wav"

    def cancel(self) -> None:
        self.started = False


class WakeReArmTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        store = MemoryStore(data_dir=Path(self._tmp.name))
        self.addCleanup(store.close)
        core.provider = ScriptedProvider("好的。")
        self.addCleanup(setattr, core, "provider", core.provider)
        core.memory = store
        self.addCleanup(setattr, core, "memory", core.memory)
        core.tools_schema = []
        self.addCleanup(setattr, core, "tools_schema", core.tools_schema)
        self.listener = FakeWakeListener()
        core.wake_listener = self.listener
        self.addCleanup(setattr, core, "wake_listener", None)
        self.recorder = FakeRecorder()
        core.voice_recorder = self.recorder
        self.addCleanup(setattr, core, "voice_recorder", core.voice_recorder)

    def test_wake_stays_paused_until_transcript_dispatched(self) -> None:
        from fastapi.testclient import TestClient

        observed = {}

        def fake_transcribe(_audio_bytes):
            observed["paused_during"] = self.listener.paused
            return "测试一句"

        patcher = unittest.mock.patch.object(core, "transcribe_wav", fake_transcribe)
        patcher.start()
        self.addCleanup(patcher.stop)

        client = TestClient(core.app)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        ws = client.websocket_connect("/ws")
        self.addCleanup(ws.__exit__, None, None, None)
        ws.__enter__()
        ws.send_json({"type": "client.hello", "role": "avatar"})
        _collect_until(ws, "client.ready")

        ws.send_json({"type": "voice.start"})
        ws.send_json({"type": "voice.stop"})

        transcript = _collect_until(ws, "voice.transcript", limit=40)[-1]
        self.assertEqual(transcript["text"], "测试一句")
        self.assertTrue(observed["paused_during"])
        self.assertEqual(self.listener.resume_count, 1)
        self.assertFalse(self.listener.paused)

    def test_failed_recording_still_re_arms_wake(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(core.app)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        ws = client.websocket_connect("/ws")
        self.addCleanup(ws.__exit__, None, None, None)
        ws.__enter__()
        ws.send_json({"type": "client.hello", "role": "avatar"})
        _collect_until(ws, "client.ready")

        # stop without any prior start: VoiceError path must still resume
        ws.send_json({"type": "voice.stop"})
        _collect_until(ws, "core.error", limit=20)
        self.assertEqual(self.listener.resume_count, 1)


class VoiceRefractoryTests(unittest.TestCase):
    def test_recent_voice_stop_drops_wake_trigger(self) -> None:
        class _SpyMemory:
            def __init__(self) -> None:
                self.events = []

            def add_event(self, event_type, payload=None):
                self.events.append((event_type, payload))

        spy = _SpyMemory()
        old_memory = core.memory
        core.memory = spy
        self.addCleanup(setattr, core, "memory", old_memory)
        old_state = core._agent_state
        core._agent_state = "idle"
        self.addCleanup(setattr, core, "_agent_state", old_state)
        recorder = FakeRecorder()
        old_recorder = core.voice_recorder
        core.voice_recorder = recorder
        self.addCleanup(setattr, core, "voice_recorder", old_recorder)

        core._voice_refractory["last_voice_stop"] = time.monotonic()
        _run(core.handle_wake_word(None))
        self.assertTrue(
            any(t == "wake.busy" and p and p.get("refractory") for t, p in spy.events)
        )

        core._voice_refractory["last_voice_stop"] = time.monotonic() - 30
        count = len(spy.events)
        _run(core.handle_wake_word(None))
        self.assertEqual(len(spy.events), count)


if __name__ == "__main__":
    unittest.main()
