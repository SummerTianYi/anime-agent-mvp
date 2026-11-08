"""Independent synthetic counterexamples through the real natural-chat entry."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from agent_core import main as core
import test_harness_v1_integration as fixture


def runner_module(name="file_models"):
    root = Path(__file__).resolve().parents[3]
    directory = root / "docs/assessments/root-cause-repair/a4-pilot/repro"
    spec = importlib.util.spec_from_file_location("memory_review_" + name, directory / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", [str(directory), *sys.path]):
        spec.loader.exec_module(module)
    return module, root


class IndependentMemoryCorrectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture.MainActionTests.setUp(self)
        for name, value in (
            ("_task_state", {}), ("_result_pages", {}),
            ("_pending_writes", {}), ("_shown_confirmations", {}),
            ("_spawn", lambda coroutine: coroutine.close()),
            ("mcp_host", SimpleNamespace(tool_entries=lambda: [])),
        ):
            guard = patch.object(core, name, value)
            guard.start()
            self.addCleanup(guard.stop)
        self.n = 0
        for content in ("银杉预算80", "银山预算90", "银杉负责人陆予", "用户喜欢天蓝色"):
            self.store.add_fact(content, scope="global", status="confirmed")

    def facts(self):
        return [dict(row) for row in self.store.connection.execute("SELECT * FROM facts ORDER BY fact_id")]

    async def chat(self, text, *, candidate=None, sid=None, request_id=None, reply=None):
        self.n += 1
        provider = SimpleNamespace(complete=AsyncMock(return_value=json.dumps({
            "decision": {"mode": "chat"},
            "reply": reply or "已更正并保存到长期记忆。",
            "memory_candidate": candidate,
            # An intentionally wrong model target must not authorize a write.
            "fact_id": 2, "entity": "银山", "attribute": "负责人", "value": "错人",
        }, ensure_ascii=False)))
        selected_session = self.sid if sid is None else sid
        with patch.object(core, "provider", provider):
            await core.handle_chat(text, request_id or f"independent-{self.n}", selected_session)
        return self.store.load_messages(100, selected_session)[-1]["content"], provider

    async def test_polite_owner_rephrase_targets_only_one_attribute(self):
        before = self.facts()
        answer, provider = await self.chat("更正一下，银杉的负责人实际是顾宁。")
        self.assertIn("银杉负责人顾宁", self.store.recall_facts(self.sid))
        self.assertEqual(self.facts()[:2], before[:2])
        self.assertEqual(self.facts()[3], before[3])
        self.assertIn("陆予", answer)
        self.assertIn("顾宁", answer)
        provider.complete.assert_not_called()

    async def test_wrong_model_entity_and_fact_id_cannot_change_neighbor(self):
        before = self.facts()
        await self.chat("把银杉的预算由80改到95。", candidate="银山预算95")
        rows = self.facts()
        self.assertEqual(rows[1:4], before[1:4])
        self.assertIn("银杉预算95", self.store.recall_facts(self.sid))

    async def test_compound_middle_attribute_preserves_spaces_and_other_items(self):
        self.store.connection.execute("DELETE FROM facts")
        original = "银杉预算 80；负责人 陆予；地点 西楼"
        self.store.add_fact(original, scope="global", status="confirmed")
        await self.chat("把银杉负责人从陆予改为顾宁。")
        self.assertEqual(self.store.recall_facts(self.sid), ["银杉预算 80；负责人 顾宁；地点 西楼"])
        self.assertEqual(self.facts()[0]["content"], original)

    async def test_two_distinct_rows_for_same_key_require_clarification(self):
        self.store.add_fact("银杉预算85", scope="global", status="confirmed")
        before = self.facts()
        answer, _ = await self.chat("银杉预算改为95。", candidate="银杉预算95")
        self.assertEqual(self.facts(), before)
        self.assertNotIn("已更正", answer)
        self.assertIn("明确", answer)

    async def test_unknown_entity_cannot_fall_back_to_similar_entity(self):
        before = self.facts()
        answer, _ = await self.chat("把银松预算改成95。", candidate="银杉预算95")
        self.assertEqual(self.facts(), before)
        self.assertNotIn("已更正", answer)

    async def test_unrecognised_rephrase_cannot_publish_unsaved_success(self):
        answer, _ = await self.chat("请将银杉预算更新为95。", candidate="银杉预算95")
        saved = "银杉预算95" in self.store.recall_facts(self.sid)
        self.assertTrue(saved or "已更正" not in answer, (answer, self.store.recall_facts(self.sid)))
        self.assertTrue(saved or "保存到长期记忆" not in answer)

    async def test_question_form_correction_cannot_publish_unsaved_success(self):
        answer, _ = await self.chat("把银杉预算改成95，可以吗？", candidate="银杉预算95")
        saved = "银杉预算95" in self.store.recall_facts(self.sid)
        self.assertTrue(saved or "已更正" not in answer, (answer, self.store.recall_facts(self.sid)))

    async def test_rephrase_without_candidate_cannot_publish_unsaved_success(self):
        answer, _ = await self.chat("请将银杉预算更新为95。")
        saved = "银杉预算95" in self.store.recall_facts(self.sid)
        self.assertTrue(saved or "已更正" not in answer, (answer, self.store.recall_facts(self.sid)))

    async def test_quoted_entity_or_question_without_candidate_has_truthful_receipt(self):
        for text in ("请把“银杉”预算更正为95。", "把银杉预算改成95，可以吗？"):
            with self.subTest(text=text):
                answer, _ = await self.chat(text)
                saved = "银杉预算95" in self.store.recall_facts(self.sid)
                self.assertTrue(saved or "已更正" not in answer, (answer, self.store.recall_facts(self.sid)))

    async def test_reference_and_normal_chat_never_promote_candidate(self):
        before = self.facts()
        await self.chat("引用资料中的例句是：银杉预算改为95。", candidate="银杉预算95",
                        reply="这是一句用于说明预算变更的例句。")
        self.assertEqual(self.facts(), before)
        await self.chat("今天去散步了。", reply="散步感觉怎么样？")
        self.assertEqual(self.facts(), before)

    async def test_uncertain_statement_is_not_an_explicit_correction(self):
        before = self.facts()
        answer, _ = await self.chat("银杉预算应是95吧", reply="还需要核对具体预算。")
        self.assertEqual(self.facts(), before, answer)

    async def test_question_without_punctuation_is_not_a_new_scalar_value(self):
        before = self.facts()
        answer, _ = await self.chat("银杉预算实际是95吗", reply="还需要核对具体预算。")
        self.assertEqual(self.facts(), before, answer)

    async def test_local_compound_override_keeps_other_session_global(self):
        self.store.connection.execute("DELETE FROM facts")
        self.store.add_fact("银杉预算80；负责人陆予；地点西楼", scope="global", status="confirmed")
        before = self.facts()
        await self.chat("仅在当前聊天生效，把银杉预算改成95。")
        self.assertEqual(self.facts()[0], before[0])
        self.assertEqual(self.store.recall_facts(self.sid), ["银杉预算95；负责人陆予；地点西楼"])
        other = self.store.create_session()["id"]
        self.assertEqual(self.store.recall_facts(other), ["银杉预算80；负责人陆予；地点西楼"])

    async def test_queued_default_session_correction_matches_delivered_session(self):
        await core.chat_lock.acquire()
        task = asyncio.create_task(core.handle_chat("仅本次会话，把银杉预算改为95。", "queued-default-review"))
        try:
            await asyncio.sleep(0)
            self.store.create_session()
        finally:
            core.chat_lock.release()
        await task
        deliveries = [call.args[1] for call in core.hub.send_roles.call_args_list
                      if call.args[1].get("type") == "chat.response"]
        delivered = deliveries[-1]
        if "已更正" in delivered["text"]:
            self.assertIn("银杉预算95", self.store.recall_facts(delivered["conversationId"]))
        self.assertIn("银杉预算80", self.store.recall_facts(self.store.create_session()["id"]))

    async def test_pending_correction_does_not_promote_or_leak_sessions(self):
        self.store.add_fact("秋港日期周五", scope="session", session_id=self.sid, status="pending")
        answer, _ = await self.chat("秋港日期更正为周六。")
        self.assertIn("秋港日期周六（待确认）", self.store.recall_facts(self.sid))
        self.assertNotIn("秋港日期周六", " ".join(self.store.recall_facts(self.store.create_session()["id"])))
        self.assertIn("待确认", answer)

    async def test_sensitive_pending_cannot_be_selected_or_exposed(self):
        self.store.add_fact("秋港代号1234567890123456", scope="session", session_id=self.sid, status="pending")
        before = self.facts()
        answer, _ = await self.chat("把秋港代号改为ABC。", candidate="秋港代号ABC")
        self.assertEqual(self.facts(), before)
        self.assertNotIn("已更正", answer)
        self.assertNotIn("1234567890123456", " ".join(self.store.recall_facts(self.sid)))

    async def test_history_preserves_original_pending_qualification(self):
        self.store.add_fact("秋港日期周五", scope="session", session_id=self.sid, status="pending")
        await self.chat("秋港日期更正为周六。")
        core._ACTIVE_CHAT_SESSION_ID[0] = self.sid
        result = await core.run_tool("recall_memory", {"query": "秋港日期", "include_history": True})
        old = next(row for row in result["history"] if "秋港日期周五" in row["content"])
        qualified = ("待确认" in old["content"] or old.get("original_status") == "pending"
                     or old.get("prior_status") == "pending")
        self.assertTrue(qualified, old)

    async def test_failed_insert_rolls_back_old_record_and_receipt(self):
        before = self.facts()
        self.store.connection.execute("CREATE TRIGGER reject_review BEFORE INSERT ON facts BEGIN SELECT RAISE(ABORT, 'synthetic reject'); END")
        answer, _ = await self.chat("银杉预算改到95。")
        self.assertEqual(self.facts(), before)
        self.assertIn("失败", answer)
        self.assertNotIn("已更正", answer)

    async def test_local_write_readback_verifies_owning_session(self):
        other = self.store.create_session()["id"]
        before = self.facts()
        # The synthetic trigger injects a post-write scope corruption. Its
        # target is a fixture-created session, never user-supplied SQL.
        self.store.connection.execute(
            "CREATE TRIGGER move_review AFTER INSERT ON facts "
            "WHEN NEW.source_request_id='review-wrong-session' BEGIN "
            f"UPDATE facts SET session_id={int(other)} WHERE fact_id=NEW.fact_id; END")
        answer, _ = await self.chat("仅本次会话，把银杉预算改成95。", request_id="review-wrong-session")
        self.assertEqual(self.facts(), before, answer)
        self.assertNotIn("已更正", answer)
        self.assertIn("银杉预算80", self.store.recall_facts(self.sid))

    async def test_repeat_and_late_old_version_preserve_latest_record(self):
        await self.chat("银杉预算从80改为95。", request_id="review-repeat")
        await self.chat("银杉预算从95改为105。")
        before = self.facts()
        replay, _ = await self.chat("银杉预算从80改为95。", request_id="review-repeat")
        self.assertEqual(self.facts(), before)
        self.assertIn("历史回执", replay)
        answer, _ = await self.chat("银杉预算从80改为85。")
        self.assertEqual(self.facts(), before)
        self.assertIn("版本", answer)

    async def test_forged_storage_plan_cannot_override_different_fact(self):
        plan = self.store.prepare_correction("银杉预算改为95。", self.sid)
        before = self.facts()
        plan["old_fact_id"] = 2
        result = self.store.correct_fact(plan, "forged-review")
        self.assertIn("error", result)
        self.assertEqual(self.facts(), before)

    async def test_tool_and_automatic_prompt_use_current_value_in_new_session(self):
        await self.chat("银杉预算改为95。")
        other = self.store.create_session()["id"]
        core._ACTIVE_CHAT_SESSION_ID[0] = other
        result = await core.run_tool("recall_memory", {"query": "银杉预算", "include_history": True})
        self.assertIn("银杉预算95", result["memories"])
        self.assertNotIn("银杉预算80", result["memories"])
        self.assertTrue(any(row["content"] == "银杉预算80" for row in result["history"]))
        _, provider = await self.chat("银杉预算现在是多少？", sid=other, reply="银杉预算为95。")
        payload = str(provider.complete.call_args)
        self.assertIn("银杉预算95", payload)
        self.assertNotIn("银杉预算80", payload)

    def test_expansion_requires_completed_restart_sequences(self):
        runner, source_root = runner_module()
        reports = []
        for provider, model in (("deepseek", "Deepseek-v4-flash"), ("glm", "GLM-5.2")):
            report = self.root / (provider + "-first-phase.json")
            report.write_text(json.dumps({
                "passed": True, "offline": False, "variant": 1, "provider": provider, "model": model,
                "source_sha256": runner.source_hashes(source_root / "services/agent-core"),
                "runner_sha256": runner.protocol_runner_hashes("memory"),
                "protocol": "memory-correction-restart-v1", "input_normalized_sha256": "same-input",
                "budget": {}, "initial_state_sha256": "same-state", "tool_schema_sha256": "same-tools",
                "phase": "before_restart", "sequence_complete": False,
            }), encoding="utf-8")
            reports.append(report)
        argv = ["file_models.py", "--provider", "deepseek", "--scenario", "memory", "--variant", "2",
                "--source-root", str(source_root), "--data-dir", str(self.root / "expansion"),
                "--ledger", str(self.root / "unused-ledger.json"),
                "--private-config", str(self.root / "never-read.env")]
        for report in reports:
            argv.extend(["--initial-report", str(report)])
        with patch.object(sys, "argv", argv), patch.object(runner, "read_connection") as read_connection, \
                patch.object(sys, "path", [str(Path(runner.__file__).parent), *sys.path]):
            read_connection.side_effect = AssertionError("Incomplete restart sequence passed the expansion gate")
            with self.assertRaises(SystemExit):
                runner.main()
            read_connection.assert_not_called()

    def test_runner_answer_oracle_rejects_swapped_entities_and_wrong_attributes(self):
        case, _ = runner_module("memory_model_case")
        correct = "晨星项目｜预算｜175\n暮云项目｜预算｜180\n用户｜最喜欢的颜色｜蓝色"
        self.assertTrue(case.answer_matches(correct, 1))
        for wrong in (
            "暮云项目｜预算｜175\n晨星项目｜预算｜180\n用户｜最喜欢的颜色｜蓝色",
            "晨星项目｜负责人｜175\n暮云项目｜预算｜180\n用户｜最喜欢的颜色｜蓝色",
            correct.replace("175", "不是175"),
            correct + "\n晨星项目｜预算｜120",
        ):
            with self.subTest(wrong=wrong):
                self.assertFalse(case.answer_matches(wrong, 1))

    def test_runner_history_oracle_rejects_swapped_versions_and_wrong_objects(self):
        case, _ = runner_module("memory_model_case")
        correct = "当前｜晨星项目｜预算｜175\n历史｜晨星项目｜预算｜120"
        self.assertTrue(case.history_matches(correct, 1))
        for wrong in (
            "当前｜晨星项目｜预算｜120\n历史｜晨星项目｜预算｜175",
            "当前｜暮云项目｜预算｜175\n历史｜晨星项目｜预算｜120",
            "当前｜晨星项目｜负责人｜175\n历史｜晨星项目｜预算｜120",
            correct + "\n当前｜晨星项目｜预算｜120",
        ):
            with self.subTest(wrong=wrong):
                self.assertFalse(case.history_matches(wrong, 1))

    def test_runner_accepts_exact_host_recall_receipts_without_relaxing_facts(self):
        case, _ = runner_module("memory_model_case")

        def receipt_answer(memories, variant=1, **changes):
            payload = {"ok": True, "memories": memories, "available_count": 3,
                       "recalled_count": len(memories),
                       "note": "未召回不等于未保存；这里只包含本会话可见记忆",
                       "result_ref": f"memory-{variant}-before_restart-new-session:read:1"}
            payload.update(changes)
            return "我核对了实际执行记录：\nrecall_memory：执行成功；" + json.dumps(payload, ensure_ascii=False)

        for variant in (1, 2, 3):
            sample = case.SAMPLES[variant]
            current = [sample["current"], *sample["facts"][1:]]
            with self.subTest(variant=variant):
                self.assertTrue(case.answer_matches(receipt_answer(current, variant), variant))

        correct = ["晨星项目预算175", "暮云项目预算180", "用户最喜欢的颜色是蓝色"]
        valid = receipt_answer(correct)
        wrong_answers = [
            receipt_answer(["暮云项目预算175", "晨星项目预算180", correct[2]]),
            receipt_answer(["晨星项目负责人175", *correct[1:]]),
            receipt_answer(["晨星项目预算不是175", *correct[1:]]),
            receipt_answer(["晨星项目预算120", *correct[1:]]),
            receipt_answer([*correct, "晨星项目预算120"]),
            receipt_answer(correct[:2]),
            receipt_answer(correct, ok=False),
            receipt_answer(correct, recalled_count=1),
            receipt_answer(correct, note="以上不是当前事实"),
            receipt_answer(correct, result_ref="unbound-result"),
            receipt_answer(correct, history=[]),
            valid.replace('"ok": true', '"ok": false, "ok": true'),
            valid.replace('"memories":', '"missing_memories":'),
            "这些结果是假的。\n" + valid,
            valid + "\n晨星的预算并非175。",
        ]
        for wrong in wrong_answers:
            with self.subTest(answer=wrong):
                self.assertFalse(case.answer_matches(wrong, 1))

    def test_runner_unions_only_same_request_host_receipts(self):
        case, _ = runner_module("memory_model_case")
        lines = ["我核对了实际执行记录："]
        for index, fact in enumerate(("晨星项目预算175", "暮云项目预算180", "用户最喜欢的颜色是蓝色"), 1):
            payload = {"ok": True, "memories": [fact], "available_count": 3, "recalled_count": 1,
                       "note": "未召回不等于未保存；这里只包含本会话可见记忆",
                       "result_ref": f"memory-1-before_restart-same-session:read:{index}"}
            lines.append("recall_memory：执行成功；" + json.dumps(payload, ensure_ascii=False))
        answer = "\n".join(lines)
        self.assertTrue(case.answer_matches(answer, 1))
        self.assertFalse(case.answer_matches(answer.replace("same-session:read:3", "new-session:read:3"), 1))
        self.assertFalse(case.answer_matches(answer + "\n" + lines[-1], 1))

    def test_runner_receipt_history_never_becomes_current(self):
        case, _ = runner_module("memory_model_case")
        payload = {"ok": True, "memories": ["晨星项目预算175", "暮云项目预算180", "用户最喜欢的颜色是蓝色"],
                   "available_count": 3, "recalled_count": 3,
                   "note": "未召回不等于未保存；这里只包含本会话可见记忆；history是已被替代的历史版本，不能作为现行事实",
                   "result_ref": "memory-1-before_restart-new-session:read:1",
                   "history": [{"fact_id": 1, "content": "晨星项目预算120", "status": "superseded",
                                "scope": "global", "original_status": "confirmed", "note": "已被替代的历史版本"}]}

        def render(value):
            return "我核对了实际执行记录：\nrecall_memory：执行成功；" + json.dumps(value, ensure_ascii=False)

        self.assertTrue(case.answer_matches(render(payload), 1))
        self.assertTrue(case.history_matches(render(payload).replace("new-session:read", "history:read"), 1))
        for field, value in (("content", "暮云项目预算120"), ("content", "晨星项目预算175"),
                             ("status", "confirmed"), ("scope", "session"), ("original_status", "pending")):
            bad = json.loads(json.dumps(payload))
            bad["history"][0][field] = value
            with self.subTest(field=field, value=value):
                self.assertFalse(case.answer_matches(render(bad), 1))
        payload["memories"][0] = "晨星项目预算120"
        self.assertFalse(case.answer_matches(render(payload), 1))

    def presentation_fixture(self):
        case, _ = runner_module("memory_model_case")
        runner, source = runner_module()
        hashes = runner.source_hashes(source / "services/agent-core")
        runners = runner.protocol_runner_hashes("memory")
        checks = dict.fromkeys(("new_session_answer", "other_memory_answers", "new_session_active_records", "actual_recall_tool",
                                "other_rows_unchanged", "one_correction_only", "source_and_scope_recorded", "automatic_injection",
                                "core_stopped", "source_unchanged", "truthful_correction_receipt", "exact_active_records",
                                "same_session_answer", "history_distinct"), True)
        checks["same_session_answer"] = checks["new_session_answer"] = False
        answer = "晨星项目｜预算｜175\n暮云项目｜预算｜180\n用户｜最喜欢的颜色｜蓝色"
        report = {"protocol": "memory-correction-restart-v1", "phase": "before_restart", "variant": 1,
                  "source_sha256": hashes, "runner_sha256": case._REVIEWED_RUNNERS[1], "checks": checks,
                  "core_pid": 123456, "passed": False, "sequence_complete": False,
                  "turns": [{"request_id": "memory-1-before_restart-" + suffix, "answer": text}
                            for suffix, text in (("same-session", answer), ("new-session", answer),
                                                 ("history", "当前｜晨星项目｜预算｜175\n历史｜晨星项目｜预算｜120"))]}
        path = self.root / "presentation-report.json"
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        return case, path, report, hashes, runners

    def test_presentation_sidecar_preserves_raw_failure_and_stage(self):
        case, path, report, hashes, runners = self.presentation_fixture()
        original = path.read_bytes()
        with patch.object(case, "process_alive", return_value=False):
            sidecar = case.write_presentation_review(path, hashes, runners)
            effective = case.load_memory_report(path, hashes, runners)
            self.assertTrue(effective["passed"])
            self.assertFalse(effective["original_passed"])
            self.assertEqual(effective["runner_sha256"], report["runner_sha256"])
            self.assertEqual(effective["phase"], "before_restart")
            self.assertFalse(effective["sequence_complete"])
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(case.memory_report_compatible(effective, runners))
            with self.assertRaises(FileExistsError):
                case.write_presentation_review(path, hashes, runners)
            with self.assertRaises(SystemExit):
                case.validate_initial_sequences([effective, effective])
            saved = sidecar.read_text(encoding="utf-8")
            sidecar.write_text(saved.replace('"effective_passed": true', '"effective_passed": false'), encoding="utf-8")
            with self.assertRaises(ValueError):
                case.load_memory_report(path, hashes, runners)
            sidecar.write_text(saved, encoding="utf-8")
            path.write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                case.load_memory_report(path, hashes, runners)
    def test_presentation_review_rejects_business_failure_source_drift_and_unknown_runner(self):
        case, path, report, hashes, runners = self.presentation_fixture()
        bad_reports = []
        for change in ("business", "source", "runner", "answer", "missing"):
            bad = json.loads(json.dumps(report))
            if change == "business":
                bad["checks"]["one_correction_only"] = False
            elif change == "source":
                bad["source_sha256"] = {"main.py": "different"}
            elif change == "runner":
                bad["runner_sha256"]["file_models.py"] = "unreviewed"
            elif change == "answer":
                bad["turns"][1]["answer"] = bad["turns"][1]["answer"].replace("175", "120")
            else:
                del bad["checks"]["automatic_injection"]
            bad_reports.append((change, bad))
        with patch.object(case, "process_alive", return_value=False):
            for change, bad in bad_reports:
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.subTest(change=change), self.assertRaises(ValueError):
                    case.write_presentation_review(path, hashes, runners)
        path.write_text(json.dumps(report), encoding="utf-8")
        with patch.object(case, "process_alive", return_value=True), self.assertRaises(ValueError):
            case.write_presentation_review(path, hashes, runners)

    def test_runner_accepts_only_exact_fixture_time_failure_pair_with_correct_memory(self):
        case, _ = runner_module("memory_model_case")
        note = "工具回执未能完成（RuntimeError）；结果未知，未自动重试"
        failure = {"ok": False, "outcome": "unknown", "error": note,
                   "result_ref": "memory-1-after_restart-new-session:read:2"}
        memories = {"ok": True, "memories": ["晨星项目预算175", "暮云项目预算180", "用户最喜欢的颜色是蓝色"],
                    "available_count": 3, "recalled_count": 3,
                    "note": "未召回不等于未保存；这里只包含本会话可见记忆",
                    "result_ref": "memory-1-after_restart-new-session:read:1"}
        answer = ("我核对了实际执行记录：\nget_time：未完成；" + note + "\nrecall_memory：执行成功；"
                  + json.dumps(memories, ensure_ascii=False) + "\nget_time：结果未知，未自动重试；"
                  + json.dumps(failure, ensure_ascii=False))
        self.assertTrue(case.answer_matches(answer, 1))
        for bad in (answer.replace("get_time：", "other_tool："), answer.replace('"ok": false', '"ok": true'),
                    answer.replace("175", "120"), answer.replace("RuntimeError", "预算不是175"),
                    answer.replace("new-session:read:2", "same-session:read:2"),
                    answer + "\n晨星项目预算不是175", "\n".join(answer.splitlines()[:2] + answer.splitlines()[3:])):
            with self.subTest(answer=bad):
                self.assertFalse(case.answer_matches(bad, 1))

    def test_regraded_restart_preserves_raw_sequence_flag_and_separates_effective_completion(self):
        case, path, report, hashes, runners = self.presentation_fixture()
        report["phase"] = "after_restart"
        for key in ("truthful_correction_receipt", "exact_active_records", "same_session_answer", "history_distinct"):
            del report["checks"][key]
        report["checks"].update(previous_phase_passed=True, different_process=True, previous_process_terminated=True)
        report["turns"] = [report["turns"][1]]
        report["turns"][0]["request_id"] = "memory-1-after_restart-new-session"
        path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        with patch.object(case, "process_alive", return_value=False):
            sidecar = case.write_presentation_review(path, hashes, runners)
            self.assertIn(runners["memory_model_case.py"], sidecar.name)
            effective = case.load_memory_report(path, hashes, runners)
            self.assertFalse(effective["sequence_complete"])
            self.assertTrue(effective["effective_sequence_complete"])
            self.assertEqual(effective["phase"], "after_restart")
            case.validate_initial_sequences([effective, effective])
            report["checks"]["different_process"] = False
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(ValueError):
                case.load_memory_report(path, hashes, runners)
