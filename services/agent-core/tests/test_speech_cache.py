"""Codex: derived farewell cache only; no production or model files."""
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from agent_core.speech_cache import pin_farewell, wav_info
from agent_core import main as core


class CacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'spool.wav'
        with wave.open(str(self.source),'wb') as wav:
            wav.setparams((1,2,16000,0,'NONE','none'))
            wav.writeframes(b'\1\0'*1600)

    async def test_pruned_spool_does_not_remove_pinned_farewell(self):
        pinned=pin_farewell(self.root/'cache','再见。',{'audioPath':str(self.source)})
        self.source.unlink()
        self.assertEqual(wav_info(Path(pinned['audioPath']))['durationMs'],100)

    async def test_bad_new_audio_cannot_overwrite_good_cache(self):
        pinned=pin_farewell(self.root/'cache','再见。',{'audioPath':str(self.source)})
        self.source.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            pin_farewell(self.root/'cache','再见。',{'audioPath':str(self.source)})
        self.assertEqual(wav_info(Path(pinned['audioPath']))['durationMs'],100)
        self.assertEqual(len(list((self.root/'cache').iterdir())),1)

    async def test_truncated_wav_rejected(self):
        raw=self.source.read_bytes()
        self.source.write_bytes(raw[:len(raw)//2])
        with self.assertRaises(ValueError):
            wav_info(self.source)

    async def test_precache_pins_and_sends_each_line_to_avatar(self):
        hub=SimpleNamespace(role_count=lambda role:1,send_roles=AsyncMock())
        manager=SimpleNamespace(client=SimpleNamespace(synthesize=lambda *a:{'audioPath':str(self.source)}),speed=1)
        with patch.multiple(core,TTS_ENABLED=True,hub=hub,memory=MagicMock(),speech_manager=manager,
                            FAREWELL_LINES=('再见。',),FAREWELL_AUDIO_CACHE={},_farewell_precaching=False), \
                patch.object(core,'default_data_dir',return_value=self.root):
            await core._precache_farewell_audio()
            data=hub.send_roles.call_args.args[1]
            self.assertEqual(data['type'],'avatar.farewell.cache')
            self.assertNotEqual(data['audioPath'],str(self.source))
            self.assertFalse(core._farewell_precaching)
