"""zcode (2026-09-09): wake-path AGC — Realtek half-wedge (30-100x gain drop)
must not starve the KWS. Pure-math tests; numpy guarded for CI."""
from __future__ import annotations

import unittest

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False

from agent_core.wake_word import WakeWordListener


class AgcMathTests(unittest.TestCase):
    def _boost(self, samples, ema=0.0):
        return WakeWordListener._agc_math(samples, ema)

    @unittest.skipUnless(_HAS_NUMPY, "numpy not installed")
    def test_quiet_signal_boosted_to_target(self):
        quiet = np.full(1600, 0.005, dtype="float32")  # rms 0.005
        boosted, ema = self._boost(quiet, 0.005)
        self.assertAlmostEqual(float(np.sqrt(np.mean(boosted**2))), 0.05, delta=0.01)

    @unittest.skipUnless(_HAS_NUMPY, "numpy not installed")
    def test_loud_signal_not_attenuated(self):
        loud = np.full(1600, 0.4, dtype="float32")  # rms 0.4 >> target
        boosted, ema = self._boost(loud, 0.4)
        self.assertAlmostEqual(float(np.max(np.abs(boosted))), 0.4, places=3)  # gain floors at 1.0

    @unittest.skipUnless(_HAS_NUMPY, "numpy not installed")
    def test_digital_zeros_stay_zeros(self):
        zeros = np.zeros(1600, dtype="float32")
        boosted, ema = self._boost(zeros, 0.0)
        self.assertEqual(float(np.max(np.abs(boosted))), 0.0)  # wedge watchdog still sees silence

    @unittest.skipUnless(_HAS_NUMPY, "numpy not installed")
    def test_boost_capped_at_max_gain(self):
        tiny = np.full(1600, 1e-5, dtype="float32")
        boosted, ema = self._boost(tiny, 1e-5)
        self.assertLessEqual(float(np.max(np.abs(boosted))), 1e-5 * 50.0 + 1e-6)
