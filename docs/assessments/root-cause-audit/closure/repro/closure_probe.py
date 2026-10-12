"""Closure probes against explicit reviewed source; no Core/import/start/network.
python -B closure_probe.py --source-root <audit checkout>
stdout contains synthetic observations, not a pass certificate. Run only offline.
"""
from __future__ import annotations
import argparse
import ast
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

sys.dont_write_bytecode = True

def extract(path, names, namespace):
    raw = path.read_bytes()
    tree = ast.parse(raw, filename=str(path))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in names]
    if len(nodes) != len(names) or {n.name for n in nodes} != set(names):
        raise RuntimeError("Source structure changed; review extraction")
    for node in nodes:
        if node.decorator_list:
            raise RuntimeError("Unexpected decorator")
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return hashlib.sha256(raw).hexdigest()

async def run(root, base):
    core = root / "services/agent-core/agent_core"
    ns = dict(Any=Any, Path=Path, os=os, time=time, asyncio=asyncio, Tool=object)
    sources = {}
    sources["tools.py"] = extract(core/"tools.py", ["write_file", "execute_tool"], ns)
    def resolve(raw):
        p = Path(raw).resolve()
        if not p.is_relative_to(base):
            raise ValueError("outside synthetic directory")
        return p
    ns.update(_resolve_write_path=resolve, MAX_WRITE_BYTES=65536)
    target = base/"write.txt"
    good = ns["write_file"](str(target), "CLOSURE-normal")
    assert good["ok"] is True and target.read_bytes() == b"CLOSURE-normal"
    read_bytes = Path.read_bytes
    def fail_target_read(p):
        if p == target:
            raise OSError("synthetic post-replace read failure")
        return read_bytes(p)
    with patch.object(Path, "read_bytes", fail_target_read):
        unknown = ns["write_file"](str(target), "CLOSURE-written")
    actual = target.read_bytes()
    assert actual == b"CLOSURE-written"
    assert unknown.get("outcome") == "unknown"

    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    late = base/"late.txt"
    def worker():
        try:
            entered.set()
            if not release.wait(3):
                raise RuntimeError("probe release missing")
            late.write_bytes(b"CLOSURE-late")
            return {"ok": True}
        finally:
            finished.set()
    registry = {"synthetic": SimpleNamespace(name="synthetic", parameters={}, timeout=0.1, func=worker)}
    try:
        timed = await ns["execute_tool"](registry, "synthetic", {})
        if not entered.is_set():
            raise RuntimeError("worker never started; invalid observation")
        before = late.exists()
        release.set()
        if not await asyncio.to_thread(finished.wait, 3):
            raise RuntimeError("worker did not settle")
        late_bytes = late.read_bytes()
    finally:
        release.set()
    assert timed.get("outcome") == "unknown"
    assert before is False and late_bytes == b"CLOSURE-late"
    result = {
        "layer": "isolated actual functions; no desktop or live services",
        "sources_sha256": sources,
        "model_calls": 0,
        "normal_write": {"ok": good["ok"], "verified": good.get("verified_readback")},
        "write_then_read_failure": {"outcome": unknown["outcome"], "artifact": actual.decode()},
        "late_worker": {"returned": timed, "artifact_before_release": before, "artifact_after": late_bytes.decode()},
        "limits": ["Does not execute ActionLedger or Godot routing.", "No proof of live deployment or database identity.", "No deadline race stress test."]
    }
    result["fixture_cleanup_owner"] = "probe TemporaryDirectory, not product write_file"
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError("Optimized Python disables probe assertions")
    with tempfile.TemporaryDirectory(prefix="tianyi-closure-") as td:
        result = asyncio.run(run(args.source_root.resolve(), Path(td).resolve()))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
