"""Natural-language Core regressions for ledger-backed progress questions."""
import asyncio
import copy
import json
import unittest
from unittest.mock import AsyncMock

import test_harness_v1_review as fixture


def final(reply):
    return {"content": json.dumps({"decision": {"mode": "chat"}, "reply": reply}, ensure_ascii=False)}


class PendingStatusTests(fixture.IndependentReviewTests):
    async def request(self, text, request_id="status", reply="已经全部完成，不需要确认了。"):
        self.core.provider.complete_with_tools = AsyncMock(return_value=final(reply))
        self.core.provider.complete = AsyncMock(return_value=final(reply)["content"])
        await self.chat(text, request_id)
        return self.latest_reply()

    async def create_pending(self, names=("first.txt",), request="proposal"):
        self.core.provider.complete_with_tools = AsyncMock(return_value={"tool_calls": [
            {"id": str(i), "name": "write_file", "arguments": {"path": str(self.root / name), "content": "175"}}
            for i, name in enumerate(names)]})
        await self.chat("把合成内容175写入指定文件", request)
        return self.book.pending(self.sid)

    async def test_explicit_progress_forms_use_ledger_without_model_or_tool(self):
        await self.create_pending()
        state = copy.deepcopy(self.core._task_state[self.sid])
        ledger = copy.deepcopy(self.book.records)
        for index, text in enumerate(("刚才那件事现在怎么样？", "当前任务进度如何？", "这个任务完成了吗？",
                "刚才的文件写好了吗？", "任务目前是什么状态？", "请查看待办状态", "之前让你做的事做完没？",
                "任务还需要我确认吗？", "刚才任务取消了吗？", "刚才那项任务办好了没有？",
                "你之前的任务有结果了吗？", "刚才交给你的任务做完了吗？",
                "刚才让你写的文件，现在完成了吗？",
                "文件还没写完吗？", "刚才那个任务有没有被取消？", "任务被取消了吗？",
                "任务是否已经被取消", "任务是不是取消了", "任务成功了吗？",
                "刚才那个文件保存了吗？", "这个任务处理好了没有？", "文件写入成功了吗？")):
            with self.subTest(text=text):
                answer = await self.request(text, f"query-{index}")
                self.assertIn("待确认，尚未执行", answer)
                self.assertIn("first.txt", answer)
                self.assertNotIn("已经全部完成", answer)
                self.assertEqual(self.core.provider.complete_with_tools.await_count, 0)
                self.assertEqual(self.core.provider.complete.await_count, 0)
                self.assertEqual(self.core._task_state[self.sid], state)
                self.assertEqual(self.book.records, ledger)
                self.assertEqual(self.effects, [])

    async def test_pending_chat_preserves_ticket_and_operation_budget(self):
        await self.create_pending()
        task = self.core._task_state[self.sid]
        budget = {k: copy.deepcopy(task.get(k)) for k in ("budget", "rounds_used", "calls_used", "corrections_used")}
        ledger = copy.deepcopy(self.book.records)
        answer = await self.request("晚上好，今天听什么歌？", reply="晚上好，我们听一首轻快的歌吧。")
        self.assertEqual(answer, "晚上好，我们听一首轻快的歌吧。")
        self.assertEqual(self.book.records, ledger)
        self.assertEqual({k: task.get(k) for k in budget}, budget)
        self.assertEqual(self.effects, [])

    async def test_pending_chat_works_with_exhausted_operation_budget(self):
        await self.create_pending()
        task = self.core._task_state[self.sid]
        task["rounds_used"] = task["budget"]["max_steps"]
        task["calls_used"] = task["budget"]["max_calls"]
        before = copy.deepcopy(task)
        answer = await self.request("聊聊音乐吧", reply="可以，一起聊音乐吧。")
        self.assertEqual(answer, "可以，一起聊音乐吧。")
        self.assertEqual(task["budget"], before["budget"])
        self.assertEqual(task["rounds_used"], before["rounds_used"])
        self.assertEqual(task["calls_used"], before["calls_used"])
        self.assertEqual(self.core.provider.complete_with_tools.await_count, 0)
        self.assertEqual(self.effects, [])

    async def test_confirmation_then_progress_and_duplicate_do_not_reexecute(self):
        await self.create_pending()
        await self.request("确认", "confirm")
        self.assertEqual(len(self.effects), 1)
        self.assertIn("执行成功", self.latest_reply())
        task = copy.deepcopy(self.core._task_state[self.sid])
        answer = await self.request("刚才任务完成了吗", "after")
        self.assertIn("执行成功", answer)
        self.assertEqual(self.core._task_state[self.sid], task)
        await self.request("确认", "again")
        self.assertEqual(len(self.effects), 1)
        self.assertIn("没有待确认", self.latest_reply())

    async def test_partial_completion_lists_each_action(self):
        await self.create_pending(("first.txt", "second.txt"))
        await self.request("确认", "confirm-one")
        answer = await self.request("这些任务都完成了吗", "partial")
        self.assertIn("first.txt", answer)
        self.assertIn("second.txt", answer)
        self.assertIn("执行成功 1项", answer)
        self.assertIn("待确认，尚未执行 1项", answer)
        self.assertEqual(len(self.effects), 1)
        self.assertEqual(len(self.book.pending(self.sid)), 1)

    async def test_failed_unknown_cancelled_and_expired_are_not_completed(self):
        for status in ("failed", "unknown", "cancelled", "expired", "executing"):
            item = self.book.propose(self.sid, "task-"+status, status, "write_file", {"path": str(self.root / (status+".txt")), "content": "175"})
            item["status"] = status
            item["receipt"] = {"ok":False,"outcome":status,"error":"synthetic"}
            self.book.save(item)
        answer = await self.request("所有任务状态如何", "states")
        for label in ("执行失败", "结果未知", "已取消", "授权已过期", "执行中"):
            self.assertIn(label, answer)
        self.assertEqual(self.effects, [])
        self.assertNotIn("已经全部完成", answer)

    async def test_multiple_tasks_and_specific_file_are_unambiguous(self):
        await self.create_pending(request="first-task")
        other = self.book.propose(self.sid, "second-task", "r2", "write_file", {"path": str(self.root/"second file.txt"), "content":"175"})
        other.update(status="succeeded", receipt={"ok":True})
        self.book.save(other)
        answer = await self.request("所有任务进度如何", "multiple")
        self.assertIn("任务 first-task", answer)
        self.assertIn("任务 second-task", answer)
        self.assertIn("待确认", answer)
        self.assertIn("执行成功", answer)
        answer = await self.request("second file.txt完成了吗", "specific")
        self.assertIn("second file.txt", answer)
        self.assertNotIn("first.txt", answer)
        self.assertNotIn("任务 first-task", answer)

    async def test_other_session_records_cannot_be_referenced(self):
        await self.create_pending()
        other_sid = self.core.memory.create_session()["id"]
        item = self.book.propose(other_sid, "foreign-task", "foreign", "write_file", {"path":"foreign-secret.txt","content":"other-session"})
        item.update(status="succeeded", receipt={"ok":True,"output":"foreign-result"})
        self.book.save(item)
        for text in ("所有任务进度如何", "任务foreign-task完成了吗", "foreign-secret.txt完成了吗"):
            answer = await self.request(text, text)
            self.assertNotIn("foreign-result", answer)
            self.assertNotIn("foreign-secret", answer)
            self.assertNotIn("foreign-task", answer)
        self.assertEqual(self.effects, [])

    async def test_progress_after_chat_recovers_ledger_task(self):
        await self.create_pending()
        await self.request("确认", "confirm")
        await self.request("聊聊音乐吧", "new-chat", reply="好呀，来聊聊音乐。")
        current = copy.deepcopy(self.core._task_state[self.sid])
        answer = await self.request("刚才那件事现在怎么样", "after-chat")
        self.assertIn("执行成功", answer)
        self.assertIn("任务 proposal", answer)
        self.assertEqual(self.core._task_state[self.sid], current)

    async def test_quoted_status_explanation_and_chat_are_not_intercepted(self):
        await self.create_pending()
        for text in ("解释一下‘任务完成了吗’这句话", "今天心情怎么样？", "请说一句晚上好", "你现在怎么样？", "怎么样？"):
            answer = await self.request(text, text, reply="这是正常的聊天回答。")
            self.assertEqual(answer, "这是正常的聊天回答。")
            self.assertEqual(self.core.provider.complete_with_tools.await_count, 0)
            self.assertEqual(self.core.provider.complete.await_count, 1)

    async def test_cancel_and_edit_still_follow_existing_parameter_version(self):
        first = (await self.create_pending())[0]
        await self.request("取消", "cancel")
        self.assertEqual(first["status"], "cancelled")
        answer = await self.request("刚才任务取消了吗", "cancel-status")
        self.assertIn("已取消，未执行", answer)
        await self.create_pending(("revised.txt",), "revision-task")
        second = self.book.pending(self.sid)[0]
        await self.request("取消旧的，改成新版", "edit")
        self.assertEqual(second["status"], "cancelled")
        self.assertEqual(self.effects, [])

    async def test_compound_cancellation_revokes_queued_confirmation(self):
        for index, text in enumerate(("任务先取消，再告诉我状态", "先不要执行，只问刚才任务进度如何？")):
            item = (await self.create_pending(request=f"proposal-{index}"))[0]
            await self.core.chat_lock.acquire()
            approval = asyncio.create_task(self.chat("确认", f"queued-confirm-{index}", confirmation=self.book.ticket(item)))
            revocation = None
            try:
                await asyncio.sleep(0)
                revocation = asyncio.create_task(self.request(text, f"revoke-query-{index}"))
                for _ in range(4):
                    await asyncio.sleep(0)
                self.assertEqual(item["status"], "cancelled")
            finally:
                self.core.chat_lock.release()
                await asyncio.gather(approval, *([revocation] if revocation else []))
            self.assertEqual(self.effects, [])
            self.assertEqual(item["status"], "cancelled")

    async def test_literal_filename_and_file_reference_revocation(self):
        await self.create_pending(("任务 notes.txt", "cancel.txt"))
        for name in ("任务 notes.txt", "cancel.txt"):
            for target in (name, str(self.root / name), f'“{name}”'):
                answer = await self.request(target + "完成了吗？", target)
                self.assertIn(name, answer)
                self.assertIn("待确认，尚未执行", answer)
            answer = await self.request(f"请告诉我 {name} 的进度", "space-" + name)
            self.assertIn(name, answer)
            self.assertIn("待确认，尚未执行", answer)
        self.assertEqual(len(self.book.pending(self.sid)), 2)
        await self.request("先取消待办再告诉我cancel.txt的状态", "file-cancel")
        self.assertFalse(self.book.pending(self.sid))
        self.assertEqual(self.effects, [])


def load_tests(loader, tests, pattern):
    # Reuse the isolation fixture without rerunning its unrelated inherited cases.
    return unittest.TestSuite(PendingStatusTests(name) for name in PendingStatusTests.__dict__ if name.startswith("test_"))
