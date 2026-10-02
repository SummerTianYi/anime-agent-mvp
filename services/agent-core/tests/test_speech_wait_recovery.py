"""Codex: pending-reply recovery, separate from existing health-cache regressions."""
import asyncio
import io
import unittest
import urllib.error
from unittest.mock import patch

from agent_core.speech import SpeechClient, SpeechManager, SpeechUnavailable


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def manager(self, outcomes, **kwargs):
        calls, played, notices = [], [], []
        def synthesize(text, speed):
            calls.append(text)
            outcome = outcomes.pop(0) if outcomes else True
            if isinstance(outcome, Exception):
                raise outcome
            return {"audioPath": "fixture.wav", "durationMs": 1, "sampleRate": 32000}
        class Client:
            pass
        client = Client()
        client.synthesize = synthesize
        async def play(payload):
            played.append(payload["text"])
            await manager.notify_finished(payload["utteranceId"])
        async def stop(*args):
            pass
        async def recovery(*args):
            notices.append(args)
        manager = SpeechManager(client, play, stop, recovery_timeout_seconds=.15,
                                retry_interval_seconds=.01, on_recovery=recovery, **kwargs)
        return manager, calls, played, notices

    async def test_warmup_retries_without_losing_first_sentence(self):
        mgr, calls, played, notices = self.manager([SpeechUnavailable('warming', retryable=True), True])
        result = await mgr.speak('你好。')
        self.assertTrue(result.has_audio)
        self.assertEqual(played, ['你好。'])
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(notices), 1)
        self.assertIsNone(mgr.current)

    async def test_mid_reply_recovers_only_unplayed_part(self):
        mgr, calls, played, _ = self.manager([True, SpeechUnavailable('down', retryable=True), True])
        await mgr.speak('第一句。第二句。')
        self.assertEqual(played, ['第一句。', '第二句。'])
        self.assertEqual(calls, ['第一句。', '第二句。', '第二句。'])

    async def test_permanent_error_is_not_retried(self):
        mgr, calls, played, _ = self.manager([SpeechUnavailable('bad input')])
        with self.assertRaises(SpeechUnavailable):
            await mgr.speak('你好。')
        self.assertEqual(len(calls), 1)
        self.assertEqual(played, [])
        self.assertIsNone(mgr.current)

    async def test_recovery_deadline_is_bounded(self):
        mgr, calls, played, _ = self.manager([SpeechUnavailable('down', retryable=True)] * 100)
        with self.assertRaises(SpeechUnavailable):
            await asyncio.wait_for(mgr.speak('你好。'), .8)
        self.assertGreater(len(calls), 1)
        self.assertEqual(played, [])
        self.assertIsNone(mgr.current)

    async def test_interrupt_between_parts_even_after_playback_ack(self):
        mgr, calls, played, notices = self.manager([True, SpeechUnavailable('down', retryable=True)] +
                                                 [SpeechUnavailable('down', retryable=True)] * 100)
        task = asyncio.create_task(mgr.speak('第一句。第二句。'))
        async with asyncio.timeout(1):
            while not notices:
                await asyncio.sleep(.001)
        self.assertTrue(await mgr.interrupt('voice'))
        result = await asyncio.wait_for(task, .1)
        self.assertTrue(result.cancelled)
        self.assertEqual(played, ['第一句。'])

    async def test_superseding_reply_discards_waiting_old_reply(self):
        mgr, calls, played, notices = self.manager([SpeechUnavailable('down', retryable=True), True])
        old = asyncio.create_task(mgr.speak('旧回复。'))
        async with asyncio.timeout(1):
            while not notices:
                await asyncio.sleep(.001)
        new = await mgr.speak('新回复。')
        self.assertFalse(new.cancelled)
        self.assertTrue((await old).cancelled)
        self.assertEqual(played, ['新回复。'])

    async def test_failed_prefetch_does_not_orphan_current_playback(self):
        mgr, calls, played, _ = self.manager([True, SpeechUnavailable('bad input')],
                                           completion_grace_seconds=1)
        async def play_without_ack(payload):
            played.append(payload['text'])
        mgr.on_speak = play_without_ack
        task = asyncio.create_task(mgr.speak('第一句。第二句。'))
        async with asyncio.timeout(1):
            while len(calls)<2:
                await asyncio.sleep(.001)
        self.assertTrue(await mgr.interrupt('voice'))
        self.assertTrue((await task).cancelled)
        self.assertEqual(played,['第一句。'])


class RetryClassificationTests(unittest.TestCase):
    def test_http_status_classification(self):
        for status, retryable in [(400, False), (401, False), (404, False), (429, True), (500, True), (503, True)]:
            with self.subTest(status=status):
                exc = urllib.error.HTTPError('http://127.0.0.1', status, 'fixture', {}, io.BytesIO())
                with patch('agent_core.speech._post_json', side_effect=exc):
                    with self.assertRaises(SpeechUnavailable) as caught:
                        SpeechClient('http://127.0.0.1').synthesize('测试')
                self.assertEqual(caught.exception.retryable, retryable)

    def test_connection_loss_is_retryable(self):
        with patch('agent_core.speech._post_json', side_effect=urllib.error.URLError('fixture')):
            with self.assertRaises(SpeechUnavailable) as caught:
                SpeechClient('http://127.0.0.1').synthesize('测试')
        self.assertTrue(caught.exception.retryable)
