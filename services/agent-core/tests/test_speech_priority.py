"""Deterministic ordering at the real synchronous synthesize() boundary."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from pathlib import Path
import tempfile
import threading
import time
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agent_core.speech import SpeechManager
from agent_core import main as core


async def load_failure_trace(manager_type=SpeechManager):
    """Hold B in the worker until C and the requested retry of A are waiting."""
    loop = asyncio.get_running_loop()
    entered_b, queued_c, queued_retry = (asyncio.Event() for _ in range(3))
    release_b = threading.Event()
    entered, plays, events = [], [], []
    active = peak = 0
    lock = threading.Lock()
    start = time.perf_counter_ns()

    def record(stage, part):
        events.append({"event": stage, "part": part, "us": (time.perf_counter_ns()-start)//1000})

    def synth(text, speed):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            entered.append(text)
            record("worker-enter", text)
        try:
            if text == "乙。":
                loop.call_soon_threadsafe(entered_b.set)
                if not release_b.wait(4):
                    raise RuntimeError("fixture did not release B")
            return {"audioPath":"fixture.wav", "sampleRate":32000, "durationMs":10}
        finally:
            with lock:
                record("worker-return", text)
                active -= 1

    async def play(p):
        plays.append((p["text"], p["playbackId"]))
        failure = len(plays) == 1
        if failure:
            await asyncio.wait_for(entered_b.wait(), 2)
            await asyncio.wait_for(queued_c.wait(), 2)
        record("avatar-load-failed" if failure else "avatar-finished", p["text"])
        accepted = await manager.notify_finished(p["utteranceId"], p["playbackId"],
                                                 error="audio-load-failed" if failure else "")
        if not accepted:
            raise AssertionError("fixture receipt rejected")

    async def stop(*args):
        raise AssertionError("unexpected stop")

    manager = manager_type(SimpleNamespace(synthesize=synth), play, stop, lookahead=2)
    serial = manager._serial_synth
    async def observed(utterance, index, text, preparation_id):
        record("submit", text)
        if text == "丙。":
            queued_c.set()
        if text == "甲。" and plays:
            queued_retry.set()
        # No yield between observation and entering the actual manager.
        return await serial(utterance, index, text, preparation_id)
    manager._serial_synth = observed
    speaking = asyncio.create_task(manager.speak("甲。乙。丙。", "synthetic-retry"))
    try:
        await asyncio.wait_for(queued_retry.wait(), 2)
        assert entered == ["甲。", "乙。"]
        record("release-inflight", "乙。")
    finally:
        release_b.set()
    utterance = await asyncio.wait_for(speaking, 3)
    return {"events":events, "synthesis":entered, "playback":[p for p, _ in plays],
            "distinctPlaybackIds":len({pid for _, pid in plays}),
            "peakWorkers":peak, "completed":utterance.completed}


class PriorityTests(unittest.IsolatedAsyncioTestCase):
    async def until(self, predicate):
        async def check():
            while not predicate():
                await asyncio.sleep(0)
        await asyncio.wait_for(check(), 2)

    async def test_failed_current_part_precedes_queued_prefetch_with_full_lookahead(self):
        result = await load_failure_trace()
        self.assertEqual(result["synthesis"], ["甲。", "乙。", "甲。", "丙。"])
        self.assertEqual(result["playback"], ["甲。", "甲。", "乙。", "丙。"])
        self.assertTrue(result["completed"])
        self.assertEqual((result["peakWorkers"], result["distinctPlaybackIds"]), (1, 4))

    async def test_prefetch_becomes_current_without_duplicate_and_cache_fifo_resumes(self):
        loop = asyncio.get_running_loop()
        submissions = []
        results = []
        trace = []
        audio = {"audioPath":"fixture.wav", "sampleRate":32000, "durationMs":10}
        def executor(pool, run, synth, text, speed):
            fut = loop.create_future()
            submissions.append(text)
            results.append(fut)
            return fut
        async def play(p):
            if p["partIndex"] == 0:
                await self.until(lambda: len(manager._synthesis_waiters) == 4)
            await manager.notify_finished(p["utteranceId"], p["playbackId"])
        manager = SpeechManager(SimpleNamespace(synthesize=lambda *_: None), play, AsyncMock(),
                                lookahead=2, on_timing=trace.append)
        with patch.object(loop, "run_in_executor", executor):
            task = asyncio.create_task(manager.speak("甲。乙。丙。"))
            await self.until(lambda: len(results) == 1)
            caches = [asyncio.create_task(manager.prepare_farewell(t)) for t in ("缓存1","缓存2","缓存3")]
            await self.until(lambda: len(manager._synthesis_waiters) == 3)
            results[0].set_result(audio)
            # One already-granted cache can run while the first file reaches playback.
            await self.until(lambda: len(results) == 2 and manager.current.needed_part == 1)
            self.assertEqual(submissions[1], "缓存1")
            for i in range(1,6):
                await self.until(lambda: len(results) > i)
                results[i].set_result(audio)
            self.assertTrue((await task).completed)
            await asyncio.gather(*caches)
        self.assertEqual(submissions, ["甲。","缓存1","乙。","丙。","缓存2","缓存3"])
        second = next(e for e in trace if e["stage"]=="synth-request" and e["partIndex"]==1)
        self.assertEqual((second["queuedPriority"], second["priority"]), (1, 0))

    async def test_cancel_at_queue_grant_running_and_return(self):
        # Control the executor future itself so cancel can land exactly between
        # grant and resume, and between thread return and waiter delivery.
        loop = asyncio.get_running_loop()
        for phase in ("queued","granted","running","returned"):
            with self.subTest(phase=phase):
                manager = SpeechManager(SimpleNamespace(synthesize=lambda *_: None), AsyncMock(), AsyncMock())
                calls = {}
                def executor(pool, run, synth, text, speed):
                    calls[text] = loop.create_future()
                    return calls[text]
                with patch.object(loop, "run_in_executor", executor):
                    first, victim, last = [asyncio.create_task(manager.prepare_farewell(t))
                                           for t in ("first","victim","last")]
                    await self.until(lambda: len(manager._synthesis_waiters)==2 and "first" in calls)
                    turn = manager._synthesis_waiters[0].turn
                    if phase == "queued":
                        self.assertFalse(turn.done())
                        victim.cancel()
                    calls["first"].set_result({})
                    if phase == "granted":
                        observed = []
                        def cancel_after_grant():
                            observed.append(turn.done() and not turn.cancelled() and "victim" not in calls)
                            victim.cancel()
                        loop.call_soon(cancel_after_grant)
                    if phase in ("running","returned"):
                        await self.until(lambda: "victim" in calls)
                        if phase == "returned":
                            calls["victim"].set_result({})
                        victim.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await victim
                    if phase == "granted":
                        self.assertEqual(observed, [True])
                    if phase == "running":
                        self.assertNotIn("last", calls)
                        self.assertFalse(calls["victim"].done())
                        calls["victim"].set_result({})
                    await self.until(lambda: "last" in calls)
                    calls["last"].set_result({})
                    await asyncio.gather(first, last)
                    self.assertEqual(list(calls), ["first","last"] if phase in ("queued","granted")
                                     else ["first","victim","last"])
                    self.assertEqual(manager._synthesis_waiters, [])
                    self.assertIsNone(manager._synthesis_worker)

    async def test_real_voice_worker_does_not_wait_in_a_saturated_shared_executor(self):
        loop = asyncio.get_running_loop()
        original_submit = loop.run_in_executor
        release = threading.Event()
        marker = ContextVar("synthetic-request", default="")
        marker.set("from-caller")
        seen = []
        def synth(*args):
            seen.append(marker.get())
            return {"audioPath":"fixture.wav","durationMs":10,"sampleRate":32000}
        async def play(p):
            await manager.notify_finished(p["utteranceId"],p["playbackId"])
        manager = SpeechManager(SimpleNamespace(synthesize=synth), play, AsyncMock())
        with ThreadPoolExecutor(max_workers=1) as shared:
            shared.submit(release.wait, 3)
            def submit(pool, fn, *args):
                return original_submit(shared if pool is None else pool, fn, *args)
            try:
                with patch.object(loop, "run_in_executor", submit):
                    self.assertTrue((await asyncio.wait_for(manager.speak("甲。"), .6)).completed)
                    self.assertEqual(seen, ["from-caller"])
            finally:
                release.set()

    async def test_real_farewell_precache_yields_and_pins_after_foreground(self):
        loop = asyncio.get_running_loop()
        started = asyncio.Event()
        release = threading.Event()
        order = []
        active = peak = 0
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "synth.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setparams((1,2,16000,0,"NONE","none"))
                wav.writeframes(bytes(320))
            def synth(text, speed):
                nonlocal active, peak
                active += 1
                peak = max(peak,active)
                order.append(text)
                try:
                    if text == "乙。":
                        loop.call_soon_threadsafe(started.set)
                        if not release.wait(4):
                            raise AssertionError("fixture timed out")
                    return {"audioPath":str(path),"durationMs":10,"sampleRate":16000}
                finally:
                    active -= 1
            async def play(p):
                await manager.notify_finished(p["utteranceId"],p["playbackId"])
            manager = SpeechManager(SimpleNamespace(synthesize=synth), play, AsyncMock(), lookahead=2)
            hub = SimpleNamespace(role_count=lambda _:1, send_roles=AsyncMock())
            cache = {}
            with patch.multiple(core,speech_manager=manager,TTS_ENABLED=True,hub=hub, memory=MagicMock(),
                                FAREWELL_AUDIO_CACHE=cache,FAREWELL_LINES=("再见一。","再见二。"),
                                _farewell_precaching=False), patch.object(core,"default_data_dir",return_value=root):
                speaking = asyncio.create_task(manager.speak("甲。乙。丙。"))
                await asyncio.wait_for(started.wait(), 2)
                caching = asyncio.create_task(core._precache_farewell_audio())
                try:
                    await self.until(lambda: any(w.utterance is None for w in manager._synthesis_waiters))
                    self.assertEqual(order, ["甲。","乙。"])
                finally:
                    release.set()
                self.assertTrue((await speaking).completed)
                await asyncio.wait_for(caching, 2)
                self.assertFalse(core._farewell_precaching)
            self.assertEqual(order, ["甲。","乙。","丙。","再见一。","再见二。"])
            self.assertEqual(peak, 1)
            self.assertEqual(hub.send_roles.await_count, 2)
            for item in cache.values():
                pinned = Path(item["audioPath"])
                self.assertTrue(pinned.is_relative_to(root / "speech-cache/farewell"))
                self.assertEqual(pinned.read_bytes(), path.read_bytes())
