"""Natural-language Core entry; controlled model, real ledger, synthetic MCP."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from agent_core.actions import ActionLedger
from agent_core.storage import MemoryStore
from test_a4_pilot import call, final
import test_harness_v1_integration as fixture
from issue_fixture import SyntheticGitHub, request


READ = "mcp__github__issue_read"
WRITE = "mcp__github__issue_write"


class IssueTaskTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture.MainActionTests.setUp(self)
        core._task_state.clear()
        self.server = SyntheticGitHub()
        self.title = "春日核验 READY-17：3cm"
        self.target = self.server.target
        for name, value in (("mcp_host", self.server.host()), ("_spawn", lambda c: c.close()),
                            ("_shown_confirmations", {}), ("_pending_writes", {}), ("_result_pages", {})):
            p = patch.object(core, name, value)
            p.start()
            self.addCleanup(p.stop)

    def read(self, **extra):
        return call(READ, **{**self.target, "method": "get", **extra})

    def write(self, **extra):
        return call(WRITE, **{**self.target, "method": "update", "title": self.title, **extra})

    async def chat(self, text, turns, rid="issue-start", **kw):
        provider = SimpleNamespace(complete_with_tools=AsyncMock(side_effect=turns))
        with patch.object(core, "provider", provider):
            await core.handle_chat(text, rid, self.sid, effort="standard", **kw)
        return self.store.load_messages(100, self.sid)[-1]["content"], provider

    async def propose(self):
        await self.chat(request(self.target, self.title), [self.read()])
        self.assertEqual(self.server.calls, [])
        await self.chat("确认", [self.write()], "issue-before")
        pending = core._sync_pending(self.sid)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["tool"], WRITE)
        self.assertEqual(pending[0]["arguments"], {**self.target, "method": "update", "title": self.title})
        self.assertEqual(self.server.writes, 0)
        return pending[0]

    async def complete(self):
        action = await self.propose()
        await self.chat("确认", [self.read()], "issue-write")
        self.assertEqual(self.server.writes, 1)
        pending = core._sync_pending(self.sid)
        self.assertEqual(len(pending), 1, "post-update same-argument read must require its own fresh ticket")
        self.assertEqual(pending[0]["tool"], READ)
        answer, _ = await self.chat("确认", [final("全部完成", "report", action_refs=[action["action_id"]])] * 2, "issue-after")
        return action, answer

    async def test_title_only_update_fresh_read_exact_delivery_reopen_and_no_replay(self):
        action, answer = await self.complete()
        self.assertIn("Issue 任务已完成", answer)
        self.assertIn(self.title, answer)
        self.assertIn("SummerTianYi/a4-synthetic", answer)
        self.assertIn("#17", answer)
        self.assertEqual(self.server.issue, {**self.server.initial, "title": self.title})
        self.assertEqual([(c["tool"], c["writes_before"]) for c in self.server.calls], [("issue_read", 0), ("issue_write", 0), ("issue_read", 1)])
        before = copy.deepcopy(self.server.calls)
        await self.chat("确认", [], "duplicate")
        await self.chat("刚才那个任务现在怎么样？", [], "status")
        self.assertEqual(before, self.server.calls)
        reopened = MemoryStore(data_dir=self.root / "db")
        try:
            self.assertEqual(list(ActionLedger(reopened.connection).records.values()), list(core._actions().records.values()))
            self.assertEqual(reopened.load_messages(100, self.sid), self.store.load_messages(100, self.sid))
            self.assertEqual(reopened.connection.execute("SELECT count(*) FROM events WHERE event_type='tool.result'").fetchone()[0], 2)
        finally:
            reopened.close()

    async def test_no_calls_cannot_manufacture_pending(self):
        answer, p = await self.chat(request(self.target, self.title), [final("已有待办，请确认"), final("已经完成")])
        self.assertIn("尚未完成", answer)
        self.assertFalse(core._sync_pending(self.sid))
        self.assertFalse(self.server.calls)
        self.assertEqual(p.complete_with_tools.await_count, 2)

    async def test_old_read_same_title_is_not_update(self):
        self.server.issue["title"] = self.title
        await self.chat(request(self.target, self.title), [self.read()])
        old = core._sync_pending(self.sid)[0]
        answer, _ = await self.chat("确认", [final("标题已更新，全部完成", "report", action_refs=[old["action_id"]])] * 2, "old-only")
        self.assertIn("尚未完成", answer)
        self.assertNotIn("标题已更新", answer)
        self.assertEqual(self.server.writes, 0)

    async def test_wrong_targets_and_extra_fields_rejected_before_ticket(self):
        for extra in ({"repo": "wrong"}, {"issue_number": 99}, {"title": "wrong"}, {"body": "evil"}, {"labels": []}, {"state": "closed"}):
            with self.subTest(extra=extra):
                core._task_state.clear()
                core._actions().cancel(self.sid)
                await self.chat(request(self.target, self.title), [self.write(**extra)] * 2, "bad-"+str(extra))
                self.assertFalse(core._sync_pending(self.sid))
                self.assertEqual(self.server.calls, [])

    async def test_cancel_and_edit_new_title_require_new_ticket(self):
        old = await self.propose()
        ticket = core._actions().ticket(old)
        self.title = "新版标题：902"
        await self.chat(f"取消旧的，标题改为「{self.title}」，其他要求不变。", [self.write()], "edit")
        self.assertEqual(old["status"], "cancelled")
        self.assertEqual(core._sync_pending(self.sid)[0]["arguments"]["title"], self.title)
        await self.chat("确认", [], "stale", confirmation=ticket)
        self.assertEqual(self.server.writes, 0)
        await self.chat("取消，不执行", [final("已经完成")], "cancel")
        self.assertEqual(self.server.writes, 0)
        self.assertFalse(core._sync_pending(self.sid))

    async def test_successful_write_then_timeout_is_not_whole_task_success(self):
        await self.propose()
        answer, _ = await self.chat("确认", [core.ProviderError("synthetic timeout")], "timeout")
        self.assertEqual(self.server.writes, 1)
        self.assertIn("更新成功", answer)
        self.assertIn("尚未完成", answer)
        self.assertNotIn("Issue 任务已完成", answer)
        await self.chat("确认", [], "duplicate")
        self.assertEqual(self.server.writes, 1)

    async def test_mismatch_and_other_issue_read_never_prove_completion(self):
        for transform in (lambda d: {**d, "title": "wrong"}, lambda d: {**d, "body": "changed"},
                          lambda d: {**d, "number": 99}, lambda d: {**d, "html_url": "https://github.com/other/repo/issues/17"}):
            # Each scenario gets a fresh session/task and synthetic server.
            self.sid = self.store.create_session()["id"]
            self.server.calls.clear(); self.server.writes = 0
            self.server.issue = copy.deepcopy(self.server.initial)
            self.server.read_transform = transform
            _, answer = await self.complete()
            self.assertIn("更新成功", answer)
            self.assertIn("核验未通过", answer)
            self.assertNotIn("Issue 任务已完成", answer)
            self.assertEqual(self.server.writes, 1)

    async def test_explanation_and_clarification_remain_normal(self):
        answer, _ = await self.chat("请解释如何仅修改 Issue 标题并重新读取核验", [final("先展示待确认操作，经确认后更新，再读取核验。")])
        self.assertIn("先展示", answer)
        answer, _ = await self.chat("请修改 Issue 标题后重新读取核验", [final("", "clarify", tool=WRITE, arguments={"method": "update"}, missing=["owner", "repo", "issue_number", "title"])], "clarify")
        self.assertIn("还需要", answer)
        self.assertFalse(self.server.calls)

    async def test_chat_preserves_pending_ticket_parameters_and_budget(self):
        action = await self.propose()
        task = core._task_state[self.sid]
        before = copy.deepcopy(action), task["rounds_used"], task["calls_used"]
        answer, _ = await self.chat("今天聊聊音乐吧", [final("想听哪首歌？")], "chat")
        self.assertEqual(answer, "想听哪首歌？")
        self.assertEqual(before, (action, task["rounds_used"], task["calls_used"]))
        self.assertEqual(self.server.writes, 0)

    async def test_lost_write_receipt_remains_unknown_without_rewrite(self):
        await self.propose()
        self.server.lose_write_receipt = True
        answer, _ = await self.chat("确认", [self.write(), final("成功")], "lost-write")
        self.assertEqual(self.server.writes, 1)
        self.assertIn("未知", answer)
        self.assertNotIn("更新成功", answer)
        self.assertNotIn("Issue 任务已完成", answer)
        await self.chat("确认", [], "duplicate-unknown")
        self.assertEqual(self.server.writes, 1)

    async def test_failed_post_read_has_successful_write_but_incomplete_delivery(self):
        self.server.fail_read_after_write = True
        _, answer = await self.complete()
        self.assertEqual(self.server.writes, 1)
        self.assertIn("更新成功", answer)
        self.assertIn("核验未通过", answer)
        self.assertNotIn("Issue 任务已完成", answer)

    async def test_extra_fields_after_valid_baseline_still_rejected(self):
        await self.chat(request(self.target, self.title), [self.read()])
        answer, _ = await self.chat("确认", [self.write(body=self.server.initial["body"])] * 2, "extra-after-read")
        self.assertEqual(self.server.writes, 0)
        self.assertFalse(core._sync_pending(self.sid))
        self.assertIn("尚未完成", answer)

    async def test_old_read_receipt_does_not_discharge_post_update_read(self):
        action = await self.propose()
        prior = next(a for a in core._actions().records.values() if a["tool"] == READ)
        answer, _ = await self.chat("确认", [final("已经全部完成", "report", action_refs=[action["action_id"], prior["action_id"]])] * 2, "old-ref")
        self.assertEqual(self.server.writes, 1)
        self.assertEqual(len([c for c in self.server.calls if c["tool"] == "issue_read"]), 1)
        self.assertIn("尚未完成", answer)
        self.assertNotIn("已经全部完成", answer)
