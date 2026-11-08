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

del _Fixture
