"""Reduce a verified transaction snapshot to registered synthetic R2 evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--human-audio", default="not confirmed")
    parser.add_argument("--allow-user-text", action="append", default=[], help="Exact synthetic input reviewed and registered by the auditor")
    args = parser.parse_args()
    identity = json.loads((args.snapshot_dir / "identity.json").read_text(encoding="utf-8"))
    snapshot = args.snapshot_dir / "transaction-snapshot.sqlite3"
    if identity["status"] != "captured" or hashlib.sha256(snapshot.read_bytes()).hexdigest() != identity["snapshot_sha256"]:
        raise RuntimeError("Unverified snapshot; extraction refused")
    db = sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    sessions = [row[0] for row in db.execute("SELECT DISTINCT conversation_id FROM messages WHERE role='user' AND content LIKE '[R2-%'")]
    messages, facts, actions = [], [], []
    for session in sessions:
        rows = [dict(row) for row in db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (session,))]
        if any(row["role"] == "user" and not (row["content"].startswith("[R2-") or row["content"] in {"确认", "取消", "不同意", "继续"} or row["content"] in args.allow_user_text) for row in rows):
            raise RuntimeError(f"Session {session} contains unregistered user input; review required")
        messages.extend(rows)
        facts.extend(dict(row) for row in db.execute("SELECT * FROM facts WHERE session_id=?", (session,)))
        actions.extend(json.loads(row[0]) for row in db.execute("SELECT payload FROM harness_actions WHERE session_id=?", (session,)))
    requests = {row["request_id"] for row in messages} - {None, ""}
    events, candidate_events = [], []
    for row in db.execute("SELECT * FROM events WHERE id>7352 ORDER BY id"):
        try:
            payload = json.loads(row["payload"])
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        item = {**dict(row), "payload": payload}
        candidate_events.append(item)
        if payload.get("request_id", payload.get("requestId")) in requests or payload.get("session_id") in sessions:
            events.append(item)
    utterances = {item["payload"].get("utteranceId") for item in events} - {None}
    ids = {item["id"] for item in events}
    events.extend(item for item in candidate_events if item["id"] not in ids and item["payload"].get("utteranceId") in utterances)
    calls = {}
    for item in events:
        if item["event_type"] == "provider.transport":
            payload = item["payload"]
            calls[payload["call_id"]] = max(calls.get(payload["call_id"], 0), payload["attempt"])
    result = {"schema": "round02-desktop-v1", "layer": "current Godot foreground input + verified SQLite transaction snapshot",
              "explicitly_registered_synthetic_inputs": args.allow_user_text,
              "sessions": sessions, "messages": messages, "events": events, "facts": facts, "actions": actions,
              "snapshot_sha256": identity["snapshot_sha256"], "source_identity": {k: identity["normal_identity"][k] for k in ("volume_serial", "file_index")},
              "captured_utc": identity["utc"], "human_audio": args.human_audio,
              "http_attempts_observed": sum(calls.values()), "calls": calls}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "OWNER_TEST_MAILBOX", text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(text)
    print(json.dumps({"sessions": sessions, "last_message_ids": [row["id"] for row in messages[-2:]], "http": sum(calls.values()),
                      "event_types": [row["event_type"] for row in events]}, ensure_ascii=False))
    db.close()


if __name__ == "__main__":
    main()
