"""Exercise public chat handling with synthetic data, a real ledger and controlled replies."""
import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from test_harness_v1_integration import MainActionTests as _Fixture

class ChannelTests(unittest.IsolatedAsyncioTestCase):
    setUp = _Fixture.setUp

    def provider(self, body, calls=()):
        schemas = [{"type": "function", "function": {"name": "write_file", "parameters": {
            "type": "object", "properties": {"path": {"type":"string"}, "content":{"type":"string"}},
            "required":["path","content"]}}}]
        p = SimpleNamespace(complete=AsyncMock(return_value=json.dumps(body, ensure_ascii=False)),
                            complete_with_tools=AsyncMock(return_value={"content": json.dumps(body, ensure_ascii=False),
                                                                       "tool_calls": list(calls)}))
        for k, value in (("provider",p),("tools_schema",schemas)):
            handle=patch.object(core,k,value);handle.start();self.addCleanup(handle.stop)
        return p

    def delivered(self, rid):
        return [call.args[1] for call in core.hub.send_roles.await_args_list
                if call.args[1].get("type") == "chat.response" and call.args[1].get("request_id")==rid]

    async def test_conversation_has_no_tool_capability(self):
        p=self.provider({"reply":"它这个店长当得还挺稳。"},[{"id":"extra","name":"write_file","arguments":{
            "path":str(self.root/"mistake.txt"),"content":"unexpected"}}])
        await core.handle_chat("店员还得从它旁边跨过去。","cat",self.sid)
        self.assertFalse(core._actions().pending(self.sid))
        self.assertEqual(p.complete.await_count,1)
        p.complete_with_tools.assert_not_awaited()
        self.assertEqual(self.delivered("cat")[0]["text"],"它这个店长当得还挺稳。")

    async def test_rejecting_advice_keeps_exact_pending_ticket(self):
        book=core._actions()
        row=book.propose(self.sid,"t","ask","write_file",{"path":str(self.root/"a"),"content":"a"})
        before=book.ticket(row)
        self.provider({"reply":"嗯，我听着。"})
        await core.handle_chat("我不想听建议，也先别问我问题。","no-advice",self.sid)
        self.assertEqual(book.ticket(book.pending(self.sid)[0]),before)
        self.assertEqual(self.delivered("no-advice")[0]["text"],"嗯，我听着。")

    async def test_failed_memory_save_keeps_chat_and_separate_receipt(self):
        self.provider({"reply":"这枚书签配蓝纸很好看。已经帮你记住了。","memory_candidate":"用户喜欢蓝色书签"})
        with patch.object(self.store,"add_fact",side_effect=OSError("synthetic disk full")):
            await core.handle_chat("记住我喜欢蓝色书签。今天的蓝纸很好看。","save",self.sid)
        items=self.delivered("save")
        self.assertIn("这枚书签配蓝纸很好看。",[x["text"] for x in items if x["channel"]=="companion"])
        self.assertTrue(any(x["channel"]=="memory" and "核验" in x["text"] for x in items))
        self.assertFalse(any("已经帮你记住" in x["text"] for x in items))

    async def test_companion_continues_while_old_task_waits(self):
        admitted, release=asyncio.Event(),asyncio.Event()
        p=self.provider({"reply":"窗边那只猫倒挺自在。"})
        async def slow(*_):
            admitted.set()
            await release.wait()
            return {"content":"{\"reply\":\"原任务结束\"}","tool_calls":[]}
        p.complete_with_tools.side_effect=slow
        old=asyncio.create_task(core.handle_chat("请读取文件 report.txt","read",self.sid))
        try:
            await asyncio.wait_for(admitted.wait(),3)
            await asyncio.wait_for(core.handle_chat("窗边来了一只猫。","new",self.sid),3)
            self.assertEqual(self.delivered("new")[0]["text"],"窗边那只猫倒挺自在。")
        finally:
            release.set()
            await old
        self.assertFalse(any(e.get("foreground",True) for e in self.delivered("read")))

    async def test_mixed_chat_and_write_have_separate_delivery(self):
        p=self.provider({"reply":"替你高兴！"},[{"id":"w","name":"write_file","arguments":{
            "path":str(self.root/"note.txt"),"content":"合成"}}])
        await core.handle_chat("今天演出成功了！顺便帮我写一个文件 note.txt，内容为合成。","mixed",self.sid)
        items=self.delivered("mixed")
        self.assertEqual([x["text"] for x in items if x["channel"]=="companion"],["替你高兴！"])
        self.assertTrue(any(x["channel"]=="task" and "待确认" in x["text"] for x in items))
        self.assertEqual(len(core._actions().pending(self.sid)),1)
        self.assertFalse((self.root/"note.txt").exists())

    def test_mixed_order_and_quoted_operations(self):
        from agent_core.chat_channels import classify
        for text in ("昨晚的演出真精彩！请读取 report.txt 文件。","请读取 report.txt 文件。昨晚的演出真精彩！"):
            route=classify(text,pending=False,active=False)
            self.assertIn("演出",route.chat)
            self.assertNotIn("演出",route.operation)
            self.assertIn("report.txt",route.operation)
        for text in ("解释一下“请删除文件”是什么意思？","他说：打开文件。","不用替我操作，解释打开文件的原理。"):
            self.assertFalse(classify(text,pending=True,active=True).operation)

    async def test_explicit_cancel_finishes_before_dispatch(self):
        started,release=asyncio.Event(),asyncio.Event()
        target=self.root/"cancelled.txt"
        p=self.provider({"reply":"已收到"})
        async def held(*_args):
            started.set()
            await release.wait()
            return {"content":"","tool_calls":[{"id":"w","name":"write_file","arguments":{"path":str(target),"content":"no"}}]}
        p.complete_with_tools.side_effect=held
        old=asyncio.create_task(core.handle_chat("请写入文件 cancelled.txt。","old-proposal",self.sid))
        await asyncio.wait_for(started.wait(),2)
        cancel=asyncio.create_task(core.handle_chat("取消刚才的操作","cancel-old",self.sid))
        try:
            await asyncio.sleep(0)
            self.assertTrue(core._agent_turns[self.sid][0].revoked)
            p.complete_with_tools.side_effect=None
        finally:
            release.set()
            await asyncio.gather(old,cancel)
        self.assertFalse(core._actions().pending(self.sid))
        self.assertFalse(target.exists())
        self.assertFalse(self.delivered("old-proposal"))

    async def test_decline_without_a_ticket_uses_the_ledger_only(self):
        p=self.provider({"reply":"已撤回全部操作。"})
        await core.handle_chat("取消刚才的操作。","stop",self.sid)
        items=self.delivered("stop")
        self.assertTrue(any(x["channel"]=="task" and "没有可取消" in x["text"] for x in items))
        p.complete.assert_not_awaited()
        p.complete_with_tools.assert_not_awaited()

    async def test_clarifying_a_correction_does_not_take_the_social_reply(self):
        self.provider({"reply":"演出成功啦！"})
        self.store.add_fact("晨星预算120",status="confirmed",scope="global")
        await core.handle_chat("我演出成功了！预算更正为175。","two-panes",self.sid)
        items=self.delivered("two-panes")
        self.assertEqual([e["text"] for e in items if e["channel"]=="companion"],["演出成功啦！"])
        self.assertTrue(any(e["channel"]=="memory" and "更正" in e["text"] for e in items))
        self.assertEqual(self.store.recall_facts(self.sid),["晨星预算120"])

    def test_current_time_and_named_targets_reach_external_lane(self):
        from agent_core.chat_channels import classify
        for text in ("现在几点？","打开记事本","请读取“报表.txt”"):
            self.assertTrue(classify(text,pending=False,active=False).operation,text)

    async def test_late_chat_is_history_only_and_cannot_promote_a_fact(self):
        p=self.provider({"reply":"轻松的新话题"})
        began,release=asyncio.Event(),asyncio.Event()
        async def ordered(messages):
            if "旧话题" in messages[-1]["content"]:
                began.set()
                await release.wait()
                return json.dumps({"reply":"先前的答复。","memory_candidate":"用户喜欢红色卡片"},ensure_ascii=False)
            return '{"reply":"新话题的答复。"}'
        p.complete.side_effect=ordered
        old=asyncio.create_task(core.handle_chat("旧话题","old-chat",self.sid))
        await asyncio.wait_for(began.wait(),2)
        await core.handle_chat("换个话题","new-chat",self.sid)
        release.set()
        await old
        self.assertEqual(self.delivered("old-chat")[0]["foreground"],False)
        self.assertEqual(self.delivered("new-chat")[0]["foreground"],True)
        self.assertIn("先前的答复。",[m["content"] for m in self.store.load_messages(10,self.sid)])
        self.assertEqual(self.store.recall_facts(self.sid),[])

    async def test_operation_claim_without_a_ticket_is_not_a_receipt(self):
        self.provider({"reply":"已把文件写好，也已经发送。"})
        await core.handle_chat("帮我写入文件 absent.txt","unsupported-claim",self.sid)
        items=self.delivered("unsupported-claim")
        self.assertEqual([e["channel"] for e in items],["task"])
        self.assertIn("没有取得可核验",items[0]["text"])
        self.assertNotIn("已把文件写好",items[0]["text"])
        self.assertFalse((self.root/"absent.txt").exists())

del _Fixture
