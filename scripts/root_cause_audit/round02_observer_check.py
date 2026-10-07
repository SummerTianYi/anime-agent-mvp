"""Isolated observer privacy/identity/exception tests plus affected regressions."""
import asyncio
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[2]
for key in list(os.environ):
    if key.startswith(("ANIME_AGENT_", "LLM_", "GLM_", "DEEPSEEK_")):
        del os.environ[key]
with tempfile.TemporaryDirectory(prefix="r2-observer-check-") as tmp:
    os.environ.update(ANIME_AGENT_CONFIG_PATH=str(Path(tmp) / "absent.env"), ANIME_AGENT_DATA_DIR=tmp,
                      ANIME_AGENT_TTS="0", ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_MCP_SERVERS="", LLM_PROVIDER="mock")
    sys.path.insert(0, str(ROOT / "services/agent-core"))
    from agent_core import main as core
    initial_memory = core.memory
    import round02_observer as observer
    control = Path(tmp) / "control.json"
    control.write_text(json.dumps({"enabled": True, "expires_epoch": time.time() + 180}), encoding="utf-8")
    observer.install_core(core, tmp)
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    private = "PRIVATE_REASONING_SENTINEL_92"
    payload = {"id": "synthetic", "reasoning": private, "choices": [{"index": 0, "finish_reason": "stop", "message": {
        "role": "assistant", "content": "正常回复", "reasoning_content": private, "reasoning_details": [{"text": private}]}}],
        "content": [{"type": "thinking", "thinking": private}, {"type": "text", "text": "普通文本"}]}
    reduced = observer.wire_response(payload)
    check("wire response excludes private reasoning", private not in json.dumps(reduced))
    check("wire preserves raw answer and finish reason", reduced["choices"][0]["message"]["content"] == "正常回复" and reduced["choices"][0]["finish_reason"] == "stop")
    request = observer.wire_request({"messages": [{"role": "system", "content": "EXISTING_PRIVATE_MEMORY_SENTINEL"}], "model": "synthetic"})
    check("request context represented without private body", "EXISTING_PRIVATE_MEMORY_SENTINEL" not in json.dumps(request) and len(request["messages_sha256"]) == 64)
    check("nested typed reasoning excluded", private not in json.dumps(observer.safe({"content": [{"type": "reasoning", "text": private}]})))
    singleton = object()
    failure = ValueError("synthetic exception")
    calls = []
    async def original(value):
        calls.append(value)
        if value == "fail":
            raise failure
        return singleton
    probe = types.SimpleNamespace(fn=original)
    observer.observe_async(probe, "fn", "synthetic")
    token = observer.TRACE.set({"request_id": "r2-isolated"})
    check("same return object", asyncio.run(probe.fn("ok")) is singleton)
    try:
        asyncio.run(probe.fn("fail"))
    except ValueError as exc:
        check("same exception object", exc is failure)
    check("one original call per wrapper", calls == ["ok", "fail"])
    tracefile = next(Path(tmp).glob("trace-*.jsonl"))
    before = tracefile.read_bytes()
    control.write_text('{"enabled":false}', encoding="utf-8")
    observer.emit("disabled", {"text": "MUST_NOT_RECORD"})
    check("disable leaves trace unchanged", tracefile.read_bytes() == before)
    control.write_text('[]', encoding="utf-8")
    check("nonobject control safely disables", observer.enabled() is False)
    control.write_text(json.dumps({"enabled": True, "expires_epoch": time.time() + 180}), encoding="utf-8")
    observer.TRACE.reset(token)
    observer.emit("unmarked", {"text": "MUST_NOT_RECORD"})
    check("unmarked leaves trace unchanged", tracefile.read_bytes() == before)
    suite = unittest.TestSuite()
    patterns = ["test_harness_v1_*.py", "test_agent_loop.py", "test_harness.py", "test_provider.py", "test_anthropic_provider.py", "test_effort.py", "test_speech_parts.py", "test_memory_promotion.py"]
    for pattern in patterns:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / "services/agent-core/tests"), pattern=pattern))
    stream = io.StringIO()
    start = time.monotonic()
    result = unittest.TextTestRunner(stream=stream).run(suite)
    report = {"layer": "isolated synthetic; no model/network/desktop", "observer_checks": checks,
              "tests": result.testsRun, "ok": result.wasSuccessful(), "seconds": round(time.monotonic()-start, 3),
              "failures": [{"id": t.id(), "detail": e.replace(tmp, "{TEMP}").replace(str(ROOT), "{SOURCE}")} for t,e in result.errors+result.failures]}
    output = ROOT / "docs/assessments/root-cause-audit/round-02/evidence/observer-check-v2.json"
    with output.open("x", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
    print(json.dumps({k:v for k,v in report.items() if k != "failures"}, ensure_ascii=False))
    print("Failures:", [x["id"] for x in report["failures"]])
    core.memory.close()
    initial_memory.close()
    raise SystemExit(not result.wasSuccessful())
