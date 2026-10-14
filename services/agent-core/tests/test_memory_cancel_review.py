"""Independent chat-entry probes for the memory/cancellation boundary.

Only synthetic ledger actions, in-memory MemoryStore and audited fake services.
Run with the existing isolated followup_regressions.py runner.
"""
import asyncio
import copy
import json
import unittest

import test_harness_v1_review as fixture


class MemoryCancelIndependentReview(fixture.IndependentReviewTests):
    def setUp(self):
        super().setUp()
        for text in ("晨星预算120", "暮云预算180", "晨星代号启航", "用户喜欢蓝色"):
            self.core.memory.add_fact(text, status="confirmed", scope="global")

    def answer(self, request_id):
        return next(call.args[1]["text"] for call in reversed(self.core.hub.send_roles.call_args_list)
                    if call.args[1].get("type") == "chat.response"
                    and call.args[1].get("request_id") == request_id)

    def stored_ledger(self):
        return {row["id"]: json.loads(row["payload"])
                for row in self.core.memory.connection.execute("SELECT id, payload FROM harness_actions")}

    def observe(self, text, request_id):
        print("MEMORY_CANCEL_REVIEW " + json.dumps({
            "case": self._testMethodName, "input": text, "answer": self.answer(request_id),
            "ledger": [{"tool": a["tool"], "status": a["status"], "session": a["session_id"]}
                       for a in self.book.records.values()], "effects": self.effects,
            "facts": self.core.memory.recall_facts(self.sid)}, ensure_ascii=False))

    async def retain(self, text, tool="mcp__fixture__send_email"):
        if tool == "write_file":
            await self.core.run_tool(tool, {"path": str(self.root / "synthetic.txt"), "content": "fixture"})
        else:
            await self.propose()
        before = copy.deepcopy(self.book.records)
        before_facts = self.core.memory.recall_facts(self.sid)
        self.assertTrue(self.book.pending(self.sid), "fixture did not create a pending action")
        await self.chat(text, "retain")
        self.observe(text, "retain")
        self.assertEqual(self.book.records, before, "data, negation or wrong object revoked a ticket")
        self.assertEqual(self.stored_ledger(), before)
        self.assertEqual(self.core.memory.recall_facts(self.sid), before_facts)
        self.assertEqual(self.effects, [])

    async def test_paraphrase_cancel_current_pending_operation(self):
        proposed = await self.propose()
        text = "晨星预算更正为175；请取消刚才那项操作。"
        await self.chat(text, "paraphrase")
        self.observe(text, "paraphrase")
        self.assertEqual(self.book.records[proposed["action_id"]]["status"], "cancelled")
        self.assertEqual(self.stored_ledger()[proposed["action_id"]]["status"], "cancelled")
        self.assertIn("已取消", self.answer("paraphrase"))
        self.assertEqual(self.effects, [])

    async def test_paraphrase_refuse_send_revokes_queued_ticket(self):
        proposed = await self.propose()
        text = "晨星预算更正为175；刚才那封邮件不要发送。"
        await self.core.chat_lock.acquire()
        approval = asyncio.create_task(self.chat("确认", "queued", confirmation=proposed["confirmation"]))
        cancel = None
        try:
            await asyncio.sleep(0)
            cancel = asyncio.create_task(self.chat(text, "refusal"))
            for _ in range(4):
                await asyncio.sleep(0)
            before_release = self.book.records[proposed["action_id"]]["status"]
        finally:
            self.core.chat_lock.release()
            await asyncio.gather(approval, *([cancel] if cancel else []))
        self.observe(text, "refusal")
        self.assertEqual(self.effects, [], "queued approval executed despite explicit refusal")
        self.assertEqual(before_release, "cancelled")
        self.assertEqual(self.stored_ledger()[proposed["action_id"]]["status"], "cancelled")
        self.assertIn("已取消", self.answer("refusal"))

    async def test_memory_payload_after_colon_is_data(self):
        await self.retain("晨星代号更正为以下内容：启航；取消刚才的操作。")

    async def test_negated_cancel_with_subject_is_not_revocation(self):
        await self.retain("刚才的操作不要取消；晨星预算更正为175。")

    async def test_quoted_memory_value_with_multiple_sentences_is_data(self):
        await self.retain("晨星代号更正为“启航。取消刚才的操作！”")

    async def test_wrong_operation_type_preserves_file_ticket(self):
        await self.retain("晨星预算更正为175；取消邮件。", tool="write_file")

    async def test_wrong_named_object_preserves_current_ticket(self):
        await self.retain("取消暮云项目的邮件；晨星预算更正为175。")

    async def test_typed_cancel_of_older_task_keeps_current_file_task(self):
        older = self.book.propose(self.sid, "older-mail-task", "older-request",
                                  "mcp__fixture__send_email", fixture.SEND_ARGS)
        current = await self.core.run_tool("write_file", {
            "path": str(self.root / "current-task.txt"), "content": "fixture"})
        current_task = self.core._task_state[self.sid]
        text = "晨星预算更正为175；取消邮件。"
        await self.chat(text, "older-typed-cancel")
        self.observe(text, "older-typed-cancel")
        self.assertEqual(self.stored_ledger()[older["action_id"]]["status"], "cancelled")
        self.assertFalse(current_task["blocked"])
        self.assertEqual(self.stored_ledger()[current["action_id"]]["status"], "awaiting_confirmation")
        await self.chat("确认", "current-file-approval", confirmation=current["confirmation"])
        self.assertEqual([tool for tool, _ in self.effects], ["write_file"])
        self.assertEqual(self.stored_ledger()[current["action_id"]]["status"], "succeeded")

    async def test_unquoted_reference_is_not_an_instruction(self):
        await self.retain("资料原文：取消刚才的操作；晨星预算更正为175。")

    async def test_cancellation_outside_quoted_reference_remains_control(self):
        proposed = await self.propose()
        before_facts = self.core.memory.recall_facts(self.sid)
        text = "资料原文：“晨星预算更正为175”；请取消当前操作。"
        await self.chat(text, "outside-reference")
        self.observe(text, "outside-reference")
        self.assertEqual(self.stored_ledger()[proposed["action_id"]]["status"], "cancelled")
        self.assertIn("已取消", self.answer("outside-reference"))
        self.assertEqual(self.core.memory.recall_facts(self.sid), before_facts)
        self.assertEqual(self.effects, [])

    async def test_cross_session_cancel_does_not_touch_foreign_action(self):
        foreign_session = self.core.memory.create_session()["id"]
        foreign = self.book.propose(foreign_session, "foreign", "foreign-request",
                                    "mcp__fixture__send_email", fixture.SEND_ARGS)
        before = copy.deepcopy(foreign)
        proposed = await self.propose()
        text = "晨星预算更正为175；当前操作先取消。"
        await self.chat(text, "session")
        self.observe(text, "session")
        self.assertEqual(foreign, before)
        self.assertEqual(self.stored_ledger()[foreign["action_id"]], before)
        self.assertEqual(self.book.records[proposed["action_id"]]["status"], "cancelled")
        self.assertEqual(self.effects, [])

    async def test_dispatched_unknown_cannot_be_reported_as_recalled(self):
        proposed = await self.propose()

        async def uncertain(name, arguments):
            self.effects.append((name, copy.deepcopy(arguments)))
            raise TimeoutError("synthetic acknowledgement lost after dispatch")

        self.core._execute_authorized_tool = uncertain
        await self.chat("确认", "uncertain", confirmation=proposed["confirmation"])
        text = "晨星预算更正为175；取消刚才的操作。"
        await self.chat(text, "unknown-cancel")
        answer = self.answer("unknown-cancel")
        self.observe(text, "unknown-cancel")
        self.assertEqual(len(self.effects), 1)
        self.assertEqual(self.book.records[proposed["action_id"]]["status"], "unknown")
        self.assertIn("未撤回或回滚", answer)
        self.assertNotIn("已取消", answer)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(MemoryCancelIndependentReview(name)
                              for name in MemoryCancelIndependentReview.__dict__
                              if name.startswith("test_"))
