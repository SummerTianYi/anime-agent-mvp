"""A4 Core entry regressions, including preserved historical model failures."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core
import test_harness_v1_integration as fixture


def final(text, mode="chat", **decision):
    return {"content": json.dumps({"reply": text, "decision": {"mode": mode, **decision}}, ensure_ascii=False)}


def call(name, **args):
    return {"tool_calls": [{"id": "a4-call", "name": name, "arguments": args}]}


class A4PilotTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixture.MainActionTests.setUp
    proposal = fixture.MainActionTests.proposal

    async def chat_with(self, turns, text="修改合成Issue标题", request="a4", execute=None):
        provider = SimpleNamespace(complete_with_tools=AsyncMock(side_effect=turns),
            complete=AsyncMock(return_value='{"reply":"这段旧自由回答不能作为交付"}'))
        schema = [{"type": "function", "function": {"name": "get_time", "parameters": {"type": "object"}}},
                  {"type": "function", "function": {"name": "write_file", "parameters": {
                      "type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["path", "content"]}}}]
        with patch.object(core, "provider", provider), patch.object(core, "tools_schema", schema):
            if execute is None:
                await core.handle_chat(text, request, self.sid, effort="standard")
            else:
                with patch.object(core, "_execute_authorized_tool", execute):
                    await core.handle_chat(text, request, self.sid, effort="standard")
        return self.store.load_messages(100, self.sid)[-1]["content"], provider

    async def test_historical_glm_no_call_failures_do_not_make_fake_pending(self):
        path = Path(__file__).resolve().parents[3] / "docs/assessments/root-cause-repair/batch-01/evidence/followup-models.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = [c for c in data["cases"] if c["model"] == "GLM-5.2" and c["scenario"] == "operation"][:2]
        for index, case in enumerate(cases):
            raw = next(c["response"]["content"] for c in data["calls"] if c["request_id"] == case["turns"][0]["request_id"])
            answer, provider = await self.chat_with([{"content": raw}]*2, request=f"historical-{index}")
            self.assertNotIn("确认后我就", answer)
            self.assertIn("尚未完成", answer)
            self.assertFalse(core._sync_pending(self.sid))
            self.assertEqual(provider.complete_with_tools.await_count, 2)

    async def test_single_correction_can_form_real_ticket_then_complete(self):
        path = str(self.root / "a4.txt")
        answer, provider = await self.chat_with([final("我等你确认", "act"), call("write_file", path=path, content="A4-175")])
        self.assertIn("待确认", answer)
        self.assertFalse(Path(path).exists())
        self.assertEqual(provider.complete.await_count, 0)
        task = core._task_state[self.sid]
        self.assertEqual(task["corrections_used"], 1)
        aid = core._sync_pending(self.sid)[0]["action_id"]
        answer, _ = await self.chat_with([final("伪造的附加完成不要展示", "report", action_refs=[aid])], "确认", "confirm")
        self.assertEqual(Path(path).read_text(encoding="utf-8"), "A4-175")
        self.assertIn("执行成功", answer)
        self.assertNotIn("伪造", answer)
        answer, p = await self.chat_with([], "确认", "confirm-again")
        self.assertIn("没有待确认", answer)
        self.assertEqual(p.complete_with_tools.await_count, 0)
        self.assertIs(task, core._task_state[self.sid])

    async def test_act_cannot_escape_to_chat_during_correction(self):
        answer, _ = await self.chat_with([final("", "act"), final("已经写入，完成了")])
        self.assertIn("尚未完成", answer)
        self.assertNotIn("已经写入", answer)
        self.assertFalse(core._actions().records)

    async def test_continue_keeps_goal_budget_and_one_correction(self):
        await self.chat_with([final("", "act")]*2)
        task = core._task_state[self.sid]
        before = task["rounds_used"]
        answer, provider = await self.chat_with([final("", "act")], "继续", "continue")
        self.assertIs(task, core._task_state[self.sid])
        self.assertEqual(task["intent"], "修改合成Issue标题")
        self.assertEqual(task["rounds_used"], before+1)
        self.assertEqual(provider.complete_with_tools.await_count, 1)
        self.assertEqual(task["corrections_used"], 1)
        self.assertIn("尚未完成", answer)

    async def test_read_then_legacy_false_write_not_delivered(self):
        raw = '{"reply":"只读结果合计175；我还把标题改好了。"}'
        answer, _ = await self.chat_with([call("get_time"), {"content": raw}, {"content": raw}],
            execute=AsyncMock(return_value={"ok": True, "output": "合计175"}))
        self.assertNotIn("标题改好了", answer)
        self.assertFalse(core._actions().records)

    async def test_full_sourced_summary_is_preserved(self):
        summary = "材料分为准备、执行和核验三部分。" + "资料正文与分析。"*1000 + "总数175。"
        answer, _ = await self.chat_with([call("get_time"), final(summary, "report", read_refs=["summary:read:1"])],
            text="总结资料", request="summary", execute=AsyncMock(return_value={"ok": True, "output": summary}))
        self.assertEqual(answer, summary)
        self.assertIn("总数175", answer)

    async def test_wrong_or_cross_task_reference_is_not_evidence(self):
        for ref in ("fabricated", "old-task:read:1"):
            answer, _ = await self.chat_with([final("已经完成", "report", read_refs=[ref])]*2, request=ref)
            self.assertNotIn("已经完成", answer)
            self.assertIn("尚未完成", answer)

    async def test_failed_and_cross_session_action_reference_cannot_supply_success(self):
        other = core._actions().propose(self.sid+1, "foreign", "r", "write_file", {"path": str(self.root/"foreign"), "content": "x"})
        answer, _ = await self.chat_with([final("已经成功", "report", action_refs=[other["action_id"]])]*2)
        self.assertNotIn("已经成功", answer)
        self.assertIn("尚未完成", answer)

    async def test_plain_chat_and_confirmation_explanation(self):
        for text in ("晚上好，我是天依。", "“确认后执行”是流程说明；实际完成需要执行回执。"):
            answer, provider = await self.chat_with([final(text)], text="聊聊天并解释确认流程", request=text[:4])
            self.assertEqual(answer, text)
            self.assertEqual(provider.complete_with_tools.await_count, 1)
            self.assertFalse(core._sync_pending(self.sid))

    async def test_missing_parameters_use_schema_and_no_ticket(self):
        answer, _ = await self.chat_with([final("我已经写好了", "clarify", tool="write_file", arguments={}, missing=["path", "content"])], text="我想写文件但未提供路径和内容")
        self.assertIn("path", answer)
        self.assertIn("content", answer)
        self.assertNotIn("已经写好了", answer)
        self.assertFalse(core._actions().records)

    async def test_fake_missing_field_cannot_escape_to_clarification(self):
        answer, _ = await self.chat_with([final("全部完成", "clarify", tool="write_file", arguments={}, missing=["fake_success"]) ]*2)
        self.assertIn("尚未完成", answer)
        self.assertNotIn("全部完成", answer)

    async def test_invalid_mode_is_corrected_without_crashing(self):
        answer, provider = await self.chat_with([final("bad", mode=[]), final("晚上好")], text="晚上好")
        self.assertEqual(answer, "晚上好")
        self.assertEqual(provider.complete_with_tools.await_count, 2)

    async def test_act_can_correct_to_required_clarification(self):
        answer, _ = await self.chat_with([final("", "act"), final("", "clarify", tool="write_file", arguments={}, missing=["path", "content"])])
        self.assertIn("path", answer)
        self.assertFalse(core._actions().records)

    async def test_invalid_proposal_corrects_without_creating_ticket(self):
        answer, provider = await self.chat_with([call("write_file", path=""), final("", "clarify", tool="write_file", arguments={}, missing=["path", "content"])])
        self.assertIn("path", answer)
        self.assertEqual(provider.complete_with_tools.await_count, 2)
        self.assertFalse(core._actions().records)

    async def test_repeated_invalid_proposals_stop_after_one_correction(self):
        answer, provider = await self.chat_with([call("write_file", path="", content="x")]*2)
        self.assertIn("尚未完成", answer)
        self.assertEqual(provider.complete_with_tools.await_count, 2)
        self.assertFalse(core._actions().records)

    async def test_budget_exhaustion_delivers_nonempty_incomplete(self):
        await self.chat_with([final("", "act")]*2)
        task = core._task_state[self.sid]
        task["rounds_used"] = task["budget"]["max_steps"]
        answer, provider = await self.chat_with([], text="继续", request="exhausted")
        self.assertIn("尚未完成", answer)
        self.assertEqual(provider.complete_with_tools.await_count, 0)

    async def test_unknown_receipt_and_failed_followup_are_not_reexecuted(self):
        await self.proposal("unknown.txt", "x")
        with patch.object(core, "_execute_authorized_tool", AsyncMock(side_effect=TimeoutError("lost"))) as execute:
            answer, _ = await self.chat_with([core.ProviderError("failed supplementary answer")], "确认", "unknown")
            self.assertIn("结果未知", answer)
            self.assertEqual(execute.await_count, 1)
            await self.chat_with([], "确认", "unknown-again")
            self.assertEqual(execute.await_count, 1)

    async def test_denial_does_not_leak_model_completion(self):
        answer, _ = await self.chat_with([call("write_file", path="Z:/denied/a4.txt", content="x"), final("完成了"), final("完成了")])
        self.assertNotIn("完成了", answer)
        self.assertIn("权限拒绝", answer)

    async def test_cancel_and_change_keep_ticket_version_checks(self):
        first = await self.proposal("edit.txt", "old")
        await self.chat_with([final("取消已完成")], "取消旧的，改成新版", "edit")
        second = await self.proposal("edit.txt", "new")
        with patch.object(core, "provider", SimpleNamespace(complete=AsyncMock(return_value=""))):
            await core.handle_chat("确认", "stale", self.sid, confirmation=first["confirmation"])
        self.assertFalse((self.root/"edit.txt").exists())
        answer, _ = await self.chat_with([final("", "report", action_refs=[second["action_id"]])], "确认", "fresh")
        self.assertEqual((self.root/"edit.txt").read_text(encoding="utf-8"), "new")
        self.assertIn("执行成功", answer)
