"""Synthetic evidence-sanitization check; no provider or Core imports."""
import copy
import asyncio
import json
from unittest.mock import AsyncMock
from followup_models import public_messages, selected_synthetic_execute

source = [{"role":"assistant", "content":[{"type":"text","text":"visible"},
    {"type":"thinking","thinking":"PRIVATE-MARKER"}], "reasoning_content":"PRIVATE-MARKER",
    "thinking":"PRIVATE-MARKER", "signature":"PRIVATE-MARKER",
    "tool_calls":[{"id":"call-1", "type":"function", "reasoning":"PRIVATE-MARKER",
                   "function":{"name":"read_file", "arguments":"{\"path\":\"synthetic.txt\"}",
                               "thinking":"PRIVATE-MARKER"}}]},
          {"role":"tool", "tool_call_id":"call-1", "content":"receipt"}]
before = copy.deepcopy(source)
public = public_messages(source)
assert source == before
assert "PRIVATE-MARKER" not in json.dumps(public)
assert public[0]["content"] == [{"type":"text", "text":"visible"}]
assert public[0]["tool_calls"][0]["function"]["arguments"] == '{"path":"synthetic.txt"}'
assert public[1]["tool_call_id"] == "call-1" and public[1]["content"] == "receipt"
print("FOLLOWUP_PROJECTION_OK: five assertions; reasoning omitted, source unchanged")

async def isolation():
    execute = AsyncMock(return_value={"ok":True,"output":"synthetic"})
    denied = await selected_synthetic_execute("clipboard_read", {}, {"mcp__github__issue_write"}, execute)
    assert denied["ok"] is False
    execute.assert_not_awaited()
    allowed = await selected_synthetic_execute("mcp__github__issue_write", {}, {"mcp__github__issue_write"}, execute)
    assert allowed["ok"] is True
    execute.assert_awaited_once()
asyncio.run(isolation())
print("FOLLOWUP_ISOLATION_OK: schema-external clipboard spy never invoked")
