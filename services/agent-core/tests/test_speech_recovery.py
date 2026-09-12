"""Codex: recovery must not be hidden behind a minute-long negative cache."""
import unittest
from unittest.mock import patch
from agent_core.speech import SpeechClient, SpeechUnavailable


class SpeechRecoveryTests(unittest.TestCase):
    def test_negative_health_rechecks_within_two_seconds(self):
        client = SpeechClient('http://127.0.0.1:1')
        with patch('agent_core.speech.time.monotonic', side_effect=[100, 101, 103, 103]), patch(
            'agent_core.speech._get_json', side_effect=[{'ok': False}, {'ok': True}]
        ) as get:
            self.assertFalse(client.probe_health())
            self.assertFalse(client.is_healthy())
            self.assertTrue(client.is_healthy())
            self.assertEqual(get.call_count, 2)

    def test_malformed_health_is_unavailable_not_uncaught(self):
        for payload in (None, [], 'ok', {'ok': 'false'}):
            with self.subTest(payload=payload), patch('agent_core.speech._get_json', return_value=payload):
                self.assertFalse(SpeechClient('http://127.0.0.1:1').probe_health())

    def test_malformed_synthesis_invalidates_cached_health(self):
        for payload in (None, [], {'ok': True}, {'ok': 'false'}):
            client = SpeechClient('http://127.0.0.1:1')
            client._healthy = True
            with self.subTest(payload=payload), patch('agent_core.speech._post_json', return_value=payload):
                with self.assertRaises(SpeechUnavailable):
                    client.synthesize('测试')
                self.assertIsNone(client._healthy)
