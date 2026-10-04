import asyncio
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, AsyncMock
from agent_core import main as core
from agent_core.storage import MemoryStore
from agent_core.actions import ActionLedger
from agent_core.stt_input import CaptureState, simplify_transcript
from agent_core.proactive import IdlePolicy
from agent_core.result_pages import ResultPages
from agent_core.memory_retrieval import retrieve_task_memories
from agent_core.harness import CharacterHarness
from agent_core.mcp_host import McpServer


class MainActionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.store=MemoryStore(data_dir=self.root/"db")
        self.addCleanup(self.store.close)
        self.patches=[]
        for name,value in (("memory",self.store),("TTS_ENABLED",False),("hub",type("Hub",(),{
            "send_roles":AsyncMock(),"role_count":lambda *_:0})()),("provider", type("Provider",(),{
            "complete":AsyncMock(return_value='{"reply":"全部成功","emotion":"neutral","gesture":"none"}')})()),
            ("tools_schema",[]),("chat_lock",asyncio.Lock()),("_action_ledger",None)):
            p=patch.object(core,name,value); p.start(); self.addCleanup(p.stop)
        p=patch.dict(os.environ,{"ANIME_AGENT_WRITE_ROOTS":str(self.root),"ANIME_AGENT_TOOLS_ROOTS":str(self.root)})
        p.start(); self.addCleanup(p.stop)
        self.sid=self.store.create_session()["id"]
        core._ACTIVE_CHAT_SESSION_ID[0]=self.sid
        core._actions()
        core._task_state[self.sid]={"id":"t","intent":"写两份文件","blocked":False}

    async def proposal(self,name,content):
        return await core.run_tool("write_file",{"path":str(self.root/name),"content":content})

    async def test_two_actions_confirm_separately_with_real_artifacts(self):
        await self.proposal("one.txt","第一份")
        await self.proposal("two.txt","第二份")
        await core.handle_chat("确认","confirm-1",self.sid)
        self.assertEqual((self.root/"one.txt").read_text(encoding="utf-8"),"第一份")
        self.assertFalse((self.root/"two.txt").exists())
        await core.handle_chat("确认","confirm-2",self.sid)
        self.assertEqual((self.root/"two.txt").read_text(encoding="utf-8"),"第二份")
        self.assertFalse(core._sync_pending(self.sid))

    async def test_refusal_prevents_mutation_despite_model_saying_success(self):
        await self.proposal("one.txt","禁止")
        await core.handle_chat("不同意，先不要执行。","deny",self.sid)
        self.assertFalse((self.root/"one.txt").exists())
        final=self.store.load_messages(10,self.sid)[-1]["content"]
        self.assertIn("已取消",final); self.assertNotIn("全部成功",final)

    async def test_changed_params_invalidate_old_ticket(self):
        first=await self.proposal("one.txt","旧版")
        await core.handle_chat("取消旧的，改成新版","edit",self.sid)
        await self.proposal("one.txt","新版")
        await core.handle_chat("确认","stale",self.sid,confirmation=first["confirmation"])
        self.assertFalse((self.root/"one.txt").exists())
        await core.handle_chat("确认","fresh",self.sid)
        self.assertEqual((self.root/"one.txt").read_text(encoding="utf-8"),"新版")

    async def test_failure_no_fake_success_repeat(self):
        await self.proposal("one.txt","x")
        with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={"ok":False,"error":"REJECTED"})) as execute:
            await core.handle_chat("确认","confirm",self.sid)
            result=await self.proposal("one.txt","x")
            self.assertFalse(result["ok"]); self.assertEqual(execute.await_count,1)
        self.assertNotIn("全部成功",self.store.load_messages(10,self.sid)[-1]["content"])

    async def test_current_roots_rechecked(self):
        await self.proposal("one.txt","x")
        with patch.dict(os.environ,{"ANIME_AGENT_WRITE_ROOTS":str(self.root/"other")}):
            await core.handle_chat("确认","confirm",self.sid)
        self.assertFalse((self.root/"one.txt").exists())

    async def test_natural_followup_preserves_pending_without_authorizing(self):
        first=await self.proposal("one.txt","新版")
        await core.handle_chat("请按新的内容办理。","followup",self.sid)
        self.assertFalse((self.root/"one.txt").exists())
        self.assertEqual(core._sync_pending(self.sid)[0]["action_id"],first["action_id"])
        await core.handle_chat("确认","confirm-later",self.sid)
        self.assertEqual((self.root/"one.txt").read_text(encoding="utf-8"),"新版")


class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_resource_text_is_not_lost(self):
        server=McpServer("test",[])
        server._roundtrip=AsyncMock(return_value={"result":{"content":[{"type":"resource",
            "resource":{"uri":"test://readme","mimeType":"text/plain","text":"BLUEBIRD READY 林岚"}}]}})
        result=await server.call("get_file_contents",{})
        self.assertIn("BLUEBIRD READY 林岚",result["text"])

    async def test_pages_preserve_tail_and_reject_other_session(self):
        store=ResultPages()
        result=store.pack({"ok":True,"content":"a"*9000+"TAIL-73921"})
        self.assertTrue(result["truncated"])
        tail=store.read(result["ref"],result["total_chars"]-50)
        self.assertIn("TAIL-73921",tail["content"])
        self.assertFalse(ResultPages().read(result["ref"])["ok"])
        self.assertFalse(store.read(result["ref"],-1)["ok"])

    async def test_multifield_recall_not_strongest_only(self):
        facts=["蓝桥项目负责人是林岚","蓝桥项目预算7600","蓝桥项目日期10月18日","蓝桥项目地点青竹","蓝桥项目代号BLUEBIRD"]
        got=retrieve_task_memories("回忆蓝桥项目的负责人、预算、日期、地点、代号",facts)
        self.assertEqual(set(got),set(facts))

    async def test_json_suffix_not_displayed(self):
        reply=CharacterHarness.parse_reply('{"reply":"读不到文件","emotion":"sad","gesture":"none"}X')
        self.assertEqual(reply.reply,"读不到文件")
        bad=CharacterHarness.parse_reply('{"reply": garbage, "emotion": bad}')
        self.assertNotIn('"reply"',bad.reply)


class VoiceInputTests(unittest.IsolatedAsyncioTestCase):
    async def test_simplify_preserves_literals_english_numbers_and_paths(self):
        text='請讀取 C:\\資料\\聲音.txt 和 /tmp/資料.txt，用 API v2 123.45，保留 "繁體字" 與 https://example.invalid/資料'
        got=simplify_transcript(text)
        self.assertIn("请读取",got)
        for token in (r"C:\資料\聲音.txt","/tmp/資料.txt","API v2 123.45",'"繁體字"',"https://example.invalid/資料"):
            self.assertIn(token,got)

    async def test_generation_old_result_cannot_fill_after_cancel_or_new(self):
        state=CaptureState()
        a=state.begin("a",1,"client")
        state.invalidate(); self.assertFalse(state.valid(a))
        b=state.begin("b",2,"client")
        self.assertFalse(state.valid(a)); self.assertTrue(state.valid(b))

    async def test_empty_stt_only_hint_no_brain_or_history(self):
        state=CaptureState(); generation=state.begin("a",1,"client")
        hub=type("Hub",(),{"send_roles":AsyncMock()})()
        with patch.object(core,"voice_capture",state),patch.object(core,"hub",hub), \
             patch.object(core,"transcribe_wav",return_value=""),patch.object(core,"handle_chat",AsyncMock()) as chat, \
             patch.object(core.memory,"add_message") as add:
            await core.handle_voice_transcription(b"wav",generation)
            self.assertTrue(any(c.args[1]["type"]=="voice.hint" for c in hub.send_roles.call_args_list))
            self.assertFalse(any(c.args[1]["type"] in {"core.error","voice.transcript","chat.response"} for c in hub.send_roles.call_args_list))
            chat.assert_not_called(); add.assert_not_called()

    async def test_cancel_during_stt_discards_late_output(self):
        state=CaptureState(); generation=state.begin("a",1,"client")
        async def delayed(*_):
            state.invalidate()
            return "過期語音"
        hub=type("Hub",(),{"send_roles":AsyncMock()})()
        with patch.object(core,"voice_capture",state),patch.object(core,"hub",hub),patch.object(core.asyncio,"to_thread",side_effect=delayed):
            await core.handle_voice_transcription(b"wav",generation)
        self.assertFalse(any(c.args[1]["type"]=="voice.transcript" for c in hub.send_roles.call_args_list))

    async def test_manual_mode_never_opens_background_listener(self):
        with patch.object(core,"VOICE_INPUT_MODE","manual"),patch.object(core,"wake_listener",None), \
             patch.object(core,"WakeWordListener") as listener,patch.object(core.memory,"sweep_empty_sessions"), \
             patch.object(core.memory,"add_event"),patch.object(core,"handle_chat",AsyncMock()) as chat:
            await core.start_wake_word_listener()
            await core.handle_wake_word(None)
            listener.assert_not_called(); chat.assert_not_called()


class IdleEpisodeTests(unittest.TestCase):
    day=time.struct_time((2026,10,4,14,0,0,0,0,0))
    def test_600_boundary_once_even_after_long_wait_then_reset(self):
        p=IdlePolicy()
        self.assertFalse(p.decide(599,self.day,1599)[0])
        self.assertTrue(p.decide(600,self.day,1600)[0])
        p.mark_spoken(1600)
        self.assertFalse(p.decide(10000,self.day,11000)[0])
        self.assertFalse(p.decide(0,self.day,11001)[0])
        self.assertTrue(p.decide(600,self.day,11601)[0])

    def test_quiet_does_not_consume_episode(self):
        p=IdlePolicy()
        night=time.struct_time((2026,10,4,23,0,0,0,0,0))
        self.assertFalse(p.decide(600,night,1600)[0])
        self.assertTrue(p.decide(700,self.day,1700)[0])
