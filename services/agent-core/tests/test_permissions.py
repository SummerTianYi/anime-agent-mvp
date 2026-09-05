"""zcode (phase B 前置): permission engine tests — deny-by-default contract."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.permissions import (  # noqa: E402
    ActionRequest,
    PermissionEngine,
    PolicyRule,
)


def make_engine(rules=None) -> PermissionEngine:
    return PermissionEngine(rules=rules)


def request(tool="read_file", arguments=None, origin="agent"):
    return ActionRequest(tool=tool, arguments=arguments or {}, origin=origin, session_id=1)


class DefaultPolicyTests(unittest.TestCase):
    def test_readonly_tools_allowed_by_default(self):
        engine = make_engine()
        for tool in ("get_time", "read_file", "list_dir", "screenshot", "active_window", "clipboard_read"):
            self.assertTrue(engine.evaluate(request(tool=tool)).allowed, tool)

    def test_unknown_tool_default_denied_with_rule_id(self):
        decision = make_engine().evaluate(request(tool="delete_file"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rule_id, "default-deny")

    def test_write_tool_not_in_registry_denied(self):
        decision = make_engine().evaluate(request(tool="write_file"))
        self.assertFalse(decision.allowed)


class PathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(
            rules=[PolicyRule(rule_id="allow-read", match_tool="read_file", match_origin="*", decision=True)]
        )

    def test_relative_escape_denied_despite_allow_rule(self):
        decision = self.engine.evaluate(request(arguments={"path": "../secrets.env"}))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rule_id, "path-safety")

    def test_absolute_path_denied_despite_allow_rule(self):
        for raw in ("C:/Windows/win.ini", "/etc/passwd", "~/keys"):
            decision = self.engine.evaluate(request(arguments={"path": raw}))
            self.assertFalse(decision.allowed, raw)

    def test_nested_traversal_denied(self):
        decision = self.engine.evaluate(request(arguments={"nested": {"p": "a/../b"}}))
        self.assertFalse(decision.allowed)


class AttributionTests(unittest.TestCase):
    def test_denied_decision_carries_rule_id_and_reason(self):
        decision = make_engine().evaluate(request(tool="write_file"))
        self.assertEqual(decision.rule_id, "default-deny")
        self.assertTrue(decision.reason)

    def test_malformed_arguments_denied(self):
        engine = make_engine(
            rules=[PolicyRule(rule_id="allow-all", match_tool="*", match_origin="*", decision=True)]
        )
        decision = engine.evaluate(ActionRequest(tool="read_file", arguments="oops", origin="agent", session_id=1))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rule_id, "malformed-request")


if __name__ == "__main__":
    unittest.main()
