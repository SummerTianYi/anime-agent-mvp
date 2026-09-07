"""zcode (2026-09-07): Realtek driver-wedge self-heal — digital-zero detection,
one automatic device reopen, actionable error. KI-001 hardening."""
from __future__ import annotations

import unittest

import numpy as np

from agent_core.voice import (
    _WEDGE_LSB_THRESHOLD,
    VoiceError,
    VoiceRecorder,
    _is_driver_wedge,
)


class WedgeThresholdTests(unittest.TestCase):
    def test_digital_zeros_are_a_wedge(self) -> None:
        self.assertTrue(_is_driver_wedge(0.0))

    def test_sub_lsb_noise_floor_is_still_a_wedge(self) -> None:
        self.assertTrue(_is_driver_wedge(1.0 / 32767.0))

    def test_real_noise_floor_is_not_a_wedge(self) -> None:
        self.assertFalse(_is_driver_wedge(50.0 / 32767.0))

    def test_threshold_is_tiny_by_design(self) -> None:
        self.assertLessEqual(_WEDGE_LSB_THRESHOLD, 4.0)


class _DummyStream:
    def __init__(self) -> None:
        self.closed = False

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class RecorderWedgeTests(unittest.TestCase):
    def _recorder(self, amplitude: float, frames: int = 1600) -> VoiceRecorder:
        recorder = VoiceRecorder()
        recorder._numpy = np
        rng = np.random.default_rng(7)
        data = rng.normal(0.0, amplitude, size=(frames, 1)).astype("float32")
        if amplitude == 0.0:
            data = np.zeros((frames, 1), dtype="float32")
        recorder._samples = [data]
        recorder._stream = _DummyStream()
        return recorder

    def test_all_zero_recording_resets_device_once_and_raises_actionable_error(self) -> None:
        recorder = self._recorder(0.0)
        resets: list[bool] = []
        recorder._attempt_device_reset = lambda sd=None: (resets.append(True), True)[1]
        with self.assertRaises(VoiceError) as ctx:
            recorder.stop()
        self.assertEqual(len(resets), 1)
        message = str(ctx.exception)
        self.assertIn("假死", message)
        self.assertIn("再", message)  # actionable: ask the user to retry
        self.assertIn("静音", message)  # external reset hint from the known trap

    def test_normal_recording_returns_wav_and_does_not_reset(self) -> None:
        recorder = self._recorder(0.05)
        resets: list[bool] = []
        recorder._attempt_device_reset = lambda sd=None: (resets.append(True), True)[1]
        wav = recorder.stop()
        self.assertEqual(resets, [])
        self.assertTrue(wav[:4] == b"RIFF")

    def test_device_reset_helper_reports_failure(self) -> None:
        class Boom:
            class InputStream:  # noqa: N801 - mirrors sounddevice usage
                def __init__(self, *args, **kwargs):
                    raise RuntimeError("driver gone")

        self.assertFalse(VoiceRecorder()._attempt_device_reset(Boom))

    def test_device_reset_helper_opens_and_closes_probe(self) -> None:
        events: list[str] = []

        class OkStream:
            def __init__(self, *args, **kwargs):
                events.append("open")

            def start(self):
                events.append("start")

            def stop(self):
                events.append("stop")

            def close(self):
                events.append("close")

        class Ok:
            InputStream = OkStream

        self.assertTrue(VoiceRecorder()._attempt_device_reset(Ok))
        self.assertEqual(events, ["open", "start", "stop", "close"])
