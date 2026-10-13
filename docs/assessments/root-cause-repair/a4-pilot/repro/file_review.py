"""Independent file-task counterexamples using real isolated file I/O only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test", action="append", default=[])
    args = parser.parse_args()
    if args.data_dir.exists() or args.output.exists():
        raise SystemExit("Refusing to overwrite prior evidence")
    args.data_dir.mkdir(parents=True)
    os.environ.update(ANIME_AGENT_DATA_DIR=str(args.data_dir),
                      ANIME_AGENT_CONFIG_PATH=str(args.data_dir / "absent.env"),
                      ANIME_AGENT_TTS="0", ANIME_AGENT_WAKE_WORD="0",
                      ANIME_AGENT_MCP_SERVERS="", LLM_PROVIDER="mock")
    sys.dont_write_bytecode = True
    package = args.source_root / "services/agent-core"
    sys.path[:0] = [str(package), str(package / "tests")]
    sources = list((package / "agent_core").glob("*.py"))
    hashes = lambda: {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    source_before = hashes()
    from agent_core import main as core
    from agent_core.file_task import read_for
    from test_file_task import FileTaskTests
    from test_a4_pilot import call, final
    from unittest.mock import patch, AsyncMock
    original_memory = core.memory
    observations = []

    class IndependentFileTests(unittest.IsolatedAsyncioTestCase):
        setUp = FileTaskTests.setUp
        chat = FileTaskTests.chat
        request = FileTaskTests.request
        propose = FileTaskTests.propose

        def observe(self, answer, **extra):
            observations.append({"test": self.id().split(".")[-1], "answer": answer,
                "file_delivery": core._task_state.get(self.sid, {}).get("file_delivery"),
                "effects": [name for name, _ in self.effects],
                "pending": len(core._sync_pending(self.sid)), **extra})

        async def test_generate_wording_cannot_fake_pending(self):
            text = f"帮我生成文件 {self.path}，然后读取它并展示完整正文。内容如下：{self.content}"
            answer, _ = await self.chat(text, [final("已安排待办，请确认"), final("文件已完成")])
            self.observe(answer, request=text)
            self.assertNotIn("已安排待办", answer)
            self.assertIn("尚未完成", answer)

        async def test_read_synonym_cannot_fake_pending(self):
            text = f"请创建文件 {self.path}，然后打开该文件，把全部正文原样显示。内容如下：{self.content}"
            answer, _ = await self.chat(text, [final("已安排待办，请确认"), final("文件已完成")])
            self.observe(answer, request=text)
            self.assertNotIn("已安排待办", answer)
            self.assertIn("尚未完成", answer)

        async def test_question_explanation_remains_chat(self):
            text = "能解释一下为什么创建文件之后还要读取文件吗？"
            expected = "读取可以核对文件实际落盘的内容。"
            answer, _ = await self.chat(text, [final(expected), final(expected)])
            self.observe(answer, request=text)
            self.assertEqual(answer, expected)

        async def test_multiline_instructions_keep_file_obligation(self):
            text = f"请创建\n文件 {self.path}\n写入后读取并展示完整正文。内容如下：{self.content}"
            answer, _ = await self.chat(text, [final("已安排待办，请确认"), final("文件已完成")])
            self.observe(answer, request=text)
            self.assertNotIn("已安排待办", answer)
            self.assertIn("尚未完成", answer)

        async def test_complete_paged_read_delivers_all_content(self):
            self.content = "甲" * 24000 + "\nEND-VERIFIED"
            item = await self.propose()
            answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
                call("read_file", path=str(self.path), offset=65535),
                final("全部完成", "report", action_refs=[item["action_id"]],
                      read_refs=["file-start:read:1", "file-start:read:2"]),
                final("全部完成", "report", action_refs=[item["action_id"]],
                      read_refs=["file-start:read:1", "file-start:read:2"])], "large-confirm")
            self.observe(answer[-2000:], bytes=len(self.content.encode()),
                reads=[{k: r["result"].get(k) for k in ("offset", "next_offset", "size", "truncated")}
                       for r in core._task_state[self.sid].get("tool_results", [])])
            self.assertEqual(self.path.read_bytes(), self.content.encode())
            self.assertTrue("文件任务已完成" in answer, "All bytes read but task not completed")
            self.assertTrue(self.content in answer, "Complete exact body not delivered")

        async def test_read_before_write_does_not_discharge_obligation(self):
            self.path.write_bytes(self.content.encode())
            answer, _ = await self.chat(self.request(), [call("read_file", path=str(self.path)),
                call("write_file", path=str(self.path), content=self.content)])
            item = core._sync_pending(self.sid)[0]
            answer, _ = await self.chat("确认", [final("全部完成", "report", action_refs=[item["action_id"]],
                read_refs=["file-start:read:1"])] * 2, "before-confirm")
            self.observe(answer)
            self.assertIn("尚未完成", answer)
            self.assertNotIn("文件任务已完成", answer)

        async def test_wrong_path_read_does_not_discharge_obligation(self):
            other = self.root / "other.txt"
            other.write_bytes(self.content.encode())
            item = await self.propose()
            answer, _ = await self.chat("确认", [call("read_file", path=str(other)),
                final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])] +
                [final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "wrong-confirm")
            self.observe(answer)
            self.assertIn("尚未完成", answer)
            self.assertNotIn("文件任务已完成", answer)

        async def test_failed_actual_read_does_not_discharge_obligation(self):
            item = await self.propose()
            original = core._execute_authorized_tool
            async def missing_read(name, arguments):
                if name == "read_file":
                    self.path.unlink()
                return await original(name, arguments)
            with patch.object(core, "_execute_authorized_tool", missing_read):
                answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
                    final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "failed-read")
            self.observe(answer)
            self.assertIn("尚未完成", answer)
            self.assertNotIn("文件任务已完成", answer)

        async def test_changed_file_bytes_not_same_receipt(self):
            item = await self.propose()
            original = core._execute_authorized_tool
            async def modified_read(name, arguments):
                if name == "read_file":
                    self.path.write_bytes(b"unrelated replacement")
                return await original(name, arguments)
            with patch.object(core, "_execute_authorized_tool", modified_read):
                answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
                    final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])] +
                    [final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "changed-read")
            self.observe(answer)
            self.assertIn("尚未完成", answer)
            self.assertNotIn("文件任务已完成", answer)

        async def test_cross_task_read_receipt_rejected(self):
            item = await self.propose()
            await self.chat("确认", [call("read_file", path=str(self.path)),
                final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "valid-read")
            task = core._task_state[self.sid]
            record = task["tool_results"][0]
            self.assertIsNotNone(read_for(item, task, self.sid))
            record["task_id"] = "unrelated-task"
            self.assertIsNone(read_for(item, task, self.sid))
            record["task_id"] = task["id"]
            record["session_id"] = self.sid + 1
            self.assertIsNone(read_for(item, task, self.sid))
            self.observe("foreign task and session read rejected")

        async def test_replacement_after_cancel_can_finish(self):
            old = await self.propose()
            self.content = "替换后的完整内容 8cm"
            await self.chat("取消旧的，改成新版，仍然写入后读取完整内容", [
                call("write_file", path=str(self.path), content=self.content)], "replace")
            item = core._sync_pending(self.sid)[0]
            answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
                final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "replace-confirm")
            self.observe(answer, old_status=old["status"], new_status=item["status"])
            self.assertEqual(self.path.read_bytes(), self.content.encode())
            self.assertIn("文件任务已完成", answer)
            self.assertIn(self.content, answer)

        async def test_read_then_timeout_still_delivers_exact_content(self):
            await self.propose()
            answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
                core.ProviderError("synthetic after-read timeout")], "timeout-after-read")
            self.observe(answer)
            self.assertIn("文件任务已完成", answer)
            self.assertIn(self.content, answer)
            await self.chat("确认", [], "duplicate-after-read")
            self.assertEqual([name for name, _ in self.effects].count("write_file"), 1)

        async def test_pending_new_file_request_not_chat_escape(self):
            await self.propose()
            text = f"另外请创建文件 {self.root / 'second.txt'}，写入后读取并展示完整内容。内容如下：SECOND"
            answer, _ = await self.chat(text, [final("第二个文件已安排待办，请确认"), final("第二个文件完成")], "second-request")
            self.observe(answer, request=text)
            self.assertNotIn("已安排待办", answer)

        async def test_continue_keeps_budget_and_obligation(self):
            await self.propose()
            await self.chat("确认", [core.ProviderError("synthetic timeout")], "first-timeout")
            task = core._task_state[self.sid]
            before = (task["id"], task["rounds_used"], task["calls_used"])
            answer, _ = await self.chat("继续", [call("read_file", path=str(self.path)),
                final("完成", "report", action_refs=[next(iter(core._actions().records))],
                      read_refs=["file-start:read:1"])], "continue")
            self.observe(answer, budget_before=before,
                budget_after=(task["id"], task["rounds_used"], task["calls_used"]))
            self.assertIs(task, core._task_state[self.sid])
            self.assertGreater(task["rounds_used"], before[1])
            self.assertIn(self.content, answer)
            self.assertIn("文件任务已完成", answer)

        async def test_real_write_then_lost_receipt_never_reexecutes(self):
            item = await self.propose()
            original = core._execute_authorized_tool
            async def lost_receipt(name, arguments):
                await original(name, arguments)
                raise TimeoutError("synthetic lost write acknowledgement")
            with patch.object(core, "_execute_authorized_tool", lost_receipt):
                answer, _ = await self.chat("确认", [final("全部完成", "report",
                    action_refs=[item["action_id"]])], "unknown-confirm")
            self.observe(answer, action_status=item["status"])
            self.assertEqual(self.path.read_bytes(), self.content.encode())
            self.assertEqual(item["status"], "unknown")
            self.assertIn("结果未知", answer)
            self.assertNotIn("文件任务已完成", answer)
            await self.chat("确认", [], "unknown-duplicate")
            self.assertEqual([name for name, _ in self.effects].count("write_file"), 1)

        async def test_pending_conversation_and_status_do_not_consume_task_budget(self):
            item = await self.propose()
            task = core._task_state[self.sid]
            before = dict(task)
            expected = "今天可以聊聊音乐。"
            answer, _ = await self.chat("今天可以聊点什么？", [final(expected)], "casual")
            self.assertEqual(answer, expected)
            # Preserve the already supported status contract. The second-run
            # evidence records a separate pre-existing classifier wording gap.
            answer, provider = await self.chat("刚才那个任务现在怎么样？", [], "status")
            self.observe(answer)
            self.assertIn("待确认", answer)
            self.assertEqual(provider.complete_with_tools.await_count, 0)
            for key in ("id", "intent", "budget", "rounds_used", "calls_used", "corrections_used"):
                self.assertEqual(task.get(key), before.get(key))
            self.assertEqual(core._sync_pending(self.sid)[0]["action_id"], item["action_id"])
            self.assertFalse(self.effects)

        async def test_literal_wrong_body_corrects_without_wrong_ticket(self):
            wrong = self.content.replace("第一行：", "").replace("第二行：", "")
            answer, provider = await self.chat(self.request(), [
                call("write_file", path=str(self.path), content=wrong),
                call("write_file", path=str(self.path), content=self.content)])
            pending = core._sync_pending(self.sid)
            self.observe(answer, provider_rounds=provider.complete_with_tools.await_count)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["arguments"]["content"], self.content)
            self.assertEqual(len(core._actions().records), 1)
            self.assertEqual(provider.complete_with_tools.await_count, 2)
            self.assertFalse(self.effects)

        async def test_literal_error_cannot_fall_back_to_fake_chat(self):
            answer, provider = await self.chat(self.request(), [
                call("write_file", path=str(self.path), content="wrong"),
                final("已经安排待办，请确认")])
            self.observe(answer)
            self.assertNotIn("已经安排待办", answer)
            self.assertIn("尚未完成", answer)
            self.assertEqual(provider.complete_with_tools.await_count, 2)
            self.assertFalse(core._actions().records)
            self.assertFalse(self.effects)

        async def test_literal_error_can_correct_missing_path(self):
            answer, provider = await self.chat(self.request(), [
                call("write_file", content=self.content),
                call("write_file", path=str(self.path), content=self.content)])
            self.observe(answer)
            self.assertEqual(provider.complete_with_tools.await_count, 2)
            self.assertEqual(len(core._actions().records), 1)
            self.assertEqual(core._sync_pending(self.sid)[0]["arguments"]["content"], self.content)
            self.assertFalse(self.effects)

        async def test_literal_explanation_and_missing_parameters_still_work(self):
            expected = "这是正文说明，不代表已创建文件。"
            answer, _ = await self.chat("请解释创建文件后读取的流程，示例内容如下：第一行：示例", [final(expected)])
            self.assertEqual(answer, expected)
            answer, _ = await self.chat("请创建文件并读回，内容如下：待指定位置", [
                final("", "clarify", tool="write_file", arguments={"content": "待指定位置"}, missing=["path"])], "literal-clarify")
            self.observe(answer)
            self.assertIn("path", answer)
            self.assertFalse(core._actions().records)
            self.assertFalse(self.effects)

        async def test_literal_body_blank_lines_and_trailing_space_remain_exact(self):
            self.content = "\n 第一行：7cm\r\n第二行：20℃  \n"
            text = f"请创建文件 {self.path}，随后实际读取并完整展示。内容如下（逐字）：\r\n{self.content}"
            answer, _ = await self.chat(text, [call("write_file", path=str(self.path), content=self.content)])
            item = core._sync_pending(self.sid)[0]
            self.assertEqual(item["arguments"]["content"], self.content)
            answer, _ = await self.chat("确认", [call("read_file", path=str(self.path)),
                final("完成", "report", action_refs=[item["action_id"]], read_refs=["file-start:read:1"])], "whitespace-confirm")
            self.observe(answer)
            self.assertEqual(self.path.read_bytes(), self.content.encode())
            self.assertIn(self.content, answer)

        async def test_literal_contract_survives_continue_after_rejected_proposals(self):
            wrong = self.content.replace("第一行：", "").replace("第二行：", "")
            await self.chat(self.request(), [call("write_file", path=str(self.path), content=wrong)] * 2)
            self.assertFalse(core._actions().records)
            task = core._task_state[self.sid]
            answer, _ = await self.chat("继续", [call("write_file", path=str(self.path), content=wrong)], "literal-continue")
            self.observe(answer, expected_content=self.content,
                ticket_contents=[item["arguments"].get("content") for item in core._sync_pending(self.sid)])
            self.assertIs(task, core._task_state[self.sid])
            self.assertFalse(core._sync_pending(self.sid), "Continuation accepted content previously rejected for the same task")
            self.assertFalse(self.effects)

        async def test_literal_edit_rejects_wrong_new_body(self):
            old = await self.propose()
            expected = "新版第一行：测试\n新版第二行：保留"
            wrong = "测试\n保留"
            text = f"取消旧的，改成新版，创建文件 {self.path} 后仍需实际读取并完整展示。内容如下：\n{expected}"
            answer, _ = await self.chat(text, [call("write_file", path=str(self.path), content=wrong)] * 2,
                "literal-edit")
            self.observe(answer, expected_content=expected,
                ticket_contents=[item["arguments"].get("content") for item in core._sync_pending(self.sid)])
            self.assertEqual(old["status"], "cancelled")
            self.assertFalse(core._sync_pending(self.sid), "Explicit edited literal body was not validated")
            self.assertFalse(self.effects)

        async def test_literal_path_only_edit_preserves_unchanged_body(self):
            old = await self.propose()
            new_path = self.root / "changed-name.txt"
            wrong = self.content.replace("第一行：", "").replace("第二行：", "")
            text = f"取消旧的，路径改为 {new_path}，正文不变，仍然要在写入后读取并展示完整内容。"
            answer, _ = await self.chat(text, [call("write_file", path=str(new_path), content=wrong)] * 2,
                "path-only-edit")
            self.observe(answer, expected_content=self.content,
                ticket_contents=[item["arguments"].get("content") for item in core._sync_pending(self.sid)])
            self.assertEqual(old["status"], "cancelled")
            self.assertFalse(core._sync_pending(self.sid), "Path-only edit dropped explicitly unchanged literal body")
            self.assertFalse(self.effects)

    stream = io.StringIO()
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            suite = (unittest.TestSuite(IndependentFileTests(name) for name in args.test) if args.test
                     else unittest.defaultTestLoader.loadTestsFromTestCase(IndependentFileTests))
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    finally:
        core.memory.close()
        original_memory.close()
    record = {"scope": "isolated deterministic providers; real temporary write_file/read_file; no model/network/services",
        "model_calls": 0, "source_sha256_before": source_before, "source_sha256_after": hashes(),
        "tests": result.testsRun, "passed": result.wasSuccessful(),
        "failures": [{"test": t.id(), "trace": s} for t, s in result.failures],
        "errors": [{"test": t.id(), "trace": s} for t, s in result.errors],
        "observations": observations}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.data_dir / "runner.txt").write_text(stream.getvalue(), encoding="utf-8")
    print(json.dumps({"tests": result.testsRun, "passed": result.wasSuccessful(),
        "failures": [t.id().split(".")[-1] for t, _ in result.failures],
        "errors": [t.id().split(".")[-1] for t, _ in result.errors], "evidence": str(args.output)}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
