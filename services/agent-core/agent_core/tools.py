"""Read-only tool registry for the agent loop (Phase A).

Every tool returns a JSON-serializable dict with an "ok" flag. Tools are
pure reads: nothing here mutates user state. Path-based tools are confined
to allow-listed roots (ANIME_AGENT_TOOLS_ROOTS, os.pathsep separated,
"*" disables the restriction); defaults cover the user profile,
LocalAppData, the temp directory and the current working directory.
"""

from __future__ import annotations

import asyncio
import ctypes
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

MAX_READ_BYTES = 64 * 1024
MAX_LIST_ENTRIES = 200
MAX_CLIPBOARD_CHARS = 16_000
TOOL_TIMEOUT_SECONDS = 15.0

_WEEKDAY_LABELS = "一二三四五六日"


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., dict[str, Any]]


def _allowed_roots() -> list[Path]:
    configured = os.getenv("ANIME_AGENT_TOOLS_ROOTS", "").strip()
    if configured == "*":
        return []
    if configured:
        roots = [item for item in (part.strip() for part in configured.split(os.pathsep)) if item]
        if roots:
            return [Path(item) for item in roots]
    defaults = [
        os.getenv("USERPROFILE", ""),
        os.getenv("LOCALAPPDATA", ""),
        os.getenv("TEMP", ""),
        os.getcwd(),
    ]
    return [Path(item) for item in defaults if item]


def _inside_allowed_roots(candidate: str, roots: list[Path]) -> bool:
    return any(
        candidate.startswith(os.path.normcase(str(root.resolve())) + os.sep)
        or candidate == os.path.normcase(str(root.resolve()))
        for root in roots
    )


def _resolve_path(raw: Any) -> Path:
    text = str(raw or "").strip().strip('"')
    if not text:
        raise ValueError("路径为空")
    expanded = os.path.expandvars(os.path.expanduser(text))
    path = Path(expanded)
    if not path.is_absolute():
        raise ValueError("必须是绝对路径")
    roots = _allowed_roots()
    if roots:
        # Dual check: the lexical path keeps redirected folders (Desktop is a
        # junction on this machine) usable, while the resolved physical path
        # still blocks ".." and symlink escapes into system areas.
        lexical = os.path.normcase(os.path.normpath(str(path)))
        resolved = os.path.normcase(str(path.resolve()))
        if not (_inside_allowed_roots(lexical, roots) or _inside_allowed_roots(resolved, roots)):
            raise ValueError("路径超出允许范围（可用 ANIME_AGENT_TOOLS_ROOTS 调整）")
    return path.resolve()


def get_time() -> dict[str, Any]:
    now = datetime.now().astimezone()
    return {
        "ok": True,
        "local_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": _WEEKDAY_LABELS[now.weekday()],
        "utc_offset": now.strftime("%z"),
    }


def read_file(path: Any) -> dict[str, Any]:
    try:
        path = _resolve_path(path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not path.is_file():
        return {"ok": False, "error": f"文件不存在：{path}"}
    try:
        size = path.stat().st_size
        with open(path, "rb") as handle:
            data = handle.read(MAX_READ_BYTES)
    except OSError as exc:
        return {"ok": False, "error": f"读取失败：{exc}"}
    text = data.decode("utf-8", errors="replace")
    if size > MAX_READ_BYTES:
        text += f"\n…（内容已截断，完整大小 {size} 字节）"
    return {"ok": True, "path": str(path), "size": size, "content": text}


def list_dir(path: Any) -> dict[str, Any]:
    try:
        path = _resolve_path(path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not path.is_dir():
        return {"ok": False, "error": f"目录不存在：{path}"}
    try:
        entries = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    except OSError as exc:
        return {"ok": False, "error": f"读取失败：{exc}"}
    items: list[dict[str, Any]] = []
    truncated = False
    for entry in entries:
        if len(items) >= MAX_LIST_ENTRIES:
            truncated = True
            break
        try:
            size = entry.stat().st_size if entry.is_file() else None
        except OSError:
            size = None
        items.append({"name": entry.name, "type": "file" if entry.is_file() else "dir", "size": size})
    return {"ok": True, "path": str(path), "entries": items, "truncated": truncated}


def screenshot() -> dict[str, Any]:
    try:
        import mss
        import mss.tools
    except ImportError:
        return {"ok": False, "error": "截图依赖 mss 未安装（pip install mss）"}
    try:
        import tempfile

        with mss.mss() as scanner:
            shot = scanner.grab(scanner.monitors[1])
            output = Path(tempfile.gettempdir()) / f"tianyi-screen-{int(time.time())}.png"
            mss.tools.to_png(shot.rgb, shot.size, output=str(output))
    except Exception as exc:  # noqa: BLE001 - tool boundary must not crash the loop
        return {"ok": False, "error": f"截图失败：{exc}"}
    return {"ok": True, "path": str(output), "width": shot.size[0], "height": shot.size[1],
            "note": "当前版本仅保存截图文件，图像内容暂不进入对话"}


def active_window() -> dict[str, Any]:
    if os.name != "nt":
        return {"ok": False, "error": "当前平台不支持前台窗口查询"}
    user32 = getattr(ctypes, "windll", None)
    if user32 is None:
        return {"ok": False, "error": "当前平台不支持前台窗口查询"}
    try:
        handle = user32.GetForegroundWindow()
        if not handle:
            return {"ok": False, "error": "无法获取前台窗口"}
        length = user32.GetWindowTextLengthW(handle)
        buffer = ctypes.create_unicode_buffer(max(int(length), 1) + 1)
        user32.GetWindowTextW(handle, buffer, len(buffer))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"窗口查询失败：{exc}"}
    return {"ok": True, "title": buffer.value.strip() or "（无标题）"}


def clipboard_read() -> dict[str, Any]:
    try:
        import pyperclip
    except ImportError:
        return {"ok": False, "error": "剪贴板依赖 pyperclip 未安装（pip install pyperclip）"}
    try:
        text = pyperclip.paste()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"剪贴板不可用：{exc}"}
    if not text:
        return {"ok": False, "error": "剪贴板为空或不是文本"}
    content = text[:MAX_CLIPBOARD_CHARS]
    if len(text) > MAX_CLIPBOARD_CHARS:
        content += "…（内容已截断）"
    return {"ok": True, "content": content}


REGISTRY: tuple[Tool, ...] = (
    Tool(
        name="get_time",
        description="获取当前本地日期、时间、星期。回答“现在几点”“今天几号”一类问题时使用。无参数。",
        parameters={"type": "object", "properties": {}, "required": []},
        func=get_time,
    ),
    Tool(
        name="read_file",
        description=(
            "读取本地文本文件内容。path 必须是绝对路径；超过 64KB 会截断。"
            "只允许访问允许目录内的文件，超出范围会返回错误。"
        ),
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "文件的绝对路径"}},
            "required": ["path"],
        },
        func=read_file,
    ),
    Tool(
        name="list_dir",
        description="列出本地目录内容（名称、类型、大小），最多 200 项。path 必须是绝对路径。",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "目录的绝对路径"}},
            "required": ["path"],
        },
        func=list_dir,
    ),
    Tool(
        name="screenshot",
        description="截取主显示器画面并保存为 PNG，返回文件路径。注意：图像内容不会提供给模型，仅保存文件。",
        parameters={"type": "object", "properties": {}, "required": []},
        func=screenshot,
    ),
    Tool(
        name="active_window",
        description="获取当前前台窗口的标题（仅 Windows）。用于了解用户正在使用什么程序。",
        parameters={"type": "object", "properties": {}, "required": []},
        func=active_window,
    ),
    Tool(
        name="clipboard_read",
        description="读取系统剪贴板中的文本，最多 16000 字符。",
        parameters={"type": "object", "properties": {}, "required": []},
        func=clipboard_read,
    ),
)


def build_tool_registry() -> dict[str, Tool]:
    return {tool.name: tool for tool in REGISTRY}


def openai_tools_schema(registry: dict[str, Tool]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in registry.values()
    ]


async def execute_tool(registry: dict[str, Tool], name: str, arguments: Any) -> dict[str, Any]:
    tool = registry.get(str(name or "").strip())
    if tool is None:
        return {"ok": False, "error": f"未知工具：{name}"}
    if not isinstance(arguments, dict):
        arguments = {}
    missing = [key for key in tool.parameters.get("required", []) if key not in arguments]
    if missing:
        return {"ok": False, "error": f"缺少参数：{'、'.join(missing)}"}
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(tool.func, **arguments), TOOL_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return {"ok": False, "error": f"工具 {tool.name} 执行超时"}
    except TypeError as exc:
        return {"ok": False, "error": f"参数无效：{exc}"}
    except Exception as exc:  # noqa: BLE001 - tool boundary must not crash the loop
        return {"ok": False, "error": str(exc)[:300]}
