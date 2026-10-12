"""Run actual selected source with isolated persistence; no servers/desktop."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--pattern", default="test_followup_delivery.py")
    a = p.parse_args()
    if a.output.exists() or a.data_dir.exists():
        raise SystemExit("Refusing to overwrite prior evidence")
    a.data_dir.mkdir(parents=True)
    sys.dont_write_bytecode = True
    package = (a.source_root / "services/agent-core").resolve()
    tests = Path(__file__).resolve().parents[5] / "services/agent-core/tests"
    sys.path[:0] = [str(package), str(tests)]
    os.environ.update(ANIME_AGENT_DATA_DIR=str(a.data_dir), ANIME_AGENT_CONFIG_PATH=str(a.data_dir/"absent.env"),
        ANIME_AGENT_TTS="0", ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_MCP_SERVERS="", LLM_PROVIDER="mock")
    from agent_core import main as core
    original = core.memory
    assert package in Path(core.__file__).resolve().parents
    stream = io.StringIO()
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                unittest.defaultTestLoader.discover(str(tests), pattern=a.pattern))
    finally:
        core.memory.close()
        original.close()
    record = {"scope":"isolated actual source; no desktop, models or active services",
        "source_sha256": {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (package/"agent_core").glob("*.py")},
        "tests": result.testsRun, "passed": result.wasSuccessful(),
        "failures": [{"test":t.id(), "trace":s} for t,s in result.failures],
        "errors": [{"test":t.id(), "trace":s} for t,s in result.errors],
        "skipped": [(t.id(), s) for t,s in result.skipped], "model_calls": 0}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (a.data_dir/"runner.txt").write_text(stream.getvalue(), encoding="utf-8")
    print(json.dumps({k:v for k,v in record.items() if k != "source_sha256"}, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
