"""Run the same gated avatar/client counterexample against the baseline and checkout."""
import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
BASE = "75b78f271ecd2d4c1b8bd8d51e621c621410ed3b"
SPEECH = "services/agent-core/agent_core/speech.py"


def run(output):
    with tempfile.TemporaryDirectory() as name:
        scratch = Path(name)
        os.environ.update(ANIME_AGENT_CONFIG_PATH=str(scratch/"absent.env"), ANIME_AGENT_DATA_DIR=name,
                          LLM_PROVIDER="mock",ANIME_AGENT_TTS="0",ANIME_AGENT_WAKE_WORD="0",ANIME_AGENT_MCP_SERVERS="")
        sys.path[:0] = [str(ROOT/"services/agent-core"),str(ROOT/"services/agent-core/tests")]
        from test_speech_priority import load_failure_trace
        from agent_core import main as core
        path = scratch / "baseline_speech.py"
        path.write_bytes(subprocess.check_output(["git","show",f"{BASE}:{SPEECH}"],cwd=ROOT))
        spec = importlib.util.spec_from_file_location("baseline_speech", path)
        old = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = old
        spec.loader.exec_module(old)
        try:
            before = asyncio.run(load_failure_trace(old.SpeechManager))
            after = asyncio.run(load_failure_trace())
            assert before["synthesis"] == ["甲。","乙。","丙。","甲。"]
            assert after["synthesis"] == ["甲。","乙。","甲。","丙。"]
            assert before["peakWorkers"] == after["peakWorkers"] == 1
            output.write_text(json.dumps(dict(before=before,after=after),ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        finally:
            core.memory.close()


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    run(p.parse_args().output)
