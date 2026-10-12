"""Batch 01 mechanism regressions: synthetic state only, no desktop/API claims."""
import io
import http.client
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import urllib.error
from unittest.mock import AsyncMock, patch

from agent_core import main as core
from agent_core import tools
from agent_core.actions import ActionLedger
from agent_core.mcp_host import McpServer
from agent_core.permissions import ActionRequest, PermissionEngine
from agent_core.result_pages import ResultPages
from agent_core.speech import SpeechClient, SpeechUnavailable
import test_harness_v1_integration as fixtures


class TaskDeliveryTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.MainActionTests.setUp
    proposal = fixtures.MainActionTests.proposal

    def final(self):
        return self.store.load_messages(20, self.sid)[-1]["content"]

    async def test_no_pending_confirmation_preserves_goal_budget_pages_and_skips_model(self):
        task = core._task_state[self.sid]
        task.update(calls_used=4, rounds_used=2, budget={"max_calls":6,"max_steps":3})
        pages = core._result_pages[self.sid] = ResultPages()
        await core.handle_chat("确认", "empty-confirm", self.sid)
        self.assertIs(core._task_state[self.sid], task)
        self.assertIs(core._result_pages[self.sid], pages)
        self.assertEqual((task["calls_used"],task["rounds_used"]),(4,2))
        core.provider.complete.assert_not_awaited()
        self.assertIn("没有待确认", self.final())

    async def test_continue_without_pending_keeps_goal_without_false_pending_context(self):
        task = core._task_state[self.sid]
        await core.handle_chat("继续", "continue", self.sid)
        self.assertIs(core._task_state[self.sid], task)
        messages = core.provider.complete.await_args.args[0]
        self.assertNotIn("既有操作仍待确认", messages[0]["content"])

    async def test_empty_controls_never_establish_a_task_or_call_model(self):
        core._task_state.pop(self.sid)
        for text in ("确认", "继续", "继续"):
            await core.handle_chat(text,"empty-"+text,self.sid)
            self.assertNotIn(self.sid,core._task_state)
        core.provider.complete.assert_not_awaited()

    async def test_confirmation_punctuation_and_stale_explicit_ticket_keep_task(self):
        task=core._task_state[self.sid]
        for text,ticket in (("确认，",None),("yes",{"action_id":"stale"})):
            await core.handle_chat(text,"stale-"+text,self.sid,confirmation=ticket)
            self.assertIs(core._task_state[self.sid],task)
        core.provider.complete.assert_not_awaited()

    async def test_github_and_drive_read_summaries_survive_long_receipts(self):
        for index,(name,args) in enumerate((("mcp__github__get_file_contents",{}),
                ("mcp__github__issue_read",{"method":"get"}),("mcp__drive__search",{}))):
            await core.handle_chat("B01 new query "+str(index),"new-"+str(index),self.sid)
            await core.run_tool(name,args)
            core.provider.complete.return_value='{"reply":"两份材料的结论是合计一百七十五。"}'
            with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={"ok":True,"output":"x"*9000+"total 175"})):
                await core.handle_chat("确认","summary-"+str(index),self.sid)
            self.assertIn("两份材料的结论",self.final())

    async def test_malformed_answer_recovers_successful_read(self):
        await core.run_tool("mcp__gmail__read_email",{"messageId":"synthetic"})
        core.provider.complete.return_value='{"reply":null}'
        with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={"ok":True,"output":"B01 recovered read"})):
            await core.handle_chat("确认","parse-failure",self.sid)
        self.assertIn("B01 recovered read",self.final())

    async def test_allowed_read_result_survives_later_model_failure(self):
        (self.root/"read.txt").write_text("B01 local result 175",encoding="utf-8")
        async def turn(*unused):
            await core.run_tool("read_file",{"path":str(self.root/"read.txt")})
            raise core.ProviderError("synthetic follow-up failure")
        core.provider.complete.side_effect=turn
        await core.handle_chat("读取B01材料","allowed-read",self.sid)
        self.assertIn("B01 local result 175",self.final())
        self.assertEqual(core._task_state[self.sid]["tool_results"][0]["request_id"],"allowed-read")

    async def test_provider_first_failure_retains_error_event_and_history(self):
        core.provider.complete.side_effect=core.ProviderError("synthetic HTTP 401")
        await core.handle_chat("你好","first-failure",self.sid)
        errors=[c.args[1] for c in core.hub.send_roles.await_args_list if c.args[1].get("type")=="core.error"]
        self.assertTrue(any("401" in e.get("message","") for e in errors))
        self.assertIn("模型答复未能完成",self.final())

    async def test_confirmed_write_survives_answer_timeout_and_reconfirmation(self):
        await self.proposal("one.txt", "B01 persistent receipt")
        core.provider.complete.side_effect = core.ProviderError("synthetic timeout")
        await core.handle_chat("确认", "timeout-after-write", self.sid)
        self.assertEqual((self.root/"one.txt").read_text(encoding="utf-8"), "B01 persistent receipt")
        self.assertIn("执行成功", self.final())
        self.assertTrue(any(c.args[1].get("type")=="chat.response" for c in core.hub.send_roles.await_args_list))
        with patch.object(core, "_execute_authorized_tool", AsyncMock()) as execute:
            await core.handle_chat("确认", "repeat-confirm", self.sid)
            execute.assert_not_awaited()
        reloaded = ActionLedger(self.store.connection)
        self.assertEqual(next(iter(reloaded.records.values()))["status"], "succeeded")
        # A fresh connection must recover both the assistant delivery and its
        # original request/session association. This is not a Godot UI check.
        with closing(fixtures.MemoryStore(data_dir=self.root/"db")) as reopened:
            row=reopened.connection.execute(
                "SELECT content,conversation_id FROM messages WHERE role='assistant' AND request_id=?",
                ("timeout-after-write",)).fetchone()
            self.assertEqual(row["conversation_id"],self.sid)
            self.assertIn("执行成功",row["content"])
            self.assertEqual(next(iter(ActionLedger(reopened.connection).records.values()))["status"],"succeeded")

    async def test_unknown_receipt_is_not_erased_by_answer_timeout(self):
        await self.proposal("unknown.txt", "B01")
        with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={
                "ok":False,"outcome":"unknown","error":"synthetic post-dispatch timeout"})):
            core.provider.complete.side_effect=core.ProviderError("synthetic timeout")
            await core.handle_chat("确认","unknown",self.sid)
        self.assertIn("结果未知",self.final())
        self.assertNotIn("执行失败",self.final())

    async def test_readonly_result_is_delivered_after_answer_timeout(self):
        await core.run_tool("mcp__gmail__read_email",{"messageId":"synthetic"})
        with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={
                "ok":True,"output":"B01 reading: total 175","outcome":"succeeded"})):
            core.provider.complete.side_effect=core.ProviderError("synthetic timeout")
            await core.handle_chat("确认","read-timeout",self.sid)
        self.assertIn("B01 reading: total 175",self.final())

    async def test_issue_write_cannot_release_false_model_completion(self):
        await core.run_tool("mcp__github__issue_write",{"method":"create","title":"B01 synthetic"})
        with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={"ok":True,"output":"issue 17"})):
            await core.handle_chat("确认","issue",self.sid)
        self.assertIn("issue 17",self.final())
        self.assertNotIn("全部成功",self.final())

    async def test_normal_read_answer_is_preserved(self):
        await core.run_tool("mcp__gmail__read_email",{"messageId":"synthetic"})
        core.provider.complete.return_value='{"reply":"合计一百七十五。"}'
        with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={"ok":True,"output":"total 175"})):
            await core.handle_chat("确认","normal-read",self.sid)
        self.assertIn("合计一百七十五",self.final())

    async def test_raw_connector_receipt_persists_without_duplicate_model_envelope(self):
        await core.run_tool("mcp__gmail__read_email",{"messageId":"synthetic"})
        raw={"content":[{"type":"text","text":"B01 raw receipt"}]}
        with patch.object(core,"_execute_authorized_tool",AsyncMock(return_value={
                "ok":True,"output":"B01 raw receipt","raw_result":raw})):
            await core.handle_chat("确认","raw-receipt",self.sid)
        item=next(iter(core._actions().records.values()))
        self.assertEqual(item["receipt"]["raw_result"],raw)
        self.assertNotIn("raw_result",core._actions().result(item))
        self.assertNotIn('"raw_result"',core.provider.complete.await_args.args[0][0]["content"])

    async def test_pending_receipt_survives_answer_timeout(self):
        await self.proposal("pending.txt","B01")
        core.provider.complete.side_effect=core.ProviderError("synthetic timeout")
        await core.handle_chat("请说明参数","pending-timeout",self.sid)
        self.assertIn("待确认",self.final())
        self.assertFalse((self.root/"pending.txt").exists())


class ConnectorContractTests(unittest.IsolatedAsyncioTestCase):
    async def result(self, tool, text, **extra):
        server=McpServer("gmail",[])
        raw={"content":[{"type":"text","text":text}],**extra}
        server._roundtrip=AsyncMock(return_value={"result":raw})
        return await server.call(tool,{}),raw

    async def test_known_gmail_business_error_is_failure_with_raw_receipt(self):
        result,raw=await self.result("read_email","Error: Invalid id value")
        self.assertFalse(result["ok"])
        self.assertEqual(result["outcome"],"failed")
        self.assertEqual(result["raw_result"],raw)

    async def test_empty_gmail_search_is_successful_empty(self):
        result,_=await self.result("search_emails","")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result_kind"],"empty")

    async def test_legitimate_error_prose_is_not_failure(self):
        for text in ("Thread ID: B01\nSubject: Error: Invalid id value\nBody: normal mail",
                     "Thread ID: B01\nSubject: normal\n\nError: the title of my article"):
            result,_=await self.result("read_email",text)
            self.assertTrue(result["ok"])

    async def test_unconfirmed_mutation_error_and_partial_batch_are_unknown(self):
        for tool,text in (("send_email","Error: socket hang up"),
            ("batch_delete_emails","Batch delete operation complete.\nSuccessfully deleted: 1 messages\nFailed to delete: 1 messages\n\nFailed message IDs:\n- B01")):
            result,_=await self.result(tool,text)
            self.assertFalse(result["ok"])
            self.assertEqual(result["outcome"],"unknown")

    def test_issue_write_unknown_method_is_denied_even_by_allow_rule(self):
        from agent_core.permissions import PolicyRule
        engine=PermissionEngine([PolicyRule("broad","*","*","allow")])
        verdict=engine.evaluate(ActionRequest("mcp__github__issue_write",{"method":"invented"},"agent",1))
        self.assertEqual(verdict.kind,"deny")
        known=PermissionEngine().evaluate(ActionRequest("mcp__github__issue_write",{"method":"create"},"agent",1))
        self.assertEqual(known.kind,"ask")

    def test_malformed_method_is_denied_without_raising(self):
        from agent_core.tool_contracts import tool_effect
        for method in (None,[],{}):
            arguments={"method":method}
            self.assertEqual(PermissionEngine().evaluate(ActionRequest("mcp__github__issue_write",arguments,"agent",1)).kind,"deny")
            self.assertEqual(tool_effect("mcp__github__issue_write",arguments),"unknown")


class PhysicalPathTests(unittest.TestCase):
    def test_default_desktop_compatibility_never_expands_explicit_or_write_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            home=base/"home"; desktop=base/"registered-desktop"
            home.mkdir(); desktop.mkdir()
            with patch.dict(os.environ,{"USERPROFILE":str(home),"ANIME_AGENT_TOOLS_ROOTS":"",
                    "LOCALAPPDATA":str(home),"TEMP":str(home),"ANIME_AGENT_WRITE_ROOTS":str(home)}), \
                    patch.object(tools,"_default_desktop_roots",return_value=[desktop]), patch.object(tools.os,"getcwd",return_value=str(home)):
                self.assertEqual(tools._resolve_path(desktop),desktop)
                with self.assertRaises(ValueError): tools._resolve_write_path(desktop/"no.txt")
                with patch.dict(os.environ,{"ANIME_AGENT_TOOLS_ROOTS":str(home)}):
                    with self.assertRaises(ValueError): tools._resolve_path(desktop)

    def test_junction_escape_denied_but_authorized_root_alias_works(self):
        with tempfile.TemporaryDirectory(prefix="tianyi-b01-path-") as directory:
            base=Path(directory)
            root=base/"allowed"; outside=base/"outside"
            root.mkdir(); outside.mkdir()
            escape=root/"escape"; alias=base/"alias"
            for link,target in ((escape,outside),(alias,root)):
                if os.name=="nt":
                    subprocess.run(["cmd","/c","mklink","/J",str(link),str(target)],check=True,capture_output=True)
                else:
                    link.symlink_to(target,target_is_directory=True)
            with patch.dict(os.environ,{"ANIME_AGENT_TOOLS_ROOTS":str(alias),"ANIME_AGENT_WRITE_ROOTS":str(alias)}):
                self.assertEqual(tools._resolve_write_path(alias/"ok.txt"),root/"ok.txt")
                self.assertEqual(tools._resolve_path(alias/"ok.txt"),root/"ok.txt")
                target=escape/"forbidden.txt"
                for resolver in (tools._resolve_path,tools._resolve_write_path):
                    with self.assertRaises(ValueError): resolver(target)
                verdict=PermissionEngine().evaluate(ActionRequest("write_file",{"path":str(target),"content":"B01"},"agent",1))
                self.assertEqual(verdict.kind,"deny")
                self.assertFalse(tools.write_file(target,"B01")["ok"])
                self.assertFalse((outside/"forbidden.txt").exists())


class SpeechErrorContractTests(unittest.TestCase):
    def test_truncated_error_body_preserves_transient_recovery(self):
        class BrokenBody:
            def read(self,*unused): raise http.client.IncompleteRead(b'')
            def close(self): pass
        error=urllib.error.HTTPError("http://127.0.0.1",503,"synthetic",{},BrokenBody())
        with patch("agent_core.speech._post_json",side_effect=error):
            with self.assertRaises(SpeechUnavailable) as caught:
                SpeechClient("http://127.0.0.1:9").synthesize("B01")
        self.assertTrue(caught.exception.retryable)
    def test_typed_encoding_503_is_not_retried_but_legacy_503_is(self):
        for body,expected in (({"error_type":"encoding","retryable":False},False), ({},True)):
            error=urllib.error.HTTPError("http://127.0.0.1",503,"synthetic",{},io.BytesIO(json.dumps(body).encode()))
            with patch("agent_core.speech._post_json",side_effect=error):
                with self.assertRaises(SpeechUnavailable) as caught:
                    SpeechClient("http://127.0.0.1:9").synthesize("B01 ✅")
            self.assertEqual(caught.exception.retryable,expected)
