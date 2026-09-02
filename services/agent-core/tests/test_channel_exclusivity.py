"""Channel exclusivity: a manual request supersedes an in-flight wake request,
and a waiting wake capture is preempted by the voice button."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import threading
import time
import unittest
import unittest.mock
from pathlib import Path

os.environ.setdefault("ANIME_AGENT_WAKE_WORD", "0")

from agent_core import main as core
from agent_core import wake_word as ww
from agent_core.storage import MemoryStore


def _run(coro):
    return asyncio.run(coro)


class SlowContractProvider:
    name = "slow-scripted"

    def __init__(self, delay: float = 0.6) -> None:
        self.delay = delay

    async def complete(self, messages) -> str:
        await asyncio.sleep(self.delay)
        return json.dumps(
            {
                "reply": "好的，我介绍完啦。",
                "emotion": "happy",
                "emotion_intensity": 0.4,
                "gesture": "none",
                "memory_candidate": None,
            },
            ensure_ascii=False,
        )


def _assistant_request_ids(store: MemoryStore) -> list[str]:
    rows = store.connection.execute(
        "SELECT request_id FROM messages WHERE role='assistant' ORDER BY id"
    ).fetchall()
    return [str(row["request_id"]) for row in rows]


class WakeSupersedeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = MemoryStore(data_dir=Path(self._tmp.name))
        self.addCleanup(self.store.close)
        old_memory = core.memory
        core.memory = self.store
        self.addCleanup(setattr, core, "memory", old_memory)
        old_provider = core.provider
        core.provider = SlowContractProvider()
        self.addCleanup(setattr, core, "provider", old_provider)
        core.tools_schema = []
        self.addCleanup(setattr, core, "tools_schema", core.tools_schema)
        old_tts = core.TTS_ENABLED
        core.TTS_ENABLED = False
        self.addCleanup(setattr, core, "TTS_ENABLED", old_tts)
        core._superseded_requests.clear()
        core._inflight_wake_request = None
        self.addCleanup(core._superseded_requests.clear)
        self.addCleanup(setattr, core, "_inflight_wake_request", None)
        # a fresh lock per test: the module-level asyncio.Lock binds to the
        # first event loop that acquires it, which poisons later asyncio.run tests
        old_lock = core.chat_lock
        core.chat_lock = asyncio.Lock()
        self.addCleanup(setattr, core, "chat_lock", old_lock)

    def test_manual_request_supersedes_inflight_wake_request(self) -> None:
        session = self.store.create_session()
        sid = int(session["id"])

        async def scenario():
            wake_task = asyncio.create_task(
                core.handle_chat("简单做个自我介绍吧", "wake-1", conversation_id=sid)
            )
            for _ in range(300):
                if core._agent_state == "thinking":
                    break
                await asyncio.sleep(0.02)
            await core.handle_chat("简单做个自我介绍吧", "manual-1", conversation_id=sid)
            await wake_task

        _run(scenario())

        self.assertEqual(_assistant_request_ids(self.store), ["manual-1"])
        superseded = [
            dict(row)["payload"]
            for row in self.store.connection.execute(
                "SELECT payload FROM events WHERE event_type='chat.superseded'"
            )
        ]
        self.assertTrue(any("wake-1" in payload for payload in superseded))

    def test_normal_wake_request_without_manual_overlap_still_answers(self) -> None:
        session = self.store.create_session()
        sid = int(session["id"])
        _run(core.handle_chat("你好", "wake-2", conversation_id=sid))
        self.assertEqual(_assistant_request_ids(self.store), ["wake-2"])

    def test_manual_supersedes_wake_registered_before_dispatch(self) -> None:
        """The review-HIGH fix: the wake id is registered when the chain accepts
        the wake phrase (before capture), so a manual request landing inside the
        capture/STT window already supersedes it; the later dispatch is dropped."""
        session = self.store.create_session()
        sid = int(session["id"])
        core._register_inflight_wake_request("wake-early")
        try:

            async def scenario():
                await core.handle_chat("简单做个自我介绍吧", "manual-early", conversation_id=sid)
                await core.handle_chat("简单做个自我介绍吧", "wake-early", conversation_id=sid)

            _run(scenario())
        finally:
            core._unregister_inflight_wake_request("wake-early")

        self.assertEqual(_assistant_request_ids(self.store), ["manual-early"])
        superseded = [
            dict(row)["payload"]
            for row in self.store.connection.execute(
                "SELECT payload FROM events WHERE event_type='chat.superseded'"
            )
        ]
        self.assertTrue(any("wake-early" in payload for payload in superseded))

    def test_post_llm_supersede_deletes_orphan_user_row(self) -> None:
        """A superseded wake turn must not leave its user message in history."""
        session = self.store.create_session()
        sid = int(session["id"])

        async def scenario():
            wake_task = asyncio.create_task(
                core.handle_chat("简单做个自我介绍吧", "wake-orphan", conversation_id=sid)
            )
            for _ in range(300):
                if core._agent_state == "thinking":
                    break
                await asyncio.sleep(0.02)
            await core.handle_chat("简单做个自我介绍吧", "manual-orphan", conversation_id=sid)
            await wake_task

        _run(scenario())

        rows = self.store.connection.execute(
            "SELECT request_id FROM messages WHERE request_id='wake-orphan'"
        ).fetchall()
        self.assertEqual(rows, [])
        kept = _assistant_request_ids(self.store)
        self.assertEqual(kept, ["manual-orphan"])

    def test_queued_supersede_withdraws_fresh_wake_session(self) -> None:
        """A superseded wake turn leaves no empty auto-titled session behind."""
        manual_session = self.store.create_session()
        manual_sid = int(manual_session["id"])
        fresh_session = self.store.create_session()
        fresh_sid = int(fresh_session["id"])
        core._register_inflight_wake_request("wake-early")
        try:

            async def scenario():
                await core.handle_chat("简单做个自我介绍吧", "manual-early", conversation_id=manual_sid)
                await core.handle_chat("简单做个自我介绍吧", "wake-early", conversation_id=fresh_sid)

            _run(scenario())
        finally:
            core._unregister_inflight_wake_request("wake-early")

        gone = self.store.connection.execute(
            "SELECT id FROM sessions WHERE id=?", (fresh_sid,)
        ).fetchall()
        kept = self.store.connection.execute(
            "SELECT id FROM sessions WHERE id=?", (manual_sid,)
        ).fetchall()
        self.assertEqual(gone, [])
        self.assertTrue(kept)


class CaptureCancelTests(unittest.TestCase):
    def test_cancel_utterance_capture_aborts_promptly(self) -> None:
        import numpy as np

        harness = {"reads": 0}
        token = ww.begin_capture_scope()
        self.addCleanup(ww.end_capture_scope, token)

        class _FakeStream:
            def start(self) -> None:
                pass

            def read(self, frames):
                harness["reads"] += 1
                if harness["reads"] == 3:
                    ww.cancel_utterance_capture()
                arr = np.zeros(frames, dtype="float32")
                return arr.reshape(-1, 1), False

            def stop(self) -> None:
                pass

            def close(self) -> None:
                pass

        class _FakeSd:
            def InputStream(self, **_kwargs):
                return _FakeStream()

        result_holder = {}

        def runner():
            result_holder["r"] = ww.capture_utterance(token)

        with unittest.mock.patch.object(ww, "_import_audio_dependencies", lambda: (np, _FakeSd())):
            thread = threading.Thread(target=runner, daemon=True)
            started = time.monotonic()
            thread.start()
            thread.join(timeout=5.0)
            elapsed = time.monotonic() - started

        self.assertFalse(thread.is_alive(), "capture_utterance did not abort after cancel")
        self.assertIsNone(result_holder["r"])
        self.assertGreaterEqual(harness["reads"], 3)
        self.assertLess(elapsed, 4.0)

    def test_cancel_before_capture_start_aborts_without_mic(self) -> None:
        token = ww.begin_capture_scope()
        self.addCleanup(ww.end_capture_scope, token)
        ww.cancel_utterance_capture()  # fires before capture_utterance starts
        self.assertTrue(token.is_set())
        self.assertIsNone(ww.capture_utterance(token))

    def test_cancel_after_scope_closed_is_noop(self) -> None:
        token = ww.begin_capture_scope()
        ww.end_capture_scope(token)
        ww.cancel_utterance_capture()
        self.assertFalse(token.is_set())


class VoiceStartCancelWiringTests(unittest.TestCase):
    def test_voice_start_calls_cancel_utterance_capture(self) -> None:
        from fastapi.testclient import TestClient

        calls = []
        old_cancel = core.cancel_utterance_capture
        core.cancel_utterance_capture = lambda: calls.append(True)
        self.addCleanup(setattr, core, "cancel_utterance_capture", old_cancel)

        client = TestClient(core.app)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        ws = client.websocket_connect("/ws")
        self.addCleanup(ws.__exit__, None, None, None)
        ws.__enter__()
        ws.send_json({"type": "client.hello", "role": "avatar"})
        for _ in range(40):
            evt = _recv_json(ws)
            if evt.get("type") == "client.ready":
                break

        ws.send_json({"type": "voice.start"})
        for _ in range(40):
            if calls:
                break
            time.sleep(0.05)
        self.assertTrue(calls)


def _recv_json(ws, timeout: float = 5.0):
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(ws.receive_json).result(timeout=timeout)


if __name__ == "__main__":
    unittest.main()
