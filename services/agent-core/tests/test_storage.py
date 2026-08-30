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


class FreshDatabaseTests(StorageTestCase):
    def test_first_run_creates_default_session(self) -> None:
        store = self.make_store()
        session_id = store.latest_session_id()
        self.assertIsNotNone(session_id)
        sessions = store.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "新对话")

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


if __name__ == "__main__":
    unittest.main()
