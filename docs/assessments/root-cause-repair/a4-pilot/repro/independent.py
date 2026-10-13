"""Offline A4 adversarial checks through the real Core entry point.

This script exits nonzero when an acceptance assertion fails. A reproduced
vulnerability is explicitly a failure, never an acceptance pass. The inherited
audit guard forbids disk writes, non-memory SQLite, subprocesses and network
during each case; JSON evidence is written only after fixture cleanup.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock


ARGS = None
CASES = []


def final(text, mode="chat", **fields):
    return {"content": json.dumps({"reply": text, "decision": {"mode": mode, **fields}}, ensure_ascii=False)}


def call(name, **arguments):
    return {"tool_calls": [{"id": "independent-call", "name": name, "arguments": arguments}]}


def hashes(root):
    return {str(p.relative_to(root)).replace(os.sep, "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / "services/agent-core/agent_core").glob("*.py"))}


def build_suite(base):
    class IndependentA4(base):
        def setUp(self):
            super().setUp()
            self.core.tools_schema += [{"type": "function", "function": {
                "name": "write_file", "parameters": {"type": "object", "properties": {
                    "path": {"type": "string"}, "content": {"type": "string"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"]}},
                    "required": ["path", "content"]}}}]
            self.row = {"case": self._testMethodName, "turns": [], "assertions": [],
                        "scope": "memory DB, scripted model, virtual tool executor"}
            CASES.append(self.row)

        async def turn(self, text, request, turns, *, effort="standard"):
            self.core.provider.complete_with_tools = AsyncMock(side_effect=copy.deepcopy(turns))
            self.core.provider.complete = AsyncMock(side_effect=AssertionError("unexpected plain model fallback"))
            entry = {"user": text, "request_id": request, "scripted_model": copy.deepcopy(turns)}
            self.row["turns"].append(entry)
            try:
                await self.chat(text, request, effort=effort)
                entry["reply"] = self.latest_reply()
            except Exception as exc:
                entry["exception"] = {"type": type(exc).__name__, "message": str(exc)}
            entry["model_calls"] = self.core.provider.complete_with_tools.await_count
            entry["plain_model_calls"] = self.core.provider.complete.await_count
            entry["effects"] = copy.deepcopy(self.effects)
            entry["actions"] = copy.deepcopy(list(self.book.records.values()))
            entry["task"] = copy.deepcopy(self.core._task_state.get(self.sid))
            return entry

        def check(self, condition, requirement):
            self.row["assertions"].append({"requirement": requirement, "passed": bool(condition)})

        def tearDown(self):
            self.row["blocked_io"] = list(self.blocked_io)
            self.row["passed"] = all(item["passed"] for item in self.row["assertions"]) and not self.blocked_io
            self.row["classification"] = "acceptance_pass" if self.row["passed"] else "acceptance_failure_reproduced"
            super().tearDown()
            self.assertTrue(self.row["passed"], json.dumps(self.row["assertions"], ensure_ascii=False))

        async def test_chat_mode_cannot_forge_pending(self):
            lie = "文件内容和目标都准备妥当了，回复确认后我就落盘。"
            r = await self.turn("把复核结果写入 a4.txt，内容为175。", "fake-pending", [final(lie)] * 2)
            self.check(lie not in r.get("reply", ""), "no ticket: do not deliver fictional pending state from model chat mode")
            self.check(not r["actions"] and not r["effects"], "fixture has no real proposal or effect")

        async def test_chat_mode_cannot_forge_completed(self):
            lie = "你要的修改已落地，目标文件现在就是175。"
            r = await self.turn("把复核结果写入 a4.txt，内容为175。", "fake-complete", [final(lie)] * 2)
            self.check(lie not in r.get("reply", ""), "no receipt: do not deliver fictional completion from model chat mode")
            self.check(not r["actions"] and not r["effects"], "fixture has no real proposal or effect")

        async def test_successful_read_cannot_launder_false_write(self):
            lie = "材料总数175；另外标题已替你改妥并保存。"
            r = await self.turn("读取资料汇总，再把目标文件改成175。", "read-launder", [
                call("get_time"), final(lie, "report", read_refs=["read-launder:read:1"])])
            self.check(lie not in r.get("reply", ""), "genuine read reference must not attest an unrelated write")
            self.check([name for name, _ in r["effects"]] == ["get_time"] and not r["actions"], "only read effect occurred")

        async def test_pending_task_cannot_be_relabelled_completed_on_later_turn(self):
            await self.turn("写入合成文件", "pending-origin", [call("write_file", path=str(self.root / "pending.txt"), content="175")])
            lie = "你刚才交代的文件已经处理好了，不需要再做任何事。"
            r = await self.turn("刚才那件事现在怎么样？", "pending-status", [final(lie)] * 2)
            self.check(lie not in r.get("reply", ""), "a later question must not hide the real pending action via chat mode")
            self.check(len(r["actions"]) == 1 and r["actions"][0]["status"] == "awaiting_confirmation" and not r["effects"], "ticket is still pending and never executed")

        async def test_act_then_real_missing_parameters_can_clarify(self):
            r = await self.turn("帮我写份备忘，路径和正文还没给你。", "act-clarify", [final("", "act"),
                final("", "clarify", tool="write_file", arguments={}, missing=["path", "content"])])
            self.check("path" in r.get("reply", "") and "content" in r.get("reply", ""), "single correction may discover legitimate missing parameters and ask for them")
            self.check(not r["actions"] and not r["effects"], "clarification creates no ticket or effect")

        async def test_mode_shape_error_is_contained(self):
            r = await self.turn("你好", "malformed-mode", [final("你好", mode={}), final("你好")])
            self.check("exception" not in r, "malformed decision.mode is corrected or rejected without escaping handle_chat")

        async def test_optional_parameter_is_not_a_required_clarification(self):
            path = str(self.root / "complete.txt")
            r = await self.turn("将175写入指定文件，使用默认覆盖模式。", "optional-missing", [final("", "clarify",
                tool="write_file", arguments={"path": path, "content": "175"}, missing=["mode"])] * 2)
            self.check("还需要你补充这些参数：mode" not in r.get("reply", ""), "schema-optional parameter cannot be presented as mandatory missing input")

        async def test_control_plain_chat_preserved(self):
            reply = "晚上好，我们聊聊今天听的音乐吧。"
            r = await self.turn("晚上好", "plain-chat", [final(reply)])
            self.check(r.get("reply") == reply and r["model_calls"] == 1, "ordinary chat remains complete and needs no correction")

        async def test_control_explanation_preserved(self):
            reply = "确认流程是先展示工具名和参数，再由你确认；完成声明需要真实执行回执。"
            r = await self.turn("解释确认后执行是什么意思", "explanation", [final(reply)])
            self.check(r.get("reply") == reply and not r["effects"] and not r["actions"], "confirmation explanation is delivered without making a proposal")

        async def test_control_long_read_summary_preserved(self):
            reply = "准备、执行、核验三部分。" + "正文分析与证据说明。" * 1000 + "最终总数175。"
            async def read(*args):
                self.effects.append(copy.deepcopy(args))
                return {"ok": True, "output": reply}
            self.core._execute_authorized_tool = read
            r = await self.turn("请阅读材料并完整汇总", "full-summary", [call("get_time"),
                final(reply, "report", read_refs=["full-summary:read:1"])])
            self.check(r.get("reply") == reply, "legitimate complete read summary remains intact")

        async def test_control_missing_required_parameters(self):
            r = await self.turn("帮我写文件，稍后提供路径和内容", "clarification", [final("", "clarify",
                tool="write_file", arguments={}, missing=["path", "content"])])
            self.check("path" in r.get("reply", "") and "content" in r.get("reply", "") and not r["actions"], "schema-valid required clarification works without a ticket")

        async def test_control_one_correction_and_continuation_budget(self):
            first = await self.turn("修改指定合成文件", "budget-origin", [final("", "act")] * 2)
            before = first["task"]
            after = await self.turn("继续", "budget-continue", [final("", "act")])
            self.check(first["model_calls"] == 2 and after["model_calls"] == 1, "at most one corrective model turn per task")
            self.check(after["task"]["id"] == before["id"] and after["task"]["intent"] == before["intent"], "continuation preserves task identity and original intent")
            self.check(after["task"]["rounds_used"] == before["rounds_used"] + 1 and after["task"]["corrections_used"] == 1, "continuation retains consumed work and corrective budget")

        async def test_control_proposal_confirmation_receipt(self):
            first = await self.turn("写入指定合成文件", "real-proposal", [call("write_file", path=str(self.root / "confirm.txt"), content="175")])
            aid = first["actions"][0]["action_id"]
            self.check(first["actions"][0]["status"] == "awaiting_confirmation" and not first["effects"], "write proposal reaches existing ticket gate before any effect")
            after = await self.turn("确认", "real-confirm", [final("已完成", "report", action_refs=[aid])])
            self.check(len(after["effects"]) == 1 and after["actions"][0]["status"] == "succeeded", "exact confirmed ticket executes once")
            self.check("执行成功" in after.get("reply", ""), "host receipt supplies successful status")
            again = await self.turn("确认", "real-again", [])
            self.check(len(again["effects"]) == 1 and again["model_calls"] == 0, "repeated confirmation does not rerun the operation")

        async def test_control_cross_task_reference_rejected(self):
            r = await self.turn("继续办理指定事项", "foreign-ref", [final("伪造完成", "report", read_refs=["foreign-task:read:1"])] * 2)
            self.check("伪造完成" not in r.get("reply", "") and r["model_calls"] == 2, "unknown references trigger one correction then host incomplete state")

    names = [name for name in IndependentA4.__dict__ if name.startswith("test_")]
    return unittest.TestSuite(IndependentA4(name) for name in names)


def main():
    global ARGS
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    ARGS = parser.parse_args()
    root = ARGS.source_root.resolve()
    os.environ["HARNESS_REVIEW_CORE_ROOT"] = str(root / "services/agent-core")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / "services/agent-core/tests"))
    import test_harness_v1_review as fixture
    before = hashes(root)
    result = unittest.TextTestRunner(verbosity=2).run(build_suite(fixture.IndependentReviewTests))
    after = hashes(root)
    evidence = {"scope": "independent offline A4 adversarial acceptance; zero real model/service calls",
                "source_root": str(root), "baseline_commit": "463cbdd647cda728e5e4bded928f59216a3d2cb1",
                "source_sha256_before": before, "source_sha256_after": after,
                "source_stable": before == after,
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                "acceptance_passed": result.wasSuccessful() and before == after, "cases": CASES}
    if ARGS.output.exists():
        raise SystemExit("Refusing to overwrite prior independent evidence")
    ARGS.output.parent.mkdir(parents=True, exist_ok=True)
    ARGS.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tests_run": result.testsRun, "acceptance_passed": evidence["acceptance_passed"],
                      "failures": len(result.failures), "errors": len(result.errors), "source_stable": before == after}))
    raise SystemExit(0 if evidence["acceptance_passed"] else 1)


if __name__ == "__main__":
    main()
