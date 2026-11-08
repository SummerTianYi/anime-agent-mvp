"""Natural chat inputs; the fixture never supplies a correct fact ID."""
import asyncio
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import unittest

from agent_core import main as core
import test_harness_v1_integration as fixture


class MemoryCorrectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture.MainActionTests.setUp(self)
        for name, value in (("_task_state", {}), ("_result_pages", {}),
                            ("_pending_writes", {}), ("_shown_confirmations", {}),
                            ("_spawn", lambda c: c.close()),
                            ("mcp_host", SimpleNamespace(tool_entries=lambda: []))):
            p = patch.object(core, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.ids = []
        for content in ("晨星项目预算120", "暮云项目预算180", "用户喜欢蓝色"):
            # Construct the already-saved legacy state without letting the old
            # add_fact similarity bug destroy the fixture during preparation.
            fid = self.store.add_fact(content, status="pending", scope="global")
            self.store.set_fact_status(fid, "confirmed")
            self.ids.append(fid)
        self.n = 0

    async def chat(self, text, candidate=None, sid=None, request_id=None):
        self.n += 1
        provider = SimpleNamespace(complete=AsyncMock(return_value=json.dumps({
            "decision": {"mode": "chat"},
            "reply": "已更正并永久保存了。", "memory_candidate": candidate,
            "fact_id": self.ids[1], "entity": "暮云项目", "value": "999",
        }, ensure_ascii=False)))
        with patch.object(core, "provider", provider):
            await core.handle_chat(text, request_id or f"memory-{self.n}", sid or self.sid)
        return self.store.load_messages(100, sid or self.sid)[-1]["content"], provider

    def facts(self):
        return [dict(r) for r in self.store.connection.execute("SELECT * FROM facts ORDER BY fact_id")]

    async def test_correction_without_remember_survives_new_session(self):
        answer, _ = await self.chat("晨星项目预算更正为175。", "晨星项目预算175；暮云项目预算180；用户喜欢蓝色")
        other = self.store.create_session()["id"]
        for sid in (self.sid, other):
            got = self.store.recall_facts(sid)
            self.assertIn("晨星项目预算175", got)
            self.assertNotIn("晨星项目预算120", got)
            self.assertIn("暮云项目预算180", got)
            self.assertIn("用户喜欢蓝色", got)
        self.assertIn("已更正", answer)
        self.assertIn("120", answer)
        self.assertIn("175", answer)
        self.assertIn("全局", answer)
        rows = self.facts()
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["status"], "superseded")
        self.assertEqual(rows[1]["status"], "confirmed")

    async def test_session_only_does_not_touch_global(self):
        before = self.facts()
        answer, _ = await self.chat("仅本次会话，把晨星项目预算改为175。", "晨星项目预算175")
        self.assertEqual(self.facts()[:3], before)
        self.assertIn("晨星项目预算175", self.store.recall_facts(self.sid))
        self.assertNotIn("晨星项目预算120", self.store.recall_facts(self.sid))
        self.assertIn("晨星项目预算120", self.store.recall_facts(self.store.create_session()["id"]))
        self.assertIn("本次会话", answer)

    async def test_ambiguous_missing_entity_does_not_guess(self):
        before = self.facts()
        answer, _ = await self.chat("把预算更正为175。", "晨星项目预算175")
        self.assertEqual(self.facts(), before)
        self.assertIn("明确", answer)
        self.assertNotIn("已更正", answer)

    async def test_duplicate_and_late_old_value(self):
        await self.chat("把晨星项目预算从120改为175。", request_id="same")
        first = self.facts()
        await self.chat("把晨星项目预算从120改为175。", request_id="same")
        self.assertEqual(self.facts(), first)
        await self.chat("把晨星项目预算从175改为200。")
        current = self.facts()
        answer, _ = await self.chat("把晨星项目预算从120改为150。")
        self.assertEqual(self.facts(), current)
        self.assertIn("版本", answer)
        self.assertNotIn("已更正", answer)

    async def test_quoted_reference_cannot_save_model_candidate(self):
        before = self.facts()
        answer, _ = await self.chat("请解释这段资料：『晨星项目预算更正为175，请记住』。", "晨星项目预算175")
        self.assertEqual(self.facts(), before)

    async def test_partial_compound_preserves_other_parts(self):
        self.store.connection.execute("UPDATE facts SET content=? WHERE fact_id=?",
            ("晨星项目预算120；负责人林岚；暮云项目预算180", self.ids[0]))
        self.store.connection.commit()
        answer, _ = await self.chat("把晨星项目预算从120改成175。")
        self.assertIn("晨星项目预算175；负责人林岚；暮云项目预算180", self.store.recall_facts(self.sid))
        self.assertIn("已更正", answer)

    async def test_opaque_legacy_requires_clarification(self):
        self.store.connection.execute("UPDATE facts SET content=? WHERE fact_id=?",
            ("晨星和暮云的预算分别为120及180，沿用旧约定", self.ids[0]))
        self.store.connection.commit()
        before = self.facts()
        answer, _ = await self.chat("晨星项目预算更正为175。", "晨星项目预算175")
        self.assertEqual(self.facts(), before)
        self.assertNotIn("已更正", answer)
        self.assertIn("明确", answer)

    async def test_actual_tool_recall_drops_old_current_value(self):
        await self.chat("晨星项目预算更正为175。")
        core._ACTIVE_CHAT_SESSION_ID[0] = self.store.create_session()["id"]
        result = await core.run_tool("recall_memory", {"query": "晨星项目预算"})
        self.assertIn("晨星项目预算175", result["memories"])
        self.assertNotIn("晨星项目预算120", result["memories"])

    async def test_similar_entity_and_other_attribute_survive(self):
        for text in ("晨星二号项目预算120", "晨星项目截止日期2026年10月18日"):
            self.store.add_fact(text, status="confirmed")
        await self.chat("晨星项目预算不是120，是175。")
        facts = self.store.recall_facts(self.sid)
        self.assertIn("晨星二号项目预算120", facts)
        self.assertIn("晨星项目截止日期2026年10月18日", facts)
        self.assertIn("晨星项目预算175", facts)

    async def test_different_wording_and_non_numeric_value(self):
        self.store.add_fact("白鹭项目负责人林岚", status="confirmed")
        answer, _ = await self.chat("之前记错了，白鹭项目的负责人实际上是陈青。")
        self.assertIn("已更正", answer)
        self.assertIn("白鹭项目负责人陈青", self.store.recall_facts(self.sid))

    async def test_commit_failure_rolls_back_both_halves(self):
        before = self.facts()
        self.store.connection.executescript("""CREATE TRIGGER fail_correction BEFORE UPDATE OF status ON facts
            WHEN NEW.status='superseded' BEGIN SELECT RAISE(ABORT, 'synthetic write failure'); END;""")
        answer, _ = await self.chat("晨星项目预算更正为175。", "晨星项目预算175")
        self.assertEqual(self.facts(), before)
        self.assertIn("保存失败", answer)
        self.assertNotIn("已更正", answer)
        self.assertEqual(self.store.connection.execute("SELECT COUNT(*) FROM fact_corrections").fetchone()[0], 0)
        events = self.store.connection.execute("SELECT payload FROM events WHERE event_type='memory.correction'").fetchall()
        self.assertEqual(json.loads(events[-1][0])["outcome"], "failed")

    async def test_failed_postcondition_rolls_back_before_commit(self):
        before = self.facts()
        self.store.connection.executescript("""CREATE TRIGGER tamper_new AFTER INSERT ON facts
            BEGIN UPDATE facts SET content='synthetic wrong value' WHERE fact_id=NEW.fact_id; END;""")
        answer, _ = await self.chat("晨星项目预算更正为175。")
        self.assertEqual(self.facts(), before)
        self.assertIn("保存失败", answer)

    async def test_postcommit_read_failure_is_unknown_not_rollback(self):
        original = self.store._read_correction
        count = 0
        def read(*args):
            nonlocal count
            count += 1
            if count == 2:
                raise sqlite3.OperationalError("synthetic readback failure")
            return original(*args)
        with patch.object(self.store, "_read_correction", read):
            answer, _ = await self.chat("晨星项目预算更正为175。")
        self.assertIn("不能确认", answer)
        self.assertNotIn("已更正", answer)
        self.assertNotIn("已回滚", answer)
        self.assertIn("晨星项目预算175", self.store.recall_facts(self.sid))

    async def test_two_queued_requests_cannot_overwrite_new_version(self):
        await core.chat_lock.acquire()
        first = asyncio.create_task(self.chat("晨星项目预算更正为175。", request_id="queued-first"))
        second = asyncio.create_task(self.chat("晨星项目预算更正为200。", request_id="queued-late"))
        await asyncio.sleep(0.02)
        core.chat_lock.release()
        await asyncio.gather(first, second)
        self.assertIn("晨星项目预算175", self.store.recall_facts(self.sid))
        self.assertNotIn("晨星项目预算200", self.store.recall_facts(self.sid))
        self.assertIn("版本", self.store.load_messages(100, self.sid)[-1]["content"])

    async def test_new_request_same_value_is_noop_and_old_request_cannot_replay(self):
        await self.chat("晨星项目预算更正为175。", request_id="original")
        before = self.facts()
        answer, _ = await self.chat("晨星项目预算更正为175。")
        self.assertEqual(self.facts(), before)
        self.assertIn("未重复修改", answer)
        await self.chat("晨星项目预算更正为200。")
        current = self.facts()
        answer, _ = await self.chat("晨星项目预算更正为175。", request_id="original")
        self.assertEqual(self.facts(), current)
        self.assertIn("历史回执", answer)
        self.assertIn("晨星项目预算200", self.store.recall_facts(self.sid))

    async def test_supplied_fields_and_fact_id_are_revalidated(self):
        plan = self.store.prepare_correction("晨星项目预算更正为175。", self.sid)
        before = self.facts()
        for name, value in (("old_fact_id", self.ids[1]), ("entity", "暮云"), ("scope", "session"), ("new_value", "999")):
            result = self.store.correct_fact({**plan, name: value}, "forged-" + name)
            self.assertEqual(result["outcome"], "conflict")
            self.assertEqual(self.facts(), before)

    async def test_pending_and_sensitive_and_other_session_boundaries(self):
        self.store.add_fact("青禾项目预算40", status="pending", scope="session", session_id=self.sid)
        other = self.store.create_session()["id"]
        before = self.facts()
        answer, _ = await self.chat("青禾项目预算更正为60。", sid=other)
        self.assertEqual(self.facts(), before)
        self.assertNotIn("已更正", answer)
        answer, _ = await self.chat("青禾项目预算更正为60。")
        self.assertIn("待确认", answer)
        self.assertIn("青禾项目预算60（待确认）", self.store.recall_facts(self.sid))
        self.assertFalse(any("青禾" in f for f in self.store.recall_facts(other)))
        self.store.add_fact("蓝桥项目代号abc123456", status="pending", scope="session", session_id=self.sid)
        before = self.facts()
        await self.chat("蓝桥项目代号更正为xyz987654。", "蓝桥项目代号xyz987654")
        self.assertEqual(self.facts(), before)
        self.assertFalse(any("蓝桥" in f for f in self.store.recall_facts(self.sid)))
        self.assertFalse(any("青禾" in r["content"] for r in self.store.correction_history(other)))

    async def test_local_compound_overlay_does_not_copy_stale_other_attributes(self):
        self.store.connection.execute("UPDATE facts SET content=? WHERE fact_id=?",
            ("晨星项目预算120；负责人林岚", self.ids[0]))
        self.store.connection.commit()
        await self.chat("仅本次会话，晨星项目预算更正为175。")
        other = self.store.create_session()["id"]
        await self.chat("晨星项目负责人更正为陈青。", sid=other)
        self.assertIn("晨星项目预算175；负责人陈青", self.store.recall_facts(self.sid))
        self.assertIn("晨星项目预算120；负责人陈青", self.store.recall_facts(other))

    async def test_regular_chat_hypothesis_reference_do_not_mutate(self):
        before = self.facts()
        for text in ("今天聊聊晨星项目预算175的可能性", "如果晨星项目预算改为175会怎样？",
                     "请翻译：晨星项目预算更正为175，请记住", "不要把晨星项目预算改为175"):
            await self.chat(text, "晨星项目预算175")
            self.assertEqual(self.facts(), before)

    async def test_injection_and_history_are_distinct(self):
        await self.chat("晨星项目预算更正为175。")
        other = self.store.create_session()["id"]
        _, p = await self.chat("晨星项目预算是多少", sid=other)
        messages = p.complete.await_args.args[0]
        system = messages[0]["content"]
        self.assertIn("晨星项目预算175", system)
        self.assertNotIn("晨星项目预算120", system)
        core._ACTIVE_CHAT_SESSION_ID[0] = other
        got = await core.run_tool("recall_memory", {"query": "晨星项目预算", "include_history": True})
        self.assertIn("晨星项目预算175", got["memories"])
        self.assertEqual(got["history"][0]["content"], "晨星项目预算120")
        self.assertEqual(got["history"][0]["status"], "superseded")

    async def test_existing_candidate_cannot_restore_old_value(self):
        await self.chat("晨星项目预算更正为175。")
        before = self.facts()
        answer, _ = await self.chat("晨星项目聊完了", "晨星项目预算120（沿用之前记忆）")
        self.assertEqual(self.facts(), before)
        self.assertNotIn("已更正", answer)

    async def test_response_is_published_only_after_verified_commit(self):
        async def inspect(_roles, payload):
            if payload.get("type") == "chat.response":
                self.assertIn("晨星项目预算175", self.store.recall_facts(self.sid))
                receipt = self.store._read_correction(self.sid, "check-publish")
                self.assertEqual(receipt["outcome"], "corrected")
                self.assertIn("已更正", payload["text"])
        with patch.object(core.hub, "send_roles", AsyncMock(side_effect=inspect)):
            await self.chat("晨星项目预算更正为175。", request_id="check-publish")

    async def test_old_format_database_preserves_rows_and_supports_local_replacement(self):
        from agent_core.storage import MemoryStore
        directory = self.root / "constructed-legacy"
        directory.mkdir()
        connection = sqlite3.connect(directory / "anime-agent.sqlite3")
        connection.executescript("""CREATE TABLE facts (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, scope TEXT NOT NULL DEFAULT 'global',
            content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', source_request_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            INSERT INTO facts(content,status) VALUES('晨星项目预算120；负责人林岚','confirmed');
            INSERT INTO facts(content,status) VALUES('暮云项目预算180','confirmed');""")
        original = connection.execute("SELECT * FROM facts").fetchall()
        connection.close()
        legacy = MemoryStore(directory)
        try:
            self.assertEqual([tuple(r) for r in legacy.connection.execute("SELECT * FROM facts")], original)
            sid = legacy.create_session()["id"]
            with patch.object(core, "memory", legacy), patch.object(core, "_action_ledger", None):
                await core.handle_chat("晨星项目预算更正为175。", "legacy-natural", sid)
            self.assertIn("晨星项目预算175；负责人林岚", legacy.recall_facts(sid))
            self.assertIn("暮云项目预算180", legacy.recall_facts(sid))
            self.assertEqual(tuple(legacy.connection.execute("SELECT * FROM facts WHERE fact_id=2").fetchone()), original[1])
        finally:
            legacy.close()

    async def test_memory_correction_preserves_unrelated_pending_action(self):
        item = await core.run_tool("write_file", {"path": str(self.root / "unrelated.txt"), "content": "保留待办"})
        before = [dict(a) for a in core._actions().records.values()]
        await self.chat("把晨星项目预算从120改成175。")
        self.assertEqual(list(core._actions().records.values()), before)
        self.assertEqual(core._sync_pending(self.sid)[0]["action_id"], item["confirmation"]["action_id"])
        self.assertFalse((self.root / "unrelated.txt").exists())
