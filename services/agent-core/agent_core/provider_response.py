"""Validate a whole non-streaming provider response before exposing any call."""
from __future__ import annotations

import json
import math
import re
from typing import Any


class ResponseProtocolError(ValueError):
    """Only fixed, safe diagnostics; never include untrusted response bodies."""


def invalid():
    raise ResponseProtocolError("API 响应格式无法识别")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            invalid()
        result[key] = value
    return result


def _json_values(value):
    if isinstance(value, str):
        value.encode('utf-8')  # Reject escaped unpaired surrogates too.
    elif isinstance(value, float) and not math.isfinite(value):
        invalid()
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                invalid()
            _json_values(key)
            _json_values(item)
    elif isinstance(value, list):
        for item in value:
            _json_values(item)
    elif value is not None and not isinstance(value, (int, float, bool)):
        invalid()


def load_json(raw: bytes | str) -> Any:
    try:
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        if not isinstance(raw, str):
            invalid()
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: invalid())
        _json_values(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ResponseProtocolError("API 响应格式无法识别") from exc


def arguments(raw: Any) -> dict:
    value = load_json(raw) if isinstance(raw, str) else raw
    if not isinstance(value, dict):
        invalid()
    try:
        _json_values(value)
    except (UnicodeError, RecursionError) as exc:
        raise ResponseProtocolError("API 工具参数格式无法识别") from exc
    return value


def tools_unsupported(raw: bytes) -> bool:
    """Only an explicit, structured capability rejection permits plain fallback."""
    try:
        payload = load_json(raw)
    except ResponseProtocolError:
        return False
    error = payload.get('error') if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return False
    message = error.get('message')
    if not isinstance(message, str):
        return False
    message = ' '.join(message.lower().split())
    return bool(re.fullmatch(
        r"(?:no tools|tools? (?:are |is )?not supported|"
        r"(?:this (?:model|endpoint) )?does not support (?:tools|tool calling|function calling)|"
        r"unsupported (?:parameter|field):? ['\"]?(?:tools|tool_choice)['\"]?)\.?", message))


def _string(value, *, nonempty=False):
    if not isinstance(value, str) or (nonempty and not value.strip()):
        invalid()
    try:
        value.encode('utf-8')
    except UnicodeError as exc:
        raise ResponseProtocolError("API 响应格式无法识别") from exc
    return value


def _call(identifier, name, raw_arguments):
    return {'id': _string(identifier, nonempty=True), 'name': _string(name, nonempty=True),
            'arguments': arguments(raw_arguments)}


def _finish(text, calls, raw):
    ids = [call['id'] for call in calls]
    if len(ids) != len(set(ids)):
        invalid()
    text = text.strip()
    if not text and not calls:
        raise ResponseProtocolError("API 返回空回复")
    return {'content': text, 'tool_calls': calls, 'raw': raw}


def openai(payload: Any) -> dict:
    if not isinstance(payload, dict) or payload.get('error') is not None:
        invalid()
    choices = payload.get('choices')
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        invalid()
    message = choices[0].get('message')
    if not isinstance(message, dict) or message.get('role', 'assistant') != 'assistant':
        invalid()
    content = message.get('content')
    if isinstance(content, list):
        parts = []
        for part in content:
            if not isinstance(part, dict) or part.get('type', 'text') not in ('text', 'output_text'):
                invalid()
            parts.append(_string(part.get('text')))
        text = ''.join(parts)
    else:
        text = '' if content is None else _string(content)
    calls = message.get('tool_calls')
    if calls is None:
        calls = []
    if not isinstance(calls, list):
        invalid()
    checked = []
    for call in calls:
        if not isinstance(call, dict) or call.get('type', 'function') != 'function':
            invalid()
        function = call.get('function')
        if not isinstance(function, dict):
            invalid()
        checked.append(_call(call.get('id'), function.get('name'), function.get('arguments')))
    return _finish(text, checked, message)


def anthropic(payload: Any) -> dict:
    if not isinstance(payload, dict) or payload.get('error') is not None:
        invalid()
    if payload.get('role', 'assistant') != 'assistant' or payload.get('type', 'message') != 'message':
        invalid()
    content = payload.get('content')
    if not isinstance(content, list):
        invalid()
    texts, calls = [], []
    for block in content:
        if not isinstance(block, dict):
            invalid()
        kind = block.get('type')
        if kind == 'text':
            texts.append(_string(block.get('text')))
        elif kind == 'tool_use':
            calls.append(_call(block.get('id'), block.get('name'), block.get('input')))
        elif kind == 'thinking':
            _string(block.get('thinking'))
        elif kind == 'redacted_thinking':
            _string(block.get('data'))
        else:
            invalid()
    text = ''.join(texts).strip()
    raw = {'role': 'assistant', 'content': text or None}
    if calls:
        raw['tool_calls'] = [{'id': call['id'], 'type': 'function', 'function': {
            'name': call['name'], 'arguments': json.dumps(call['arguments'], ensure_ascii=False)}} for call in calls]
    return _finish(text, calls, raw)
