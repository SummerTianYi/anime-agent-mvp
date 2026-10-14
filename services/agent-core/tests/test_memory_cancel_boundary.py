"""Actual chat-entry cancellation/memory boundary; synthetic ledger and service only."""
import asyncio
import copy
import json
import unittest
from unittest.mock import patch

import test_harness_v1_review as fixture


FIRST = "取消刚才的操作，晨星预算更正为175。"
LAST = "晨星预算更正为175；取消刚才的操作。"


class MemoryCancelBoundaryTests(fixture.IndependentReviewTests):
    def setUp(self):
        super().setUp()
        for content in ("晨星预算120", "暮云预算180", "用户喜欢蓝色"):
            self.core.memory.add_fact(content, status="confirmed", scope="global")

    def facts(self):
        return [dict(row) for row in self.core.memory.connection.execute("SELECT * FROM facts ORDER BY fact_id")]

    def stored_action(self, action_id):
        row = self.core.memory.connection.execute("SELECT payload FROM harness_actions WHERE id=?", (action_id,)).fetchone()
        return json.loads(row[0])

    def answer(self, request_id):
        return next(call.args[1]["text"] for call in reversed(self.core.hub.send_roles.call_args_list)
                    if call.args[1].get("type") == "chat.response" and call.args[1].get("request_id") == request_id)

    def observe(self, text, answer, **extra):
        print("MEMORY_CANCEL_OBSERVATION " + json.dumps({
            "case": self._testMethodName, "input": text, "answer": answer,
            "ledger": [{"session": a["session_id"], "status": a["status"], "target": a["arguments"].get("to")}
                       for a in self.book.records.values()], "synthetic_effects": self.effects,
            "effective_facts": self.core.memory.recall_facts(self.sid), **extra}, ensure_ascii=False))

    async def combined(self, text):
        proposed = await self.propose()
        before = self.facts()
        await self.chat(text, "combined")
        answer = self.answer("combined")
        self.observe(text, answer)
        self.assertEqual(self.book.records[proposed["action_id"]]["status"], "cancelled")
        self.assertEqual(self.stored_action(proposed["action_id"])["status"], "cancelled")
        self.assertIn("已取消", answer)
        self.assertIn("未执行", answer)
        # Do not expand the memory grammar to guess which compound clause to save.
        self.assertIn("尚未更正", answer)
        self.assertEqual(self.facts(), before)
        self.assertEqual(self.effects, [])
        self.assertEqual(self.core.provider.complete_with_tools.await_count, 0)

    async def test_cancel_before_memory(self):
        await self.combined(FIRST)

    async def test_cancel_after_memory(self):
        await self.combined(LAST)

    async def queued(self, text):
        proposed = await self.propose()
        await self.core.chat_lock.acquire()
        approval = asyncio.create_task(self.chat("确认", "queued-approval", confirmation=proposed["confirmation"]))
        cancel = None
        before_release = None
        try:
            await asyncio.sleep(0)
            cancel = asyncio.create_task(self.chat(text, "queued-cancel"))
            for _ in range(4):
                await asyncio.sleep(0)
            before_release = self.book.records[proposed["action_id"]]["status"]
            self.assertEqual(self.effects, [])
        finally:
            self.core.chat_lock.release()
            await asyncio.gather(approval, *([cancel] if cancel is not None else []))
        self.observe(text, self.answer("queued-cancel"), before_lock_release=before_release)
        self.assertEqual(self.effects, [], "queued old ticket dispatched after cancellation")
        self.assertEqual(before_release, "cancelled")
        self.assertEqual(self.book.records[proposed["action_id"]]["status"], "cancelled")
        self.assertEqual(self.stored_action(proposed["action_id"])["status"], "cancelled")
        self.assertIn("已取消", self.answer("queued-cancel"))

    async def test_queued_confirmation_cancel_before_memory(self):
        await self.queued(FIRST)

    async def test_queued_confirmation_cancel_after_memory(self):
        await self.queued(LAST)

    async def test_cancel_only_control(self):
        proposal = await self.propose()
        before = self.facts()
        await self.chat("取消刚才的操作。", "cancel-only")
        self.assertEqual(self.book.records[proposal["action_id"]]["status"], "cancelled")
        self.assertIn("已取消", self.latest_reply())
        self.assertEqual(self.facts(), before)
        self.assertEqual(self.effects, [])

    async def test_memory_only_keeps_ticket_and_saves(self):
        await self.propose()
        before = copy.deepcopy(self.book.records)
        for index, verb in enumerate(("更正为", "改为", "改成")):
            await self.chat(f"晨星预算{verb}{175 + index}。", f"memory-only-{index}")
            self.assertEqual(self.book.records, before)
            self.assertIn(f"晨星预算{175 + index}", self.core.memory.recall_facts(self.sid))
            self.assertIn("已更正并读回核验", self.latest_reply())
        other = self.core.memory.create_session()["id"]
        self.assertIn("晨星预算177", self.core.memory.recall_facts(other))
        self.assertEqual(self.effects, [])

    async def preserved(self, text):
        await self.propose()
        before = copy.deepcopy(self.book.records)
        await self.chat(text, "preserve")
        self.assertEqual(self.book.records, before, text)
        self.assertEqual(self.effects, [])

    async def test_negated_cancellation_keeps_ticket(self):
        await self.preserved("不要取消刚才的操作，晨星预算更正为175。")

    async def test_quoted_command_keeps_ticket(self):
        await self.preserved("引用资料：“取消刚才的操作，晨星预算更正为175。”")

    async def test_memory_value_is_not_command(self):
        self.core.memory.add_fact("晨星代号启航", status="confirmed", scope="global")
        await self.preserved("晨星代号更正为取消刚才的操作。")
        self.assertIn("晨星代号取消刚才的操作", self.core.memory.recall_facts(self.sid))

    async def test_quoted_memory_value_is_not_command(self):
        await self.preserved("晨星代号更正为“启航；取消刚才的操作”。")

    async def test_other_session_pending_unchanged(self):
        other = self.core.memory.create_session()["id"]
        foreign = self.book.propose(other, "foreign", "foreign", "mcp__fixture__send_email",
                                    fixture.SEND_ARGS | {"to": "foreign@example.invalid"})
        before = copy.deepcopy(foreign)
        await self.combined(FIRST)
        self.assertEqual(foreign, before)

    async def test_targeted_mail_cancel_preserves_file_and_its_confirmation(self):
        mail = await self.propose()
        file = self.book.propose(self.sid, "file-task", "file-proposal", "write_file",
                                 {"path": str(self.root / "preserved.txt"), "content": "synthetic"})
        self.core._task_state[self.sid] = {"id": "file-task", "intent": "写合成文件", "blocked": False}
        before = copy.deepcopy(file)
        await self.chat("晨星预算更正为175；取消刚才那封邮件。", "typed-cancel")
        self.assertEqual(self.stored_action(mail["action_id"])["status"], "cancelled")
        self.assertEqual(file, before)
        self.assertFalse(self.core._task_state[self.sid]["blocked"])
        await self.chat("确认", "confirm-file", confirmation=self.book.ticket(file))
        self.assertEqual([name for name, _ in self.effects], ["write_file"])
        self.assertEqual(file["status"], "succeeded")

    async def test_targeted_file_cancel_preserves_mail(self):
        mail = await self.propose()
        file = self.book.propose(self.sid, "file-task", "file-proposal", "write_file",
                                 {"path": str(self.root / "cancelled.txt"), "content": "synthetic"})
        before = copy.deepcopy(self.book.records[mail["action_id"]])
        await self.chat("晨星预算更正为175；取消当前文件。", "file-cancel")
        self.assertEqual(self.stored_action(file["action_id"])["status"], "cancelled")
        self.assertEqual(self.book.records[mail["action_id"]], before)
        self.assertEqual(self.effects, [])

    async def test_ambiguity_does_not_swallow_cancellation(self):
        await self.combined("取消刚才的操作；把预算更正为175。")

    async def test_memory_save_failure_still_delivers_cancellation(self):
        proposal = await self.propose()
        before = self.facts()
        with patch.object(self.core.memory, "correct_fact", return_value={
                "outcome": "failed", "error": "更正保存失败，旧有效值保留。"}):
            await self.chat(FIRST, "save-failed")
        self.assertEqual(self.book.records[proposal["action_id"]]["status"], "cancelled")
        self.assertIn("已取消", self.latest_reply())
        self.assertIn("保存失败", self.latest_reply())
        self.assertNotIn("已更正", self.latest_reply())
        self.assertEqual(self.facts(), before)

    async def test_cancel_after_dispatch_does_not_claim_rollback(self):
        proposal = await self.propose()
        dispatched, release = asyncio.Event(), asyncio.Event()

        async def executor(name, arguments):
            self.effects.append((name, copy.deepcopy(arguments)))
            dispatched.set()
            await release.wait()
            return {"ok": True, "output": "synthetic accepted"}

        self.core._execute_authorized_tool = executor
        approval = asyncio.create_task(self.chat("确认", "inflight", confirmation=proposal["confirmation"]))
        cancellation = None
        try:
            await asyncio.wait_for(dispatched.wait(), 3)
            cancellation = asyncio.create_task(self.chat(LAST, "too-late"))
            for _ in range(4):
                await asyncio.sleep(0)
            status_on_arrival = self.book.records[proposal["action_id"]]["status"]
        finally:
            release.set()
            await asyncio.gather(approval, *([cancellation] if cancellation else []))
        answer = self.answer("too-late")
        self.observe(LAST, answer, status_on_arrival=status_on_arrival)
        self.assertEqual(len(self.effects), 1)
        self.assertEqual(status_on_arrival, "executing")
        self.assertEqual(self.book.records[proposal["action_id"]]["status"], "succeeded")
        self.assertIn("已经派发", answer)
        self.assertIn("未撤回或回滚", answer)
        self.assertNotIn("已取消", answer)

    async def test_already_completed_not_recalled(self):
        proposed = await self.propose()
        await self.chat("确认", "executed", confirmation=proposed["confirmation"])
        await self.chat(FIRST, "late-cancel")
        self.assertEqual(len(self.effects), 1)
        self.assertIn("已经派发", self.latest_reply())
        self.assertIn("未撤回或回滚", self.latest_reply())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(MemoryCancelBoundaryTests(name) for name in MemoryCancelBoundaryTests.__dict__
                              if name.startswith("test_"))
