"""Codex: offline checks for append selection, wire halt and original freeze."""
import io
import unittest
import urllib.error
from email.message import Message
from unittest.mock import Mock, patch

from .budget import BudgetExceeded
from .resume_batch import blocked_slots
from .resume_worker import WireGate
from .runner import verify


class ResumeTests(unittest.TestCase):
    def test_frozen_original_unchanged(self):
        self.assertEqual(verify()["version"], "v0.1")

    def test_only_blocked_selected_and_failures_retained(self):
        rows = [{"model_tag": "ds", "case_id": str(i), "repeat": 1, "verdict": v}
                for i, v in enumerate(("PASS", "FAIL", "PARTIAL", "BLOCKED"))]
        self.assertEqual(blocked_slots(rows), [rows[3]])
        self.assertEqual(rows[1]["verdict"], "FAIL")

    def test_duplicate_slot_refused(self):
        r = {"model_tag": "ds", "case_id": "F04", "repeat": 1, "verdict": "BLOCKED"}
        with self.assertRaises(AssertionError):
            blocked_slots([r, r])

    def test_error_body_retained_and_next_wire_not_reserved(self):
        headers = Message(); headers["Retry-After"] = "60"
        error = urllib.error.HTTPError("https://synthetic.invalid", 429, "rate", headers, io.BytesIO(b'{"error":"rate"}'))
        gate = WireGate()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            gate.open(Mock(side_effect=error), None, None)
        self.assertEqual(gate.errors[0]["retry_after"], "60")
        self.assertEqual(caught.exception.read(), b'{"error":"rate"}')
        original = Mock()
        with self.assertRaises(BudgetExceeded):
            gate.reserve(original, "unused", "trial")
        original.assert_not_called()

    def test_200_not_halted(self):
        gate = WireGate()
        self.assertEqual(gate.open(Mock(return_value=b"ok"), None, None), b"ok")
        self.assertIsNone(gate.halted)

    def test_minimum_gap(self):
        gate = WireGate(); gate.last = 10
        with patch("scripts.harness_v0.resume_worker.time.monotonic", return_value=11), patch("scripts.harness_v0.resume_worker.time.sleep") as sleep:
            gate.reserve(Mock(return_value=1), "db", "trial")
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
