import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core, public_search
from agent_core.chat_channels import classify
from agent_core.permissions import ASK, PermissionEngine, PolicyRule
import test_harness_v1_integration as fixtures


class AdmissionTests(unittest.TestCase):
    def test_negatives_and_quotations_never_admit_a_lookup(self):
        samples = (
            "我不想知道现在F1积分如何。", "不用你替我上网查F1的积分。", "先不查英超赛程了。",
            "我没有让你搜索网页查F1积分榜。", "没必要查今年诺贝尔物理学奖得主。",
            "查一下F1积分，算了，不必上网了。", "F1的积分先不用去查。", "别帮我搜网页，我只想聊聊F1积分。",
            "请解释“现在F1积分如何”这句话。", "Can you explain ‘search the web for F1 standings’?",
            "我不是让你查现在的F1赛程。", "我没叫你再查F1的积分榜。",
            "请查F1积分，算了，不需要了。",
            "消息里写着 '查F1积分'。", "我没有要你查询F1赛程。",
            "请搜索网页查F1积分，算了。",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertIsNone(public_search.plan(text))
                self.assertEqual(classify(text, pending=True, active=True).chat, text)
                self.assertFalse(public_search.manual_query_allowed(text, {"query":"F1积分"}))

    def test_negative_scope_keeps_separate_positive_requests(self):
        for text, subject, fields in (
            ("别查赛程，只查F1积分榜。","F1",("积分榜",)),
            ("查一下F1积分，不要再搜赛程。","F1",("积分榜",)),
            ("别查F1积分，查一下英超赛程。","英超",("赛程",)),
            ("你能不能帮我查一下F1积分？","F1",("积分榜",)),
            ("请查F1积分，只报前两位，不提赛程。","F1",("积分榜",)),
            ("不用讲积分规则，告诉我现在F1下一站在哪？","F1",("赛程",)),
            ("你知不知道F1现在的积分榜？","F1",("积分榜",)),
            ("别查F1积分，查一下英超积分榜。","英超",("积分榜",)),
            ("查一下F1车手积分，不要查车队积分。","F1",("积分榜",)),
            ("查一下F1积分，算了，改查英超积分榜。","英超",("积分榜",)),
        ):
            with self.subTest(text=text):
                lookup = public_search.plan(text)
                self.assertIsNotNone(lookup)
                self.assertEqual((lookup.subject,lookup.fields),(subject,fields))
                self.assertEqual(classify(text,pending=False,active=False).operation,text)
        self.assertEqual(classify("别帮我查网页。请读取文件 note.txt",pending=False,active=False).operation,
                         "请读取文件 note.txt")

    def test_legacy_negative_tail_cannot_become_a_search(self):
        self.assertFalse(public_search.manual_query_allowed("请搜索极光预报。算了，不用联网。",
                                                            {"query":"极光预报"}))

    def test_historical_series_category_and_cutoff_reach_fixed_transport(self):
        from unittest.mock import MagicMock
        query = "查一下2024年F1车队积分榜，截至2024年6月18日，只报前两名。"
        scope = public_search.plan(query).arguments()
        self.assertEqual(scope,{"subject":"F1","fields":["车队积分榜"],"year":2024,"through":"2024-06-18"})
        self.assertTrue(public_search.valid(scope))
        self.assertFalse(public_search.valid({**scope,"through":"2024-13-98"}))
        self.assertIsNone(public_search.plan(query.replace("6月18","13月98")))
        with (patch.dict(os.environ,{"TAVILY_API_KEY":"synthetic"}),
              patch("urllib.request.build_opener") as opener):
            response=MagicMock()
            response.read.return_value=b'{"results":[]}'
            opened=opener.return_value.open
            opened.return_value.__enter__.return_value=response
            public_search.search(scope)
            body=json.loads(opened.call_args.args[0].data)
            self.assertIn("constructors",body["query"])
            self.assertEqual(body["end_date"],"2024-06-18")
            public_search.search(public_search.plan("请查2024年F1车手积分榜。").arguments())
            historical=json.loads(opened.call_args.args[0].data)
            self.assertIn("2024 F1 drivers",historical["query"])
            self.assertNotIn("as of",historical["query"])
            self.assertNotIn("end_date",historical)

    def test_mail_and_private_clause_only_stay_local(self):
        q = public_search.answer_question("请查F1积分榜。我的住址是合成巷927号。只列前三名，然后发给 x@example.org")
        self.assertIn("只列前三名",q)
        self.assertNotIn("927",q)
        self.assertNotIn("example.org",q)
        after_mail = public_search.answer_question("查F1积分并发给 x@example.org。回答只列前二。邮件正文：甲，乙。")
        self.assertIn("回答只列前二",after_mail)
        self.assertNotIn("乙",after_mail)
        self.assertNotIn("example.org",after_mail)


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.MainActionTests.setUp

    def rig(self, ask=False):
        self.transport = AsyncMock(return_value={"ok":True,"as_of":"2025-04-12","sources":[
            {"title":"合成计分表","field":"积分榜","url":"https://example.org/score","content":"周遥368分。"}]})
        self.model = AsyncMock(return_value=json.dumps({"reply":"周遥，368分。","source_numbers":[1],
            "emotion":"happy","emotion_intensity":0.73,"gesture":"nod","memory_candidate":"不应保存合成比赛事实"},ensure_ascii=False))
        rules = PermissionEngine().rules
        if ask:
            rules.insert(0, PolicyRule("force","public_web_search","user",ASK))
        for p in (patch.dict(os.environ,{"TAVILY_API_KEY":"synthetic"}),
                  patch.object(core,"permission_engine",PermissionEngine(rules)),
                  patch.object(core,"_execute_authorized_tool",self.transport),patch.object(core.provider,"complete",self.model)):
            p.start()
            self.addCleanup(p.stop)

    def last_event(self):
        return next(c.args[1] for c in reversed(core.hub.send_roles.await_args_list) if c.args[1]["type"]=="chat.response")

    async def test_original_constraints_in_solver_but_not_search(self):
        self.rig()
        text = "请查2025年F1车手积分。只报第二名；用表格，保留分数并注明是哪一轮。"
        self.store.add_message("user","我的旧门牌是4491。","past",self.sid)
        await core.handle_chat(text,"unique",self.sid)
        messages = self.model.await_args.args[0]
        self.assertIn(text,messages[-1]["content"])
        self.assertNotIn("4491",str(messages))
        self.assertNotIn("表格",str(self.transport.await_args))
        self.assertIn("368",self.last_event()["text"])

    async def test_approval_recovers_constraints_and_excludes_recipient(self):
        self.rig(ask=True)
        await core.handle_chat("查一下2025年F1积分，只报第二名。查好后发给 guest@example.org","start",self.sid)
        self.model.assert_not_awaited()
        await core.handle_chat("确认","approved",self.sid)
        messages = self.model.await_args.args[0]
        self.assertIn("只报第二名",messages[-1]["content"])
        self.assertNotIn("guest@example.org",str(messages))
        self.transport.assert_awaited_once()

    async def test_matching_ticket_uses_latest_presentation_without_double_dispatch(self):
        self.rig(ask=True)
        await core.handle_chat("查一下F1积分榜，只报榜首。","one",self.sid)
        await core.handle_chat("查一下F1积分榜，这次只报第二名。","two",self.sid)
        self.assertEqual(len(core._actions().pending(self.sid)),1)
        await core.handle_chat("同意","approve",self.sid)
        self.transport.assert_awaited_once()
        prompt=self.model.await_args.args[0][-1]["content"]
        self.assertIn("只报第二名",prompt)
        self.assertNotIn("只报榜首",prompt)

    async def test_avatar_fields_survive_delivery_without_memory_side_effect(self):
        self.rig()
        await core.handle_chat("现在F1积分如何？","emotion",self.sid)
        event = self.last_event()
        self.assertEqual((event["emotion"],event["emotion_intensity"],event["gesture"]),("happy",0.73,"nod"))
        self.assertFalse(self.store.connection.execute("SELECT 1 FROM facts").fetchone())

    async def test_muted_foreground_avatar_still_gets_expression_after_idle(self):
        self.rig()
        with (patch.object(core.hub,"role_count",return_value=1),
              patch.object(core,"_speak_reply",new_callable=AsyncMock) as speaker):
            await core.handle_chat("现在F1积分如何？","muted",self.sid)
        speaker.assert_not_awaited()
        events = [c.args[1] for c in core.hub.send_roles.await_args_list]
        idle = next(i for i,e in enumerate(events) if e.get("state")=="idle")
        commands = [e for e in events[idle+1:] if e["type"]=="avatar.command"]
        self.assertEqual([e["event"] for e in commands],["avatar.smile","avatar.nod"])
        self.assertEqual(commands[0]["payload"],{"intensity":0.73})

    async def test_negation_preserves_unrelated_pending_ticket(self):
        self.rig(ask=True)
        self.model.return_value = '{"reply":"好，我们聊聊。"}'
        row = core._actions().propose(self.sid,"separate","original","mcp__gmail__send_email",{"to":["holder@example.org"]})
        await core._publish_pending(self.sid)
        await core.handle_chat("不用你替我上网查F1的积分。","negative",self.sid)
        self.assertEqual(core._actions().pending(self.sid),[row])
        self.transport.assert_not_awaited()
        self.assertEqual(self.last_event()["channel"],"companion")

    async def test_explicit_withdrawal_only_revokes_matching_pending_read(self):
        self.rig(ask=True)
        await core.handle_chat("查一下F1积分榜。","lookup",self.sid)
        book = core._actions()
        pending = book.pending(self.sid)[0]
        other = book.propose(self.sid,"mail","earlier","mcp__gmail__send_email",{"to":["test@example.org"]})
        await core._publish_pending(self.sid)
        await core.handle_chat("先别查F1的积分了。","withdrawn",self.sid)
        self.assertEqual(pending["status"],"cancelled")
        self.assertEqual(book.pending(self.sid),[other])
        await core.handle_chat("确认","stale",self.sid,confirmation=book.ticket(pending))
        self.transport.assert_not_awaited()
        self.assertEqual(book.pending(self.sid),[other])

    async def test_withdrawal_matches_year_and_cutoff_without_revoking_other_reads(self):
        self.rig(ask=True)
        for i,question in enumerate(("查一下2025年F1积分榜。","查一下2024年F1积分榜，截至6月18日。",
                                     "查一下2024年F1积分榜，截至8月18日。")):
            await core.handle_chat(question,"read-"+str(i),self.sid)
        book=core._actions()
        rows=book.pending(self.sid)
        self.assertEqual(len(rows),3)
        await core.handle_chat("先别查2024年F1积分榜，截至6月18日的那份。","stop-june",self.sid)
        self.assertEqual([r["status"] for r in rows],["awaiting_confirmation","cancelled","awaiting_confirmation"])
        await core.handle_chat("不用查2023年F1积分榜。","absent",self.sid)
        self.assertEqual(book.pending(self.sid),[rows[0],rows[2]])
        self.transport.assert_not_awaited()

    async def test_summary_does_not_duplicate_its_date(self):
        self.rig()
        self.model.return_value='{"reply":"周遥368分。查询日期：2025-04-12。","source_numbers":[1]}'
        await core.handle_chat("查一下F1积分。","once",self.sid)
        self.assertEqual(self.last_event()["text"].count("2025-04-12"),1)
