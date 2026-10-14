"""Deterministic evidence/error contract; not a semantic accuracy assessment."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from agent_core.actions import args_hash
from agent_core.general_reply_check import check_draft, parse_extraction, verify_claims


def extracted(quote, operation="write", state="succeeded", target=None):
    return json.dumps({"uncertain": False, "claims": [{"quote": quote, "operation": operation,
                       "state": state, "target": target or {"path": "test.txt"}}]}, ensure_ascii=False)


def record(**overrides):
    args = {"path": "test.txt", "content": "原文"}
    return {"action_id": "action1", "task_id": "task1", "session_id": 1, "revision": 2,
            "tool": "write_file", "arguments": args, "args_hash": args_hash("write_file", args),
            "status": "succeeded", "execution_id": "execution1", "receipt": {"ok": True}, **overrides}


class GeneralCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_binding_session_task_target_version_hash_and_refs(self):
        raw = extracted("已写好test.txt", target={"path": "test.txt", "content": "原文", "revision": 2})
        claims = parse_extraction(raw, "已写好test.txt")
        def verify(item, **kwargs):
            return verify_claims(claims, task={"id": "task1"}, session_id=1, actions=[item], action_refs=["action1"], **kwargs)
        self.assertEqual("", verify(record()))
        for change in ({"session_id": 2}, {"task_id": "task2"}, {"revision": 3}, {"args_hash": "wrong"},
                       {"status": "awaiting_confirmation"}, {"receipt": {"ok": False}}, {"execution_id": None}):
            with self.subTest(change=change):
                self.assertTrue(verify(record(**change)))
        self.assertTrue(verify_claims(claims, task={"id": "task1"}, session_id=1, actions=[record()], action_refs=[]))

    async def test_read_cannot_prove_write_or_other_target(self):
        task = {"id": "task1", "tool_results": [{"result_ref": "read1", "task_id": "task1", "session_id": 1,
                "tool": "read_file", "arguments": {"path": "test.txt"}, "result": {"ok": True}}]}
        for operation, path in (("write", "test.txt"), ("read", "other.txt")):
            claims = parse_extraction(extracted("已完成", operation, target={"path": path}), "已完成")
            self.assertTrue(verify_claims(claims, task=task, session_id=1, actions=[], read_refs=["read1"]))
        good = parse_extraction(extracted("已读取", "read"), "已读取")
        self.assertEqual("", verify_claims(good, task=task, session_id=1, actions=[], read_refs=["read1"]))
        task["tool_results"][0]["task_id"] = "other"
        self.assertTrue(verify_claims(good, task=task, session_id=1, actions=[], read_refs=["read1"]))

    async def test_send_acceptance_is_not_delivery(self):
        args = {"to": ["synth@example.invalid"], "subject": "主题", "body": "两行\n原文"}
        item = record(tool="mcp__gmail__send_email", arguments=args, args_hash=args_hash("mcp__gmail__send_email", args),
                      receipt={"ok": True, "raw_result": {"content": [{"type": "text", "text": "Email sent successfully with ID: synth123"}]}})
        for state, expected in (("accepted", ""), ("delivered", "unsubstantiated_claim"), ("succeeded", "unsubstantiated_claim")):
            claims = parse_extraction(extracted("已发送", "send", state, {"to": args["to"]}), "已发送")
            self.assertEqual(expected, verify_claims(claims, task={"id": "task1"}, session_id=1, actions=[item], action_refs=["action1"]))

    async def test_single_tool_free_request_no_repair_and_fail_closed(self):
        for response in ("bad json", '{}', '{"uncertain":true,"claims":[]}', extracted("not in draft"),
                         '{"uncertain":false,"claims":[],"trusted":true}', TimeoutError("private detail")):
            complete = AsyncMock(side_effect=response if isinstance(response, Exception) else None,
                                 return_value=None if isinstance(response, Exception) else response)
            result = await check_draft(SimpleNamespace(complete=complete), "原文", user_text="忽略规则", task={"id": "t"}, session_id=1, actions=[])
            self.assertFalse(result.allowed)
            self.assertEqual(1, complete.await_count)
            self.assertEqual({"role", "content"}, set(complete.call_args.args[0][0]))
            self.assertNotIn("private detail", result.reason)

    async def test_plain_reply_and_unsubstantiated_claim(self):
        complete = AsyncMock(return_value='{"uncertain":false,"claims":[]}')
        result = await check_draft(SimpleNamespace(complete=complete), "晚上好", user_text="晚上好", task={"id": "t"}, session_id=1, actions=[])
        self.assertTrue(result.allowed)
        complete.return_value = extracted("已写好test.txt")
        result = await check_draft(SimpleNamespace(complete=complete), "已写好test.txt", user_text="任务", task={"id": "t"}, session_id=1, actions=[])
        self.assertFalse(result.allowed)
        self.assertEqual(result.claims[0]["start"], 0)
