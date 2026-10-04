"""Isolated unit evidence runner; no production config, data, microphone or TTS."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
for key in list(os.environ):
    if key.startswith(("ANIME_AGENT_", "LLM_", "GLM_", "DEEPSEEK_")):
        del os.environ[key]
with tempfile.TemporaryDirectory(prefix="tianyi-v1-unittest-") as tmp:
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(Path(tmp)/"absent.env"),ANIME_AGENT_DATA_DIR=tmp,
        ANIME_AGENT_TTS="0",ANIME_AGENT_WAKE_WORD="0",ANIME_AGENT_MCP_SERVERS="",LLM_PROVIDER="mock")
    sys.path.insert(0,str(ROOT/"services/agent-core"))
    from agent_core import main as core
    initial_store = core.memory
    suite=unittest.defaultTestLoader.discover(str(ROOT/"services/agent-core/tests"), pattern=sys.argv[1] if len(sys.argv)>1 else "test*.py")
    started=time.monotonic()
    result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=1).run(suite)
    summary={"tests":result.testsRun,"seconds":round(time.monotonic()-started,3),"ok":result.wasSuccessful(),
             "failures":[{"id":t.id(),"detail":str(e)[:2400]} for t,e in result.failures+result.errors]}
    out=ROOT/"docs/assessments/harness-v1/evidence/unit"/f"{time.time_ns()}.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(summary,ensure_ascii=False,indent=2).replace(tmp,"{TEMP}").replace(str(ROOT),"{SOURCE}")
    out.write_text(text,encoding="utf-8")
    print(json.dumps({"tests":summary["tests"],"seconds":summary["seconds"],"ok":summary["ok"],
                      "failed":[x["id"] for x in summary["failures"]],"evidence":out.relative_to(ROOT).as_posix()},ensure_ascii=False))
    initial_store.close()
    raise SystemExit(not result.wasSuccessful())
