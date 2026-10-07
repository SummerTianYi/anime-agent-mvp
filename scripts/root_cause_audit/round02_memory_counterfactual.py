"""Synthetic replay of the observed R2 memory correction; no production DB I/O."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--production", type=Path, required=True)
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    core = a.production / "services/agent-core/agent_core"
    source = (core / "main.py").read_bytes()
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"_auto_confirm_memory", "_fact_promotion_status"}:
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"_AUTO_CONFIRM_MEMORY_MARKERS", "_EXPLICIT_REMEMBER_MARKERS"} for t in node.targets):
            selected.append(node)
    assert len(selected) == 4
    scope = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "R2-memory-AST", "exec"), scope)
    spec = importlib.util.spec_from_file_location("r2_storage", core / "storage.py")
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    report = json.loads(a.trace.read_text(encoding="utf-8"))
    records = report["records"]
    correction = next(r for r in records if r["stage"] == "input" and r["data"]["text"].startswith("[R2-MEM05]"))
    rid = correction["trace"]["request_id"]
    candidate = next(r["data"]["memory_candidate"] for r in records if r["stage"] == "parse.out" and r["trace"]["request_id"] == rid)
    facts = [r["data"]["args"][0] for r in records if r["stage"] == "state.fact.in" and r["trace"]["request_id"] != rid]
    assert len(facts) == 3 and all("R2-" in f for f in [*facts, candidate])
    observations = []
    for suffix in ("", " 请记住。"):
        text = correction["data"]["text"] + suffix
        status = scope["_fact_promotion_status"](candidate, text)
        with tempfile.TemporaryDirectory(prefix="r2-memory-") as tmp:
            store = storage.MemoryStore(Path(tmp) / "synthetic.sqlite3")
            try:
                session = store.create_session("R2 synthetic correction")["id"]
                assert type(session) is int
                for content in facts:
                    store.add_fact(content, session_id=session, scope="global", status="confirmed")
                store.add_fact(candidate, session_id=session, scope="global" if status == "confirmed" else "session", status=status)
                rows = [dict(r) for r in store.connection.execute("SELECT fact_id,scope,status,content FROM facts ORDER BY fact_id")]
                observations.append({"appended_user_text": suffix, "promotion": status, "facts": rows, "other_session_recall": store.recall_facts(-1)})
            finally:
                store.close()
    assert [o["promotion"] for o in observations] == ["pending", "confirmed"]
    assert observations[0]["facts"][-1]["scope"] == "session"
    assert observations[1]["facts"][-1]["scope"] == "global"
    assert all(candidate not in text for text in observations[0]["other_session_recall"])
    assert candidate in observations[1]["other_session_recall"]
    assert all(r["status"] == "confirmed" for r in observations[0]["facts"][:-1])
    assert facts[0] in observations[0]["other_session_recall"]
    assert all(o["facts"][-1]["status"] == o["promotion"] for o in observations)
    out = {"schema": "r2-memory-counterfactual-v1", "layer": "actual AST and storage, temporary synthetic databases", "observations": observations, "model_api_calls": 0, "production_database_reads": 0, "source_sha256": {n: hashlib.sha256((core/n).read_bytes()).hexdigest() for n in ("main.py", "storage.py")}, "input_trace_sha256": hashlib.sha256(a.trace.read_bytes()).hexdigest(), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "limits": ["Does not rerun the model", "Candidate held identical; only explicit remember marker changes", "Temporary databases cleaned after capturing results"]}
    with a.output.open("x", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"cases": len(observations), "model_api_calls": 0}))


if __name__ == "__main__":
    main()
