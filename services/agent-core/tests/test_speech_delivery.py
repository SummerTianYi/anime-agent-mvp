"""Codex: playback acknowledgements, retries and scene success boundaries."""
import asyncio
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
