"""Codex: installed speech recognition must not need a model-host connection."""
import sys
import types
import unittest
from unittest.mock import patch
from agent_core import voice


class OfflineVoiceTests(unittest.TestCase):
    def test_cached_stt_works_with_model_host_unavailable(self):
        calls = []
        def model(*args, **kwargs):
            calls.append(kwargs)
            if not kwargs.get('local_files_only'):
                raise OSError('simulated model-host TLS failure')
            return types.SimpleNamespace(transcribe=lambda *a, **k: ([types.SimpleNamespace(text='你好天依')], None))
        with patch.object(voice, '_stt_model', None), patch.dict(sys.modules, {'faster_whisper': types.SimpleNamespace(WhisperModel=model)}):
            self.assertEqual(voice.transcribe_wav(b'isolated fixture'), '你好天依')
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]['local_files_only'])

    def test_missing_cache_is_an_explicit_error_not_a_network_download(self):
        calls = []
        def model(*args, **kwargs):
            calls.append(kwargs)
            raise FileNotFoundError('no cached model')
        with patch.object(voice, '_stt_model', None), patch.dict(sys.modules, {'faster_whisper': types.SimpleNamespace(WhisperModel=model)}):
            with self.assertRaises(voice.VoiceError):
                voice.transcribe_wav(b'isolated fixture')
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].get('local_files_only'))
