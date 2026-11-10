import json
import os
import time
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from agent_core.chat_channels import classify
from agent_core.permissions import ASK, ActionRequest, PermissionEngine, PolicyRule
from agent_core.mcp_host import McpServer
import test_harness_v1_integration as fixtures
from public_query_fixture import lookup, native, script
from agent_core import public_query_turn

F1 = "你知道现在F1进行到哪一站了吗？积分情况如何"
AWARD = "这一届诺贝尔物理学奖是谁拿的？"
SOURCE = {"title":"合成赛事公报","url":"https://example.org/results","content":"蓝队以37分领先。"}
RESULT = {"ok":True,"sources":[SOURCE],"as_of":"2026-11-09"}


class QueryTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.MainActionTests.setUp

    def rig(self, ask=False, result=None, proposals=()):
        script(self,*proposals)
        self.transport = AsyncMock(return_value=result or RESULT)
        self.model = AsyncMock(return_value=json.dumps({"reply":"蓝队以37分领先。"},ensure_ascii=False))
        rules = PermissionEngine().rules
        if ask:
            rules.insert(0,PolicyRule("force-ask","public_web_search","user",ASK))
        for handle in [patch.dict(os.environ,{"TAVILY_API_KEY":"synthetic"}),patch.object(core,"permission_engine",PermissionEngine(rules)),
                       patch.object(core,"_execute_authorized_tool",self.transport),patch.object(core.provider,"complete",self.model)]:
            handle.start()
            self.addCleanup(handle.stop)

    async def say(self, text, rid, ticket=None):
        await core.handle_chat(text,rid,self.sid,confirmation=ticket)
        return self.store.load_messages(50,self.sid)[-1]["content"]

    def test_admission_and_private_boundaries(self):
        for text in (F1,AWARD,"现在英超的射手榜谁排第一？","查一下积分榜，先别发邮件"):
            with self.subTest(text=text):
                self.assertTrue(public_query_turn.offered(text,None,[]))
        for text in ("你现在开心吗？","他说“查一下积分榜”。","为什么读取文件需要授权？","今天排练取消了"):
            self.assertEqual(classify(text,pending=True,active=True).chat,text)
        for tool in ("public_web_search","mcp__search__tavily_search","mcp__gmail__read_email",
                     "mcp__drive__search","look_at_screen","mcp__x__read"):
            self.assertFalse(PermissionEngine().evaluate(ActionRequest(tool,{"query":"我的地址"},"agent",self.sid)).allowed)
        from agent_core import public_search as search
        for text,subject,field in (("你知道现在温布尔登网球公开赛的赛程吗？","温布尔登网球公开赛","赛程"),
                             ("请在公开网页搜索《火星探测任务最新进展》","火星探测任务最新进展","公开资料"),
                             ("你知道现在Python最新版本号吗？","Python","最新稳定版本")):
            args=lookup(subject,[field],evidence=text)
            self.assertEqual(public_query_turn.resolve(native(args),text,None,[]).lookup.subject,subject)
        for text,subject in (("请在公开网页搜索《同学的内部账号》","同学的内部账号"),
                             ("同事张明去了网球公开赛，查一下赛程","同事张明去了网球公开赛")):
            with self.assertRaises(ValueError):
                public_query_turn.resolve(native(lookup(subject,["公开资料"],evidence=text)),text,None,[])

    def test_fixed_transport_scope_is_required_before_any_allow(self):
        from agent_core import public_search as search
        question="现在F1的积分如何？我的门牌号是927，别发给 a@example.org"
        safe = public_query_turn.resolve(native(lookup(evidence="现在F1的积分如何")),question,None,[]).lookup.arguments()
        self.assertNotIn("927",str(safe))
        self.assertNotIn("@",str(safe))
        gate = PermissionEngine()
        self.assertFalse(gate.evaluate(ActionRequest(search.TOOL,safe,"user",self.sid,safe)).allowed)
        self.assertTrue(gate.evaluate(ActionRequest(search.TOOL,safe,"user",self.sid,safe,"query")).allowed)
        for args, origin, sid, scope in ((safe,"user",None,safe),(safe,"schedule",self.sid,safe),
                (safe,"user",self.sid,None),({**safe,"query":"private"},"user",self.sid,safe),
                ({**safe,"subject":"网盘"},"user",self.sid,safe),({**safe,"url":"https://example.org"},"user",self.sid,safe)):
            self.assertFalse(gate.evaluate(ActionRequest(search.TOOL,args,origin,sid,scope,"query")).allowed)

    async def test_normal_has_evidence_and_private_history_does_not_egress(self):
        self.rig()
        self.store.add_message("user","我的门牌号是合成巷927号","older",self.sid)
        answer=await self.say(F1,"query")
        self.assertTrue(self.transport.await_count)
        for call in self.transport.await_args_list:
            self.assertEqual(call.args[0],"public_web_search")
            self.assertNotIn("合成巷",str(call))
        self.assertIn("37",answer)
        self.assertIn(SOURCE["url"],answer)
        self.assertIn("2026-11-09",answer)
        self.assertNotIn("result_ref",answer)
        messages = self.model.await_args.args[0]
        self.assertEqual(messages[-1]["role"],"user")
        self.assertIn(SOURCE["content"],messages[-1]["content"])
        self.assertNotIn("合成巷",str(messages))
        self.transport.return_value={**RESULT,"sources":[{**SOURCE,"url":f"https://example.org/{i}"} for i in range(4)]}
        self.model.return_value=json.dumps({"reply":"最后一份公报更新了积分。","source_numbers":[1,2,3,4]})
        self.assertIn("https://example.org/3",await self.say(F1,"all-cited-sources"))

    async def test_legacy_connector_cannot_export_private_context_or_extra_filters(self):
        self.rig()
        core._task_state[self.sid]["intent"]="请搜索极光预报。我的门牌号是私巷927号。"
        for args in ({"query":"私巷927号"},{"query":"极光预报","include_domains":["private.example.org"]}):
            result = await core.run_tool("mcp__search__tavily_search",args)
            self.assertEqual(result["outcome"],"denied")
        self.assertFalse(core._actions().pending(self.sid))
        allowed=await core.run_tool("mcp__search__tavily_search",{"query":"极光预报"})
        self.assertTrue(allowed["needs_confirmation"])
        self.transport.assert_not_awaited()

    async def test_ask_chat_approve_and_duplicate(self):
        self.rig(ask=True,proposals=[lookup("诺贝尔物理学奖",["获奖理由及得主"])])
        before=await self.say(AWARD,"request")
        self.assertIn("诺贝尔",before)
        self.assertNotIn('{"',before)
        self.transport.assert_not_awaited()
        ticket=core._actions().ticket(core._actions().pending(self.sid)[0])
        await self.say("下午排练取消了","aside")
        await self.say("他说的“确认”是什么意思？","quote")
        await self.say("可以不发吗？","question")
        self.transport.assert_not_awaited()
        answer=await self.say("同意","confirm",ticket)
        self.assertIn("37",answer)
        self.assertIn(SOURCE["url"],answer)
        await self.say("确认","again",ticket)
        self.transport.assert_awaited_once()

    async def test_decline_expiry_and_distinct_questions(self):
        self.rig(ask=True,proposals=[lookup("诺贝尔物理学奖",["获奖理由及得主"]),lookup("F1",["赛程","积分榜"])])
        await self.say(AWARD,"first")
        await self.say("不同意","no")
        self.assertFalse(core._actions().pending(self.sid))
        self.transport.assert_not_awaited()
        await self.say(F1,"second")
        row=core._actions().pending(self.sid)[0]
        row["expires"]=time.time()-1
        answer=await self.say("确认","late",core._actions().ticket(row))
        self.assertIn("过期",answer)
        self.transport.assert_not_awaited()

    async def test_lookup_with_negative_clause_and_missing_recipient(self):
        self.rig(proposals=[{"mode":"clarify"},lookup("F1",["赛程","积分榜"]),lookup(),lookup()])
        self.assertIn("哪项赛事",await self.say("查一下积分榜","which"))
        await self.say(F1,"establish-sport")
        answer=await self.say("查一下积分榜，先别发邮件","lookup")
        self.assertIn("37",answer)
        self.assertFalse(core._actions().pending(self.sid))
        answer=await self.say("查一下积分榜并发给同学","share")
        self.assertIn("37",answer)
        self.assertIn("邮箱",answer)
        self.assertTrue(all(c.args[0]=="public_web_search" for c in self.transport.await_args_list))

    async def test_missing_key_is_not_consent(self):
        self.rig(ask=True)
        with patch.dict(os.environ,{"TAVILY_API_KEY":""}):
            answer=await self.say(F1,"missing")
        self.assertIn("配置",answer)
        self.assertFalse(core._actions().pending(self.sid))
        self.transport.assert_not_awaited()

    async def test_two_actions_require_selection(self):
        self.rig()
        book=core._actions()
        a=book.propose(self.sid,"one","one","mcp__gmail__send_email",{"to":["a@example.org"],"body":"甲"})
        b=book.propose(self.sid,"two","two","mcp__gmail__send_email",{"to":["b@example.org"],"body":"乙"})
        await core._publish_pending(self.sid)
        await self.say("确认","ambig")
        self.transport.assert_not_awaited()
        self.assertEqual(len(book.pending(self.sid)),2)
        await self.say("确认第2项","select")
        self.transport.assert_awaited_once_with(b["tool"],b["arguments"])
        self.assertEqual(book.pending(self.sid),[a])

    async def test_pending_lookup_duplicates_share_scope_but_different_facts_survive(self):
        award=lookup("诺贝尔物理学奖",["获奖理由及得主"])
        self.rig(ask=True,proposals=[award,award,lookup("F1",["赛程","积分榜"])])
        await self.say(AWARD,"one")
        first=core._actions().pending(self.sid)[0]
        await self.say("请查最近一届诺贝尔物理学奖得主","same")
        self.assertEqual(core._actions().pending(self.sid),[first])
        await self.say(F1,"second")
        pending=core._actions().pending(self.sid)
        self.assertEqual(len(pending),2)
        await self.say("确认","legacy-first",core._actions().ticket(first))
        self.transport.assert_not_awaited()
        await self.say("确认第2项","selected")
        self.transport.assert_awaited_once_with("public_web_search",pending[1]["arguments"])
        self.assertEqual(core._actions().pending(self.sid),[first])

    async def test_source_error_is_not_model_success(self):
        self.rig(result={"ok":False,"kind":"timeout","error":"Traceback internal.abc"})
        answer=await self.say(F1,"timeout")
        self.assertIn("超时",answer)
        self.assertNotIn("37",answer)
        self.assertNotIn("Traceback",answer)
        self.assertFalse(core._actions().pending(self.sid))

    async def test_query_and_mail_preview_edits_and_one_dispatch(self):
        self.rig()
        server=McpServer("gmail",[],tools=[{"name":"send_email","inputSchema":{"type":"object"}}],started=True)
        effects=[]
        async def dispatch(name,args):
            if name=="public_web_search":
                return RESULT
            effects.append((name,args))
            return {"ok":True,"output":"INTERNAL_MAIL_ACK","outcome":"succeeded"}
        self.transport.side_effect=dispatch
        with patch.dict(core.mcp_host.servers,{"gmail":server}):
            first=await self.say("查一下F1积分榜并发给同学","first")
            self.assertIn("37",first)
            self.assertIn("邮箱",first)
            preview=await self.say("one@example.org","address")
            self.assertIn("one@example.org",preview)
            self.assertIn("37",preview)
            book=core._actions()
            old=book.ticket(book.pending(self.sid)[0])
            await self.say("把收件人改成 two@example.org","edit")
            changed=book.pending(self.sid)[0]
            self.assertEqual(changed["arguments"]["to"],["two@example.org"])
            self.assertNotEqual(old["args_hash"],changed["args_hash"])
            await self.say("正文改成：周末一起看比赛。","edit-body")
            new=book.pending(self.sid)[0]
            await self.say("确认","stale",old)
            self.assertFalse(effects)
            self.assertIn("待确认",await self.say("当前任务进度如何？","status"))
            answer=await self.say("确认","yes",book.ticket(new))
            self.assertEqual(effects,[("mcp__gmail__send_email",new["arguments"])])
            self.assertEqual(new["arguments"]["body"],"周末一起看比赛。")
            self.assertNotIn("INTERNAL",answer)
            await self.say("确认","dup",book.ticket(new))
            self.assertEqual(len(effects),1)

    async def test_not_sending_is_enforced_at_dispatch_and_technical_payload_preserved(self):
        self.rig()
        goal="帮我写文件 draft.txt。不要发给任何人。"
        self.assertEqual(classify(goal,pending=False,active=False).operation,goal)
        core._task_state[self.sid]["intent"]=goal
        receipt=await core.run_tool("mcp__gmail__send_email",{"to":["guard@example.org"],"body":"私人内容"})
        self.assertEqual(receipt["outcome"],"denied")
        self.assertFalse(core._actions().pending(self.sid))
        self.transport.assert_not_awaited()
        data='{"width":"15cm","command":"get_time","value":"结果未知"}'
        self.model.return_value=json.dumps({"reply":data},ensure_ascii=False)
        self.assertEqual(await self.say("请给我一个 JSON 示例","json"),data)
        code="\x60\x60\x60python\nx = '2kg'\n\x60\x60\x60"
        self.model.return_value=json.dumps({"reply":code})
        self.assertEqual(await self.say("演示这段代码","code"),code)

    async def test_cancel_synonyms_and_explanatory_question(self):
        self.rig()
        for i,text in enumerate(("算了，先别寄出去。","那封邮件别发了。","别发了","这件事就此作罢")):
            action=core._actions().propose(self.sid,"mail"+str(i),"p","mcp__gmail__send_email",{"to":[f"x{i}@example.org"]})
            await core._publish_pending(self.sid)
            await self.say(text,"c"+str(i))
            self.assertEqual(action["status"],"cancelled",text)
        for text in ("打开文件会发生什么？","读取文件为什么要授权？","我现在看F1很开心。"):
            self.assertEqual(classify(text,pending=False,active=True).chat,text)
        self.transport.assert_not_awaited()

    async def test_delayed_speech_recovery_has_original_owner(self):
        from agent_core import chat_channels
        old=chat_channels.Turn(self.sid,"old")
        token=chat_channels.current.set(old)
        try:
            with patch.object(core,"_visible_turn",chat_channels.Turn(self.sid+1,"new")):
                await core._broadcast_speech_recovery("utterance","old")
                self.assertFalse(any(c.args[1]["type"]=="core.error" for c in core.hub.send_roles.await_args_list))
            with patch.object(core,"_visible_turn",old):
                await core._broadcast_speech_recovery("utterance","old")
                frame=core.hub.send_roles.await_args.args[1]
                self.assertEqual((frame["conversationId"],frame["turnId"],frame["foreground"]),(self.sid,"old",True))
        finally:
            chat_channels.current.reset(token)
