"""Plain natural-language handle_chat requests; model output is untrusted."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from agent_core.actions import ActionLedger
from agent_core.storage import MemoryStore
from test_a4_pilot import call, final
import test_harness_v1_integration as fixture
from email_fixture import SEND, SyntheticGmail, request


class EmailTaskTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture.MainActionTests.setUp(self)
        core._task_state.clear()
        self.server = SyntheticGmail()
        self.args = dict(to=["qingzhu@example.invalid"], subject="合成回执 175", body="第一行：Error 是正文\n第二行：蓝桥 42kg")
        for name, value in (("mcp_host", self.server.host()), ("_spawn", lambda c: c.close()),
                            ("_shown_confirmations", {}), ("_pending_writes", {}), ("_result_pages", {})):
            p = patch.object(core, name, value)
            p.start()
            self.addCleanup(p.stop)

    def text(self):
        return request(self.args["to"][0], self.args["subject"], self.args["body"])

    def send(self, **extra):
        return call(SEND, **{**self.args, **extra})

    async def chat(self, text, turns, rid="email-start", **kw):
        provider = SimpleNamespace(complete_with_tools=AsyncMock(side_effect=turns))
        with patch.object(core, "provider", provider):
            await core.handle_chat(text, rid, self.sid, effort="standard", **kw)
        return self.store.load_messages(100, self.sid)[-1]["content"], provider

    async def propose(self):
        await self.chat(self.text(), [self.send()])
        self.assertEqual(self.server.calls, [])
        pending = core._sync_pending(self.sid)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["arguments"], self.args)
        return pending[0]

    async def test_accept_once_exact_delivery_error_body_reopen(self):
        action = await self.propose()
        answer, _ = await self.chat("确认", [final("已送达并已读", "chat")] * 2, "confirmed")
        self.assertEqual(len(self.server.mailbox), 1)
        message = self.server.mailbox[0]
        self.assertEqual(message["arguments"], self.args)
        self.assertEqual(message["recipients"], self.args["to"])
        for literal in (*self.args["to"], self.args["subject"], self.args["body"], message["id"], "发送请求已受理"):
            self.assertIn(literal, answer)
        self.assertNotIn("已送达", answer)
        self.assertEqual(action["status"], "succeeded")
        before = copy.deepcopy(self.server.calls)
        await self.chat("确认", [], "duplicate")
        await self.chat("刚才那个任务现在怎么样？", [], "status")
        self.assertEqual(before, self.server.calls)
        reopened = MemoryStore(data_dir=self.root / "db")
        try:
            self.assertEqual(list(ActionLedger(reopened.connection).records.values()), list(core._actions().records.values()))
            self.assertEqual(reopened.load_messages(100, self.sid), self.store.load_messages(100, self.sid))
        finally:
            reopened.close()

    async def test_no_proposal_chat_claim_cannot_manufacture_ticket(self):
        answer, p = await self.chat(self.text(), [final("已有待办，确认即可发送"), final("已发送并送达")])
        self.assertFalse(core._sync_pending(self.sid))
        self.assertFalse(self.server.calls)
        self.assertIn("尚未完成", answer)
        self.assertNotIn("已发送", answer)
        self.assertEqual(p.complete_with_tools.await_count, 2)

    async def test_bad_recipient_extra_fields_and_changed_body_rejected_before_ticket(self):
        for extra in ({"to": ["other@example.invalid"]}, {"to": self.args["to"]+["extra@example.invalid"]},
                      {"cc": ["hidden@example.invalid"]}, {"bcc": []}, {"attachments": []},
                      {"htmlBody": "extra"}, {"mimeType": "text/html"}, {"threadId": "old"},
                      {"subject": "changed"}, {"body": self.args["body"]+"。"}):
            with self.subTest(extra=extra):
                core._task_state.clear()
                core._actions().cancel(self.sid)
                await self.chat(self.text(), [self.send(**extra)] * 2, "bad-"+str(extra))
                self.assertFalse(core._sync_pending(self.sid))
                self.assertEqual(self.server.calls, [])

    async def test_reject_edit_and_stale_confirmation(self):
        old = await self.propose()
        ticket = core._actions().ticket(old)
        self.args["subject"] = "新版主题 902"
        await self.chat("取消旧的，主题改为「新版主题 902」，其他要求不变。", [self.send()], "edit")
        self.assertEqual(old["status"], "cancelled")
        self.assertEqual(core._sync_pending(self.sid)[0]["arguments"], self.args)
        await self.chat("确认", [], "stale", confirmation=ticket)
        self.assertEqual(self.server.calls, [])
        await self.chat("取消，不发送", [final("已经发出")], "cancel")
        self.assertEqual(self.server.calls, [])
        self.assertFalse(core._sync_pending(self.sid))

    async def test_success_then_followup_timeout_keeps_receipt(self):
        await self.propose()
        answer, _ = await self.chat("确认", [core.ProviderError("synthetic timeout")], "timeout")
        self.assertEqual(len(self.server.mailbox), 1)
        self.assertIn("发送请求已受理", answer)
        self.assertIn(self.server.mailbox[0]["id"], answer)
        self.assertIn(self.args["body"], answer)
        await self.chat("确认", [], "duplicate")
        self.assertEqual(len(self.server.calls), 1)

    async def test_business_error_never_success(self):
        await self.propose()
        self.server.error = "invalid_grant"
        answer, _ = await self.chat("确认", [final("发送成功")], "failed")
        self.assertEqual(self.server.mailbox, [])
        self.assertIn("执行失败", answer)
        self.assertNotIn("发送请求已受理", answer)
        self.assertEqual(next(iter(core._actions().records.values()))["status"], "failed")

    async def test_unknown_never_resends_including_optional_default_mime(self):
        await self.propose()
        self.server.lose_receipt = True
        answer, _ = await self.chat("确认", [self.send(mimeType="text/plain"), final("成功")], "unknown")
        self.assertEqual(len(self.server.mailbox), 1)
        self.assertIn("未知", answer)
        self.assertNotIn("发送请求已受理", answer)
        self.assertFalse(core._sync_pending(self.sid))
        await self.chat("确认", [], "repeat")
        self.assertEqual(len(self.server.calls), 1)

    async def test_duplicate_proposal_with_optional_default_mime_reuses_action(self):
        await self.propose()
        answer, _ = await self.chat("确认", [self.send(mimeType="text/plain"), final("已完成"), final("已完成")], "repeat-proposal")
        self.assertFalse(core._sync_pending(self.sid))
        self.assertEqual(len(self.server.calls), 1)
        self.assertIn("发送请求已受理", answer)

    async def test_malformed_success_envelope_is_unknown(self):
        await self.propose()
        self.server.success_override = "Email sent successfully with ID: undefined"
        answer, _ = await self.chat("确认", [final("全部完成")] * 2, "malformed")
        self.assertIn("未知", answer)
        self.assertNotIn("发送请求已受理", answer)
        self.assertEqual(next(iter(core._actions().records.values()))["status"], "unknown")

    async def test_chat_and_explanation_and_missing_parameters(self):
        answer, _ = await self.chat("请解释如何给单个收件人发送纯文本邮件", [final("先核对参数并确认，再发送并交付受理回执。")])
        self.assertIn("先核对参数", answer)
        await self.propose()
        task = core._task_state[self.sid]
        before = copy.deepcopy(core._sync_pending(self.sid)), task["rounds_used"], task["calls_used"]
        answer, _ = await self.chat("今天聊聊音乐吧", [final("想听哪首歌？")], "chat")
        self.assertEqual(answer, "想听哪首歌？")
        self.assertEqual(before, (core._sync_pending(self.sid), task["rounds_used"], task["calls_used"]))
        await self.chat("取消", [final("已取消")], "cancel")
        answer, _ = await self.chat("请发送一封纯文本邮件", [final("", "clarify", tool=SEND, arguments={}, missing=["to", "subject", "body"])], "missing")
        self.assertIn("还需要", answer)
        self.assertFalse(self.server.calls)
