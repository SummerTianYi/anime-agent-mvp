from __future__ import annotations

import unittest

from agent_core.agent_loop import (
    AgentStep,
    ToolsUnsupportedError,
    run_agent_loop,
)

TOOLS_SCHEMA = [{"type": "function", "function": {"name": "get_time", "parameters": {"type": "object"}}}]


def _assistant_tool_call(name: str = "get_time", call_id: str = "c1") -> dict:
    return {
        "content": None,
        "tool_calls": [{"id": call_id, "name": name, "arguments": {}}],
        "raw": {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": call_id, "type": "function", "function": {"name": name, "arguments": "{}"}}
            ],
        },
    }


def _final_turn(text: str) -> dict:
    return {"content": text, "tool_calls": [], "raw": {"role": "assistant", "content": text}}


async def _executor(name: str, arguments: dict) -> dict:
    return {"ok": True, "tool": name}


async def _failing_executor(name: str, arguments: dict) -> dict:
    raise RuntimeError("boom")


class PlainProvider:
    """Mirrors the pre-loop baseline: only complete() exists."""

    name = "plain"

    def __init__(self) -> None:
        self.plain_messages = None

    async def complete(self, messages) -> str:
        self.plain_messages = messages
        return '{"reply":"直接回答"}'


class ScriptedProvider:
    name = "scripted"

    def __init__(self, turns: list[dict], final_text: str = '{"reply":"最终回答"}') -> None:
        self.turns = list(turns)
        self.final_text = final_text
        self.tool_calls_log: list[list] = []
        self.plain_log: list[list] = []

    async def complete_with_tools(self, messages, tools) -> dict:
        self.tool_calls_log.append([list(messages), tools])
        return self.turns.pop(0)

    async def complete(self, messages) -> str:
        self.plain_log.append(list(messages))
        return self.final_text


class AlwaysToolProvider(ScriptedProvider):
    def __init__(self) -> None:
        super().__init__([])
    async def complete_with_tools(self, messages, tools) -> dict:
        self.tool_calls_log.append([list(messages), tools])
        return _assistant_tool_call()


class UnsupportedProvider(ScriptedProvider):
    async def complete_with_tools(self, messages, tools) -> dict:
        raise ToolsUnsupportedError("HTTP 400")


class AgentLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_fallback_when_provider_lacks_tools(self) -> None:
        provider = PlainProvider()
        result = await run_agent_loop(provider, [{"role": "user", "content": "hi"}], TOOLS_SCHEMA, _executor)
        self.assertEqual(result.text, '{"reply":"直接回答"}')
        self.assertEqual(result.steps, [])
        self.assertTrue(result.degraded)
        self.assertFalse(result.hit_step_limit)
        self.assertEqual(provider.plain_messages, [{"role": "user", "content": "hi"}])

    async def test_tool_roundtrip_appends_assistant_and_tool_messages(self) -> None:
        provider = ScriptedProvider([_assistant_tool_call(), _final_turn('{"reply":"done"}')])
        result = await run_agent_loop(provider, [{"role": "user", "content": "几点了"}], TOOLS_SCHEMA, _executor)
        self.assertEqual(result.text, '{"reply":"done"}')
        self.assertEqual(len(result.steps), 1)
        self.assertTrue(result.steps[0].ok)
        self.assertFalse(result.degraded)
        second_conversation = provider.tool_calls_log[1][0]
        self.assertEqual(second_conversation[1]["role"], "assistant")
        self.assertEqual(second_conversation[2]["role"], "tool")
        self.assertEqual(second_conversation[2]["tool_call_id"], "c1")

    async def test_executor_failure_feeds_error_back_to_model(self) -> None:
        provider = ScriptedProvider([_assistant_tool_call(), _final_turn('{"reply":"recovered"}')])
        result = await run_agent_loop(provider, [{"role": "user", "content": "x"}], TOOLS_SCHEMA, _failing_executor)
        self.assertEqual(result.text, '{"reply":"recovered"}')
        self.assertFalse(result.steps[0].ok)
        tool_message = provider.tool_calls_log[1][0][2]
        self.assertIn("boom", tool_message["content"])

    async def test_step_limit_triggers_plain_finalize_with_summary(self) -> None:
        provider = AlwaysToolProvider()
        result = await run_agent_loop(
            provider,
            [{"role": "system", "content": "角色提示"}, {"role": "user", "content": "x"}],
            TOOLS_SCHEMA,
            _executor,
            max_steps=3,
        )
        self.assertTrue(result.hit_step_limit)
        self.assertEqual(len(result.steps), 3)
        self.assertEqual(len(provider.plain_log), 1)
        self.assertEqual(len(provider.plain_log[0]), 2)
        self.assertIn("工具执行记录", provider.plain_log[0][0]["content"])
        self.assertEqual(provider.plain_log[0][1]["role"], "user")

    async def test_tools_unsupported_degrades_to_plain(self) -> None:
        provider = UnsupportedProvider([])
        result = await run_agent_loop(provider, [{"role": "user", "content": "x"}], TOOLS_SCHEMA, _executor)
        self.assertTrue(result.degraded)
        self.assertEqual(result.steps, [])
        self.assertEqual(len(provider.plain_log), 1)

    async def test_on_step_callback_fires(self) -> None:
        provider = ScriptedProvider([_assistant_tool_call(), _final_turn("ok")])
        seen: list[AgentStep] = []

        async def on_step(step: AgentStep) -> None:
            seen.append(step)

        await run_agent_loop(provider, [{"role": "user", "content": "x"}], TOOLS_SCHEMA, _executor, on_step=on_step)
        self.assertEqual([step.tool for step in seen], ["get_time"])

    async def test_empty_turn_without_calls_falls_back(self) -> None:
        provider = ScriptedProvider([{"content": None, "tool_calls": [], "raw": {"role": "assistant", "content": None}}])
        result = await run_agent_loop(provider, [{"role": "user", "content": "x"}], TOOLS_SCHEMA, _executor)
        self.assertEqual(result.text, '{"reply":"最终回答"}')
        self.assertEqual(result.steps, [])


if __name__ == "__main__":
    unittest.main()
