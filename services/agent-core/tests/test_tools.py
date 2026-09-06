from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from agent_core.tools import (
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
