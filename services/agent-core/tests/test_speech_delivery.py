"""Codex: playback acknowledgements, retries and scene success boundaries."""
import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agent_core.speech import SpeechManager, SpeechUnavailable
from agent_core import main as core


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    def manager(self, play):
        self.calls, self.payloads, self.stops = [], [], []
        def synthesize(text, speed):
            self.calls.append(text)
            return {"audioPath": "fixture.wav", "durationMs": 1, "sampleRate": 32000}
        async def on_speak(payload):
            self.payloads.append(payload)
            await play(payload)
        async def stop(*args):
            self.stops.append(args)
        self.mgr = SpeechManager(SimpleNamespace(synthesize=synthesize), on_speak, stop,
                                 completion_grace_seconds=.01, retry_interval_seconds=.001)
        return self.mgr

    async def ack(self, p, **kwargs):
        return await self.mgr.notify_finished(p["utteranceId"], p["playbackId"], **kwargs)

    async def test_no_receipt_is_failure_not_completed(self):
        mgr = self.manager(AsyncMock())
        with self.assertRaises(SpeechUnavailable):
            await mgr.speak("测试。")
        self.assertEqual(len(self.payloads), 3)
        self.assertEqual(len({p['playbackId'] for p in self.payloads}), 1)
        self.assertEqual(len(self.calls), 1, 'unknown delivery must not resynthesize')
        self.assertIsNone(mgr.current)
        self.assertEqual(self.stops[0][1], 'playback-failed')

    async def test_lost_ack_same_id_then_receipt_completes(self):
        async def play(p):
            if len(self.payloads) == 2:
                await self.ack(p)
        result = await self.manager(play).speak('测试。')
        self.assertTrue(result.completed)
        self.assertEqual(self.payloads[0], self.payloads[1])

    async def test_explicit_unplayed_failure_resynthesizes_only_that_part(self):
        async def play(p):
            await self.ack(p, error='audio-load-failed' if len(self.payloads) == 1 else '')
        result = await self.manager(play).speak('第一句。第二句。')
        self.assertTrue(result.completed)
        self.assertEqual(self.calls.count('第一句。'), 2)
        self.assertEqual(self.calls.count('第二句。'), 1)
        self.assertEqual([p['partIndex'] for p in self.payloads], [0, 0, 1])
        self.assertEqual(len({p['playbackId'] for p in self.payloads}), 3)

    async def test_stale_previous_part_receipt_rejected(self):
        async def play(p):
            if p['partIndex'] == 1:
                self.assertFalse(await self.ack(self.payloads[0]))
                self.assertFalse(self.mgr.current.done.is_set())
            await self.ack(p)
        result = await self.manager(play).speak('第一句。第二句。')
        self.assertTrue(result.completed)

    async def test_interrupted_receipt_is_not_success(self):
        async def play(p):
            await self.ack(p, interrupted=True)
        result = await self.manager(play).speak('测试。')
        self.assertTrue(result.cancelled)
        self.assertFalse(result.completed)

    async def test_repeated_failed_audio_bounded(self):
        async def play(p):
            await self.ack(p, error='audio-load-failed')
        with self.assertRaises(SpeechUnavailable):
            await self.manager(play).speak('测试。')
        self.assertEqual(len(self.calls), 3)

    async def test_prepared_audio_uses_same_confirmation_path(self):
        async def play(p):
            await self.ack(p)
        mgr = self.manager(play)
        result = await mgr.speak('再见。下次见。', 'exit-1', prepared_audio={
            'audioPath':'cache.wav','durationMs':1,'sampleRate':32000})
        self.assertTrue(result.completed)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.payloads[0]['partCount'], 1)

    async def test_interrupt_during_receipt_retry_stops_old_delivery(self):
        ready = asyncio.Event()
        async def play(p):
            ready.set()
        mgr = self.manager(play)
        task = asyncio.create_task(mgr.speak('测试。'))
        await ready.wait()
        await mgr.interrupt('voice')
        self.assertTrue((await task).cancelled)
        self.assertEqual(len(self.payloads), 1)


class LookaheadTests(unittest.IsolatedAsyncioTestCase):
    async def test_barge_in_drops_prepared_and_waiting_parts_and_serializes_old_worker(self):
        release = threading.Event()
        started = threading.Event()
        calls = []
        plays = []
        stops = []
        def synth(text, speed):
            calls.append(text)
            if text == "第二。":
                started.set()
                if not release.wait(3):
                    raise AssertionError("test worker timed out")
            return {"audioPath": "test.wav", "durationMs": 100, "sampleRate": 32000}
        async def play(p):
            plays.append(p)
            if p["text"] == "新。":
                await manager.notify_finished(p["utteranceId"], p["playbackId"])
        async def stop(*args):
            stops.append(args)
        manager = SpeechManager(SimpleNamespace(synthesize=synth), play, stop, lookahead=2)
        old = asyncio.create_task(manager.speak("第一。第二。第三。第四。"))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            new = asyncio.create_task(manager.speak("新。"))
            self.assertTrue((await asyncio.wait_for(old, 1)).cancelled)
            await asyncio.sleep(.02)
            self.assertEqual(calls, ["第一。", "第二。"])
            self.assertFalse(await manager.notify_finished(plays[0]["utteranceId"], plays[0]["playbackId"]))
        finally:
            release.set()
        self.assertTrue((await new).completed)
        self.assertEqual([p["text"] for p in plays], ["第一。", "新。"])
        self.assertEqual(stops, [(plays[0]["utteranceId"], "superseded")])

    async def test_bounded_ready_files_first_part_is_delivered_before_future_audio(self):
        hold = asyncio.Event()
        first = asyncio.Event()
        prepared = []
        trace = []
        def synth(text, speed):
            prepared.append(text)
            return {"audioPath": "fixture.wav", "durationMs": 1, "sampleRate": 32000,
                    "takeTiming": {"selectedTake": 2}}
        async def play(p):
            if p["partIndex"] == 0:
                first.set()
                await hold.wait()
            await manager.notify_finished(p["utteranceId"], p["playbackId"])
        manager = SpeechManager(SimpleNamespace(synthesize=synth), play, AsyncMock(),
                                lookahead=999, on_timing=trace.append)
        t = asyncio.create_task(manager.speak("一。二。三。四。", "synthetic"))
        await asyncio.wait_for(first.wait(), 1)
        for _ in range(100):
            if len(prepared) == 3:
                break
            await asyncio.sleep(.005)
        self.assertEqual(prepared, ["一。", "二。", "三。"])
        hold.set()
        self.assertTrue((await t).completed)
        self.assertEqual(prepared, ["一。", "二。", "三。", "四。"])
        for index in range(4):
            events = [e for e in trace if e["partIndex"] == index]
            self.assertEqual([e["stage"] for e in events], ["synth-request", "ready", "dispatch"])
            self.assertEqual({e["requestId"] for e in events}, {"synthetic"})
            self.assertEqual(len({e["preparationId"] for e in events}), 1)
            self.assertEqual(events[-1]["selectedTake"], 2)


class SceneSuccessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.policy = MagicMock()
        self.policy.allow.return_value = (True, '')
        self.policy.decide.return_value = (True, '')
        self.speak = AsyncMock(return_value=False)
        for key, val in {'TTS_ENABLED':True, 'speech_manager':SimpleNamespace(current=None),
                         'proactive_policy':self.policy,'idle_policy':self.policy,
                         '_proactive_pending':set(), '_agent_state':'idle',
                         'memory':MagicMock(), '_speak_reply':self.speak,
                         'hub':SimpleNamespace(role_count=lambda role:1)}.items():
            ctx=patch.object(core,key,val)
            ctx.start()
            self.addCleanup(ctx.stop)

    async def test_failed_greeting_does_not_consume_cooldown(self):
        await core._proactive_greeting('avatar-connect')
        self.policy.mark_spoken.assert_not_called()
        self.assertEqual(core._proactive_pending,set())

    async def test_failed_idle_does_not_consume_cooldown(self):
        await core._proactive_idle(5000)
        self.policy.mark_spoken.assert_not_called()

    async def test_greeting_marks_after_playback_idle_not_remarked_after_playback(self):
        async def success(*args, **kw):
            self.policy.mark_spoken.assert_not_called()
            return True
        self.speak.side_effect=success
        await core._proactive_greeting('avatar-connect')
        self.policy.mark_spoken.assert_called_once()
        self.policy.mark_spoken.reset_mock()
        await core._proactive_idle(5000)
        # Idle consumption happens at _broadcast_speak, not after playback;
        # otherwise activity while speaking would consume the next episode.
        self.policy.mark_spoken.assert_not_called()

    async def test_concurrent_greetings_not_duplicate(self):
        entered, release=asyncio.Event(),asyncio.Event()
        async def wait(*args, **kwargs):
            entered.set()
            await release.wait()
            return True
        self.speak.side_effect=wait
        task=asyncio.create_task(core._proactive_greeting('avatar-connect'))
        await entered.wait()
        await core._proactive_greeting('avatar-connect')
        await core._proactive_idle(5000)
        release.set()
        await task
        self.speak.assert_awaited_once()

    async def test_idle_does_not_interrupt_active_reasoning(self):
        core._agent_state='thinking'
        await core._proactive_idle(5000)
        self.speak.assert_not_awaited()
