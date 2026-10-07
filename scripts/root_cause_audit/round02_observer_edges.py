"""Reproduce independently reported observer edge cases without runtime I/O."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import round02_observer as observer

checks = []
with tempfile.TemporaryDirectory(prefix="r2-observer-edges-") as temp:
    root = Path(temp)
    (root / "control.json").write_text(json.dumps({"enabled": True, "expires_epoch": time.time()+60}), encoding="utf-8")
    value = object()
    original_error = RuntimeError("synthetic failure")
    calls = []
    class Voice:
        def run(self, text, *args, **kwargs):
            calls.append((text, args, kwargs))
            if kwargs.get("fail"):
                raise original_error
            return value
    observer.install_tts(types.SimpleNamespace(VoiceSelfCheck=Voice), temp)
    fingerprint = hashlib.sha256("合成".encode()).hexdigest()
    rows = [{"sha256": fingerprint, "epoch": time.time(), "trace": {"request_id": request}} for request in ("A", "B")]
    (root / "tts-allow.jsonl").write_text("\n".join(json.dumps(x) for x in rows)+ '\nnull\n[]\n42\n{"epoch":"bad"}\n{broken', encoding="utf-8")
    saved_stdout = sys.stdout
    closed = io.StringIO()
    closed.close()
    try:
        for stream in (None, closed):
            sys.stdout = stream
            before = len(calls)
            assert Voice().run("合成", 1.0) is value
            assert len(calls) == before+1 and observer.TRACE.get() is None
        checks.append("None/closed stdout preserves original call, return object and TRACE reset")
        try:
            Voice().run("合成", fail=True)
        except RuntimeError as exc:
            assert exc is original_error and observer.TRACE.get() is None
            checks.append("original exception object and TRACE reset preserved")
    finally:
        sys.stdout = saved_stdout
    trace = [json.loads(line) for line in next(root.glob("trace-*.jsonl")).read_text(encoding="utf-8").splitlines()]
    sidecar = next(row for row in trace if row["stage"] == "tts.sidecar.in")
    assert sidecar["trace"]["request_id"] == "ambiguous-tts-text"
    assert {x["request_id"] for x in sidecar["trace"]["candidates"]} == {"A", "B"}
    checks.append("same text keeps both candidates, never attributes latest as certain")
    checks.append("malformed JSONL rows do not discard valid matches or block synthesis")
    for data in ([], None, 42, "bad", {"enabled": True, "expires_epoch": "bad"}):
        (root / "control.json").write_text(json.dumps(data), encoding="utf-8")
        assert observer.enabled() is False
    checks.append("non-object and invalid expiry control disable safely")
    assert observer.trace_for({"request_id": [], "utteranceId": {}}) is None
    checks.append("unhashable event identifiers do not change business outcome")
output = Path(__file__).resolve().parents[2] / "docs/assessments/root-cause-audit/round-02/evidence/observer-edges.json"
report = {"layer": "isolated synthetic observer counterexamples; no Core/TTS/service calls", "checks": checks, "ok": True,
          "observer_sha256": hashlib.sha256(Path(observer.__file__).read_bytes()).hexdigest()}
with output.open("x", encoding="utf-8") as file:
    json.dump(report, file, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False))
