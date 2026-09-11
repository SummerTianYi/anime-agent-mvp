"""Codex: startup liveness must never depend on the optional speech service."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from agent_core import main as core


class LivenessTests(unittest.TestCase):
    def test_liveness_does_not_probe_speech_or_llm(self):
        # A dependency that hangs, fails, or is still loading cannot block startup.
        with patch.object(core, "TTS_ENABLED", True), patch.object(
            core.speech_client, "is_healthy", side_effect=AssertionError("dependency probe")
        ) as speech, patch.object(core.provider, "complete") as llm:
            response = TestClient(core.app).get("/health/live")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "anime-agent-core")
        self.assertEqual(payload["pid"], os.getpid())
        self.assertIn("avatar", payload["roles"])
        speech.assert_not_called()
        llm.assert_not_called()

    def test_detailed_health_remains_compatible_when_speech_offline(self):
        with patch.object(core, "TTS_ENABLED", True), patch.object(
            core.speech_client, "is_healthy", return_value=False
        ):
            response = TestClient(core.app).get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertFalse(response.json()["tts"]["available"])

    def test_fresh_start_history_has_integer_empty_session_id(self):
        # A fresh database used to send null; Godot int(null) aborts UI history setup.
        with patch.object(core.memory, "latest_session_id", return_value=None):
            with TestClient(core.app).websocket_connect("/ws") as ws:
                self.assertEqual(ws.receive_json()["type"], "core.status")
                ws.send_json({"type": "chat.history.request"})
                reply = ws.receive_json()
        self.assertEqual(reply["type"], "chat.history.response")
        self.assertEqual(reply["conversationId"], -1)
        self.assertEqual(reply["messages"], [])


if __name__ == "__main__":
    unittest.main()
