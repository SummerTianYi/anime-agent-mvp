"""Publish a fresh sanitized projection; never rewrite the retained first run."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from models import public_messages, score_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    raw = args.private_run.read_bytes()
    record = json.loads(raw)
    original_hash = hashlib.sha256(raw).hexdigest()
    history = []
    for case in record["cases"]:
        db = args.private_run.parent / case["id"] / "db/anime-agent.sqlite3"
        with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id", (case["session_id"],)).fetchall()
        expected = [{"role": m["role"], "content": m["content"]} for m in case["reopened_messages"]]
        history.append({"case": case["id"], "messages": len(rows), "same_as_first_reopen": [dict(row) for row in rows] == expected,
                        "db_sha256": hashlib.sha256(db.read_bytes()).hexdigest()})
        case["first_score_preserved"] = case["passed"]
        case["rescored_final_assertions"] = bool(score_case(case))
        case["reopened_messages"] = public_messages(case["reopened_messages"])
    for call in record["calls"]:
        call["messages"] = public_messages(call["messages"])
        if "response" in call:
            response = call["response"]
            projected = public_messages([{**response, "role": "assistant"}])[0]
            call["response"] = {"content": projected.get("content"), "tool_calls": projected.get("tool_calls", []),
                                "finish_reason": response.get("finish_reason")}
    record["publication"] = {"original_private_sha256": original_hash, "first_scores_unchanged": True,
        "reasoning_projection": "Only message/tool function whitelist; separate reasoning omitted; assistant tool-call prose omitted; known think-delimited prefixes removed.",
        "count_caveat": "23 observed _request entries; first-run redirect dispatches were not instrumented, so exact wire count and hard cap cannot be independently proven.",
        "no_more_live_requests": True, "live_run_is_final_source": False}
    source = args.source_root / "services/agent-core/agent_core"
    manifest = {"baseline_commit": "463cbdd647cda728e5e4bded928f59216a3d2cb1",
        "final_business_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.py")},
        "first_live_business_sha256": record["source_sha256"],
        "history": history, "history_all_equal": all(h["same_as_first_reopen"] for h in history)}
    if hashlib.sha256(args.private_run.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("Historical input changed during export")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (("models-initial.json", record), ("manifest.json", manifest)):
        with (args.output_dir / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"cases": len(record["cases"]), "observed_requests": len(record["calls"]),
        "first_passes": sum(c["passed"] for c in record["cases"]),
        "reassessed_passes": sum(c["rescored_final_assertions"] for c in record["cases"]),
        "history_all_equal": manifest["history_all_equal"]}))


if __name__ == "__main__":
    main()
