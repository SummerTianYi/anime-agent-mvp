"""Agent tool-call loop (Phase A).

Drives a Provider through tool-call rounds: the model may request tools,
the executor runs them, results are fed back as "tool" messages, and the
final answer is expected to satisfy the character JSON contract exactly as
before. Providers without ``complete_with_tools`` (and the mock provider)
fall back to a single plain completion, byte-identical to the pre-loop
baseline, so a broken or tool-incapable endpoint can never regress chat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


MAX_TOOL_STEPS = 5
TOOL_RESULT_CHAR_LIMIT = 1200


class ToolsUnsupportedError(RuntimeError):
    """The provider rejected the tools payload; the loop should degrade."""


@dataclass(frozen=True, slots=True)
class AgentStep:
    tool: str
    arguments: dict[str, Any]
    ok: bool
    summary: str


@dataclass(slots=True)
class AgentLoopResult:
    text: str
    steps: list[AgentStep] = field(default_factory=list)
    degraded: bool = False
    hit_step_limit: bool = False


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…（结果已截断）"


def _fallback_messages(
    messages: list[dict[str, Any]], steps: list[AgentStep]
) -> list[dict[str, Any]]:
    """Baseline-shaped messages (one leading system, then user/assistant) for plain completion.

    Tool transcripts never reach providers in plain mode; the outcome is
    merged into the existing system message — GLM rejects a second system
    role, so message shapes stay identical to the pre-loop baseline.
    """
    if not steps:
        return list(messages)
    lines = "\n".join(
        f"- {step.tool}: {'成功' if step.ok else '失败'} {step.summary}" for step in steps
    )
    summary = f"【工具执行记录】\n{lines}"
    if messages and str(messages[0].get("role")) == "system":
        merged = [dict(messages[0])]
        merged[0]["content"] = f"{messages[0].get('content', '')}\n\n{summary}"
        return [*merged, *messages[1:]]
    return [*messages, {"role": "system", "content": summary}]


async def run_agent_loop(
    provider: Any,
    messages: list[dict[str, Any]],
    tools_schema: list[dict[str, Any]],
    executor: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
    on_step: Callable[[AgentStep], Awaitable[None]] | None = None,
    max_steps: int = MAX_TOOL_STEPS,
    permission_gate: Callable[[str, dict[str, Any]], Any] | None = None,
) -> AgentLoopResult:
    conversation: list[dict[str, Any]] = [dict(item) for item in messages]
    steps: list[AgentStep] = []
    supports_tools = bool(tools_schema) and hasattr(provider, "complete_with_tools")
    final_text: str | None = None
    degraded = not supports_tools
    exhausted = False

    if supports_tools:
        exhausted = True
        for _ in range(max_steps):
            try:
                turn = await provider.complete_with_tools(conversation, tools_schema)
            except ToolsUnsupportedError:
                degraded = True
                exhausted = False
                break
            calls = turn.get("tool_calls") or []
            if not calls:
                text = str(turn.get("content") or "").strip()
                if text:
                    final_text = text
                exhausted = False
                break
            raw_message = turn.get("raw") or {"role": "assistant", "content": None}
            conversation.append(raw_message)
            for index, call in enumerate(calls):
                name = str(call.get("name", "")).strip()
                arguments = call.get("arguments") or {}
                allowed = True
                if permission_gate is not None:
                    try:
                        decision = permission_gate(name, arguments)
                        allowed = bool(getattr(decision, "allowed", True))
                        rule_id = str(getattr(decision, "rule_id", "default-deny"))
                        reason = str(getattr(decision, "reason", "未获授权"))
                    except Exception as exc:  # noqa: BLE001 - a broken gate must fail closed
                        allowed = False
                        rule_id = "gate-error"
                        reason = str(exc)[:200]
                if allowed:
                    try:
                        result = await executor(name, arguments)
                    except Exception as exc:  # noqa: BLE001 - a crashing executor must not kill the loop
                        result = {"ok": False, "error": str(exc)[:300]}
                else:
                    result = {
                        "ok": False,
                        "error": f"权限拒绝（{rule_id}）：{reason}",
                    }
                step = AgentStep(
                    tool=name,
                    arguments=arguments,
                    ok=bool(result.get("ok")),
                    summary=_truncate(
                        json.dumps(result, ensure_ascii=False, default=str),
                        TOOL_RESULT_CHAR_LIMIT,
                    ),
                )
                steps.append(step)
                if on_step is not None:
                    await on_step(step)
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(call.get("id") or f"call_{index}"),
                        "content": step.summary,
                    }
                )

    if final_text is None:
        final_text = await provider.complete(_fallback_messages(messages, steps))
    return AgentLoopResult(
        text=final_text,
        steps=steps,
        degraded=degraded,
        hit_step_limit=exhausted,
    )
