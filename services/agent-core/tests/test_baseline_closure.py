"""Cross-flow boundaries through handle_chat; use the existing isolated runner.

Provider replacement here is ordinary test dependency injection, not a new
runtime switching feature. No intent, authorization, action or result is seeded.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from agent_core.actions import ActionLedger
from agent_core.storage import MemoryStore
from agent_core.tools import openai_tools_schema
from email_fixture import SEND, SyntheticGmail, request as email_request
from issue_fixture import SyntheticGitHub, request as issue_request
from test_a4_pilot import call, final

READ, WRITE = "mcp__github__issue_read", "mcp__github__issue_write"


class ControlledProvider:
    def __init__(self, name):
        self.name, self.turns, self.inputs = name, [], []

    async def complete_with_tools(self, messages, tools):
        self.inputs.append(copy.deepcopy(messages))
        if not self.turns:
            raise AssertionError("Unexpected model invocation: " + self.name)
        value = self.turns.pop(0)
        if isinstance(value, Exception):
            raise value
        return value() if callable(value) else value


class BaselineClosureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        isolated = Path(os.environ["ANIME_AGENT_DATA_DIR"]).resolve()
        self.assertEqual(Path(os.environ["ANIME_AGENT_CONFIG_PATH"]).resolve().parent, isolated)
        self.assertEqual(os.environ["LLM_PROVIDER"], "mock")
        self.root = isolated / "boundary" / self._testMethodName
        self.root.mkdir(parents=True, exist_ok=False)
        self.store = MemoryStore(data_dir=self.root / "db")
        self.addCleanup(self.store.close)
        self.github, self.gmail = SyntheticGitHub(), SyntheticGmail(self.root / "mailbox.json")
        host = self.github.host()
        host.servers["gmail"] = self.gmail
        registry = {k: v for k, v in core.tool_registry.items() if k in {"read_file", "write_file"}}
        self.effects, self.trace, self.serial = [], [], 0
        self.a, self.b = ControlledProvider("controlled-A"), ControlledProvider("controlled-B")
        original = core._execute_authorized_tool

        async def execute(name, args):
            self.effects.append({"tool": name, "arguments": copy.deepcopy(args)})
            result = await original(name, args)
            if name == "write_file" and getattr(self, "lose_file_receipt", False):
                raise TimeoutError("synthetic post-write loss")
            return result

        for name, value in (("memory", self.store), ("mcp_host", host), ("provider", self.a),
                            ("tool_registry", registry), ("tools_schema", openai_tools_schema(registry)),
                            ("_action_ledger", None), ("_task_state", {}), ("_pending_writes", {}),
                            ("_shown_confirmations", {}), ("_result_pages", {}),
                            ("chat_lock", asyncio.Lock()), ("TTS_ENABLED", False),
                            ("hub", type("Hub", (), {"send_roles": AsyncMock(), "role_count": lambda *_: 0})()),
                            ("broadcast_state", AsyncMock()), ("broadcast_behavior", AsyncMock()),
                            ("_spawn", lambda c: c.close()), ("_execute_authorized_tool", execute)):
            p = patch.object(core, name, value); p.start(); self.addCleanup(p.stop)
        p = patch.dict(os.environ, ANIME_AGENT_WRITE_ROOTS=str(self.root), ANIME_AGENT_TOOLS_ROOTS=str(self.root))
        p.start(); self.addCleanup(p.stop)
        p = patch.object(core.asyncio, "sleep", AsyncMock())  # Presentation pause only.
        p.start(); self.addCleanup(p.stop)
        core._actions()
        self.sid = self.store.create_session()["id"]
        self.path = self.root / "cross-flow.txt"
        self.body = "文件原文：Error 是数据\n末行 FILE-823 42kg"
        self.title = "交界核验 ISSUE-926"
        self.mail = dict(to=["boundary@example.invalid"], subject="邮件 MAIL-715", body="第一行 MAIL 原文\n第二行 取消只是正文")

    def snapshot(self):
        return {"tasks": copy.deepcopy(core._task_state), "actions": copy.deepcopy(list(core._actions().records.values())),
                "effects": copy.deepcopy(self.effects), "github": copy.deepcopy(self.github.calls),
                "mailbox": copy.deepcopy(self.gmail.mailbox), "shown": copy.deepcopy(core._shown_confirmations)}

    def tearDown(self):
        data = {"test": self.id(), "trace": self.trace, "final": self.snapshot(), "model_http_calls": 0}
        (self.root / "trace.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def text(self, kind):
        return (f"请创建文件 {self.path}，写入后实际读取该文件并展示完整内容。内容如下：\n{self.body}"
                if kind == "file" else issue_request(self.github.target, self.title) if kind == "issue"
                else email_request(self.mail["to"][0], self.mail["subject"], self.mail["body"]))

    def mutation(self, kind, **extra):
        name, args = (("write_file", dict(path=str(self.path), content=self.body)) if kind == "file"
                      else (WRITE, dict(self.github.target, method="update", title=self.title)) if kind == "issue"
                      else (SEND, self.mail))
        return call(name, **{**args, **extra})

    def read(self, kind):
        return call("read_file", path=str(self.path)) if kind == "file" else call(READ, **self.github.target, method="get")

    def report(self, sid):
        def response():
            task = core._task_state[sid]
            return final("模型摘要", "report", action_refs=[a["action_id"] for a in core._actions().task_items(sid, task["id"]) if a["status"] == "succeeded"],
                         read_refs=[r["result_ref"] for r in task.get("tool_results", [])])
        return response

    async def chat(self, text, turns=(), *, sid=None, model=None, **kwargs):
        sid = self.sid if sid is None else sid
        model = core.provider if model is None else model
        model.turns = list(turns)
        self.serial += 1
        rid = f"boundary-{sid}-{self.serial}"
        with patch.object(core, "provider", model):
            await core.handle_chat(text, rid, sid, effort="standard", **kwargs)
        answer = self.store.load_messages(100, sid)[-1]["content"]
        self.trace.append({"input": text, "request_id": rid, "session": sid, "provider": model.name,
                           "answer": answer, **self.snapshot()})
        return answer

    async def propose(self, kind, *, sid=None):
        sid = self.sid if sid is None else sid
        await self.chat(self.text(kind), [self.read(kind) if kind == "issue" else self.mutation(kind)], sid=sid)
        if kind == "issue":
            await self.chat("确认", [self.mutation(kind)], sid=sid)
        item = core._sync_pending(sid)[0]
        self.assertEqual(item["tool"], {"file": "write_file", "issue": WRITE, "email": SEND}[kind])
        self.assertEqual(core._shown_confirmations[sid], core._actions().ticket(item))
        return item

    async def finish(self, kind, *, sid=None, model=None):
        sid = self.sid if sid is None else sid
        if kind == "file":
            answer = await self.chat("确认", [self.read(kind), self.report(sid)], sid=sid, model=model)
        elif kind == "issue":
            await self.chat("确认", [self.read(kind)], sid=sid, model=model)
            answer = await self.chat("确认", [self.report(sid)], sid=sid, model=model)
        else:
            answer = await self.chat("确认", [self.report(sid)], sid=sid, model=model)
        self.assertIn({"file": "文件任务已完成", "issue": "Issue 任务已完成", "email": "发送请求已受理"}[kind], answer)
        return answer

    def budget(self, sid):
        return {k: copy.deepcopy(core._task_state[sid].get(k)) for k in ("id", "budget", "rounds_used", "calls_used", "corrections_used")}

    async def test_three_flows_sequential_and_reopened(self):
        tasks, answers = [], []
        for kind in ("file", "issue", "email"):
            await self.propose(kind)
            answers.append(await self.finish(kind))
            tasks.append(copy.deepcopy(core._task_state[self.sid]))
        self.assertEqual(len({t["id"] for t in tasks}), 3)
        self.assertEqual([set(t) & {"file_delivery", "file_request_text", "issue_contract", "email_contract"} for t in tasks],
                         [{"file_delivery", "file_request_text"}, {"issue_contract"}, {"email_contract"}])
        for task in tasks:
            self.assertTrue(all(r["task_id"] == task["id"] and r["session_id"] == self.sid for r in task.get("tool_results", [])))
        self.assertEqual(self.path.read_bytes(), self.body.encode())
        self.assertEqual(self.github.writes, 1)
        self.assertEqual(self.gmail.mailbox[0]["arguments"], self.mail)
        self.assertIn(self.body, answers[0]); self.assertNotIn(self.body, answers[1])
        self.assertIn(self.title, answers[1]); self.assertNotIn(self.title, answers[2])
        self.assertIn(self.gmail.mailbox[0]["id"], answers[2])
        before = self.snapshot()
        await self.chat("确认", model=self.b)
        await self.chat("刚才那个任务现在怎么样？", model=self.b)
        self.assertEqual(before["effects"], self.effects)
        reopened = MemoryStore(data_dir=self.root / "db")
        try:
            self.assertEqual(list(ActionLedger(reopened.connection).records.values()), list(core._actions().records.values()))
            self.assertEqual(reopened.load_messages(100, self.sid), self.store.load_messages(100, self.sid))
        finally:
            reopened.close()

    async def test_previous_success_and_foreign_references_do_not_complete_next_task(self):
        await self.propose("file"); await self.finish("file")
        old = copy.deepcopy(core._task_state[self.sid])
        refs = [a["action_id"] for a in core._actions().task_items(self.sid, old["id"])]
        for kind in ("issue", "email", "file"):
            for reply in (final("已完成", "chat"), final("已完成", "report", action_refs=refs, read_refs=[old["tool_results"][0]["result_ref"]])):
                effects = copy.deepcopy(self.effects)
                answer = await self.chat(self.text(kind), [reply, reply], model=self.b)
                self.assertIn("尚未完成", answer)
                self.assertEqual(self.effects, effects)
                self.assertFalse(core._sync_pending(self.sid))

    async def test_two_sessions_confirm_only_the_displayed_owned_ticket(self):
        other = self.store.create_session()["id"]
        left = await self.propose("file")
        right = await self.propose("email", sid=other)
        for sid, foreign in ((self.sid, right), (other, left)):
            before = self.budget(sid)
            await self.chat("确认", sid=sid, model=self.b, confirmation=core._actions().ticket(foreign))
            self.assertEqual(before, self.budget(sid))
        self.assertFalse(self.effects)
        await self.finish("email", sid=other, model=self.b)
        self.assertEqual(left["status"], "awaiting_confirmation")
        self.assertFalse(self.path.exists())
        await self.finish("file", model=self.b)
        before = copy.deepcopy(self.effects)
        await self.chat("确认", model=self.a)
        await self.chat("确认", sid=other, model=self.a)
        self.assertEqual(before, self.effects)

    async def test_cancel_edit_isolated_between_issue_and_email_sessions(self):
        other = self.store.create_session()["id"]
        left = await self.propose("issue")
        old = await self.propose("email", sid=other)
        ticket = core._actions().ticket(old)
        before = copy.deepcopy(left), self.budget(self.sid)
        self.mail = {**self.mail, "subject": "新版 MAIL-716"}
        await self.chat("取消旧的，主题改为「新版 MAIL-716」，其他要求不变。", [self.mutation("email")], sid=other, model=self.b)
        self.assertEqual(old["status"], "cancelled")
        self.assertEqual(before, (left, self.budget(self.sid)))
        await self.chat("确认", sid=other, confirmation=ticket)
        self.assertFalse(self.gmail.mailbox)
        await self.chat("取消，不执行", [final("已完成")], sid=self.sid, model=self.b)
        self.assertEqual(left["status"], "cancelled")
        await self.finish("email", sid=other)
        self.assertEqual(self.github.writes, 0)

    async def test_provider_replacement_pending_does_not_expand_authorization(self):
        for kind in ("file", "issue", "email"):
            sid = self.store.create_session()["id"]
            item = await self.propose(kind, sid=sid)
            before = copy.deepcopy(item), self.budget(sid)
            core.provider = self.b
            await self.chat("刚才那个任务现在怎么样？", sid=sid)
            await self.chat("今天聊聊音乐吧", [final("一起聊音乐。")], sid=sid)
            self.assertEqual(before, (item, self.budget(sid)))
            answer = await self.finish(kind, sid=sid)
            self.assertTrue(answer)
            self.assertEqual(item["status"], "succeeded")
            self.assertEqual(before[1]["id"], self.budget(sid)["id"])
            self.assertEqual(before[1]["budget"], self.budget(sid)["budget"])

    async def test_provider_replacement_success_duplicate_calls_do_not_reexecute(self):
        for kind in ("file", "issue", "email"):
            sid = self.store.create_session()["id"]
            await self.propose(kind, sid=sid); await self.finish(kind, sid=sid)
            before, budget = copy.deepcopy(self.effects), self.budget(sid)
            core.provider = self.b
            await self.chat("确认", sid=sid)
            self.assertEqual(budget, self.budget(sid))
            await self.chat("继续", [self.mutation(kind), self.report(sid)], sid=sid)
            self.assertEqual(before, self.effects)
            after = self.budget(sid)
            self.assertEqual(budget["id"], after["id"])
            self.assertEqual(budget["budget"], after["budget"])
            self.assertGreaterEqual(after["rounds_used"], budget["rounds_used"])
            self.assertLessEqual(after["rounds_used"], after["budget"]["max_steps"])

    async def test_provider_replacement_unknown_no_resend_or_budget_refill(self):
        for kind in ("file", "issue", "email"):
            sid = self.store.create_session()["id"]
            item = await self.propose(kind, sid=sid)
            self.lose_file_receipt = kind == "file"
            self.github.lose_write_receipt = kind == "issue"
            self.gmail.lose_receipt = kind == "email"
            await self.chat("确认", [core.ProviderError("synthetic followup timeout")], sid=sid)
            self.assertEqual(item["status"], "unknown")
            before, budget = copy.deepcopy(self.effects), self.budget(sid)
            core.provider = self.b
            answer = await self.chat("继续", [self.mutation(kind), final("成功", "chat"), final("成功", "chat")], sid=sid)
            self.assertIn("未知", answer)
            self.assertEqual(before, self.effects)
            self.assertEqual(item["status"], "unknown")
            self.assertEqual(budget["id"], self.budget(sid)["id"])
            self.assertEqual(budget["budget"], self.budget(sid)["budget"])
            self.assertGreaterEqual(self.budget(sid)["calls_used"], budget["calls_used"])
            self.lose_file_receipt = self.github.lose_write_receipt = self.gmail.lose_receipt = False

    async def test_cross_flow_duplicate_tool_must_not_create_unrelated_ticket(self):
        await self.propose("email"); await self.finish("email")
        before = len(core._actions().records)
        answer = await self.chat(self.text("file"), [self.mutation("email"), self.mutation("email")], model=self.b)
        self.assertEqual(len(core._actions().records), before)
        self.assertFalse(core._sync_pending(self.sid))
        self.assertIn("尚未完成", answer)
        self.assertEqual(len(self.gmail.mailbox), 1)

    async def test_provider_without_tools_does_not_discard_pending_or_refill_budget(self):
        class PlainProvider:
            name = "controlled-no-tools"
            async def complete(self, messages):
                return json.dumps({"decision": {"mode": "chat"}, "reply": "文件已经完成"}, ensure_ascii=False)

        item = await self.propose("file")
        before, budget = copy.deepcopy(item), self.budget(self.sid)
        with patch.object(core, "provider", PlainProvider()):
            await core.handle_chat("继续", "without-tools", self.sid, effort="deep")
        self.assertEqual(item, before)
        self.assertEqual(budget["id"], self.budget(self.sid)["id"])
        self.assertEqual(budget["budget"], self.budget(self.sid)["budget"])
        self.assertFalse(self.effects)
        self.assertNotIn("文件已经完成", self.store.load_messages(100, self.sid)[-1]["content"])
        await self.finish("file", model=self.b)

    async def test_plain_chat_explanations_and_required_clarification_after_flow(self):
        await self.propose("email"); await self.finish("email")
        for text in ("今天聊聊音乐吧", "请解释写文件、改Issue标题和发邮件为什么需要确认"):
            self.assertEqual(await self.chat(text, [final("先核对参数，再正常确认。")], model=self.b), "先核对参数，再正常确认。")
        for text, name, arguments, missing in (
            ("请创建一个文件，再读取并展示完整内容", "write_file", {}, ["path", "content"]),
            ("请修改Issue标题后重新读取核验", WRITE, {"method": "update"}, ["owner", "repo", "issue_number", "title"]),
            ("请发送一封纯文本邮件", SEND, {}, ["to", "subject", "body"])):
            answer = await self.chat(text, [final("", "clarify", tool=name, arguments=arguments, missing=missing)], model=self.b)
            self.assertIn("还需要", answer)
            self.assertFalse(core._sync_pending(self.sid))
        self.assertEqual(len(self.gmail.mailbox), 1)
