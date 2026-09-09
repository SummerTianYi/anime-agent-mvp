from __future__ import annotations

import unittest

from agent_core.main import (
    DEFAULT_EFFORT,
    EFFORT_LEVELS,
    MAX_TOOL_STEPS,
    effective_tools_for_effort,
    resolve_effort,
)


def _schema(*names: str) -> list:
    return [{"type": "function", "function": {"name": name}} for name in names]


READONLY_SAMPLE = ("get_time", "read_file", "list_dir", "screenshot", "active_window", "clipboard_read")
WRITE_SAMPLE = ("write_file", "run_command", "look_at_screen")
MCP_SAMPLE = [{"type": "function", "function": {"name": "mcp__github__get_me"}}]


class ResolveEffortTest(unittest.TestCase):
    def test_default_is_deep(self) -> None:
        self.assertEqual(DEFAULT_EFFORT, "deep")
        self.assertEqual(resolve_effort(None), "deep")
        self.assertEqual(resolve_effort(""), "deep")

    def test_unknown_value_falls_back_to_deep(self) -> None:
        self.assertEqual(resolve_effort("turbo"), "deep")
        self.assertEqual(resolve_effort(123), "deep")

    def test_known_values_pass_through_case_insensitive(self) -> None:
        self.assertEqual(resolve_effort("chill"), "chill")
        self.assertEqual(resolve_effort("  STANDARD  "), "standard")

    def test_deep_keeps_historical_loop_budget(self) -> None:
        self.assertEqual(EFFORT_LEVELS["deep"]["max_steps"], MAX_TOOL_STEPS)
        self.assertEqual(EFFORT_LEVELS["deep"]["tools"], "all")


class EffectiveToolsForEffortTest(unittest.TestCase):
    def _base(self) -> list:
        return _schema(*READONLY_SAMPLE, *WRITE_SAMPLE)

    def test_chill_sends_no_tools(self) -> None:
        self.assertEqual(effective_tools_for_effort(self._base(), MCP_SAMPLE, "chill"), [])

    def test_standard_keeps_only_readonly_tools(self) -> None:
        tools = effective_tools_for_effort(self._base(), MCP_SAMPLE, "standard")
        names = [t["function"]["name"] for t in tools]
        self.assertEqual(sorted(names), sorted(READONLY_SAMPLE))

    def test_deep_keeps_full_registry_plus_mcp(self) -> None:
        tools = effective_tools_for_effort(self._base(), MCP_SAMPLE, "deep")
        names = [t["function"]["name"] for t in tools]
        for name in READONLY_SAMPLE:
            self.assertIn(name, names)
        for name in WRITE_SAMPLE:
            self.assertIn(name, names)
        self.assertIn("mcp__github__get_me", names)


if __name__ == "__main__":
    unittest.main()
