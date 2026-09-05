"""zcode (T1): write_file tool tests — atomic, sandbox-scoped, encoding-safe."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.tools import write_file  # noqa: E402


class WriteRootTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patcher = mock.patch.dict(os.environ, {"ANIME_AGENT_WRITE_ROOTS": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_overwrite_creates_file(self):
        result = write_file(str(self.root / "note.txt"), "你好，天依")
        self.assertTrue(result["ok"], result)
        self.assertEqual((self.root / "note.txt").read_text(encoding="utf-8"), "你好，天依")

    def test_append_preserves_and_separates(self):
        target = self.root / "log.txt"
        target.write_text("第一行", encoding="utf-8")
        result = write_file(str(target), "第二行", mode="append")
        self.assertTrue(result["ok"], result)
        self.assertEqual(target.read_text(encoding="utf-8"), "第一行\n第二行")

    def test_special_chars_and_emoji_roundtrip(self):
        content = "曌丨生僻字 🈶🈚️ emoji \"引号\" and \\backslash\\"
        target = self.root / "special.txt"
        self.assertTrue(write_file(str(target), content)["ok"])
        self.assertEqual(target.read_text(encoding="utf-8"), content)

    def test_no_bom_written(self):
        target = self.root / "bom.txt"
        self.assertTrue(write_file(str(target), "无BOM")["ok"])
        self.assertNotEqual(target.read_bytes()[:3], b"\xef\xbb\xbf")


class WriteBoundaryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patcher = mock.patch.dict(os.environ, {"ANIME_AGENT_WRITE_ROOTS": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_traversal_denied(self):
        result = write_file(str(self.root / ".." / "escape.txt"), "x")
        self.assertFalse(result["ok"])

    def test_outside_roots_denied(self):
        with tempfile.TemporaryDirectory() as other:
            result = write_file(str(Path(other) / "outside.txt"), "x")
            self.assertFalse(result["ok"])

    def test_no_roots_configured_disables_writing(self):
        with mock.patch.dict(os.environ, {"ANIME_AGENT_WRITE_ROOTS": ""}):
            with tempfile.TemporaryDirectory() as tmp:
                result = write_file(str(Path(tmp) / "a.txt"), "x")
        self.assertFalse(result["ok"])
        self.assertIn("未启用", result["error"])

    def test_invalid_mode_rejected(self):
        result = write_file(str(self.root / "a.txt"), "x", mode="delete")
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
