"""Typed model decisions; action state is always rendered from host records.

These checks establish provenance and control-state consistency, not a semantic
proof of arbitrary conversational prose. Keep that distinction explicit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


INCOMPLETE = "这次任务尚未完成：没有取得可交付的任务决策或有效提案。原目标和已有记录已保留，没有生成新的确认票据。"


@dataclass(frozen=True)
class DeliveryDecision:
    text: str = ""
    error: str = ""
    mode: str = ""


def decode_decision(raw: str) -> tuple[dict[str, Any], dict[str, Any]]:
    # Do not recover a trailing object after arbitrary visible prose here.
    # CharacterHarness may still recover presentation fields after validation.
    try:
        payload = json.loads(raw, strict=False)
    except (ValueError, TypeError):
        return {}, {}
    if not isinstance(payload, dict) or not isinstance(payload.get("decision"), dict):
        return {}, {}
    return payload, payload["decision"]


def validate_decision(raw, *, task, session_id, request_id, actions, schemas):
    payload, decision = decode_decision(raw)
    mode = decision.get("mode")
    if not isinstance(mode, str) or mode not in {"chat", "clarify", "act", "report"}:
        return DeliveryDecision(error="缺少合法 decision.mode：chat/clarify/act/report")
    refs = decision.get("action_refs", [])
    read_refs = decision.get("read_refs", [])
    if any(not isinstance(v, list) or any(not isinstance(r, str) for r in v)
           or len(v) != len(set(v)) for v in (refs, read_refs)):
        return DeliveryDecision(error="引用必须是无重复的字符串数组", mode=mode)
    # Only the active task may supply proof, including a reused ledger action
    # explicitly observed by this task (deduplication never transfers consent).
    owned = {a["action_id"]: a for a in actions
             if a["session_id"] == session_id and
             (a["task_id"] == task["id"] or a["action_id"] in task.get("observed_actions", []))}
    reads = {r["result_ref"]: r for r in task.get("tool_results", [])
             if r.get("session_id") == session_id and r.get("task_id") == task["id"]
             and r.get("result_ref")}
    if any(ref not in owned for ref in refs) or any(ref not in reads for ref in read_refs):
        return DeliveryDecision(error="引用不存在或不属于当前会话任务", mode=mode)
    current = [a for aid, a in owned.items() if aid in task.get("delivery_actions", [])]
    current_reads = [r for r in reads.values() if r["request_id"] == request_id]
    current_failures = [f for f in task.get("tool_failures", []) if f.get("request_id") == request_id]
    if mode == "act":
        task["needs_proposal"] = True
        return DeliveryDecision(error="操作必须使用真实 tool_calls 提案，不能用 reply 或 decision 代替", mode=mode)
    if mode in {"chat", "clarify"}:
        if refs or read_refs or current or current_reads or current_failures or (mode == "chat" and task.get("needs_proposal")):
            return DeliveryDecision(error="当前已有任务证据或尚缺真实提案，不能改报聊天/澄清", mode=mode)
        if mode == "clarify":
            name, args, missing = decision.get("tool"), decision.get("arguments", {}), decision.get("missing")
            schema = schemas.get(name) if isinstance(name, str) else None
            if not schema or not isinstance(args, dict) or not isinstance(missing, list) or not missing:
                return DeliveryDecision(error="澄清必须给出已注册 tool、已知 arguments 和 missing 参数", mode=mode)
            properties = schema.get("properties", {})
            required = required_parameters(name, args, schema)
            # GitHub update has a choice of edit fields. Asking which value to
            # set is legitimate only before any edit field has been supplied.
            if name == "mcp__github__issue_write" and args.get("method") == "update" and not any(k in args for k in ("title", "body", "state", "labels", "assignees", "milestone")):
                required |= {"title", "body"}
            if any(not isinstance(k, str) or k not in properties or k not in required or k in args for k in missing):
                return DeliveryDecision(error="缺少的参数必须属于工具且不在已知参数中", mode=mode)
            if len(set(missing)) != len(missing):
                return DeliveryDecision(error="缺参列表不能重复", mode=mode)
            return DeliveryDecision(text="还需要你补充这些参数：" + "、".join(missing) + "。补齐后才能提出操作；当前没有新增待确认操作。", mode=mode)
        reply = payload.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            return DeliveryDecision(error="聊天回答不能为空", mode=mode)
        return DeliveryDecision(text=reply.strip(), mode=mode)
    if not refs and not read_refs:
        return DeliveryDecision(error="report 必须引用真实动作或只读结果", mode=mode)
    # A report is not allowed to relabel a failed/unknown/pending action.
    # main renders ALL current action states regardless of the selected refs.
    if any(owned[r]["status"] != "succeeded" for r in refs):
        return DeliveryDecision(mode=mode)
    if any(reads[r]["result"].get("ok") is not True for r in read_refs):
        return DeliveryDecision(mode=mode)
    summary = payload.get("reply", "")
    if not isinstance(summary, str):
        return DeliveryDecision(error="reply 必须是文字", mode=mode)
    # Natural summaries remain possible only over successful read evidence.
    # Write status never comes from this string, even with valid action refs.
    readable = bool(read_refs) or any(owned[r].get("effect") == "read" for r in refs)
    return DeliveryDecision(text=summary.strip() if readable else "", mode=mode)


def required_parameters(name, arguments, schema):
    required = set(schema.get("required", []))
    if name == "mcp__github__issue_write" and arguments.get("method") == "update":
        required.add("issue_number")
    return required


def validate_proposal(name, arguments, schemas):
    """Reject malformed proposals before permission, ledger or execution.

    This is a small argument gate for the pilot, not a full JSON Schema engine
    or a proof that arguments express the user's natural-language intention.
    """
    schema = schemas.get(name)
    if schema is None:
        return "工具未在本轮注册"
    if not isinstance(arguments, dict):
        return "工具参数必须是对象"
    if name == "read_tool_result":
        # The existing bounded page reader owns ref/offset validation and
        # persists its failed read receipt; do not erase that recovery path.
        return ""
    missing = required_parameters(name, arguments, schema) - arguments.keys()
    if missing:
        return "缺少必要参数：" + "、".join(sorted(missing))
    types = {"string": str, "object": dict, "array": list, "boolean": bool,
             "integer": int, "number": (int, float)}
    for key, value in arguments.items():
        field = schema.get("properties", {}).get(key, {})
        kind = field.get("type")
        if isinstance(kind, str) and kind in types:
            if not isinstance(value, types[kind]) or (kind in {"integer", "number"} and isinstance(value, bool)):
                return "参数类型错误：" + key
        if "enum" in field and value not in field["enum"]:
            return "参数值不在允许范围：" + key
    nonempty = {"path"} if name in {"read_file", "write_file"} else set()
    if name in {"mcp__github__issue_write", "mcp__github__issue_read"}:
        nonempty |= {"owner", "repo"}
        if name.endswith("issue_write") and "title" in arguments:
            nonempty.add("title")
        if "issue_number" in arguments:
            number = arguments["issue_number"]
            if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                return "issue_number 必须为正整数"
    if any(not isinstance(arguments.get(k), str) or not arguments[k].strip() for k in nonempty):
        return "目标和标题参数不能为空：" + "、".join(sorted(nonempty))
    return ""
