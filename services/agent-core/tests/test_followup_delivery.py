"""Reproducible ALLOW-path exceptions must reach task delivery, not just AgentStep."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from agent_core.result_pages import ResultPages
import test_harness_v1_integration as fixtures


class FollowupDeliveryTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.MainActionTests.setUp

    async def run_failure(self, name, arguments, execute=None):
        replies = [
            {"tool_calls": [{"id": "synthetic", "name": name, "arguments": arguments}],
             "raw": {"role": "assistant", "content": None, "tool_calls": []}},
            {"content": '{"reply":"全部操作已经成功完成"}', "tool_calls": []},
        ]
        provider = SimpleNamespace(complete_with_tools=AsyncMock(side_effect=replies),
                                   complete=AsyncMock(return_value='{"reply":"全部操作已经成功完成"}'))
        with patch.object(core, "provider", provider), patch.object(core, "tools_schema", [
                {"type":"function", "function":{"name": name, "parameters":{"type":"object"}}}]):
            if execute is None:
                await core.handle_chat("请调用工具执行这项合成操作", "followup-error", self.sid)
            else:
                with patch.object(core, "_execute_authorized_tool", execute):
                    await core.handle_chat("请调用工具执行这项合成操作", "followup-error", self.sid)
        task = core._task_state[self.sid]
        answer = self.store.load_messages(20, self.sid)[-1]["content"]
        self.assertNotIn("全部操作已经成功完成", answer)
        self.assertTrue(task["tool_failures"])
        self.assertEqual(task["tool_results"][0]["request_id"], "followup-error")
        self.assertEqual(task["tool_results"][0]["task_id"], task["id"])
        self.assertFalse(core._sync_pending(self.sid))
        return task, answer

    async def test_invalid_result_reference_is_saved_and_delivered(self):
        task, answer = await self.run_failure("read_tool_result", {"ref": [], "offset": 0})
        self.assertEqual(task["tool_results"][0]["result"]["outcome"], "failed")
        self.assertIn("ref",task["tool_results"][0]["result"]["error"])
        self.assertNotIn("ref",answer)
        self.assertIn("失败",answer)

    async def test_allowed_executor_exception_retains_unknown_without_success_prose(self):
        task, answer = await self.run_failure("get_time", {}, AsyncMock(side_effect=RuntimeError("synthetic")))
        self.assertEqual(task["tool_results"][0]["result"]["outcome"], "unknown")
        self.assertIn("结果未知", answer)

    def test_result_reference_types_fail_without_throwing(self):
        pages = ResultPages()
        for ref in ([], {}, None, 1, True):
            with self.subTest(ref=ref):
                self.assertFalse(pages.read(ref)["ok"])

    def test_result_tail_and_offset_checks_remain(self):
        pages = ResultPages()
        first = pages.pack({"ok": True, "content": "x"*8000+"TAIL-175"})
        ref = first["ref"]
        self.assertIn("TAIL-175", pages.read(ref, first["total_chars"]-50)["content"])
        for offset in (-1, True, [], "0", first["total_chars"]+1):
            self.assertFalse(pages.read(ref, offset)["ok"])
        self.assertNotIn(ref, ResultPages().items)
