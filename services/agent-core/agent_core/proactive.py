"""zcode (D 期): proactive trigger policy — quiet hours, cooldown, debounce.

Pure policy logic, unit-testable offline. The runtime asks this module
whether a proactive line is allowed right now; it never speaks on its own.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


def _parse_hhmm(text: str) -> tuple[int, int]:
    hours, minutes = text.split(":")
    return int(hours), int(minutes)


@dataclass
class ProactivePolicy:
    quiet_start: str = "23:00"   # 免打扰开始
    quiet_end: str = "08:00"     # 免打扰结束
    cooldown_seconds: float = 1800.0  # 两条主动发言的最小间隔
    _last_spoken: float = field(default=0.0)

    def in_quiet_hours(self, now: time.struct_time | None = None) -> bool:
        now = now or time.localtime()
        minutes_now = now.tm_hour * 60 + now.tm_min
        start_h, start_m = _parse_hhmm(self.quiet_start)
        end_h, end_m = _parse_hhmm(self.quiet_end)
        minutes_start, minutes_end = start_h * 60 + start_m, end_h * 60 + end_m
        if minutes_start <= minutes_end:
            return minutes_start <= minutes_now < minutes_end
        # overnight window (e.g. 23:00 -> 08:00)
        return minutes_now >= minutes_start or minutes_now < minutes_end

    def on_cooldown(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return (now - self._last_spoken) < self.cooldown_seconds

    def allow(self, now: time.struct_time | None = None, monotonic: float | None = None) -> tuple[bool, str]:
        if self.in_quiet_hours(now):
            return False, "quiet-hours"
        if self.on_cooldown(monotonic if monotonic is not None else time.time()):
            return False, "cooldown"
        return True, ""

    def mark_spoken(self, monotonic: float | None = None) -> None:
        self._last_spoken = monotonic if monotonic is not None else time.time()


@dataclass
class IdlePolicy:
    """Idle-trigger gate (D 期收尾): speak only after real user inactivity,
    never during quiet hours, never twice within the cooldown. Pure local
    logic — no provider involvement (zero-quota guarantee)."""

    threshold_seconds: float = 2700.0
    quiet_start: str = "23:00"
    quiet_end: str = "08:00"
    cooldown_seconds: float = 3600.0
    _last_spoken: float = field(default=0.0)

    def decide(
        self,
        idle_seconds: float,
        now: time.struct_time | None = None,
        monotonic: float | None = None,
    ) -> tuple[bool, str]:
        if idle_seconds < self.threshold_seconds:
            return False, "not-idle"
        if self.in_quiet_hours(now):
            return False, "quiet-hours"
        if self.on_cooldown(time.time() if monotonic is None else monotonic):
            return False, "cooldown"
        return True, ""

    def in_quiet_hours(self, now: time.struct_time | None = None) -> bool:
        return ProactivePolicy(quiet_start=self.quiet_start, quiet_end=self.quiet_end).in_quiet_hours(now)

    def on_cooldown(self, monotonic: float | None = None) -> bool:
        return (time.time() if monotonic is None else monotonic) - self._last_spoken < self.cooldown_seconds

    def mark_spoken(self, monotonic: float | None = None) -> None:
        self._last_spoken = monotonic if monotonic is not None else time.time()
