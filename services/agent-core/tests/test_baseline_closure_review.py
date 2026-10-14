"""Independent boundary probes; run only through followup_regressions.py.

All endpoints are in-process synthetic fixtures. Each test retains its trace
and reopens only its own closed database with a read-only immutable connection.
"""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from agent_core import main as core
import test_baseline_closure as fixture
from test_a4_pilot import final


class PlainProvider:
    name = "independent-plain-provider"

    async def complete(self, messages):
        return json.dumps({"decision": {"mode": "chat"}, "reply": "FAKE-DONE 已经全部完成"}, ensure_ascii=False)


class IndependentClosureTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixture.BaselineClosureTests.setUp
    snapshot = fixture.BaselineClosureTests.snapshot
    text = fixture.BaselineClosureTests.text
    mutation = fixture.BaselineClosureTests.mutation
    read = fixture.BaselineClosureTests.read
    report = fixture.BaselineClosureTests.report
    chat = fixture.BaselineClosureTests.chat
    propose = fixture.BaselineClosureTests.propose
    finish = fixture.BaselineClosureTests.finish
    budget = fixture.BaselineClosureTests.budget

    def tearDown(self):
        state = self.snapshot()
        messages = [dict(row) for row in self.store.connection.execute("SELECT * FROM messages ORDER BY id")]
        events = [dict(row) for row in self.store.connection.execute("SELECT * FROM events ORDER BY id")]
        database = Path(self.store.path).resolve()
        self.assertTrue(database.is_relative_to(self.root.resolve()))
        self.store.close()
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        with sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True) as reopened:
            reopened.row_factory = sqlite3.Row
            saved = [json.loads(row[0]) for row in reopened.execute("SELECT payload FROM harness_actions")]
            self.assertEqual({item["action_id"]: item for item in saved},
                             {item["action_id"]: item for item in state["actions"]})
            self.assertEqual(messages, [dict(row) for row in reopened.execute("SELECT * FROM messages ORDER BY id")])
            self.assertEqual(events, [dict(row) for row in reopened.execute("SELECT * FROM events ORDER BY id")])
        after = hashlib.sha256(database.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        package = Path(core.__file__).parent
        evidence = {
            "test": self.id(), "trace": self.trace, "final": state,
            "source_sha256": {name: hashlib.sha256((package / name).read_bytes()).hexdigest()
                              for name in ("main.py", "verified_task.py", "task_delivery.py", "actions.py")},
            "immutable_reopen": {"database": str(database), "mode": "ro&immutable=1", "sha256": after,
                                 "actions": len(saved), "messages": len(messages), "events": len(events)},
            "model_http_calls": 0,
        }
        (self.root / "trace.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    async def test_pending_paraphrases_plain_provider_preserve_truth(self):
        for kind, wording in (("file", "继续处理刚才的任务"), ("issue", "麻烦接着完成刚才的事"),
                              ("email", "请继续执行上面的任务。")):
            with self.subTest(kind=kind, wording=wording):
                sid = self.store.create_session()["id"]
                item = await self.propose(kind, sid=sid)
                ticket, budget, effects = copy.deepcopy(item), self.budget(sid), copy.deepcopy(self.effects)
                with patch.object(core, "provider", PlainProvider()):
                    await core.handle_chat(wording, f"paraphrase-{sid}", sid, effort="deep")
                answer = self.store.load_messages(100, sid)[-1]["content"]
                self.trace.append({"input": wording, "session": sid, "answer": answer, **self.snapshot()})
                self.assertEqual(ticket, item)
                self.assertEqual(budget["id"], self.budget(sid)["id"])
                self.assertEqual(budget["budget"], self.budget(sid)["budget"])
                self.assertEqual(effects, self.effects)
                self.assertNotIn("FAKE-DONE", answer)
                self.assertIn("待确认", answer)

    async def test_file_pending_allows_explicit_unrelated_read_request(self):
        parked = await self.propose("file")
        before = copy.deepcopy(parked), self.budget(self.sid)
        await self.chat("先查看仓库 SummerTianYi/a4-synthetic 的 Issue #17 当前标题，只读即可。",
                        [self.read("issue"), self.read("issue")], model=self.b)
        reads = [a for a in core._sync_pending(self.sid) if a["tool"] == fixture.READ]
        self.assertEqual(1, len(reads), "Explicit read must still reach the ordinary ASK permission gate")
        self.assertEqual(before[0], parked)
        self.assertEqual(before[1]["id"], self.budget(self.sid)["id"])
        self.assertFalse(self.effects)
        answer = await self.chat("确认", [final("独立只读标题：合成初始标题", "report",
                                               action_refs=[reads[0]["action_id"]])],
                                 confirmation=core._actions().ticket(reads[0]), model=self.b)
        self.assertIn("合成初始标题", answer)
        self.assertEqual(parked["status"], "awaiting_confirmation")
        self.assertEqual([effect["tool"] for effect in self.effects], [fixture.READ])
        self.assertEqual(self.github.writes, 0)

    async def test_plain_conversation_with_pending_preserves_budget_and_text(self):
        item = await self.propose("file")
        before = copy.deepcopy(item), self.budget(self.sid)
        for message in ("今天想聊一聊洛天依的音乐", "解释一下为什么这些操作要确认",
                        "继续聊刚才的音乐吧", "请解释一下继续执行是什么意思", "“继续执行”是什么意思？"):
            answer = await self.chat(message, [final("独立正常回答 MUSIC-813")], model=self.b)
            self.assertEqual("独立正常回答 MUSIC-813", answer)
            self.assertEqual(before, (item, self.budget(self.sid)))
        self.assertFalse(self.effects)

    async def test_displayed_session_ticket_and_edit_revision_survive_replacement(self):
        other = self.store.create_session()["id"]
        old = await self.propose("email")
        parked = await self.propose("file", sid=other)
        old_ticket = copy.deepcopy(core._actions().ticket(old))
        self.mail = {**self.mail, "subject": "独立新主题 REV-991"}
        await self.chat("取消旧的，主题改为「独立新主题 REV-991」，其他要求不变。",
                        [self.mutation("email")], model=self.b)
        item = core._sync_pending(self.sid)[0]
        self.assertGreater(item["revision"], old["revision"])
        self.assertEqual(old["status"], "cancelled")
        event = [entry.args[1] for entry in core.hub.send_roles.await_args_list
                 if entry.args[1].get("type") == "permission.pending"
                 and entry.args[1].get("conversationId") == self.sid][-1]
        self.assertEqual(event["actions"][0]["action_id"], item["action_id"])
        self.assertEqual(core._shown_confirmations[self.sid], core._actions().ticket(item))
        before = self.budget(self.sid)
        for ticket in (old_ticket, core._actions().ticket(parked),
                       {**core._actions().ticket(item), "revision": item["revision"] + 1}):
            await self.chat("确认", confirmation=ticket, model=self.a)
            self.assertEqual(before, self.budget(self.sid))
            self.assertFalse(self.effects)
        await self.finish("email", model=self.b)
        self.assertEqual(self.gmail.mailbox[0]["arguments"]["subject"], "独立新主题 REV-991")
        self.assertEqual(parked["status"], "awaiting_confirmation")
        self.assertEqual(1, len(self.gmail.mailbox))

    async def test_success_paraphrase_does_not_start_duplicate_task(self):
        for kind in ("file", "issue", "email"):
            with self.subTest(kind=kind):
                sid = self.store.create_session()["id"]
                await self.propose(kind, sid=sid)
                await self.finish(kind, sid=sid)
                before, budget = copy.deepcopy(self.effects), self.budget(sid)
                await self.chat("接着处理刚才的任务吧", [self.mutation(kind), self.report(sid)], sid=sid, model=self.b)
                self.assertEqual(before, self.effects)
                self.assertEqual(budget["id"], self.budget(sid)["id"])
                self.assertEqual(budget["budget"], self.budget(sid)["budget"])
                self.assertFalse(core._sync_pending(sid))

    async def test_unknown_paraphrase_retains_budget_and_never_resends(self):
        for kind in ("file", "issue", "email"):
            with self.subTest(kind=kind):
                sid = self.store.create_session()["id"]
                item = await self.propose(kind, sid=sid)
                self.lose_file_receipt = kind == "file"
                self.github.lose_write_receipt = kind == "issue"
                self.gmail.lose_receipt = kind == "email"
                await self.chat("确认", [core.ProviderError("independent receipt loss")], sid=sid)
                self.assertEqual(item["status"], "unknown")
                before, budget = copy.deepcopy(self.effects), self.budget(sid)
                answer = await self.chat("请继续处理刚才的任务", [self.mutation(kind), final("已完成"), final("已完成")],
                                         sid=sid, model=self.b)
                self.assertEqual(before, self.effects)
                self.assertEqual(item["status"], "unknown")
                self.assertIn("未知", answer)
                self.assertEqual(budget["id"], self.budget(sid)["id"])
                self.assertEqual(budget["budget"], self.budget(sid)["budget"])
                self.assertGreaterEqual(self.budget(sid)["calls_used"], budget["calls_used"])
                self.lose_file_receipt = self.github.lose_write_receipt = self.gmail.lose_receipt = False
