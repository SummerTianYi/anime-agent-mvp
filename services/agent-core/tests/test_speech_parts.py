"""Streaming multi-part speech, wake busy-suppression, and session-switch interrupts."""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANIME_AGENT_WAKE_WORD", "0")

from agent_core import main as core
from agent_core.speech import SpeechManager, SpeechUnavailable, split_reply_into_parts
from agent_core.storage import MemoryStore
try:
    from test_speech_ws import FakeSpeechClient, ScriptedProvider, _collect_until
except ImportError:  # module-path execution: fall back to package-relative import
    from tests.test_speech_ws import FakeSpeechClient, ScriptedProvider, _collect_until


def _run(coro):
    return asyncio.run(coro)


class SplitterTests(unittest.TestCase):
    def test_strong_punctuation_splits_and_stays_attached(self) -> None:
        self.assertEqual(split_reply_into_parts("你好。今天天气很好！"), ["你好。", "今天天气很好！"])

    def test_newline_is_a_strong_break(self) -> None:
        self.assertEqual(split_reply_into_parts("第一行\n第二行"), ["第一行", "第二行"])

    def test_long_chunk_repacked_at_weak_punctuation(self) -> None:
        text = "她说明天要去公园，还有超市，然后回家，最后休息。"
        parts = split_reply_into_parts(text, 10)
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(len(part) <= 12 for part in parts))

    def test_punct_free_text_hard_wrapped(self) -> None:
        self.assertEqual(split_reply_into_parts("a" * 100, 30), ["a" * 30, "a" * 30, "a" * 30, "a" * 10])

    def test_whitespace_only_text_gives_no_parts(self) -> None:
        self.assertEqual(split_reply_into_parts("   "), [])


class ScriptedStreamClient:
    def __init__(self, fail_on_call: int | None = None) -> None:
        self.calls: list[str] = []
        self._fail_on_call = fail_on_call

    def is_healthy(self) -> bool:
        return True

    def synthesize(self, text: str, speed: float = 1.0) -> dict:
        self.calls.append(text)
        if self._fail_on_call is not None and len(self.calls) == self._fail_on_call:
            raise SpeechUnavailable("boom")
        index = len(self.calls)
        return {"audioPath": f"C:/x/{index}.wav", "durationMs": 10, "sampleRate": 32000}


def _make_manager(client: ScriptedStreamClient, auto_finish: bool):
    payloads: list[dict] = []
    stops: list[tuple[str, str]] = []
    holder: dict = {}

    async def on_speak(payload: dict) -> None:
        payloads.append(payload)
        if auto_finish:
            await holder["mgr"].notify_finished(payload["utteranceId"])

    async def on_interrupt(utterance_id: str, reason: str) -> None:
        stops.append((utterance_id, reason))

    holder["mgr"] = SpeechManager(
        client, on_speak=on_speak, on_interrupt=on_interrupt, completion_grace_seconds=5
    )
    return holder["mgr"], payloads, stops


THREE_PARTS = "第一句。第二句很长很长很长很长很长很长很长很长很长。第三句！"


class StreamingSpeechTests(unittest.TestCase):
    def test_multi_part_streams_same_utterance_id(self) -> None:
        client = ScriptedStreamClient()
        mgr, payloads, _stops = _make_manager(client, auto_finish=True)
        utt = _run(mgr.speak(THREE_PARTS, "r1"))
        self.assertEqual([p["partIndex"] for p in payloads], [0, 1, 2])
        self.assertEqual(payloads[0]["partCount"], 3)
        self.assertEqual(len({p["utteranceId"] for p in payloads}), 1)
        self.assertEqual(payloads[0]["text"], "第一句。")
        self.assertTrue(utt.done.is_set())
        self.assertEqual(len(client.calls), 3)

    def test_interrupt_stops_remaining_parts(self) -> None:
        client = ScriptedStreamClient()
        mgr, payloads, stops = _make_manager(client, auto_finish=False)

        async def scenario():
            task = asyncio.create_task(mgr.speak(THREE_PARTS, "r1"))
            for _ in range(500):
                if payloads:
                    break
                await asyncio.sleep(0.01)
            await mgr.interrupt("voice")
            return await task

        utt = _run(scenario())
        self.assertEqual(len(payloads), 1)
        self.assertTrue(utt.cancelled)
        self.assertEqual(stops, [(payloads[0]["utteranceId"], "voice")])

    def test_followup_failure_ends_gracefully(self) -> None:
        client = ScriptedStreamClient(fail_on_call=2)
        mgr, payloads, _stops = _make_manager(client, auto_finish=True)
        utt = _run(mgr.speak(THREE_PARTS, "r1"))
        self.assertEqual(len(payloads), 1)
        self.assertTrue(utt.done.is_set())
        self.assertFalse(utt.cancelled)

    def test_new_speak_supersedes_streaming_utterance(self) -> None:
        client = ScriptedStreamClient()
        mgr, payloads, stops = _make_manager(client, auto_finish=False)

        async def scenario():
            first = asyncio.create_task(mgr.speak(THREE_PARTS, "r1"))
            for _ in range(500):
                if payloads:
                    break
                await asyncio.sleep(0.01)
            second = await mgr.speak("好。", "r2")
            return await first, second

        first, second = _run(scenario())
        self.assertTrue(first.cancelled)
        self.assertEqual(len(payloads), 2)
        self.assertEqual(stops[-1][1], "superseded")
        self.assertNotEqual(first.id, second.id)


class WakeBusyTests(unittest.TestCase):
    def test_wake_trigger_dropped_while_agent_busy(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = MemoryStore(data_dir=Path(tmp.name))
        self.addCleanup(store.close)
        old_memory = core.memory
        core.memory = store
        self.addCleanup(setattr, core, "memory", old_memory)
        old_state = core._agent_state
        core._agent_state = "speaking"
        self.addCleanup(setattr, core, "_agent_state", old_state)

        sessions_before = len(store.list_sessions())
        _run(core.handle_wake_word(None))

        self.assertEqual(len(store.list_sessions()), sessions_before)
        self.assertFalse(core._wake_busy)


class SessionSwitchInterruptTests(unittest.TestCase):
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
        speech_client = FakeSpeechClient()
        core.speech_client = speech_client
        self.addCleanup(setattr, core, "speech_client", core.speech_client)
        core.speech_manager = SpeechManager(
            speech_client,
            on_speak=core._broadcast_speak,
            on_interrupt=core._broadcast_speech_stop,
        )
        self.addCleanup(setattr, core, "speech_manager", core.speech_manager)

    def test_session_new_interrupts_speech(self) -> None:
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
        speak = _collect_until(ws, "avatar.speak")[-1]

        ws.send_json({"type": "session.new"})
        stop = _collect_until(ws, "avatar.speech.stop")[-1]
        self.assertEqual(stop["utteranceId"], speak["utteranceId"])
        self.assertEqual(stop["reason"], "session-switch")


if __name__ == "__main__":
    unittest.main()
