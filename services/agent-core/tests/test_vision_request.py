"""Vision request builders for both dialects, without touching the network."""
from __future__ import annotations

import unittest
import urllib.parse

from agent_core.tools import _vision_request, _vision_text


class VisionRequestTest(unittest.TestCase):
    def test_openai_branch_keeps_chat_completions_shape(self) -> None:
        request, protocol = _vision_request(
            "openai", "https://example.test/v1", "sk-test", "vision-model", "B64DATA", "看看屏幕"
        )
        self.assertTrue(request.full_url.endswith("/chat/completions"))
        self.assertEqual(request.get_header("Authorization"), "Bearer sk-test")
        body = request.data.decode("utf-8")
        self.assertIn("image_url", body)
        self.assertIn("data:image/png;base64,B64DATA", body)

    def test_anthropic_branch_builds_messages_shape(self) -> None:
        request, protocol = _vision_request(
            "anthropic", "https://example.test/step_plan", "sf-key", "step-3.7-flash", "B64DATA", "看看屏幕"
        )
        self.assertTrue(request.full_url.endswith("/step_plan/v1/messages"))
        self.assertEqual(request.get_header("X-api-key"), "sf-key")
        body = request.data.decode("utf-8")
        self.assertIn('"type": "image"', body)
        self.assertIn('"media_type": "image/png"', body)
        self.assertIn("step-3.7-flash", body)
        self.assertEqual(protocol, "anthropic")

    def test_anthropic_url_join_is_safe_with_trailing_slash(self) -> None:
        request, _ = _vision_request(
            "anthropic", "https://example.test/step_plan/", "k", "m", "D", "q"
        )
        self.assertNotIn("//v1/messages", request.full_url)


class VisionTextTest(unittest.TestCase):
    def test_anthropic_payload_skips_thinking_blocks(self) -> None:
        payload = {
            "content": [
                {"type": "thinking", "thinking": "hmm"},
                {"type": "text", "text": "一个红色圆"},
            ]
        }
        self.assertEqual(_vision_text("anthropic", payload), "一个红色圆")

    def test_openai_payload_handles_list_content(self) -> None:
        payload = {"choices": [{"message": {"content": [{"type": "text", "text": "ok"}]}}]}
        self.assertEqual(_vision_text("openai", payload), "ok")

    def test_openai_payload_handles_plain_string(self) -> None:
        self.assertEqual(_vision_text("openai", {"choices": [{"message": {"content": "plain"}}]}), "plain")


if __name__ == "__main__":
    unittest.main()
