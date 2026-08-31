from __future__ import annotations

import concurrent.futures
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANIME_AGENT_WAKE_WORD", "0")

from fastapi.testclient import TestClient

from agent_core import main as core
from agent_core.storage import MemoryStore


class ScriptedProvider:
    """Stands in for the LLM: always answers in contract JSON with a fixed title."""

    name = "scripted"

    def __init__(self, reply_text: str, title: str | None) -> None:
        self.reply_text = reply_text
        self.title = title

    async def complete(self, messages) -> str:
        payload = {
            "reply": self.reply_text,
            "emotion": "happy",
            "emotion_intensity": 0.5,
            "gesture": "none",
            "memory_candidate": None,
        }
        if self.title is not None:
            payload["session_title"] = self.title
        return json.dumps(payload, ensure_ascii=False)


def _recv(ws, timeout: float = 10.0):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(ws.receive_json).result(timeout=timeout)


def _collect_until(ws, stop_type: str, match: dict | None = None, limit: int = 25):
    seen = []
    for _ in range(limit):
        event = _recv(ws)
        seen.append(event)
        if event.get("type") == stop_type and (
            match is None or all(event.get(k) == v for k, v in match.items())
        ):
            return seen
    raise AssertionError(f"event {stop_type} {match or ''} never arrived; saw: {[e.get('type') for e in seen]}")


class SessionLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = MemoryStore(data_dir=Path(self._tmp.name))
        self.addCleanup(self.store.close)
        self.provider = ScriptedProvider("你好呀，我是洛天依。", "你好与自我介绍")
        core.provider = self.provider
        self.addCleanup(setattr, core, "provider", core.provider)
        self.addCleanup(setattr, core, "memory", core.memory)
        core.memory = self.store
        core.tools_schema = []
        self.addCleanup(setattr, core, "tools_schema", core.tools_schema)

    def _connect(self) -> TestClient:
        client = TestClient(core.app)
        self.addCleanup(client.__exit__, None, None, None)
        client.__enter__()
        ws = client.websocket_connect("/ws")
        self.addCleanup(ws.__exit__, None, None, None)
        ws.__enter__()
        ws.send_json({"type": "client.hello", "role": "avatar"})
        _collect_until(ws, "client.ready")
        return client, ws

    def test_first_chat_titles_session_then_delete_full_chain(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "session.new"})
        switched = _collect_until(ws, "session.switched")[-1]
        session_id = int(switched["conversationId"])
        self.assertEqual(switched["title"], "新对话")

        ws.send_json({"type": "chat.message", "messageId": "m1", "text": "你好呀", "conversationId": session_id})
        events = _collect_until(ws, "agent.state", match={"state": "idle"}, limit=30)
        stop = events[-1]
        self.assertEqual(stop["state"], "idle")
        chat_response = next(e for e in events if e["type"] == "chat.response")
        self.assertEqual(int(chat_response["conversationId"]), session_id)
        title_event = next(e for e in events if e["type"] == "session.title")
        self.assertEqual(int(title_event["conversationId"]), session_id)
        self.assertEqual(title_event["title"], "你好与自我介绍")
        self.assertEqual(self.store.get_session(session_id)["title"], "你好与自我介绍")

        ws.send_json({"type": "chat.message", "messageId": "m2", "text": "继续聊", "conversationId": session_id})
        turn2 = _collect_until(ws, "agent.state", match={"state": "idle"}, limit=30)
        self.assertEqual(turn2[-1]["state"], "idle")
        self.assertFalse(
            [e for e in turn2 if e["type"] == "session.title"],
            "second exchange must not retitle the session",
        )
        self.assertEqual(self.store.get_session(session_id)["title"], "你好与自我介绍")

        ws.send_json({"type": "session.delete", "conversationId": session_id})
        deleted = _collect_until(ws, "session.deleted")[-1]
        self.assertEqual(int(deleted["conversationId"]), session_id)
        after = _collect_until(ws, "session.switched")[-1]
        fresh_id = int(after["conversationId"])
        self.assertNotEqual(fresh_id, session_id)
        self.assertEqual(after["title"], "新对话")
        self.assertNotIn(session_id, [s["id"] for s in self.store.list_sessions()])
        self.assertEqual(self.store.load_messages(conversation_id=session_id), [])
        self.assertEqual(self.store.get_session(fresh_id)["title"], "新对话")

    def test_title_falls_back_to_user_text_when_model_omits(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "session.new"})
        session_id = int(_collect_until(ws, "session.switched")[-1]["conversationId"])
        core.provider = ScriptedProvider("我来啦。", None)
        ws.send_json({"type": "chat.message", "messageId": "m2", "text": "帮我写一首关于晚风与海的歌", "conversationId": session_id})
        events = _collect_until(ws, "agent.state", match={"state": "idle"}, limit=30)
        self.assertEqual(events[-1]["state"], "idle")
        title_event = next(e for e in events if e["type"] == "session.title")
        self.assertEqual(title_event["title"], "帮我写一首关于晚风与海的")

    def test_delete_unknown_session_reports_error(self) -> None:
        _client, ws = self._connect()
        ws.send_json({"type": "session.delete", "conversationId": 424242})
        error = _collect_until(ws, "core.error")[-1]
        self.assertIn("不存在", str(error.get("message", "")))


if __name__ == "__main__":
    unittest.main()
