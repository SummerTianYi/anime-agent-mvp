"""Offline boundary checks for the owner's 01:00–07:00 configuration."""
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/agent-core"))
from agent_core.proactive import IdlePolicy, ProactivePolicy

checks = []
for h, m, expected in [(0, 59, False), (1, 0, True), (6, 59, True), (7, 0, False), (23, 0, False)]:
    now = time.struct_time((2026, 10, 5, h, m, 0, 0, 0, 0))
    quiet = ProactivePolicy(quiet_start="01:00", quiet_end="07:00").in_quiet_hours(now)
    idle, reason = IdlePolicy(quiet_start="01:00", quiet_end="07:00").decide(600, now, 1600)
    assert quiet == expected and idle == (not expected)
    checks.append(dict(time=f"{h:02}:{m:02}", quiet=quiet, idle_600_allowed=idle, reason=reason, passed=True))
record = dict(quiet_start="01:00", quiet_end="07:00", checks=checks,
              real_10_minute_test=False, llm_calls=0, passed=True)
out = ROOT / "docs/assessments/harness-v1/evidence/quiet-hours.json"
out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(record, ensure_ascii=False))
