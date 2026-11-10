import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core, public_search, public_query_turn as query
from agent_core.actions import ActionLedger
from agent_core.permissions import ASK, DENY, PermissionEngine, PolicyRule
from public_query_fixture import lookup, native
from test_harness_v1_integration import MainActionTests as _Fixture


class PublicWireTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_proposal_rejects_error_response_with_a_call(self):
        options = dict(name="fixture", base_url="https://example.invalid", model="fixture",
                       api_key="offline", timeout_seconds=1)
        arguments = lookup(evidence="查一下 F1 积分榜")
        function = {"name": query.NAME, "arguments": json.dumps(arguments)}
        message = {"role": "assistant", "tool_calls": [{"id": "one", "type": "function", "function": function}]}
        records = [
            (core.OpenAICompatibleProvider, {"choices": [{"message": message}]}),
            (core.AnthropicCompatibleProvider, {"content": [{"type": "tool_use", "id": "one",
                                                              "name": query.NAME, "input": arguments}]}),
        ]
        for adapter, payload in records:
            with self.subTest(adapter=adapter.__name__):
                provider = adapter(**options)
                wire = json.dumps({"error": {"type": "request_failed"}, **payload}).encode()
                with patch.object(provider, "_send_with_config_reload", new_callable=AsyncMock, return_value=wire):
                    with self.assertRaises(core.ProviderError):
                        await provider.complete_with_tools([{"role": "user", "content": "查一下 F1 积分榜"}], [query.SCHEMA])


class PublicTurnTests(unittest.IsolatedAsyncioTestCase):
    setUp = _Fixture.setUp

    async def rig(self, *, rule=ASK, extra_mail=False, prior_subject="F1"):
        self.dispatch=AsyncMock(return_value={"ok":False,"kind":"empty"})
        self.propose=AsyncMock()
        rules=PermissionEngine().rules
        rules.insert(0,PolicyRule("isolated",public_search.TOOL,"user",rule))
        for handle in (patch.dict(os.environ,{"TAVILY_API_KEY":"synthetic"}), patch.object(core,"permission_engine",PermissionEngine(rules)),
                       patch.object(core,"_execute_authorized_tool",self.dispatch),
                       patch.object(core.provider,"complete_with_tools",self.propose,create=True)):
            handle.start()
            self.addCleanup(handle.stop)
        self.book=core._actions()
        self.original=None
        if prior_subject:
            scope={"subject":prior_subject,"fields":["积分榜"],"year":public_search.date.today().year}
            self.original=self.book.propose(self.sid,"old","first",public_search.TOOL,scope)
            self.original.update(intent=f"请查{prior_subject}积分榜",public_scope=scope)
            self.book.save(self.original)
        if extra_mail:
            self.mail=self.book.propose(self.sid,"mail","other","mcp__gmail__send_email",{"body":"消息正文不得进入提案"})
        await core._publish_pending(self.sid)

    async def test_pause_and_denial_invalidate_the_exact_ticket(self):
        await self.rig(extra_mail=True)
        for i,text in enumerate(("我没有同意你去查 F1 积分榜","请暂停查询 F1 积分榜","一级方程式的排名，先搁一下")):
            if i:
                scope=self.original["arguments"]
                self.original=self.book.propose(self.sid,str(i),"new",public_search.TOOL,scope)
                await core._publish_pending(self.sid)
            ticket=self.book.ticket(self.original)
            self.propose.return_value=native({"mode":"withdraw","ticket":1,"reference":"一级方程式" if i==2 else "F1"})
            await core.handle_chat(text,"stop"+str(i),self.sid)
            messages, schemas=self.propose.await_args.args
            self.assertEqual(messages[-1]["content"],text)
            self.assertNotIn("消息正文不得进入提案",str(messages))
            self.assertEqual(len(schemas),1)
            self.assertEqual(ActionLedger(self.store.connection).records[ticket["action_id"]]["status"],"cancelled")
            await core.handle_chat("确认","repeat"+str(i),self.sid,confirmation=ticket)
        self.assertEqual(self.book.pending(self.sid),[self.mail])
        self.dispatch.assert_not_awaited()

    async def test_replace_and_reconfirm_only_the_new_public_subject(self):
        await self.rig()
        text="别查 F1，改查英超"
        self.propose.return_value=native(lookup("英超", mode="replace",ticket=1,reference="F1",evidence="改查英超"))
        await core.handle_chat(text,"switch",self.sid)
        new,=self.book.pending(self.sid)
        self.assertEqual(new["arguments"],{"subject":"英超","fields":["积分榜"],"year":public_search.date.today().year})
        self.assertEqual(self.original["status"],"cancelled")
        await core.handle_chat("确认","stale",self.sid,confirmation=self.book.ticket(self.original))
        self.dispatch.assert_not_awaited()
        for rid in ("yes","again"):
            await core.handle_chat("确认",rid,self.sid,confirmation=self.book.ticket(new))
        self.dispatch.assert_awaited_once_with(public_search.TOOL,new["arguments"])
        self.propose.assert_awaited_once()

    async def test_replacement_is_subject_to_fresh_permission(self):
        await self.rig(rule=DENY)
        self.propose.return_value=native(lookup("英超",mode="replace",ticket=1,reference="F1",evidence="只看英超"))
        await core.handle_chat("F1那项撤回，只看英超的积分。","denied",self.sid)
        self.assertEqual(self.original["status"],"cancelled")
        self.assertFalse(self.book.pending(self.sid))
        self.dispatch.assert_not_awaited()

    async def test_unresolved_or_malformed_proposals_have_no_effect(self):
        await self.rig()
        text="别查 F1，改查英超"
        valid=lookup("英超",mode="replace",ticket=1,reference="F1",evidence="改查英超")
        for i,output in enumerate((
            {"content":"已取消。","tool_calls":[]},native({"mode":"clarify"}),
            native({**valid,"ticket":2}),native({**valid,"subject":"用户家里的网盘"}),
            native({**valid,"fields":["私人邮件"]}), native({**valid,"subject":"NBA"}),
            {"tool_calls":native(valid)["tool_calls"]*2},
            {"tool_calls":[{"name":"mcp__gmail__send_email","arguments":{}}]})):
            self.propose.return_value=output
            await core.handle_chat(text,"bad"+str(i),self.sid)
            self.assertEqual(self.book.pending(self.sid),[self.original])
            self.assertNotIn("已取消",self.store.load_messages(1,self.sid)[-1]["content"])
        # Quoting only a shared field is insufficient when the user named another event.
        self.propose.return_value=native({"mode":"withdraw","ticket":1,"reference":"积分榜"})
        for i,other in enumerate(("先停一下英超的积分榜","温布尔登网球公开赛的积分榜先别查")):
            await core.handle_chat(other,"other-event"+str(i),self.sid)
            self.assertEqual(self.book.pending(self.sid),[self.original])
        self.propose.side_effect=core.ProviderError("offline")
        await core.handle_chat(text,"offline",self.sid)
        self.assertEqual(self.book.pending(self.sid),[self.original])
        self.dispatch.assert_not_awaited()

    async def test_confirmation_arriving_while_withdrawal_is_parsed_is_stale(self):
        await self.rig()
        started,release=asyncio.Event(),asyncio.Event()
        async def delayed(*_args):
            started.set()
            await release.wait()
            return native({"mode":"withdraw","ticket":1,"reference":"F1"})
        self.propose.side_effect=delayed
        first=asyncio.create_task(core.handle_chat("请暂停查询 F1 积分榜","stop",self.sid))
        await asyncio.wait_for(started.wait(),2)
        second=asyncio.create_task(core.handle_chat("确认","late",self.sid,confirmation=self.book.ticket(self.original)))
        await asyncio.sleep(0)
        release.set()
        await asyncio.wait_for(asyncio.gather(first,second),2)
        self.assertEqual(self.original["status"],"cancelled")
        self.dispatch.assert_not_awaited()

    async def submit_while_locked(self, *turns):
        queued = []
        async with core.chat_lock:
            for text, request, ticket in turns:
                queued.append(asyncio.create_task(core.handle_chat(text, request, self.sid, confirmation=ticket)))
                await asyncio.sleep(0)  # Let this input reach the lock before admitting the next one.
                arrived = self.store.connection.execute(
                    "SELECT request_id FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 1", (self.sid,)
                ).fetchone()
                self.assertEqual(arrived[0], request)
        await asyncio.wait_for(asyncio.gather(*queued), 3)

    async def add_league_ticket(self):
        scope = {**self.original["arguments"], "subject":"英超"}
        other = self.book.propose(self.sid, "league", "seed", public_search.TOOL, scope)
        other.update(public_scope=scope, intent="查英超积分榜")
        self.book.save(other)
        await core._publish_pending(self.sid)
        return other

    async def test_queued_f1_approval_then_pause_never_dispatches_search(self):
        execute = core._execute_authorized_tool
        await self.rig(extra_mail=True)
        other = await self.add_league_ticket()
        self.dispatch.side_effect = execute
        self.propose.return_value = native({"mode":"withdraw","ticket":1,"reference":"F1"})
        with patch.object(public_search, "search", return_value={"ok":False, "kind":"empty"}) as search:
            old = self.book.ticket(self.original)
            await self.submit_while_locked(("确认第1项", "old", old), ("请暂停查询 F1 积分榜", "pause", None))
            self.assertEqual(search.call_count, 0, "queued F1 approval reached the search worker")
            self.assertNotIn("execution_id", self.original)
            self.assertEqual(ActionLedger(self.store.connection).records[old["action_id"]]["status"], "cancelled")
            self.assertEqual(self.book.pending(self.sid), [self.mail, other])
            await core.handle_chat("确认", "old-repeat", self.sid, confirmation=old)
            fresh = self.book.ticket(other)
            await self.submit_while_locked(("确认第2项", "new", fresh), ("确认第2项", "repeat", fresh))
            search.assert_called_once_with(other["arguments"])
            self.assertEqual(self.book.pending(self.sid), [self.mail])

    async def test_pause_received_after_lock_grant_before_dispatch(self):
        await self.rig()
        entered, release = asyncio.Event(), asyncio.Event()
        async def broadcast(state, request):
            if (state, request) == ("thinking", "old"):
                entered.set()
                await release.wait()
        self.propose.return_value = native({"mode":"withdraw","ticket":1,"reference":"F1"})
        with patch.object(core, "broadcast_state", side_effect=broadcast):
            first = asyncio.create_task(core.handle_chat("确认", "old", self.sid, confirmation=self.book.ticket(self.original)))
            await asyncio.wait_for(entered.wait(), 2)
            later = asyncio.create_task(core.handle_chat("请暂停查询 F1 积分榜", "pause", self.sid))
            await asyncio.sleep(0)
            self.assertFalse(self.dispatch.called)
            release.set()
            await asyncio.wait_for(asyncio.gather(first, later), 3)
        self.dispatch.assert_not_awaited()
        self.assertEqual(self.original["status"], "cancelled")

    async def test_unclear_overlapping_turn_holds_only_the_queued_confirmation(self):
        await self.rig()
        old = self.book.ticket(self.original)
        parsing, release = asyncio.Event(), asyncio.Event()
        async def reviews(messages, _tools):
            if messages[-1]["content"].startswith("室友"):
                parsing.set()
                await release.wait()
                return native({"mode":"keep"})
            raise core.ProviderError("fixture")
        self.propose.side_effect = reviews
        async with core.chat_lock:
            approval = asyncio.create_task(core.handle_chat("确认", "old", self.sid, confirmation=old))
            await asyncio.sleep(0)
            quote = asyncio.create_task(core.handle_chat("室友说“别查 F1”，我只是转述。", "quote1", self.sid))
            await asyncio.sleep(0)
        await asyncio.wait_for(parsing.wait(), 2)
        pause = asyncio.create_task(core.handle_chat("请暂停查询 F1 积分榜", "unclear", self.sid))
        await asyncio.sleep(0)
        release.set()
        await asyncio.wait_for(asyncio.gather(approval, quote, pause), 3)
        self.dispatch.assert_not_awaited()
        self.assertEqual(self.book.pending(self.sid), [self.original])
        self.propose.side_effect = None
        self.propose.return_value = native({"mode":"keep"})
        await self.submit_while_locked(("确认", "fresh", old), ("室友说“别查 F1”，我只是转述。", "quote", None))
        self.dispatch.assert_awaited_once_with(public_search.TOOL, self.original["arguments"])

    async def test_queued_unrelated_confirmation_runs_once_when_f1_is_paused(self):
        await self.rig(extra_mail=True)
        other = await self.add_league_ticket()
        ticket = self.book.ticket(other)
        self.propose.return_value = native({"mode":"withdraw", "ticket":1, "reference":"F1"})
        await self.submit_while_locked(("确认第3项", "league-first", ticket), ("请暂停查询 F1 积分榜", "stop", None),
                                       ("确认第3项", "league-repeat", ticket))
        self.dispatch.assert_awaited_once_with(public_search.TOOL, other["arguments"])
        self.assertEqual(other["confirmation_request_id"], "league-first")
        self.assertEqual(self.original["status"], "cancelled")
        self.assertEqual(self.book.pending(self.sid), [self.mail])

    async def test_pause_after_dispatch_preserves_original_receipt(self):
        await self.rig()
        started, finish = asyncio.Event(), asyncio.Event()
        async def search(_name, _args):
            started.set()
            await finish.wait()
            return {"ok":False, "kind":"empty"}
        self.dispatch.side_effect = search
        self.propose.return_value = native({"mode":"keep"})
        ticket = self.book.ticket(self.original)
        approval = asyncio.create_task(core.handle_chat("确认", "sent", self.sid, confirmation=ticket))
        await asyncio.wait_for(started.wait(), 2)
        self.assertEqual(self.original["status"], "executing")
        pause = asyncio.create_task(core.handle_chat("请暂停查询 F1 积分榜", "pause", self.sid))
        await asyncio.sleep(0)
        finish.set()
        await asyncio.wait_for(asyncio.gather(approval, pause), 3)
        self.dispatch.assert_awaited_once_with(public_search.TOOL, self.original["arguments"])
        self.assertEqual(self.original["status"], "failed")
        self.assertEqual(self.original["receipt"]["kind"], "empty")

    async def test_plain_chat_proposal_cannot_claim_to_cancel_a_live_ticket(self):
        await self.rig()
        self.propose.return_value=native({"mode":"chat"})
        core.provider.complete.return_value='{"reply":"已经替你取消查询了。"}'
        await core.handle_chat("我没有同意你去查 F1 积分榜","untrusted-chat",self.sid)
        self.assertEqual(self.book.pending(self.sid),[self.original])
        self.assertNotIn("替你取消", self.store.load_messages(1,self.sid)[0]["content"])
        self.dispatch.assert_not_awaited()

    async def test_topic_change_and_implicit_withdrawal_while_a_public_ticket_is_open(self):
        await self.rig()
        self.propose.return_value=native({"mode":"chat"})
        core.provider.complete.return_value='{"reply":"排练辛苦啦。"}'
        await core.handle_chat("我今天排练到很晚。","chat",self.sid)
        self.assertEqual(self.store.load_messages(1,self.sid)[0]["content"],"排练辛苦啦。")
        self.assertEqual(self.book.pending(self.sid),[self.original])
        self.propose.return_value=native({"mode":"withdraw","ticket":1,"reference":"刚才的"})
        await core.handle_chat("先把刚才的搁下吧。","implicit",self.sid)
        self.assertEqual(self.original["status"],"cancelled")
        self.propose.return_value=native({"mode":"keep"})
        await core.handle_chat("我可没答应查 F1 积分榜。","no-ticket",self.sid)
        self.assertFalse(self.book.pending(self.sid))
        self.dispatch.assert_not_awaited()

    def test_new_target_needs_a_field_and_does_not_inherit_an_unrelated_season(self):
        previous={"subject":"F1","fields":["积分榜"],"year":2024}
        with self.assertRaises(ValueError):
            query.resolve(native(lookup("英超",evidence="改查英超")),"改查英超",None,[])
        text="查一下 Godot 的稳定版号"
        actual=query.resolve(native(lookup("Godot",["最新稳定版本"],evidence=text)),text,previous,[])
        self.assertEqual(actual.lookup.year,public_search.date.today().year)


del _Fixture
