"""zcode (C 期): minimal MCP server over stdio for verification.

Implements the 2024-11-05 subset: initialize, notifications/initialized,
tools/list, tools/call. Newline-delimited JSON-RPC 2.0 on stdin/stdout.
Exposes one harmless tool: echo(upper) — returns the input uppercased, and
count_words(text) — counts whitespace-separated words.
"""
from __future__ import annotations

import json
import sys

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "echo",
        "description": "把输入文本变成大写返回（测试工具）",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "要大写的文本"}},
            "required": ["text"],
        },
    },
    {
        "name": "count_words",
        "description": "统计输入文本的词数（按空格切分）",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]


def call_tool(name: str, arguments: dict) -> dict:
    if name == "echo":
        return {"content": [{"type": "text", "text": str(arguments.get("text", "")).upper()}]}
    if name == "count_words":
        text = str(arguments.get("text", ""))
        return {"content": [{"type": "text", "text": str(len(text.split()))}]}
    return {"isError": True, "content": [{"type": "text", "text": f"unknown tool: {name}"}]}


def handle(msg: dict) -> dict | None:
    method = msg.get("method", "")
    msg_id = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "tianyi-test-mcp", "version": "0.1.0"},
        }}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params", {})
        return {"jsonrpc": "2.0", "id": msg_id, "result": call_tool(str(params.get("name")), params.get("arguments") or {})}
    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"unknown method: {method}"}}
    return None


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
