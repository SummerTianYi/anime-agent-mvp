"""Independent follow-up review: in-memory state, no service or desktop access.

Reuses the existing audit-guarded review fixture, not implementation tests.
The two A4 tests assert that the known counterexamples remain reproducible;
their success must never be described as A4 being fixed.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "services" / "agent-core" / "tests"))
import test_harness_v1_review as fixture


class FollowupReview(fixture.IndependentReviewTests):
    def setUp(self):
        super().setUp()
        self.expect(Path(self.core.__file__).resolve().parent == fixture.CORE_ROOT / "agent_core",
                    "source import drift")

    def answer_after(self, name, arguments, answer=fixture.FALSE_SUCCESS):
        self.core.provider.complete_with_tools.side_effect = [
            {"tool_calls": [fixture._call(name, arguments)]},
            {"content": fixture._reply(answer)},
        ]

    async def test_invalid_reference_is_a_durable_failure(self):
        for index, ref in enumerate(([], {}, None, 1, True)):
            self.answer_after("read_tool_result", {"ref": ref, "offset": 0})
            request = "invalid-ref-" + str(index)
            await self.chat("读取下一页", request)
            task = self.core._task_state[self.sid]
            record = task["tool_results"][0]
            self.expect(record["result"].get("outcome") == "failed", "bad ref not recorded as failed")
            self.expect(record["request_id"] == request and record["task_id"] == task["id"],
                        "failed read was attributed to another request or task")
            self.expect(bool(task["tool_failures"]), "failed read missing delivery evidence")
            self.expect(fixture.FALSE_SUCCESS not in self.latest_reply(), "bad ref leaked false success")
            self.expect(not self.book.pending(self.sid), "bad ref created a confirmation ticket")

    async def test_allow_exception_is_unknown_and_not_repeated(self):
        execute = AsyncMock(side_effect=RuntimeError("synthetic executor exception"))
        self.core._execute_authorized_tool = execute
        self.answer_after("get_time", {})
        await self.chat("读取合成状态", "allow-exception")
        task = self.core._task_state[self.sid]
        self.expect(task["tool_results"][0]["result"]["outcome"] == "unknown", "exception lost unknown")
        self.expect("结果未知" in self.latest_reply(), "unknown missing from delivered reply")
        self.expect(fixture.FALSE_SUCCESS not in self.latest_reply(), "exception leaked false success")
        await self.chat("确认", "empty-confirm-after-exception")
        self.expect(execute.await_count == 1, "empty confirmation repeated the read")
        self.expect(self.core._task_state[self.sid] is task, "empty confirmation reset the task")

    async def test_cancellation_is_not_converted_to_unknown(self):
        self.core._execute_authorized_tool = AsyncMock(side_effect=asyncio.CancelledError())
        self.answer_after("get_time", {})
        propagated = False
        try:
            await self.chat("读取合成状态", "cancel-control")
        except asyncio.CancelledError:
            propagated = True
        self.expect(propagated, "CancelledError was swallowed by ALLOW recovery")
        self.expect(not self.core._task_state[self.sid].get("tool_results"), "cancellation manufactured a receipt")

    async def test_existing_failed_and_unknown_receipts_stay_guarded(self):
        for outcome in ("failed", "unknown"):
            self.core._execute_authorized_tool = AsyncMock(return_value={
                "ok": False, "outcome": outcome, "error": "FIXTURE_READ_" + outcome,
            })
            self.answer_after("get_time", {})
            await self.chat("读取合成状态", "typed-" + outcome)
            self.expect(fixture.FALSE_SUCCESS not in self.latest_reply(), "non-success leaked model assertion")
            self.expect("FIXTURE_READ_" + outcome in self.latest_reply(), "known error was lost")
            if outcome == "unknown":
                self.expect("结果未知" in self.latest_reply(), "unknown mislabeled")

    async def test_long_read_tail_and_substantive_summary_survive(self):
        answer = "材料的最后结论是合计一百七十五。"
        self.core._execute_authorized_tool = AsyncMock(return_value={
            "ok": True, "output": "x" * 9000 + "TAIL-175",
        })
        turns = 0

        async def provider(*_):
            nonlocal turns
            turns += 1
            if turns == 1:
                return {"tool_calls": [fixture._call("get_time", {})]}
            if turns == 2:
                pages = self.core._result_pages[self.sid]
                ref = next(iter(pages.items))
                return {"tool_calls": [fixture._call("read_tool_result", {
                    "ref": ref, "offset": len(pages.items[ref]) - 50,
                })]}
            return {"content": fixture._reply(answer)}

        self.core.provider.complete_with_tools.side_effect = provider
        await self.chat("归纳材料末尾的数字", "tail-summary")
        task = self.core._task_state[self.sid]
        self.expect(self.latest_reply() == answer, "read summary was replaced")
        self.expect("TAIL-175" in task["tool_results"][-1]["result"]["content"], "tail page was lost")
        self.expect(not task.get("tool_failures"), "valid page was classified as failed")

    async def test_ordinary_chat_keeps_old_pending(self):
        proposal = await self.propose()
        answer = "晚上好，我是天依。希望你今天过得开心。"
        self.core.provider.complete_with_tools.return_value = {"content": fixture._reply(answer)}
        await self.chat("保留待办，先问候一句", "pending-chat")
        self.expect(self.latest_reply() == answer, "old pending replaced normal chat")
        self.expect(self.book.pending(self.sid)[0]["action_id"] == proposal["action_id"], "pending was lost")
        self.expect(not self.effects, "ordinary chat authorized a pending operation")

    async def test_process_explanation_and_quote_are_preserved(self):
        answer = "界面上的“确认”表示同意当前提案；邮件原文可以包含“已经发送”这句话。"
        self.core.provider.complete_with_tools.return_value = {"content": fixture._reply(answer)}
        await self.chat("解释确认按钮并举一句引用的例子", "content-control")
        self.expect(self.latest_reply() == answer, "ordinary explanation or quote was removed")
        self.expect(not self.effects and not self.book.records, "explanation created an action")

    async def test_a4_no_calls_false_pending_remains_reproducible(self):
        answer = "我已准备更新标题，你确认就能执行。"
        self.core.provider.complete_with_tools.return_value = {"content": fixture._reply(answer)}
        await self.chat("更新合成Issue标题", "a4-no-calls")
        self.expect(self.latest_reply() == answer, "known A4 no-calls counterexample changed")
        self.expect(not self.book.records and not self.effects, "A4 fixture unexpectedly made a real proposal")

    async def test_a4_read_success_extra_write_remains_reproducible(self):
        answer = "只读结果合计175；我还把标题改好了。"
        self.answer_after("get_time", {}, answer)
        await self.chat("查看合成只读结果", "a4-read-extra-write")
        self.expect(self.latest_reply() == answer, "known A4 read counterexample changed")
        self.expect([name for name, _ in self.effects] == ["get_time"], "A4 fixture executed an additional action")
        self.expect(not self.book.records, "A4 fixture unexpectedly created an action ticket")


def source_hashes():
    return {name: hashlib.sha256((fixture.CORE_ROOT / "agent_core" / name).read_bytes()).hexdigest()
            for name in ("main.py", "result_pages.py", "actions.py")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=REPO)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not __debug__:
        parser.error("optimized Python is not an accepted review runner")
    fixture.CORE_ROOT = (args.source_root / "services" / "agent-core").resolve()
    before = source_hashes()
    own_names = sorted(name for name in FollowupReview.__dict__ if name.startswith("test_"))
    compatibility = [
        "test_p1_unbound_duplicate_cannot_authorize_next_parameters",
        "test_control_explicit_ticket_double_click_then_fresh_ticket",
        "test_p1_cancel_received_before_dispatch_revokes_queued_approval",
        "test_p1_reused_unknown_receipt_blocks_resend_and_false_success",
        "test_p1_no_pending_continue_does_not_refill_call_budget_or_effort",
        "test_p1_no_pending_continue_does_not_refill_round_budget",
    ]
    suite = unittest.TestSuite([FollowupReview(name) for name in own_names] +
                              [fixture.IndependentReviewTests(name) for name in compatibility])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    stable = before == source_hashes()
    record = {
        "kind": "independent isolated follow-up review; not desktop or model acceptance",
        "baseline_commit": "d0ff796a61cbbd10eb3af1cd9ba28775253891e2",
        "source_sha256": before,
        "sources_stable_during_run": stable,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tests_run": result.testsRun,
        "assertions_executed": sum(fixture.ASSERTION_COUNTS.values()),
        "assertions_by_test": dict(sorted(fixture.ASSERTION_COUNTS.items())),
        "failed_tests": [case.id() for case, _ in result.failures],
        "error_tests": [case.id() for case, _ in result.errors],
        "checks_passed": result.wasSuccessful() and stable,
        "a4_status": "unresolved: both counterexamples are deliberately asserted to remain visible",
        "real_model_calls": 0,
        "desktop_actions": 0,
        "filesystem_database_reads": 0,
        "isolation": "existing fixture audit guard denies network, filesystem DBs, writes, subprocesses and .env reads",
    }
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
