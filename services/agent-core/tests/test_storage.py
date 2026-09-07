from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from agent_core.storage import MemoryStore


class StorageTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data_dir = Path(tmp.name) / "data"

    def make_store(self) -> MemoryStore:
        store = MemoryStore(data_dir=self.data_dir)
        self.addCleanup(store.close)
        return store

    def store_messages(self, store, session_ids):
        for sid in session_ids:
            store.add_message("user", f"消息-{sid}", conversation_id=sid)


class FreshDatabaseTests(StorageTestCase):
    def test_first_run_creates_default_session(self) -> None:
        store = self.make_store()
        session_id = store.latest_session_id()
        self.assertIsNotNone(session_id)
        # GPT-style: default shell exists but stays hidden until first message.
        self.assertEqual(store.list_sessions(), [])

    def test_messages_go_to_default_session(self) -> None:
        store = self.make_store()
        store.add_message("user", "你好")
        store.add_message("assistant", "你好呀")
        messages = store.load_messages(limit=20)
        self.assertEqual([m["content"] for m in messages], ["你好", "你好呀"])

    def test_explicit_conversation_id_routes_message(self) -> None:
        store = self.make_store()
        first = store.latest_session_id()
        second = store.create_session()["id"]
        store.add_message("user", "旧会话消息", conversation_id=first)
        store.add_message("user", "新会话消息", conversation_id=second)
        old = store.load_messages(conversation_id=first)
        new = store.load_messages(conversation_id=second)
        self.assertEqual([m["content"] for m in old], ["旧会话消息"])
        self.assertEqual([m["content"] for m in new], ["新会话消息"])

    def test_list_sessions_ordered_by_recent_activity(self) -> None:
        store = self.make_store()
        first = store.create_session()["id"]
        store.create_session()
        time.sleep(0.03)
        store.add_message("user", "早", conversation_id=first)
        ids = [s["id"] for s in store.list_sessions()]
        self.assertEqual(ids[0], first)

    def test_first_user_message_titles_untitled_session(self) -> None:
        store = self.make_store()
        session_id = store.create_session()["id"]
        store.add_message("user", "今天天气怎么样呀", conversation_id=session_id)
        sessions = {s["id"]: s for s in store.list_sessions()}
        self.assertEqual(sessions[session_id]["title"], "今天天气怎么样呀")


class LegacyMigrationTests(StorageTestCase):
    def test_existing_messages_migrate_into_initial_session(self) -> None:
        self.data_dir.mkdir(parents=True)
        connection = sqlite3.connect(self.data_dir / "anime-agent.sqlite3")
        connection.executescript(
            """
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                request_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT INTO messages (role, content) VALUES ('user', '旧消息一');
            INSERT INTO messages (role, content) VALUES ('assistant', '旧消息二');
            """
        )
        connection.commit()
        connection.close()

        store = self.make_store()
        sessions = store.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "初始会话")
        messages = store.load_messages(limit=20)
        self.assertEqual([m["content"] for m in messages], ["旧消息一", "旧消息二"])

        store.add_message("user", "新消息")
        self.assertEqual(len(store.load_messages(limit=20)), 3)

    def test_load_history_returns_ui_shape(self) -> None:
        store = self.make_store()
        session_id = store.create_session()["id"]
        store.add_message("user", "第一条", conversation_id=session_id)
        store.add_message("assistant", "第二条", conversation_id=session_id)
        history = store.load_history(conversation_id=session_id)
        self.assertEqual(
            history,
            [
                {"role": "user", "text": "第一条", "createdAt": history[0]["createdAt"]},
                {"role": "assistant", "text": "第二条", "createdAt": history[1]["createdAt"]},
            ],
        )
        self.assertTrue(all(h["createdAt"] for h in history))

    def test_reopening_does_not_duplicate_sessions(self) -> None:
        store = self.make_store()
        store.add_message("user", "一条")
        reopened = self.make_store()
        self.assertEqual(reopened.latest_session_id(), store.latest_session_id())
        self.assertEqual(len(reopened.list_sessions()), 1)
        self.assertEqual(len(reopened.load_messages(limit=20)), 1)


class SessionDeletionTests(StorageTestCase):
    def test_delete_session_removes_messages_and_row(self) -> None:
        store = self.make_store()
        first = store.latest_session_id()
        second = store.create_session()["id"]
        store.add_message("user", "old", conversation_id=first)
        store.add_message("user", "new", conversation_id=second)
        self.assertTrue(store.delete_session(first))
        sessions = store.list_sessions()
        self.assertEqual([s["id"] for s in sessions], [second])
        self.assertEqual(store.load_messages(conversation_id=first), [])
        self.assertEqual([m["content"] for m in store.load_messages(conversation_id=second)], ["new"])

    def test_delete_unknown_session_returns_false(self) -> None:
        store = self.make_store()
        self.assertFalse(store.delete_session(999))

    def test_delete_last_session_creates_fresh_default(self) -> None:
        store = self.make_store()
        store.add_message("user", "only")
        only = store.latest_session_id()
        self.assertTrue(store.delete_session(only))
        fresh = store.latest_session_id()
        self.assertIsNotNone(fresh)
        self.assertNotEqual(fresh, only)
        # hidden until a message lands
        self.assertEqual(store.list_sessions(), [])
        store.add_message("user", "after")
        self.assertEqual(store.load_messages(conversation_id=fresh), [{"role": "user", "content": "after"}])


class SessionRenameTests(StorageTestCase):
    def test_rename_updates_title_and_bumps_order(self) -> None:
        store = self.make_store()
        session_id = store.create_session()["id"]
        other = store.create_session()["id"]
        self.store_messages(store, [session_id, other])
        time.sleep(0.03)
        self.assertTrue(store.rename_session(session_id, "晚风与合唱"))
        sessions = {s["id"]: s for s in store.list_sessions()}
        self.assertEqual(sessions[session_id]["title"], "晚风与合唱")
        self.assertEqual(sessions[other]["title"], f"消息-{other}")
        ids = [s["id"] for s in store.list_sessions()]
        self.assertEqual(ids[0], session_id)

    def test_rename_caps_length_and_strips_decorations(self) -> None:
        store = self.make_store()
        session_id = store.create_session()["id"]
        self.assertTrue(store.rename_session(session_id, "x" * 40 + "《》"))
        title = store.get_session(session_id)["title"]
        self.assertLessEqual(len(title), 24)
        self.assertNotIn("《", title)

    def test_rename_unknown_or_empty_is_false(self) -> None:
        store = self.make_store()
        self.assertFalse(store.rename_session(999, "随便"))
        session_id = store.create_session()["id"]
        self.assertFalse(store.rename_session(session_id, "   "))


if __name__ == "__main__":
    unittest.main()


# zcode (2026-09-07): T2+ exam findings — facts need supersession on
# contradiction, and pending facts must stay visible (tagged) to recall.
class FactSupersessionTests(StorageTestCase):
    def test_confirmed_contradiction_supersedes_old(self) -> None:
        store = self.make_store()
        first = store.add_fact("用户最喜欢的歌手是林俊杰", scope="global", status="confirmed")
        second = store.add_fact("用户最喜欢的歌手是邓紫棋", scope="global", status="confirmed")
        rows = {r["fact_id"]: r["status"] for r in store.connection.execute("SELECT fact_id, status FROM facts")}
        self.assertEqual(rows[first], "superseded")
        self.assertEqual(rows[second], "confirmed")
        self.assertEqual(store.recall_facts(), ["用户最喜欢的歌手是邓紫棋"])

    def test_unrelated_confirmed_facts_coexist(self) -> None:
        store = self.make_store()
        store.add_fact("用户最喜欢的歌手是林俊杰", scope="global", status="confirmed")
        store.add_fact("用户养了一只猫叫团子", scope="global", status="confirmed")
        self.assertEqual(len(store.recall_facts()), 2)

    def test_session_facts_do_not_conflict_with_global(self) -> None:
        store = self.make_store()
        store.add_fact("用户最喜欢的水果是西瓜", scope="global", status="confirmed")
        store.add_fact("用户最喜欢的水果是榴莲", scope="session", session_id=3, status="confirmed")
        rows = {r["fact_id"]: r["status"] for r in store.connection.execute("SELECT fact_id, status FROM facts")}
        self.assertEqual(sorted(rows.values()), ["confirmed", "confirmed"])  # different scopes never supersede
        self.assertEqual(store.recall_facts(), ["用户最喜欢的水果是西瓜"])  # global view: global only
        self.assertEqual(
            store.recall_facts(3),
            ["用户最喜欢的水果是榴莲", "用户最喜欢的水果是西瓜"],  # session view: own first (newer), then global
        )

    def test_pending_facts_recalled_with_tag(self) -> None:
        store = self.make_store()
        store.add_fact("用户最喜欢的歌手是林俊杰", scope="global", status="confirmed")
        store.add_fact("用户下个月要考驾照", scope="session", session_id=7, status="pending")
        recalled = store.recall_facts(7)
        self.assertEqual(recalled[0], "用户最喜欢的歌手是林俊杰")
        self.assertEqual(recalled[1], "用户下个月要考驾照（待确认）")

    def test_sensitive_pending_fact_stays_hidden(self) -> None:
        store = self.make_store()
        store.add_fact("用户的银行卡尾号是1234", scope="session", session_id=9, status="pending")
        store.add_fact("用户的登录密码是abc123456", scope="session", session_id=9, status="pending")
        store.add_fact("用户下个月要考驾照", scope="session", session_id=9, status="pending")
        recalled = store.recall_facts(9)
        self.assertEqual(recalled, ["用户下个月要考驾照（待确认）"])
