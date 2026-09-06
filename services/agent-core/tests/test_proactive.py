"""zcode (D 期): proactive policy tests — quiet hours, cooldown."""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.proactive import ProactivePolicy  # noqa: E402


class ProactivePolicyTests(unittest.TestCase):
    def test_quiet_hours_overnight_window(self):
        policy = ProactivePolicy(quiet_start="23:00", quiet_end="08:00")
        late = time.struct_time((2026, 9, 6, 23, 30, 0, 0, 0, 0))
        early = time.struct_time((2026, 9, 6, 7, 30, 0, 0, 0, 0))
        day = time.struct_time((2026, 9, 6, 14, 0, 0, 0, 0, 0))
        self.assertTrue(policy.in_quiet_hours(late))
        self.assertTrue(policy.in_quiet_hours(early))
        self.assertFalse(policy.in_quiet_hours(day))

    def test_cooldown_blocks_repeat(self):
        policy = ProactivePolicy(cooldown_seconds=1800)
        now = 1000.0
        policy.mark_spoken(now - 3600)  # 模拟很久之前说过话
        allowed, reason = policy.allow(day_time(), monotonic=now)
        self.assertTrue(allowed)
        policy.mark_spoken(now)
        allowed, reason = policy.allow(day_time(), monotonic=now + 600)
        self.assertFalse(allowed)
        self.assertEqual(reason, "cooldown")

    def test_allow_after_cooldown(self):
        policy = ProactivePolicy(cooldown_seconds=1800)
        now = 1000.0
        policy.mark_spoken(now)
        allowed, _ = policy.allow(day_time(), monotonic=now + 1801)
        self.assertTrue(allowed)


def day_time():
    return time.struct_time((2026, 9, 6, 14, 0, 0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
