"""Independent pending-status counterexamples through isolated handle_chat."""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[5]
CORE_ROOT = (ROOT / "services/agent-core").resolve()
os.environ["HARNESS_REVIEW_CORE_ROOT"] = str(CORE_ROOT)
sys.path.insert(0, str(ROOT / "services/agent-core/tests"))
import test_pending_status as existing

if existing.fixture.CORE_ROOT.resolve() != CORE_ROOT:
    raise RuntimeError("Review fixture Core root differs from the hashed candidate")

CASES = []


def finalize_case_outcomes(result):
    unsuccessful = {
        getattr(test, "test_case", test)._testMethodName
        for test, _ in result.failures + result.errors
    }
    for case in CASES:
        case["passed"] = (bool(case["checks"])
                          and all(check["passed"] for check in case["checks"])
                          and case.get("blocked_io") == []
                          and case["case"] not in unsuccessful)


def source_hashes():
    return {
        name: hashlib.sha256((ROOT / "services/agent-core/agent_core" / name).read_bytes()).hexdigest()
        for name in ("main.py", "task_status.py", "task_delivery.py", "actions.py", "agent_loop.py")
    }


class PendingIndependentReview(existing.PendingStatusTests):
    def setUp(self):
        super().setUp()
        # Real natural-language task creation must establish its own intent.
        self.core._task_state.pop(self.sid, None)
        self.record = {"case": self._testMethodName, "turns": [], "checks": []}
        CASES.append(self.record)

    def snapshot(self):
        return copy.deepcopy({
            "ledger": list(self.book.records.values()),
            "task": self.core._task_state.get(self.sid),
            "effects": self.effects,
        })

    async def chat(self, text, request_id, **kwargs):
        before = self.snapshot()
        await super().chat(text, request_id, **kwargs)
        self.record["turns"].append({
            "user": text, "request_id": request_id,
            "reply": self.latest_reply(), "before": before, "after": self.snapshot(),
            "model_calls": self.core.provider.complete_with_tools.await_count,
            "plain_model_calls": self.core.provider.complete.await_count,
        })

    def check(self, requirement, passed):
        self.record["checks"].append({"requirement": requirement, "passed": bool(passed)})
        self.assertTrue(passed, requirement)

    def tearDown(self):
        self.record["blocked_io"] = list(self.blocked_io)
        self.record["passed"] = all(check["passed"] for check in self.record["checks"])
        super().tearDown()

    async def test_explicit_natural_progress_rephrase(self):
        await self.create_pending()
        before = self.snapshot()
        answer = await self.request("刚才让你写的文件，现在完成了吗？", "rephrase")
        self.check("explicit progress question uses pending ledger instead of false model completion",
                   "待确认，尚未执行" in answer and "已经全部完成" not in answer)
        self.check("progress is read only", self.snapshot() == before)

    async def test_explicit_progress_negative_question(self):
        await self.create_pending()
        before = self.snapshot()
        answer = await self.request("文件还没写完吗？", "negative-progress")
        self.check("negative progress question cannot surface a false completion",
                   "待确认，尚未执行" in answer and "已经全部完成" not in answer)
        self.check("negative progress question preserves task and ledger", self.snapshot() == before)

    async def test_cancel_status_question_is_not_revocation(self):
        await self.create_pending()
        before = self.snapshot()
        answer = await self.request("刚才那个任务有没有被取消？", "cancel-question")
        self.check("asking whether cancellation occurred must preserve pending parameters and status",
                   self.snapshot() == before)
        self.check("cancel status question reports still pending", "待确认，尚未执行" in answer)

    async def test_explicit_revocation_is_not_swallowed_by_status(self):
        item = (await self.create_pending())[0]
        await self.request("任务先取消，再告诉我状态", "cancel-then-status")
        self.check("explicit cancellation in compound request revokes the pending ticket",
                   item["status"] == "cancelled")
        self.check("cancel request has no effects", not self.effects)

    async def test_queued_approval_obeys_compound_revocation(self):
        await self.queued_revocation("任务先取消，再告诉我状态")

    async def test_file_reference_does_not_swallow_compound_revocation(self):
        await self.queued_revocation("先取消待办再告诉我first.txt的状态")

    async def test_hold_before_status_revokes_queued_approval(self):
        await self.queued_revocation("先不要执行，只问刚才任务进度如何？")

    async def queued_revocation(self, text):
        item = (await self.create_pending())[0]
        await self.core.chat_lock.acquire()
        approval = asyncio.create_task(self.chat("确认", "queued-approval", confirmation=self.book.ticket(item)))
        cancellation = None
        try:
            await asyncio.sleep(0)
            cancellation = asyncio.create_task(self.chat(text, "queued-revocation"))
            for _ in range(4):
                await asyncio.sleep(0)
            self.record["before_unlock"] = self.snapshot()
        finally:
            self.core.chat_lock.release()
            await asyncio.gather(approval, *([cancellation] if cancellation is not None else []))
        self.check("revocation received before dispatch prevents queued approved mutation", not self.effects)
        self.check("compound cancellation retains cancelled receipt", item["status"] == "cancelled")

    async def test_normal_personal_greeting_is_not_task_query(self):
        await self.create_pending()
        before = self.snapshot()
        answer = await self.request("你现在怎么样？", "greeting", reply="我很好呀，谢谢关心！")
        self.check("ordinary personal check-in still receives its chat answer", answer == "我很好呀，谢谢关心！")
        after = self.snapshot()
        budget_keys = ("id", "budget", "rounds_used", "calls_used", "corrections_used")
        self.check("greeting preserves pending state and budget", after["ledger"] == before["ledger"]
                   and after["effects"] == before["effects"]
                   and all(after["task"].get(key) == before["task"].get(key) for key in budget_keys))

    async def test_file_target_spaces_are_preserved(self):
        await self.create_pending(("review draft.txt",))
        answer = await self.request("review draft.txt完成了吗？", "file-space")
        self.check("explicit existing filename with spaces resolves its own pending ticket",
                   "review draft.txt" in answer and "待确认，尚未执行" in answer)

    async def test_control_literal_names_and_absolute_paths(self):
        await self.create_pending(("取消记录.txt", "review draft.txt"))
        before = self.snapshot()
        for index, text in enumerate(("取消记录.txt完成了吗？", "“取消记录.txt”完成了吗？",
                                      str(self.root / "review draft.txt") + "完成了吗？",
                                      "请告诉我 review draft.txt 的进度")):
            with self.subTest(text=text):
                answer = await self.request(text, f"literal-file-{index}")
                self.check("literal file progress is ledger-backed: " + text,
                           "待确认，尚未执行" in answer and "已经全部完成" not in answer)
                self.check("literal file progress preserves ledger and task", self.snapshot() == before)

    async def test_control_ledger_query_and_confirmation(self):
        await self.create_pending(("first.txt", "second.txt"))
        before = self.snapshot()
        answer = await self.request("这些任务都完成了吗？", "control-before")
        self.check("recognized status query reports two pending actions", "待确认，尚未执行 2项" in answer)
        self.check("recognized status query is read only", self.snapshot() == before)
        await self.request("确认", "control-confirm")
        answer = await self.request("所有任务状态如何", "control-partial")
        self.check("partial result distinguishes success and pending", "执行成功 1项" in answer and "待确认，尚未执行 1项" in answer)
        self.check("progress does not reexecute", len(self.effects) == 1)

    async def test_common_completion_verbs_use_existing_ledger(self):
        await self.create_pending()
        ledger = copy.deepcopy(self.book.records)
        for index, text in enumerate(("刚才那个文件保存了吗？", "文件写入成功了吗？", "这个任务处理好了没有？")):
            with self.subTest(text=text):
                answer = await self.request(text, f"completion-verb-{index}")
                self.check("ordinary explicit progress phrasing is ledger-backed: " + text,
                           "待确认，尚未执行" in answer and "已经全部完成" not in answer)
                self.check("ordinary progress phrasing does not mutate tickets",
                           self.book.records == ledger and not self.effects)

    async def test_control_cross_session_query(self):
        await self.create_pending()
        other_sid = self.core.memory.create_session()["id"]
        self.book.propose(other_sid, "foreign-task", "foreign", "write_file", {"path": "foreign-only.txt", "content": "synthetic"})
        before = self.snapshot()
        answer = await self.request("任务foreign-task完成了吗？", "foreign-query")
        self.check("foreign task is not exposed", "foreign-only" not in answer and "foreign-task" not in answer)
        self.check("foreign query cannot execute or alter tickets", self.snapshot() == before)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", help="Run one named independent test without discovery")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite prior review evidence")
    before = source_hashes()
    selected = [name for name in PendingIndependentReview.__dict__ if name.startswith("test_") and (args.case is None or name == args.case)]
    if not selected:
        raise SystemExit("No matching independent test case")
    suite = unittest.TestSuite(PendingIndependentReview(name) for name in selected)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    finalize_case_outcomes(result)
    after = source_hashes()
    evidence = {
        "scope": "independent offline pending-status review; handle_chat; in-memory DB; scripted model; no real tool IO",
        "source_sha256_before": before, "source_sha256_after": after, "source_stable": before == after,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "actual_core_root": existing.fixture.CORE_ROOT.resolve().as_posix(),
        "source_root_verified": existing.fixture.CORE_ROOT.resolve() == CORE_ROOT,
        "real_model_calls": 0, "real_external_calls": 0,
        "acceptance_passed": result.wasSuccessful() and before == after, "cases": CASES,
        "failure_details": [{"case": test.id(), "details": details} for test, details in result.failures + result.errors],
    }
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2)
    serialized = serialized.replace(str(ROOT).replace(chr(92), chr(92) * 2), "<candidate-root>")
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(serialized + "\n")
    print(json.dumps({"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "source_stable": before == after}))
    return 0 if result.wasSuccessful() and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
