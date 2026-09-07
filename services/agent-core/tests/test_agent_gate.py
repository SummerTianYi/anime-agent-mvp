"""zcode (phase B 前置): agent loop permission-gate integration tests.

Uses a fake provider so the whole loop runs offline: one turn that requests
tools, then a final plain answer.
"""
from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.agent_loop import run_agent_loop  # noqa: E402
from agent_core.permissions import ActionRequest, PermissionEngine  # noqa: E402

SCHEMA = [
    {"type": "function", "function": {
        "name": "get_time",
        "description": "time",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "dangerous",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    }},
]


class FakeProvider:
    def __init__(self, calls):
        self.calls = calls
        self.round = 0

    async def complete_with_tools(self, messages, tools_schema):
        self.round += 1
        if self.round == 1:
            return {"tool_calls": [{"id": f"c{self.round}", "name": self.calls[0][0],
                                    "arguments": self.calls[0][1]}], "raw": {"role": "assistant", "content": None}}
        return {"tool_calls": [], "content": "好的，已完成。"}

    async def complete(self, messages):
        return "好的，已完成。"


def gate(engine):
    return lambda name, arguments: engine.evaluate(
        ActionRequest(tool=name, arguments=arguments, origin="agent", session_id=1)
    )


def run(coro):
    return asyncio.run(coro)


class GateIntegrationTests(unittest.TestCase):
    def test_allowed_tool_executes_and_returns_final_answer(self):
        provider = FakeProvider([("get_time", {})])
        executed = []

        async def executor(name, args):
            executed.append(name)
            return {"ok": True, "time": "12:00"}

        result = run(run_agent_loop(provider, [{"role": "user", "content": "现在几点"}],
                                    SCHEMA, executor, permission_gate=gate(PermissionEngine())))
        self.assertEqual(executed, ["get_time"])
        self.assertTrue(result.steps[0].ok)
        self.assertEqual(result.text, "好的，已完成。")

    def test_denied_tool_never_reaches_executor_and_reports_back(self):
        provider = FakeProvider([("write_file", {"path": "../win.ini"})])
        executed = []

        async def executor(name, args):
            executed.append(name)
            return {"ok": True}

        result = run(run_agent_loop(provider, [{"role": "user", "content": "删了它"}],
                                    SCHEMA, executor, permission_gate=gate(PermissionEngine())))
        self.assertEqual(executed, [])  # executor never called
        self.assertFalse(result.steps[0].ok)
        self.assertIn("权限拒绝", result.steps[0].summary)
        self.assertIn("path-safety", result.steps[0].summary)  # traversal in arguments
        # absolute path (no traversal) would instead be default-deny: write
        # tools ship in phase B with explicit rules
        self.assertEqual(result.text, "好的，已完成。")

    def test_broken_gate_fails_closed(self):
        provider = FakeProvider([("get_time", {})])
        executed = []

        async def executor(name, args):
            executed.append(name)
            return {"ok": True}

        def broken_gate(name, arguments):
            raise RuntimeError("gate exploded")

        result = run(run_agent_loop(provider, [{"role": "user", "content": "现在几点"}],
                                    SCHEMA, executor, permission_gate=broken_gate))
        self.assertEqual(executed, [])  # fail closed: never execute
        self.assertFalse(result.steps[0].ok)

    def test_ask_decision_parks_call_without_execution(self):
        import os
        from unittest import mock
        tmproot = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmproot, ignore_errors=True))
        patcher = mock.patch.dict(os.environ, {"ANIME_AGENT_WRITE_ROOTS": tmproot})
        patcher.start()
        self.addCleanup(patcher.stop)
        provider = FakeProvider([("write_file", {"path": tmproot + "/note.txt", "content": "hi"})])
        executed = []

        async def executor(name, args):
            executed.append(name)
            return {"ok": True}

        result = run(run_agent_loop(provider, [{"role": "user", "content": "写一下"}],
                                    SCHEMA, executor, permission_gate=gate(PermissionEngine())))
        self.assertEqual(executed, [])  # ask tier never executes directly
        self.assertFalse(result.steps[0].ok)
        self.assertIn("写入工具需用户确认", result.steps[0].summary)

    def test_loop_without_gate_keeps_baseline_behavior(self):
        provider = FakeProvider([("get_time", {})])
        executed = []

        async def executor(name, args):
            executed.append(name)
            return {"ok": True}

        result = run(run_agent_loop(provider, [{"role": "user", "content": "现在几点"}],
                                    SCHEMA, executor))
        self.assertEqual(executed, ["get_time"])


if __name__ == "__main__":
    unittest.main()


# zcode (2026-09-07, T-MCP 验收考出): the one-shot confirm flag was session-
# scoped, so after confirming tool A the NEXT unrelated ask-tier tool B got a
# data-less "already executed" receipt instead of its own ask flow. The flag
# must be scoped to the tool name.
class OneShotFlagScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        import agent_core.main as core

        self.core = core
        core._confirmed_write_once.clear()
        self.addCleanup(core._confirmed_write_once.clear)
        self._session = core._ACTIVE_CHAT_SESSION_ID[0]
        core._ACTIVE_CHAT_SESSION_ID[0] = 5
        self.addCleanup(self.core._ACTIVE_CHAT_SESSION_ID.__setitem__, 0, self._session)

    def test_flag_does_not_leak_to_unrelated_tool(self) -> None:
        self.core._confirmed_write_once[5] = "write_file"
        result = run(self.core.run_tool("mcp__github__get_me", {}))
        self.assertNotIn("already_executed", result)
        self.assertTrue(result.get("needs_confirmation"))

    def test_flag_consumed_by_same_tool_retry(self) -> None:
        self.core._confirmed_write_once[5] = "look_at_screen"
        result = run(self.core.run_tool("look_at_screen", {}))
        self.assertTrue(result.get("already_executed"))
        self.assertNotIn(5, self.core._confirmed_write_once)  # consumed exactly once
