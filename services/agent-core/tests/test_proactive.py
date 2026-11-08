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


# zcode (2026-09-07): idle trigger policy (D 期收尾) — pure local logic, no LLM.
from agent_core.proactive import IdlePolicy  # noqa: E402


class IdlePolicyTests(unittest.TestCase):
    def test_startup_preserves_idle_opt_out_and_fixed_v1_interval(self):
        import os
        from unittest.mock import patch
        from agent_core import main as core

        for setting, enabled in (("0", False), ("0.0", False), ("-1", False),
                                 ("600", True), ("1200", True), ("invalid", True)):
            with self.subTest(setting=setting), patch.dict(os.environ, ANIME_AGENT_IDLE_THRESHOLD=setting), \
                    patch.object(core, "TTS_ENABLED", True), patch.object(core.threading, "Thread") as worker, \
                    patch.object(core.asyncio, "get_event_loop"), patch.object(core.memory, "add_event") as record:
                core._start_idle_watch()
                if enabled:
                    worker.return_value.start.assert_called_once()
                    self.assertEqual(record.call_args.args[0], "proactive.idle.enabled")
                    self.assertEqual(record.call_args.args[1]["threshold"], 600.0)
                else:
                    worker.assert_not_called()
                    record.assert_called_once_with("proactive.idle.disabled", {})

    def test_not_idle_is_ignored_before_anything_else(self):
        policy = IdlePolicy(threshold_seconds=600.0)
        allowed, reason = policy.decide(idle_seconds=10.0, monotonic=0.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "not-idle")

    def test_idle_but_quiet_hours_ignored(self):
        policy = IdlePolicy(threshold_seconds=600.0, quiet_start="23:00", quiet_end="08:00")
        allowed, reason = policy.decide(idle_seconds=3600.0, now=late_time(), monotonic=0.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "quiet-hours")

    def test_same_idle_episode_never_repeats(self):
        policy = IdlePolicy(threshold_seconds=600.0, cooldown_seconds=300.0)
        policy.mark_spoken(monotonic=0.0)
        allowed, reason = policy.decide(idle_seconds=3600.0, now=day_time(), monotonic=100.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "already-reminded-this-idle")

    def test_new_episode_resets_even_inside_old_cooldown(self):
        policy = IdlePolicy(threshold_seconds=600.0, cooldown_seconds=300.0)
        policy.decide(idle_seconds=600, now=day_time(), monotonic=600)
        policy.mark_spoken(monotonic=600)
        policy.decide(idle_seconds=0, now=day_time(), monotonic=601)
        allowed, reason = policy.decide(idle_seconds=600, now=day_time(), monotonic=1201)
        self.assertTrue(allowed)
        self.assertEqual(reason, "")


def late_time():
    return time.struct_time((2026, 9, 6, 23, 30, 0, 0, 0, 0))
