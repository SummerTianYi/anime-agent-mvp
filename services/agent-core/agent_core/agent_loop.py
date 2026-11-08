"""Agent tool-call loop (Phase A).

Drives a Provider through tool-call rounds: the model may request tools,
the executor runs them, results are fed back as "tool" messages, and the
Core validates the final task decision independently of presentation fields.
Providers without tools use the same bounded decision contract. Standalone
callers may omit the validator for backwards-compatible plain completion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


MAX_TOOL_STEPS = 5
TOOL_RESULT_CHAR_LIMIT = 8000


class ToolsUnsupportedError(RuntimeError):
    """The provider rejected the tools payload; the loop should degrade."""


@dataclass(frozen=True, slots=True)
class AgentStep:
    tool: str
    arguments: dict[str, Any]
    ok: bool
    summary: str
    outcome: str = ""


@dataclass(slots=True)
class AgentLoopResult:
    text: str
    steps: list[AgentStep] = field(default_factory=list)
    degraded: bool = False
    hit_step_limit: bool = False
    rounds: int = 0
    decision_error: str = ""
    host_delivery: bool = False


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
    labels = {"succeeded":"成功", "failed":"失败", "unknown":"结果未知", "awaiting_confirmation":"待确认，未执行",
              "cancelled":"已取消，未执行", "expired":"授权过期，未执行"}
    lines = "\n".join(f"- {step.tool}: {labels.get(step.outcome, '成功' if step.ok else '未完成')} {step.summary}"
                      for step in steps)
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
    max_calls: int = 18,
    on_round: Callable[[], None] | None = None,
    on_call: Callable[[], None] | None = None,
    validate_final: Callable[[str], str] | None = None,
    take_correction: Callable[[], bool] | None = None,
    still_authorized: Callable[[], bool] | None = None,
    validate_call: Callable[[str, dict[str, Any]], str] | None = None,
) -> AgentLoopResult:
    conversation: list[dict[str, Any]] = [dict(item) for item in messages]
    steps: list[AgentStep] = []
    supports_tools = bool(tools_schema) and hasattr(provider, "complete_with_tools")
    final_text: str | None = None
    degraded = not supports_tools
    exhausted = False
    rounds = 0
    decision_error = ""

    def accepted(text):
        nonlocal decision_error
        decision_error = validate_final(text) if validate_final is not None else ""
        return not decision_error

    def correct(text, *, append_text=True):
        if take_correction is None or not take_correction():
            return False
        if append_text:
            conversation.append({"role": "assistant", "content": text})
        # One system message remains compatible with both deployed providers.
        note = ("\n【宿主纠正】" + decision_error +
                "。保留原任务目标和剩余预算；这是唯一一次纠正机会。需要操作请使用真实tool_calls；"
                "聊天/解释用chat，缺参用clarify，报告引用真实结果。不要用口头确认代替提案。")
        if conversation and conversation[0].get("role") == "system":
            conversation[0] = {**conversation[0], "content": str(conversation[0].get("content", "")) + note}
        else:
            conversation.insert(0, {"role": "system", "content": note})
        return True

    if (supports_tools or validate_final is not None) and (max_steps <= 0 or max_calls <= 0):
        return AgentLoopResult(text="本任务的工具预算已用完，没有执行新的操作。已有回执与产物仍保留；新任务需明确提出。",
                               hit_step_limit=True, host_delivery=validate_final is not None)

    if supports_tools or validate_final is not None:
        exhausted = True
        for _ in range(max_steps):
            if still_authorized is not None and not still_authorized():
                return AgentLoopResult(text="",steps=steps,rounds=rounds,host_delivery=True)
            rounds += 1
            if on_round is not None:
                on_round()
            try:
                turn = (await provider.complete_with_tools(conversation, tools_schema) if supports_tools
                        else {"content": await provider.complete(conversation)})
            except ToolsUnsupportedError:
                degraded = True
                if validate_final is None:
                    exhausted = False
                    break
                supports_tools = False
                continue
            if still_authorized is not None and not still_authorized():
                return AgentLoopResult(text="",steps=steps,rounds=rounds,host_delivery=True)
            calls = turn.get("tool_calls") or []
            if not calls:
                text = str(turn.get("content") or "").strip()
                if text and accepted(text):
                    final_text = text
                elif not text and validate_final is not None:
                    accepted(text)
                    if rounds < max_steps and correct(text):
                        continue
                elif rounds < max_steps and correct(text):
                    continue
                exhausted = False
                break
            raw_message = turn.get("raw") or {"role": "assistant", "content": None}
            conversation.append(raw_message)
            invalid_proposal = False
            pending_proposal = False
            # Adapters validate wire structure first. Validate the entire batch's
            # tool contracts before dispatch, including calls beyond this turn's
            # execution budget; a malformed tail must not permit a partial write.
            proposal_errors = [validate_call(call["name"], call["arguments"]) for call in calls] if validate_call else []
            batch_error = next((error for error in proposal_errors if error), "")
            # A pathological provider batch cannot create an unbounded executor loop.
            for index, call in enumerate(calls[:max(0, max_calls-len(steps))]):
                if on_call is not None:
                    on_call()
                name = str(call.get("name", "")).strip()
                arguments = call.get("arguments", {})
                argument_error = batch_error
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
                if argument_error:
                    invalid_proposal = True
                    decision_error = argument_error
                    result = {"ok": False, "error": argument_error, "outcome": "invalid_proposal"}
                elif allowed:
                    try:
                        if len(steps) >= max_calls:
                            result = {"ok":False,"error":"本轮工具调用预算已用完；未执行","outcome":"budget_exhausted"}
                        else:
                            result = await executor(name, arguments)
                    except Exception as exc:  # noqa: BLE001 - a crashing executor must not kill the loop
                        result = {"ok": False, "error": str(exc)[:300]}
                else:
                    result = {
                        "ok": False,
                        "error": f"权限拒绝（{rule_id}）：{reason}",
                    }
                pending_proposal = pending_proposal or bool(result.get("needs_confirmation"))
                step = AgentStep(
                    tool=name,
                    arguments=arguments,
                    ok=bool(result.get("ok")),
                    outcome=str(result.get("outcome") or ("succeeded" if result.get("ok") else "failed")),
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
            if pending_proposal:
                exhausted = False
                if validate_call is not None or validate_final is not None:
                    return AgentLoopResult(text="", steps=steps, rounds=rounds, host_delivery=True)
                break
            if invalid_proposal:
                if rounds < max_steps and correct("", append_text=False):
                    continue
                return AgentLoopResult(text="", steps=steps, rounds=rounds,
                                       decision_error=decision_error, host_delivery=True)
            if len(steps) >= max_calls:
                break

    if still_authorized is not None and not still_authorized():
        return AgentLoopResult(text="",steps=steps,rounds=rounds,host_delivery=True)
    if final_text is None and validate_final is None:
        final_text = await provider.complete(_fallback_messages(messages, steps))
    return AgentLoopResult(
        text=final_text or "",
        steps=steps,
        degraded=degraded,
        hit_step_limit=exhausted,
        rounds=rounds,
        decision_error=decision_error,
        host_delivery=validate_final is not None and final_text is None,
    )
