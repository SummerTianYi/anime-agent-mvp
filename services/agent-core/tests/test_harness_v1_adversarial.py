"""Codex V1 adversarial self-review: no independent reviewer instance."""
import asyncio, json, sqlite3, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from agent_core.actions import ActionLedger, args_hash
from agent_core import main as core
from agent_core.proactive import IdlePolicy
from agent_core.tools import read_file, write_file
from agent_core.agent_loop import run_agent_loop
from agent_core.mcp_host import McpServer

class AdversarialTests(unittest.IsolatedAsyncioTestCase):
    async def test_effect_then_timeout_is_unknown_no_repeat_even_explicit_default_mode(self):
        db=sqlite3.connect(":memory:");self.addCleanup(db.close)
        book=ActionLedger(db)
        args={"path":"test.txt","content":"once"}
        a=book.propose(1,"t","r","write_file",args);effects=[]
        async def uncertain(*_):
            effects.append("written")
            raise TimeoutError("lost ack after effect")
        result=await book.execute(1,book.ticket(a),"confirm",lambda *_:True,uncertain)
        self.assertEqual(result["outcome"],"unknown")
        b=book.propose(1,"new-task","r2","write_file",args|{"mode":"overwrite"})
        self.assertEqual(a["action_id"],b["action_id"])
        await book.execute(1,book.ticket(b),"again",lambda *_:True,uncertain)
        self.assertEqual(effects,["written"])

    async def test_expired_approval_and_wrong_parameter_digest_never_execute(self):
        db=sqlite3.connect(":memory:");self.addCleanup(db.close)
        book=ActionLedger(db); a=book.propose(1,"t","r","write_file",{"path":"x","content":"one"})
        execute=AsyncMock()
        ticket=book.ticket(a)
        a["arguments"]["content"]="injected"
        result=await book.execute(1,ticket,"c",lambda *_:True,execute)
        self.assertFalse(result["ok"])
        a["arguments"]["content"]="one";a["expires"]=time.time()-1
        result=await book.execute(1,ticket,"c",lambda *_:True,execute)
        self.assertFalse(result["ok"]);execute.assert_not_called()

    async def test_pathological_provider_batch_cannot_exceed_executor_budget(self):
        provider=SimpleNamespace(
            complete_with_tools=AsyncMock(return_value={"tool_calls":[{"name":"read_file","arguments":{}}]*10000}),
            complete=AsyncMock(return_value="budget stopped"))
        execute=AsyncMock(return_value={"ok":True})
        r=await run_agent_loop(provider,[],[{"type":"function"}],execute,max_steps=3,max_calls=6)
        self.assertEqual(execute.await_count,6);self.assertEqual(len(r.steps),6)

    async def test_utf8_continuation_and_readback_hash_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ",
                {"ANIME_AGENT_WRITE_ROOTS":tmp,"ANIME_AGENT_TOOLS_ROOTS":tmp}):
            path=str(Path(tmp)/"large.txt");text="天依🎵"*22000
            Path(path).write_text(text,encoding="utf-8")
            out=[];offset=0
            while True:
                page=read_file(path,offset);self.assertTrue(page["ok"])
                out.append(page["content"])
                if page["next_offset"] is None:break
                offset=page["next_offset"]
            self.assertEqual("".join(out),text)
            result=write_file(str(Path(tmp)/"out.txt"),"verified")
            self.assertTrue(result["verified_readback"]);self.assertEqual(len(result["sha256"]),64)

    async def test_idle_preplayback_activity_or_busy_prevents_audio_without_llm(self):
        policy=IdlePolicy(quiet_start="00:00",quiet_end="00:00")
        hub=SimpleNamespace(role_count=lambda *_:1,send_roles=AsyncMock())
        with patch.object(core,"idle_policy",policy),patch.object(core,"hub",hub), \
             patch.object(core,"_idle_seconds_now",return_value=0),patch.object(core,"provider") as model, \
             patch.object(core,"broadcast_state",AsyncMock()),patch.object(core,"chat_lock",asyncio.Lock()):
            with self.assertRaises(RuntimeError):await core._broadcast_speak({"requestId":"proactive-idle"})
            hub.send_roles.assert_not_called();self.assertEqual(model.mock_calls,[])
        for state in ("thinking","listening"):
            with patch.object(core,"idle_policy",policy),patch.object(core,"hub",hub), \
                 patch.object(core,"_idle_seconds_now",return_value=600),patch.object(core,"_agent_state",state), \
                 patch.object(core,"chat_lock",asyncio.Lock()):
                with self.assertRaises(RuntimeError):await core._broadcast_speak({"requestId":"proactive-idle"})
        hub.send_roles.assert_not_called()

    async def test_mcp_timeout_does_not_reuse_jsonrpc_id(self):
        server=McpServer("fixture",[]);server._roundtrip=AsyncMock(side_effect=[TimeoutError(),{"result":{"content":[{"type":"text","text":"next"}]}}])
        with self.assertRaises(TimeoutError):await server.call("send_email",{})
        result=await server.call("read_email",{})
        self.assertTrue(result["ok"])
        ids=[c.args[0]["id"] for c in server._roundtrip.call_args_list]
        self.assertEqual(len(ids),len(set(ids)))
