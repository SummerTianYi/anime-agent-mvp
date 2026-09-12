"""AnthropicCompatibleProvider: dialect translation without touching the wire.

The agent loop speaks OpenAI shapes (system rows, tool rows, tool_calls with
stringified arguments). These tests pin the translation in both directions so
the loop never learns a second dialect.
"""
from __future__ import annotations

import asyncio
import json
import unittest

from agent_core.main import AnthropicCompatibleProvider, ProviderError


def _make_provider() -> AnthropicCompatibleProvider:
    provider = AnthropicCompatibleProvider(
        name="stepfun",
        base_url="https://example.test/step_plan",
        model="step-3.7-flash",
        api_key="test-key",
        timeout_seconds=5,
    )
    return provider


def _run(awaitable):
    return asyncio.run(awaitable)


class TranslateMessagesTest(unittest.TestCase):
    def test_system_rows_merge_into_top_level_system(self) -> None:
        provider = _make_provider()
        system, messages = provider._to_anthropic_messages(
            [
                {"role": "system", "content": "人设"},
                {"role": "user", "content": "你好"},
            ]
        )
        self.assertEqual(system, "人设")
        self.assertEqual(messages, [{"role": "user", "content": [{"type": "text", "text": "你好"}]}])

    def test_assistant_tool_calls_become_tool_use_blocks(self) -> None:
        provider = _make_provider()
        _, messages = provider._to_anthropic_messages(
            [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_time", "arguments": '{"tz": "Asia/Shanghai"}'},
                        }
                    ],
                }
            ]
        )
        self.assertEqual(messages[0]["role"], "assistant")
        block = messages[0]["content"][0]
        self.assertEqual(block["type"], "tool_use")
        self.assertEqual(block["id"], "call_1")
        self.assertEqual(block["name"], "get_time")
        self.assertEqual(block["input"], {"tz": "Asia/Shanghai"})

    def test_tool_rows_become_user_tool_result_blocks(self) -> None:
        provider = _make_provider()
        _, messages = provider._to_anthropic_messages(
            [{"role": "tool", "tool_call_id": "call_1", "content": '{"ok": true}'}]
        )
        self.assertEqual(messages[0]["role"], "user")
        block = messages[0]["content"][0]
        self.assertEqual(block["type"], "tool_result")
        self.assertEqual(block["tool_use_id"], "call_1")
        self.assertEqual(block["content"], '{"ok": true}')

    def test_tool_arguments_survive_bad_json(self) -> None:
        provider = _make_provider()
        _, messages = provider._to_anthropic_messages(
            [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "x", "arguments": "{not json"}}
                    ],
                }
            ]
        )
        self.assertEqual(messages[0]["content"][0]["input"], {})


class TranslateToolsTest(unittest.TestCase):
    def test_openai_function_schema_maps_to_input_schema(self) -> None:
        tools = AnthropicCompatibleProvider._to_anthropic_tools(
            [
                {
                    "type": "function",
                    "function": {
                        "name": "get_time",
                        "description": "Get time",
                        "parameters": {"type": "object", "properties": {"tz": {"type": "string"}}},
                    },
                }
            ]
        )
        self.assertEqual(
            tools,
            [
                {
                    "name": "get_time",
                    "description": "Get time",
                    "input_schema": {"type": "object", "properties": {"tz": {"type": "string"}}},
                }
            ],
        )


class ParseResponseTest(unittest.TestCase):
    def test_thinking_blocks_skipped_text_and_tool_use_extracted(self) -> None:
        provider = _make_provider()
        turn = provider._parse_response(
            {
                "content": [
                    {"type": "thinking", "thinking": "inner monologue"},
                    {"type": "text", "text": "马上查"},
                    {"type": "tool_use", "id": "call_9", "name": "get_time", "input": {}},
                ]
            }
        )
        self.assertEqual(turn["content"], "马上查")
        self.assertEqual(len(turn["tool_calls"]), 1)
        self.assertEqual(turn["tool_calls"][0]["name"], "get_time")
        self.assertEqual(turn["raw"]["tool_calls"][0]["function"]["arguments"], "{}")

    def test_raw_message_stays_openai_shaped_for_the_loop(self) -> None:
        provider = _make_provider()
        turn = provider._parse_response(
            {
                "content": [
                    {"type": "tool_use", "id": "call_1", "name": "read_file", "input": {"path": "a.txt"}}
                ]
            }
        )
        raw = turn["raw"]
        self.assertEqual(raw["role"], "assistant")
        self.assertIsNone(raw["content"])
        call = raw["tool_calls"][0]
        self.assertEqual(call["id"], "call_1")
        self.assertEqual(call["function"]["name"], "read_file")
        self.assertEqual(json.loads(call["function"]["arguments"]), {"path": "a.txt"})

    def test_non_list_content_raises_provider_error(self) -> None:
        provider = _make_provider()
        with self.assertRaises(ProviderError):
            provider._parse_response({"content": "plain string"})


class CompleteTest(unittest.TestCase):
    def test_complete_sends_system_and_parses_text(self) -> None:
        provider = _make_provider()
        captured: dict = {}

        def fake_request(request):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return json.dumps(
                {"content": [{"type": "text", "text": "收到"}]}
            ).encode("utf-8")

        provider._request = fake_request
        reply = _run(provider.complete([{"role": "system", "content": "人设"}, {"role": "user", "content": "hi"}]))
        self.assertEqual(reply, "收到")
        self.assertTrue(captured["url"].endswith("/step_plan/v1/messages"))
        self.assertEqual(captured["body"]["system"], "人设")
        self.assertEqual(captured["body"]["max_tokens"], provider.DEFAULT_MAX_TOKENS)
        self.assertEqual(captured["body"]["messages"][0]["content"][0]["text"], "hi")

    def test_tools_rejection_maps_to_tools_unsupported(self) -> None:
        from agent_core.main import ToolsUnsupportedError
        import io
        import urllib.error

        provider = _make_provider()

        def fake_request(request):
            body = json.dumps({"error": {"message": "no tools"}}).encode("utf-8")
            raise urllib.error.HTTPError(provider.messages_url, 400, "bad", {}, io.BytesIO(body))

        provider._request = fake_request
        with self.assertRaises(ToolsUnsupportedError):
            _run(
                provider.complete_with_tools(
                    [{"role": "user", "content": "hi"}],
                    [{"type": "function", "function": {"name": "x"}}],
                )
            )


if __name__ == "__main__":
    unittest.main()
