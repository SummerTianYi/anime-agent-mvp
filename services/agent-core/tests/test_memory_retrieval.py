"""zcode (phase B 记忆接入): retrieval quality + facts storage tests."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.memory_retrieval import retrieve_relevant, score_retrieval  # noqa: E402
from agent_core.storage import MemoryStore  # noqa: E402

GOLDEN = [
    {"query": "用户喜欢什么颜色", "stored": ["用户最喜欢的颜色是蓝色", "用户在杭州工作"], "relevant": ["用户最喜欢的颜色是蓝色"]},
    {"query": "用户的职业", "stored": ["用户是后端工程师", "用户最近在健身"], "relevant": ["用户是后端工程师"]},
    {"query": "用户养的宠物", "stored": ["用户的生日是7月12日", "用户养了一只猫"], "relevant": ["用户养了一只猫"]},
    {"query": "怎么称呼用户", "stored": ["用户希望被称呼为老板"], "relevant": ["用户希望被称呼为老板"]},
]


class RetrievalQualityTests(unittest.TestCase):
    def test_golden_precision_recall_meet_threshold(self):
        result = score_retrieval(GOLDEN)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["precision"], 0.8)
        self.assertGreaterEqual(result["recall"], 0.8)

    def test_zero_lexical_overlap_bridged_by_expansion(self):
        result = retrieve_relevant("用户的职业", ["用户是后端工程师", "用户最近在健身"])
        self.assertEqual(result, ["用户是后端工程师"])

    def test_empty_stored_returns_empty(self):
        self.assertEqual(retrieve_relevant("任何问题", []), [])


class FactsStorageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = MemoryStore(data_dir=Path(tmp.name) / "data")
        self.addCleanup(self.store.close)

    def test_pending_facts_are_not_recallable(self):
        self.store.add_fact("用户的银行卡尾号是1234", status="pending")
        self.assertEqual(self.store.recall_facts(1), [])
        self.assertEqual(len(self.store.pending_facts()), 1)

    def test_confirmed_global_fact_recallable_across_sessions(self):
        self.store.add_fact("用户最喜欢的颜色是蓝色", status="confirmed", scope="global")
        self.assertIn("用户最喜欢的颜色是蓝色", self.store.recall_facts(1))
        self.assertIn("用户最喜欢的颜色是蓝色", self.store.recall_facts(99))

    def test_session_scoped_fact_stays_isolated(self):
        self.store.add_fact("会话内事实", session_id=1, scope="session", status="confirmed")
        self.assertIn("会话内事实", self.store.recall_facts(1))
        self.assertNotIn("会话内事实", self.store.recall_facts(2))

    def test_set_fact_status_promotes_pending(self):
        fact_id = self.store.add_fact("用户讨厌香菜", status="pending")
        self.assertTrue(self.store.set_fact_status(fact_id, "confirmed"))
        self.assertIn("用户讨厌香菜", self.store.recall_facts(1))


if __name__ == "__main__":
    unittest.main()
