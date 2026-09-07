from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from agent_core import tools as tools_mod
from agent_core.tools import (
    Tool,
    active_window,
    build_tool_registry,
    clipboard_read,
    execute_tool,
    get_time,
    list_dir,
    openai_tools_schema,
    read_file,
    screenshot,
)


_OLD_ROOTS_ENV = None


def setUpModule() -> None:
    """Pin default roots: other tests import agent_core.main, whose
    load_dotenv may set ANIME_AGENT_TOOLS_ROOTS to a narrow exam sandbox."""
    global _OLD_ROOTS_ENV
    _OLD_ROOTS_ENV = os.environ.pop("ANIME_AGENT_TOOLS_ROOTS", None)


def tearDownModule() -> None:
    if _OLD_ROOTS_ENV is not None:
        os.environ["ANIME_AGENT_TOOLS_ROOTS"] = _OLD_ROOTS_ENV


class ToolRegistryTests(unittest.TestCase):
    def test_schema_is_wellformed(self) -> None:
        registry_map = build_tool_registry()
        schema = openai_tools_schema(registry_map)
        self.assertEqual(len(schema), 9)  # 6 read-only + write_file + run_command + look_at_screen
        for entry in schema:
            self.assertEqual(entry["type"], "function")
            self.assertIn(entry["function"]["name"], registry_map)
            self.assertEqual(entry["function"]["parameters"]["type"], "object")

    def test_get_time_returns_parseable_fields(self) -> None:
        result = get_time()
        self.assertTrue(result["ok"])
        self.assertRegex(result["local_time"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertIn(result["weekday"], "一二三四五六日")


class ReadFileTests(unittest.TestCase):
    def test_reads_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "hello.txt"
            target.write_text("你好，天依", encoding="utf-8")
            result = read_file(str(target))
        self.assertTrue(result["ok"])
        self.assertIn("天依", result["content"])

    def test_truncates_large_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "big.txt"
            target.write_text("天" * (128 * 1024), encoding="utf-8")
            result = read_file(str(target))
        self.assertTrue(result["ok"])
        self.assertLess(len(result["content"]), 128 * 1024)
        self.assertIn("截断", result["content"])

    def test_rejects_relative_path(self) -> None:
        result = read_file("relative/path.txt")
        self.assertFalse(result["ok"])

    def test_rejects_path_outside_allowed_roots(self) -> None:
        result = read_file("C:/Program Files/Windows Defender/settings.txt")
        self.assertFalse(result["ok"])

    def test_rejects_dotdot_escape_from_allowed_root(self) -> None:
        import os

        home = os.getenv("USERPROFILE", str(Path.home()))
        result = read_file(f"{home}/../../Windows/win.ini")
        self.assertFalse(result["ok"])

    def test_allows_user_profile_descendant(self) -> None:
        import os

        home = os.getenv("USERPROFILE", str(Path.home()))
        result = list_dir(f"{home}/Desktop")
        self.assertTrue(result["ok"], result.get("error"))

    def test_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = read_file(str(Path(tmp) / "missing.txt"))
        self.assertFalse(result["ok"])


class ListDirTests(unittest.TestCase):
    def test_lists_entries_dirs_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            (root / "a.txt").write_text("x", encoding="utf-8")
            result = list_dir(str(root))
        self.assertTrue(result["ok"])
        names = [item["name"] for item in result["entries"]]
        self.assertIn("sub", names)
        self.assertIn("a.txt", names)
        self.assertEqual(names.index("sub"), 0)

    def test_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = list_dir(str(Path(tmp) / "nope"))
        self.assertFalse(result["ok"])


class DegradedToolTests(unittest.TestCase):
    def test_screenshot_without_mss(self) -> None:
        saved = sys.modules.get("mss")
        sys.modules["mss"] = None
        try:
            result = screenshot()
        finally:
            if saved is None:
                sys.modules.pop("mss", None)
            else:
                sys.modules["mss"] = saved
        self.assertFalse(result["ok"])

    def test_clipboard_without_pyperclip(self) -> None:
        saved = sys.modules.get("pyperclip")
        sys.modules["pyperclip"] = None
        try:
            result = clipboard_read()
        finally:
            if saved is None:
                sys.modules.pop("pyperclip", None)
            else:
                sys.modules["pyperclip"] = saved
        self.assertFalse(result["ok"])

    def test_active_window_off_windows(self) -> None:
        import unittest.mock

        with unittest.mock.patch("os.name", "posix"):
            result = active_window()
        self.assertFalse(result["ok"])


class ExecuteToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_tool(self) -> None:
        result = await execute_tool(build_tool_registry(), "nope", {})
        self.assertFalse(result["ok"])

    async def test_missing_required_argument(self) -> None:
        result = await execute_tool(build_tool_registry(), "read_file", {})
        self.assertFalse(result["ok"])
        self.assertIn("path", result["error"])

    async def test_success_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "x.txt"
            target.write_text("data", encoding="utf-8")
            result = await execute_tool(build_tool_registry(), "read_file", {"path": str(target)})
        self.assertTrue(result["ok"])

    async def test_tool_exception_becomes_error_result(self) -> None:
        result = await execute_tool(build_tool_registry(), "get_time", {"unexpected": 1})
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()


# zcode (2026-09-07): per-tool execution timeout — vision tools need more than
# the 15s default; the live T-chain showed look_at_screen dying at exactly 15s
# inside execute_tool while its own HTTP budget is 60s.
class PerToolTimeout(unittest.TestCase):
    def _tool(self, name, func, timeout=None):
        kwargs = {"name": name, "description": "d", "parameters": {"type": "object", "properties": {}}, "func": func}
        if timeout is not None:
            kwargs["timeout"] = timeout
        return Tool(**kwargs)

    def test_look_at_screen_registered_with_extended_timeout(self):
        registry = build_tool_registry()
        self.assertGreaterEqual(registry["look_at_screen"].timeout, 60.0)
        self.assertEqual(registry["get_time"].timeout, tools_mod.TOOL_TIMEOUT_SECONDS)

    def test_execute_tool_respects_per_tool_timeout(self):
        def slow(**_):
            time.sleep(0.6)
            return {"ok": True}

        def quick(**_):
            return {"ok": True}

        registry = {
            "slow_small": self._tool("slow_small", slow, timeout=0.1),
            "slow_big": self._tool("slow_big", slow, timeout=5.0),
            "quick_default": self._tool("quick_default", quick),
        }
        failed = asyncio.run(execute_tool(registry, "slow_small", {}))
        self.assertFalse(failed["ok"])
        self.assertIn("超时", failed["error"])
        passed = asyncio.run(execute_tool(registry, "slow_big", {}))
        self.assertTrue(passed["ok"])
        passed_default = asyncio.run(execute_tool(registry, "quick_default", {}))
        self.assertTrue(passed_default["ok"])


# zcode (2026-09-07): Windows spawn resolution — MCP host must resolve bare
# executables (npx/npm/python) through PATH+PATHEXT or create_subprocess_exec
# fails with WinError 2 on Windows.
class McpCommandResolutionTests(unittest.TestCase):
    def test_bare_npx_resolves_to_absolute_path(self):
        from agent_core.mcp_host import _resolve_command

        resolved = _resolve_command(["npx", "-y", "some-package"])
        self.assertNotEqual(resolved[0].lower(), "npx")
        self.assertIn("npx", resolved[0].lower())
        self.assertTrue(Path(resolved[0]).is_absolute())
        self.assertEqual(resolved[1:], ["-y", "some-package"])

    def test_unknown_command_passes_through(self):
        from agent_core.mcp_host import _resolve_command

        self.assertEqual(_resolve_command(["definitely-not-a-real-exe-xyz", "a"]), ["definitely-not-a-real-exe-xyz", "a"])

    def test_absolute_path_untouched(self):
        from agent_core.mcp_host import _resolve_command

        exe = sys.executable
        self.assertEqual(_resolve_command([exe, "-c", "1"]), [exe, "-c", "1"])
