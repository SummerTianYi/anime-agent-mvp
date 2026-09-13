"""Codex: farewell correlation/failure regressions; no real sidecar or database."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agent_core import main as core
from agent_core.speech import SpeechUnavailable


class FarewellDeliveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audio = Path(self.temp.name) / "farewell.wav"
        self.audio.write_bytes(b"synthetic cached path fixture")
        self.manager = SimpleNamespace(interrupt=AsyncMock(), speak=AsyncMock(
            return_value=SimpleNamespace(has_audio=True, cancelled=False)))
        self.broadcast = AsyncMock()
        self.hub = SimpleNamespace(send_roles=AsyncMock())
        for name, value in (("TTS_ENABLED", True), ("FAREWELL_LINES", ("再见。",)),
                            ("FAREWELL_AUDIO_CACHE", {}), ("speech_manager", self.manager),
                            ("_broadcast_speak", self.broadcast), ("hub", self.hub),
                            ("memory", MagicMock())):
            ctx = patch.object(core, name, value)
            ctx.start()
            self.addCleanup(ctx.stop)

    async def test_disabled_voice_settles_only_matching_exit(self):
        core.TTS_ENABLED = False
        await core._deliver_farewell("exit-test")
        self.manager.speak.assert_not_awaited()
        payload = self.hub.send_roles.call_args.args[1]
        self.assertEqual((payload["type"], payload["requestId"], payload["state"]),
                         ("avatar.farewell.status", "exit-test", "unavailable"))

    async def test_cached_audio_echoes_request_and_single_part_contract(self):
        core.FAREWELL_AUDIO_CACHE["再见。"] = {"audioPath": str(self.audio), "durationMs": 6000, "sampleRate": 32000}
        await core._deliver_farewell("exit-test")
        data = self.broadcast.call_args.args[0]
        self.assertEqual((data["requestId"], data["partIndex"], data["partCount"]), ("exit-test", 0, 1))
        self.assertEqual(data["durationMs"], 6000)
        self.manager.interrupt.assert_awaited_once_with("exit")
        self.manager.speak.assert_not_awaited()

    async def test_stale_cached_path_resynthesizes_with_same_request(self):
        core.FAREWELL_AUDIO_CACHE["再见。"] = {"audioPath": str(self.audio.with_suffix(".missing"))}
        await core._deliver_farewell("exit-test")
        self.manager.speak.assert_awaited_once_with("再见。", "exit-test")
        self.broadcast.assert_not_awaited()

    async def test_synthesis_failure_explicitly_settles(self):
        self.manager.speak.side_effect = SpeechUnavailable("synthetic failure")
        await core._deliver_farewell("exit-test")
        self.assertEqual(self.hub.send_roles.call_args.args[1]["state"], "unavailable")

    async def test_no_audio_settles(self):
        self.manager.speak.return_value.has_audio = False
        await core._deliver_farewell("exit-test")
        self.hub.send_roles.assert_awaited_once()

    async def test_cancelled_audio_settles(self):
        self.manager.speak.return_value.cancelled = True
        await core._deliver_farewell("exit-test")
        self.hub.send_roles.assert_awaited_once()

    async def test_disabled_tts_never_runs_think_filler(self):
        core.TTS_ENABLED = False
        with patch.object(core, "_speak_reply", new_callable=AsyncMock) as speak, \
                patch.object(core.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            await core._maybe_speak_think_filler("test", "deep")
            speak.assert_not_awaited()
            sleep.assert_not_awaited()
