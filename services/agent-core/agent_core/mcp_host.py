"""zcode (C 期): minimal MCP stdio host — spawn a server, list tools, call them.

Local-first: the server process runs on this machine, JSON-RPC 2.0 over
newline-delimited stdio. Tools from MCP servers are merged into the agent
tool schema with an ``mcp__<server>__<tool>`` name and default to the
"ask" permission tier (roadmap C 期口径).
"""
from __future__ import annotations

import asyncio
import json
import os
import shlex
import shutil
from pathlib import Path
from dataclasses import dataclass, field

PROTOCOL_VERSION = "2024-11-05"


def _split_command(command: str) -> list[str]:
    """Codex: preserve quoted portable paths using the platform's argv rules.

    This only parses arguments; it does not invoke a shell or expand variables.
    Windows backslashes must not be treated as POSIX escape characters.
    """
    command = command.strip()
    if not command:
        return []
    if os.name != "nt":
        return shlex.split(command)
    import ctypes
    from ctypes import wintypes

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    parse = shell32.CommandLineToArgvW
    parse.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    parse.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    count = ctypes.c_int()
    argv = parse(command, ctypes.byref(count))
    if not argv:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return [argv[i] for i in range(count.value)]
    finally:
        kernel32.LocalFree(argv)


def _resolve_command(parts: list[str]) -> list[str]:
    """Windows-safe spawn resolution: create_subprocess_exec does not do
    PATHEXT lookup, so bare "npx"/"npm"/"python" must become the absolute
    path (npx.cmd etc.) or the spawn fails with WinError 2."""
    if not parts:
        return parts
    head = parts[0]
    if os.path.sep in head or Path(head).is_absolute():
        return parts
    found = shutil.which(head)
    return ([found, *parts[1:]] if found else parts)


@dataclass
class McpServer:
    name: str
    command: list[str]
    process: asyncio.subprocess.Process | None = None
    next_id: int = 1
    tools: list[dict] = field(default_factory=list)
    started: bool = False
    error: str = ""

    async def _roundtrip(self, payload: dict, timeout: float = 15.0) -> dict:
        assert self.process is not None and self.process.stdin and self.process.stdout
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        self.process.stdin.write(line.encode("utf-8"))
        await self.process.stdin.drain()
        while True:
            raw = await asyncio.wait_for(self.process.stdout.readline(), timeout=timeout)
            if not raw:
                raise RuntimeError("MCP server closed stdout")
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            msg = json.loads(text)
            if msg.get("id") == payload.get("id"):
                return msg

    async def start(self) -> None:
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=1024 * 1024,  # zcode: big schemas (github server) exceed the 64KB default line limit
        )
        reply = await self._roundtrip({
            "jsonrpc": "2.0", "id": self.next_id, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                       "clientInfo": {"name": "anime-agent-core", "version": "0.2.0"}},
        })
        self.next_id += 1
        if "error" in reply:
            raise RuntimeError(f"MCP initialize failed: {reply['error']}")
        self.process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        await self.process.stdin.drain()
        listing = await self._roundtrip({"jsonrpc": "2.0", "id": self.next_id, "method": "tools/list", "params": {}})
        self.next_id += 1
        self.tools = listing.get("result", {}).get("tools", [])
        self.started = True

    async def call(self, tool: str, arguments: dict) -> dict:
        reply = await self._roundtrip({
            "jsonrpc": "2.0", "id": self.next_id, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        })
        self.next_id += 1
        if "error" in reply:
            return {"ok": False, "error": str(reply["error"])[:300]}
        result = reply.get("result", {})
        parts = [str(part.get("text", "")) for part in result.get("content", []) if part.get("type") == "text"]
        text = "\n".join(parts)[:4000]
        return {"ok": not result.get("isError", False), "text": text}

    async def stop(self) -> None:
        if self.process is not None and self.process.returncode is None:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass


class McpHost:
    """Manages configured MCP servers and their merged tool schemas."""

    def __init__(self) -> None:
        self.servers: dict[str, McpServer] = {}

    async def start_from_env(self) -> None:
        """ANIME_AGENT_MCP_SERVERS: 'name=command args' entries, os.pathsep separated."""
        configured = os.getenv("ANIME_AGENT_MCP_SERVERS", "").strip()
        if not configured:
            return
        for entry in configured.split(os.pathsep):
            entry = entry.strip()
            if not entry or "=" not in entry:
                continue
            name, command = entry.split("=", 1)
            name = name.strip()
            parts = _resolve_command(_split_command(command))
            if not parts:
                continue
            server = McpServer(name=name, command=parts)
            try:
                await server.start()
                self.servers[name] = server
            except Exception as exc:  # noqa: BLE001 - one bad server must not kill the core
                server.error = str(exc)[:200]
                self.servers[name] = server

    def tool_entries(self) -> list[tuple[str, str, dict]]:
        """(qualified_name, description, inputSchema) across all servers."""
        entries = []
        for server in self.servers.values():
            for tool in server.tools:
                entries.append((
                    f"mcp__{server.name}__{tool.get('name', '')}",
                    str(tool.get("description", "")),
                    tool.get("inputSchema", {"type": "object", "properties": {}}),
                ))
        return entries

    def status(self) -> dict:
        return {name: {"started": s.started, "tools": len(s.tools), "error": s.error}
                for name, s in self.servers.items()}

    async def stop_all(self) -> None:
        for server in self.servers.values():
            await server.stop()


async def _self_test() -> None:
    server = McpServer(name="exam", command=[sys.executable,
                       r"D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\scripts\test_mcp_server.py"])
    await server.start()
    assert server.started, "server failed to start"
    entries = [(f"mcp__exam__{t['name']}", t["description"], t["inputSchema"]) for t in server.tools]
    assert any(e[0] == "mcp__exam__echo" for e in entries), entries
    result = await server.call("echo", {"text": "天依万岁"})
    assert result["ok"] and "天依万岁" in result["text"].upper(), result
    await server.stop()
    print("MCP self-test OK:", [e[0] for e in entries])


if __name__ == "__main__":
    import sys

    asyncio.run(_self_test())
