"""File delivery through natural-language chat, real sandbox I/O and receipts."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from agent_core.storage import MemoryStore
from agent_core.tools import openai_tools_schema
import test_harness_v1_integration as fixture
from test_a4_pilot import call, final


class FileTaskTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture.MainActionTests.setUp(self)
        core._task_state.clear()
        self.path = self.root / "different name.txt"
        self.content = "第一行：7月12日 3cm\n第二行：普通Disco 20℃"
        self.effects = []
        original = core._execute_authorized_tool

        async def execute(name, arguments):
            self.effects.append((name, dict(arguments)))
            return await original(name, arguments)

        registry = {k: v for k, v in core.tool_registry.items() if k in {"write_file", "read_file"}}
        for name, value in (("tools_schema", openai_tools_schema(registry)),
                            ("_execute_authorized_tool", execute), ("_spawn", lambda c: c.close())):
            p = patch.object(core, name, value)
            p.start()
            self.addCleanup(p.stop)

    def request(self):
        return f"请创建文件 {self.path}，写入后实际读取该文件并展示完整内容。内容如下：\n{self.content}"

    async def chat(self, text, turns, request="file-start"):
        provider = SimpleNamespace(complete_with_tools=AsyncMock(side_effect=turns))
        with patch.object(core, "provider", provider):
            await core.handle_chat(text, request, self.sid, effort="standard")
        return self.store.load_messages(100, self.sid)[-1]["content"], provider

    async def propose(self):
        answer, _ = await self.chat(self.request(), [call("write_file", path=str(self.path), content=self.content)])
        self.assertIn("待确认", answer)
        self.assertFalse(self.path.exists())
        pending = core._sync_pending(self.sid)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["arguments"], {"path": str(self.path), "content": self.content})
        return pending[0]

    async def test_confirm_requires_real_read_then_exact_content_without_extra_user_request(self):
        item = await self.propose()
        # A mutation-only report is insufficient. The same confirmation turn
        # must continue to the real read tool, within the original budget.
        answer, provider = await self.chat("确认", [
            final("完成了", "report", action_refs=[item["action_id"]]),
            call("read_file", path=str(self.path)),
            final("摘要不能替代原文", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"]),
        ], "file-confirm")
        self.assertEqual(self.path.read_bytes(), self.content.encode())
        self.assertEqual([n for n, _ in self.effects], ["write_file", "read_file"])
        self.assertIn(self.content, answer)
        self.assertNotIn("摘要不能替代", answer)
        self.assertEqual(provider.complete_with_tools.await_count, 3)
        self.assertIn("文件任务已完成", answer)
        task = core._task_state[self.sid]
        before = (task["rounds_used"], task["calls_used"])
        status, p = await self.chat("刚才那个任务现在怎么样？", [], "file-status")
        self.assertIn("执行成功", status)
        self.assertEqual(p.complete_with_tools.await_count, 0)
        await self.chat("确认", [], "file-duplicate")
        self.assertEqual([n for n, _ in self.effects].count("write_file"), 1)
        self.assertEqual(before, (task["rounds_used"], task["calls_used"]))
        reopened = MemoryStore(data_dir=self.root / "db")
        try:
            self.assertTrue(any(self.content in m["content"] for m in reopened.load_messages(100, self.sid) if m["role"] == "assistant"))
            self.assertEqual(len(reopened.load_messages(100, self.sid)), 8)
        finally:
            reopened.close()

    async def test_chat_mode_cannot_fake_file_proposal(self):
        answer, p = await self.chat(self.request(), [final("已安排待办，请确认"), final("文件已完成")])
        self.assertIn("尚未完成", answer)
        self.assertNotIn("已安排待办", answer)
        self.assertFalse(core._sync_pending(self.sid))
        self.assertFalse(self.effects)
        self.assertFalse(self.path.exists())
        self.assertEqual(p.complete_with_tools.await_count, 2)

    async def test_write_internal_verification_does_not_discharge_read(self):
        item = await self.propose()
        answer, _ = await self.chat("确认", [final("完成", "report", action_refs=[item["action_id"]])] * 2, "file-confirm")
        self.assertEqual(self.path.read_bytes(), self.content.encode())
        self.assertIn("尚未完成", answer)
        self.assertNotIn("文件任务已完成", answer)
        self.assertEqual([n for n, _ in self.effects], ["write_file"])

    async def test_bad_parameters_never_produce_ticket(self):
        answer, _ = await self.chat(self.request(), [call("write_file", path="", content=5)] * 2)
        self.assertIn("尚未完成", answer)
        self.assertFalse(core._sync_pending(self.sid))
        self.assertFalse(self.effects)

    async def test_missing_parameters_clarify(self):
        answer, _ = await self.chat("请创建一个文件，再读取并展示完整内容", [
            final("已完成", "clarify", tool="write_file", arguments={}, missing=["path", "content"])])
        self.assertIn("path", answer)
        self.assertIn("content", answer)
        self.assertFalse(self.effects)
        self.assertFalse(core._sync_pending(self.sid))

    async def test_refusal_never_executes_or_reproposes(self):
        item = await self.propose()
        answer, _ = await self.chat("取消，不执行", [call("write_file", path=str(self.path), content=self.content), final("完成")], "file-refuse")
        self.assertEqual(item["status"], "cancelled")
        self.assertIn("已取消", answer)
        self.assertFalse(self.effects)
        self.assertFalse(core._sync_pending(self.sid))

    async def test_post_write_timeout_does_not_claim_delivery_or_repeat_write(self):
        await self.propose()
        answer, _ = await self.chat("确认", [core.ProviderError("synthetic timeout")], "file-timeout")
        self.assertTrue(self.path.exists())
        self.assertIn("尚未完成", answer)
        self.assertNotIn("文件任务已完成", answer)
        await self.chat("确认", [], "file-duplicate")
        self.assertEqual([n for n, _ in self.effects], ["write_file"])

    async def test_read_failure_is_not_completed(self):
        item = await self.propose()
        with patch.object(core, "_execute_authorized_tool", AsyncMock(side_effect=[
                {"ok": True, "verified_readback": True}, {"ok": False, "error": "synthetic read failure"}])):
            answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
                final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "file-read-fail")
        self.assertIn("尚未完成", answer)
        self.assertNotIn("文件任务已完成", answer)

    async def test_pending_plain_chat_preserves_ticket_and_budget(self):
        item = await self.propose()
        task = core._task_state[self.sid]
        before = {k: task.get(k) for k in ("id", "intent", "budget", "rounds_used", "calls_used", "corrections_used")}
        answer, _ = await self.chat("晚上好，聊聊音乐吧", [final("晚上好，我们聊聊音乐。")], "file-chat")
        self.assertEqual(answer, "晚上好，我们聊聊音乐。")
        self.assertEqual({k: task.get(k) for k in before}, before)
        self.assertEqual(core._sync_pending(self.sid)[0]["action_id"], item["action_id"])

    async def test_file_confirmation_explanation_is_chat(self):
        answer, _ = await self.chat("解释一下创建文件再读回时，确认流程是怎样的？", [final("确认前只有提案；确认后写入，再实际读取和交付。")])
        self.assertEqual(answer, "确认前只有提案；确认后写入，再实际读取和交付。")
        self.assertFalse(self.effects)
        self.assertFalse(core._sync_pending(self.sid))

    async def test_independent_wording_and_explanation_counterexamples(self):
        for index, text in enumerate((
                f"帮我生成文件 {self.path}，然后读取它并展示完整正文。内容如下：{self.content}",
                f"请创建文件 {self.path}，然后打开该文件，把全部正文原样显示。内容如下：{self.content}",
                f"请创建\n文件 {self.path}\n写入后读取并展示完整正文。内容如下：{self.content}")):
            answer, _ = await self.chat(text, [final("已安排待办，请确认"), final("完成")], f"variant-{index}")
            self.assertIn("尚未完成", answer)
            self.assertFalse(core._sync_pending(self.sid))
        answer, _ = await self.chat("能解释一下为什么创建文件之后还要读取文件吗？", [final("读取可以核对实际落盘的内容。")], "explanation")
        self.assertEqual(answer, "读取可以核对实际落盘的内容。")

    async def test_independent_cancelled_revision_does_not_block_replacement(self):
        old = await self.propose()
        self.content = "新版第一行\n新版第二行"
        await self.chat("取消旧的，改成新版，仍然写入后读取完整内容", [call("write_file", path=str(self.path), content=self.content)], "replace")
        item = core._sync_pending(self.sid)[0]
        answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
            final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "replace-confirm")
        self.assertEqual(old["status"], "cancelled")
        self.assertIn("文件任务已完成", answer)
        self.assertIn(self.content, answer)

    async def test_independent_paged_read_preserves_full_two_lines(self):
        self.content = "甲" * 24000 + "\nTAIL-73921"
        item = await self.propose()
        answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
            call("read_file", path=str(self.path), offset=65535),
            final("摘要", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1", "file-start:read:2"])], "pages")
        self.assertIn("文件任务已完成", answer)
        self.assertIn(self.content, answer)

    async def test_independent_pending_new_file_cannot_reuse_old_ticket_as_proposal(self):
        item = await self.propose()
        answer, _ = await self.chat(f"另外请创建文件 {self.root / 'second.txt'}，写入后读取并展示完整内容。内容如下：SECOND",
            [final("第二个文件已安排待办，请确认"), final("第二个文件完成")], "second-request")
        self.assertNotIn("已安排待办", answer)
        self.assertIn("待确认", answer)
        self.assertEqual(core._sync_pending(self.sid)[0]["action_id"], item["action_id"])
        self.assertEqual(len(core._sync_pending(self.sid)), 1)
        self.assertFalse(self.effects)

    async def test_independent_lost_write_receipt_stays_unknown(self):
        item = await self.propose()
        original = core._execute_authorized_tool
        async def lost(name, arguments):
            await original(name, arguments)
            raise TimeoutError("synthetic lost receipt")
        with patch.object(core, "_execute_authorized_tool", lost):
            answer, _ = await self.chat("确认", [final("全部完成", "report", action_refs=[item["action_id"]])], "lost")
        self.assertTrue(self.path.exists())
        self.assertEqual(item["status"], "unknown")
        self.assertIn("结果未知", answer)
        self.assertNotIn("文件任务已完成", answer)
        await self.chat("确认", [], "lost-duplicate")
        self.assertEqual([n for n, _ in self.effects], ["write_file"])

    async def test_literal_body_mismatch_corrects_before_ticket(self):
        answer, provider = await self.chat(self.request(), [
            call("write_file", path=str(self.path), content="丢失行首的错误正文"),
            call("write_file", path=str(self.path), content=self.content)])
        self.assertEqual(provider.complete_with_tools.await_count, 2)
        self.assertEqual(len(core._actions().records), 1)
        self.assertEqual(core._sync_pending(self.sid)[0]["arguments"]["content"], self.content)
        self.assertIn("待确认", answer)
        self.assertFalse(self.path.exists())

    async def test_repeated_literal_mismatch_never_makes_ticket(self):
        answer, provider = await self.chat(self.request(), [call("write_file", path=str(self.path), content="不完整")] * 2)
        self.assertEqual(provider.complete_with_tools.await_count, 2)
        self.assertFalse(core._sync_pending(self.sid))
        self.assertFalse(self.effects)
        self.assertIn("尚未完成", answer)

    async def test_literal_constraint_survives_continue(self):
        bad = call("write_file", path=str(self.path), content="删掉行首的正文")
        await self.chat(self.request(), [bad, bad])
        task = core._task_state[self.sid]
        answer, p = await self.chat("继续", [bad], "literal-continue")
        self.assertIs(core._task_state[self.sid], task)
        self.assertEqual(p.complete_with_tools.await_count, 1)
        self.assertFalse(core._sync_pending(self.sid))
        self.assertIn("尚未完成", answer)

    async def test_literal_constraint_updates_on_edit_before_proposal(self):
        old = await self.propose()
        self.content = "新版第一行：测试\n新版第二行：保留"
        text = "取消旧的，改成新版，" + self.request()
        await self.chat(text, [call("write_file", path=str(self.path), content="测试\n保留"),
                              call("write_file", path=str(self.path), content=self.content)], "literal-edit")
        self.assertEqual(old["status"], "cancelled")
        self.assertEqual(len(core._actions().records), 2)
        self.assertEqual(core._sync_pending(self.sid)[0]["arguments"]["content"], self.content)
        self.assertFalse(self.path.exists())

    async def test_path_only_edit_keeps_original_literal_body(self):
        old = await self.propose()
        new_path = self.root / "renamed.txt"
        text = f"取消旧的，路径改为 {new_path}，正文不变，仍然要在写入后读取并展示完整内容。"
        await self.chat(text, [call("write_file", path=str(new_path), content="删掉行首"),
                              call("write_file", path=str(new_path), content=self.content)], "path-edit")
        self.assertEqual(old["status"], "cancelled")
        self.assertEqual(len(core._actions().records), 2)
        self.assertEqual(core._sync_pending(self.sid)[0]["arguments"]["content"], self.content)
        self.assertEqual(core._sync_pending(self.sid)[0]["arguments"]["path"], str(new_path))
        self.assertFalse(self.effects)
