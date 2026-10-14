"""Independent scope regressions through isolated actual Core chat."""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.data_dir.exists() or args.output.exists():
        raise SystemExit("Refusing to overwrite previous evidence")
    args.data_dir = args.data_dir.resolve()
    args.data_dir.mkdir(parents=True)
    root = Path(__file__).resolve().parents[5]
    package = root / "services/agent-core"
    tests = package / "tests"
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(package), str(tests)]
    os.environ.update(ANIME_AGENT_DATA_DIR=str(args.data_dir / "import-db"),
        ANIME_AGENT_CONFIG_PATH=str(args.data_dir / "absent.env"), ANIME_AGENT_TTS="0",
        ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_MCP_SERVERS="", LLM_PROVIDER="mock")
    paths = list((package / "agent_core").glob("*.py")) + [Path(__file__),
        tests / "test_issue_adversarial.py", tests / "issue_fixture.py",
        tests / "test_a4_pilot.py", tests / "test_harness_v1_integration.py"]

    def hashes():
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

    before = hashes()
    from agent_core import main as core
    from agent_core.tools import openai_tools_schema
    from test_a4_pilot import call, final
    from test_issue_adversarial import IssueAdversarialTests

    original = core.memory

    class ScopeTests(unittest.IsolatedAsyncioTestCase):
        setUp = IssueAdversarialTests.setUp
        chat = IssueAdversarialTests.chat
        write = IssueAdversarialTests.write

        async def test_original_a4_no_readback_request_keeps_generic_path(self):
            path = self.root / "legacy-a4.txt"
            registry = {k: v for k, v in core.tool_registry.items() if k == "write_file"}
            with patch.object(core, "tools_schema", openai_tools_schema(registry)):
                await self.chat("修改合成Issue标题", [call("write_file", path=str(path), content="legacy-synthetic")])
                self.assertNotIn("issue_contract", core._task_state[self.sid])
                pending = core._sync_pending(self.sid)
                self.assertEqual(len(pending), 1)
                self.assertFalse(path.exists())
                answer, _ = await self.chat("确认", [final("完成", "report", action_refs=[pending[0]["action_id"]])])
            self.assertEqual(path.read_text(encoding="utf-8"), "legacy-synthetic")
            self.assertIn("执行成功", answer)
            self.assertFalse(self.server.calls)

        async def test_readback_words_inside_title_do_not_activate_workflow(self):
            self.title = "读取核验 READY-17"
            text = (f"请把仓库 {self.target['owner']}/{self.target['repo']} 的 Issue #17 "
                    f"标题改为「{self.title}」，其他字段保持不变。")
            await self.chat(text, [self.write()])
            self.assertNotIn("issue_contract", core._task_state[self.sid])
            pending = core._sync_pending(self.sid)
            self.assertEqual(len(pending), 1)
            self.assertEqual(self.server.writes, 0)
            answer, _ = await self.chat("确认", [final("完成", "report", action_refs=[pending[0]["action_id"]])])
            self.assertEqual(self.server.issue, {**self.server.initial, "title": self.title})
            self.assertEqual([c["tool"] for c in self.server.calls], ["issue_write"])
            self.assertIn("执行成功", answer)

        async def test_explicitly_unneeded_readback_keeps_generic_path(self):
            text = (f"请把仓库 {self.target['owner']}/{self.target['repo']} 的 Issue #17 "
                    f"标题改为「{self.title}」，无需重新读取，其他字段保持不变。")
            await self.chat(text, [self.write()]*2)
            self.assertNotIn("issue_contract", core._task_state[self.sid])
            pending = core._sync_pending(self.sid)
            self.assertEqual(len(pending), 1)
            self.assertEqual(self.server.writes, 0)
            await self.chat("确认", [final("完成", "report", action_refs=[pending[0]["action_id"]])])
            self.assertEqual(self.server.issue, {**self.server.initial, "title": self.title})
            self.assertEqual([c["tool"] for c in self.server.calls], ["issue_write"])

    stream = io.StringIO()
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(ScopeTests))
    finally:
        original.close()
    after = hashes()
    record = {"scope": "actual handle_chat; controlled providers; isolated persistence and synthetic transport",
        "tests": result.testsRun, "passed": result.wasSuccessful() and before == after,
        "failures": [{"test": t.id(), "trace": s} for t, s in result.failures],
        "errors": [{"test": t.id(), "trace": s} for t, s in result.errors],
        "source_sha256_before": before, "source_sha256_after": after,
        "source_unchanged": before == after, "model_calls": 0, "external_business_calls": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(record, output, ensure_ascii=False, indent=2)
    (args.data_dir / "runner.txt").write_text(stream.getvalue(), encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if not k.startswith("source_sha256")}, ensure_ascii=False))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
