from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_core.storage import MemoryStore


class SessionVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(data_dir=Path(self._tmp.name))

    def tearDown(self) -> None:
        self.store.connection.close()
        self._tmp.cleanup()

    def test_empty_session_hidden_from_list(self) -> None:
        store = self.store
        store.create_session()
        self.assertEqual(store.list_sessions(), [])

    def test_first_message_makes_session_visible(self) -> None:
        session = self.store.create_session()
        self.store.add_message("user", "hello", conversation_id=session["id"])
        visible = self.store.list_sessions()
        self.assertEqual([s["id"] for s in visible], [session["id"]])

    def test_sweep_removes_empty_keeps_content(self) -> None:
        session = self.store.create_session()
        self.store.add_message("user", "question", conversation_id=session["id"])
        other = self.store.create_session()
        swept = self.store.sweep_empty_sessions()
        self.assertNotIn(session["id"], swept)
        self.assertIn(other["id"], swept)
        ids = [s["id"] for s in self.store.list_sessions()]
        self.assertEqual(ids, [session["id"]])

    def test_ordering_by_activity(self) -> None:
        store = self.store
        first = store.create_session()
        store.add_message("user", "older-session-new-message", conversation_id=first["id"])
        second = store.create_session()
        store.add_message("user", "newer-session-message", conversation_id=second["id"])
        order = [s["id"] for s in store.list_sessions()]
        self.assertEqual(order, [second["id"], first["id"]])
