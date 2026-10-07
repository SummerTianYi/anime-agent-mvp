"""R2 isolated branch observations, with explicit synthetic files and memory only.

No Core import, server, model, clipboard, screen or live database. All command
execution is mocked. Existing evidence files are never overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.production.resolve() / "services/agent-core"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    from agent_core import tools
    from agent_core import storage
    from agent_core.storage import MemoryStore
    for module in (tools, storage):
        expected = (source / "agent_core" / (module.__name__.split(".")[-1] + ".py")).resolve()
        if Path(module.__file__).resolve() != expected:
            raise RuntimeError("Imported implementation differs from selected source")

    rows = []

    def record(case, result, expected, passed):
        rows.append(dict(case=case, observed=result, expected=expected, matched=bool(passed)))

    with tempfile.TemporaryDirectory(prefix="tianyi-r2-branches-") as directory:
        root = Path(directory)
        with patch.dict(os.environ, {"ANIME_AGENT_TOOLS_ROOTS": str(root),
                                     "ANIME_AGENT_WRITE_ROOTS": str(root)}):
            # Force UTF-8's three-byte character across the actual 64 KiB cap.
            payload = "A" * 65535 + "蓝色纸鹤-END"
            file = root / "boundary.txt"
            file.write_text(payload, encoding="utf-8")
            first = tools.read_file(str(file))
            second = tools.read_file(str(file), first["next_offset"])
            record("read-byte-boundary", {"first_offset": first["offset"],
                "next_offset": first["next_offset"], "second_text": second["content"],
                "joined_sha256": hashlib.sha256((first["content"] + second["content"]).encode()).hexdigest()},
                "next=65535; exact joined UTF-8 payload", first["next_offset"] == 65535 and
                first["content"] + second["content"] == payload)
            for offset in (-1, True, "0", file.stat().st_size + 1):
                result = tools.read_file(str(file), offset)
                record("read-offset-" + repr(offset), result, "reject invalid byte offset", result.get("ok") is False)
            result = tools.read_file(str(file), file.stat().st_size)
            record("read-eof", result, "empty successful end, no next offset", result.get("ok") is True and
                   result["content"] == "" and result["next_offset"] is None)
            # Mid-character offsets are valid integers but cannot preserve text.
            result = tools.read_file(str(file), 65536)
            record("read-mid-character", result, "document observed decoding; not claimed rejected", "\ufffd" in result.get("content", ""))
            absent = tools.read_file(str(root / "absent.txt"))
            record("read-missing", absent, "missing file rejected", absent.get("ok") is False)
            listing = root / "listing"
            listing.mkdir()
            (listing / "Z-dir").mkdir()
            for number in range(201):
                (listing / f"f{number:03}.txt").write_text("R2", encoding="utf-8")
            result = tools.list_dir(str(listing))
            record("list-cap-sort", {"count": len(result["entries"]), "first": result["entries"][0],
                                     "last": result["entries"][-1], "truncated": result["truncated"]},
                   "200 entries, directories first, truncation explicit", len(result["entries"]) == 200 and
                   result["entries"][0]["type"] == "dir" and result["truncated"])
            target = root / "write.txt"
            for name, initial, addition, expected in (
                ("missing", None, "乙", "乙"), ("no-newline", "甲", "乙", "甲\n乙"),
                ("existing-newline", "甲\n", "乙", "甲\n乙"),
                ("content-newline", "甲", "\n乙", "甲\n乙")):
                if initial is not None:
                    target.write_text(initial, encoding="utf-8")
                result = tools.write_file(str(target), addition, "append")
                actual = target.read_text(encoding="utf-8")
                record("write-append-" + name, {"receipt": result, "readback": actual}, expected,
                       result.get("verified_readback") is True and actual == expected)
            for name, content, mode in (("bad-mode", "R2", "erase"), ("bad-type", 175, "overwrite"),
                                        ("oversize", "A" * (tools.MAX_WRITE_BYTES + 1), "overwrite")):
                before = target.read_bytes()
                result = tools.write_file(str(target), content, mode)
                record("write-" + name, result, "reject without mutation", result.get("ok") is False and
                       target.read_bytes() == before)
            with patch.object(tools.os, "replace", side_effect=PermissionError("R2 synthetic denial")):
                before = target.read_bytes()
                result = tools.write_file(str(target), "R2-new")
                leftovers = [{"name": item.name, "bytes": item.stat().st_size}
                             for item in root.glob("write.txt.tmp-*")]
                record("write-replace-error", {"receipt": result, "temporary_residue": leftovers,
                        "cleanup_owner": "this isolated harness after observation, not write_file"},
                       "error and original intact; report any temporary residue", result.get("ok") is False and
                       target.read_bytes() == before)

        # Every path below intercepts subprocess.run before invoking run_command.
        cases = [
            ("disabled", "", "python --version", None),
            ("empty", "python", "", None),
            ("not-allowed", "python", "other --version", None),
            ("metachar", "python", "python --version & other", None),
            ("parse-error", "python", 'python "unterminated', None),
            ("success", "python", 'python -c "print(175)"', subprocess.CompletedProcess([], 0, "175\n", "")),
            ("nonzero", "python", "python --version", subprocess.CompletedProcess([], 2, "", "R2 stderr")),
            ("truncated", "python", "python --version", subprocess.CompletedProcess([], 0, "R" * 4010, "")),
            ("missing-exe", "python", "python --version", FileNotFoundError("R2 missing")),
            ("timeout", "python", "python --version", subprocess.TimeoutExpired(["python"], 30)),
        ]
        for name, allowed, line, response in cases:
            with patch.dict(os.environ, {"ANIME_AGENT_ALLOWED_COMMANDS": allowed}), \
                    patch.object(subprocess, "run") as run:
                if isinstance(response, Exception):
                    run.side_effect = response
                elif response is not None:
                    run.return_value = response
                else:
                    run.side_effect = AssertionError("guard should prevent command execution")
                try:
                    result = tools.run_command(line)
                    extra = {"result": result, "mock_calls": run.call_count}
                    if run.called:
                        extra["argv"] = run.call_args.args[0]
                        extra["kwargs"] = run.call_args.kwargs
                    expected = "no subprocess" if response is None else "mock subprocess only"
                    passed = run.call_count == (0 if response is None else 1)
                    if response is None or isinstance(response, Exception) or name == "nonzero":
                        passed = passed and result.get("ok") is False
                    error_markers = {"disabled": "未启用", "empty": "空命令", "not-allowed": "不在白名单",
                                     "metachar": "特殊字符", "parse-error": "解析失败", "missing-exe": "找不到可执行文件",
                                     "timeout": "超时"}
                    if name in error_markers:
                        passed = passed and error_markers[name] in result.get("error", "")
                    if name == "timeout":
                        passed = passed and result.get("outcome") == "unknown"
                    if name == "success":
                        passed = passed and result.get("ok") is True and result.get("output") == "175"
                        passed = passed and extra["argv"] == ["python", "-c", "print(175)"]
                    if name == "nonzero":
                        passed = passed and result.get("returncode") == 2 and result.get("output") == "R2 stderr"
                    if run.called:
                        passed = passed and extra["kwargs"] == dict(capture_output=True, text=True, timeout=30.0, shell=False)
                    if name == "truncated":
                        passed = passed and result.get("output", "").startswith("R" * 4000) and "截断" in result.get("output", "")
                    record("command-" + name, extra, expected, passed)
                except Exception as exc:
                    record("command-" + name, {"exception": type(exc).__name__, "message": str(exc)}, "bounded result", False)

        database = MemoryStore(root / "database")
        try:
            a = database.create_session("R2-HISTORY-A")["id"]
            b = database.create_session("R2-HISTORY-B")["id"]
            for number in range(25):
                database.add_message("user" if number % 2 == 0 else "assistant", f"R2-A-{number:02}",
                                     request_id=f"r2-{number}", conversation_id=a)
            database.add_message("user", "R2-B-ONLY", request_id="r2-b", conversation_id=b)
            history = database.load_messages(20, a)
            record("history-20-window", history, "exact A05..A24, ordered and no B", [r["content"] for r in history] ==
                   [f"R2-A-{n:02}" for n in range(5, 25)])
            empty = database.create_session("R2-EMPTY")["id"]
            before = [r["id"] for r in database.list_sessions()]
            swept = database.sweep_empty_sessions()
            after = [r["id"] for r in database.list_sessions()]
            after_a = database.load_messages(30, a)
            after_b = database.load_messages(30, b)
            record("empty-session-isolation", {"listed_before": before, "listed_after": after, "swept": swept,
                                               "messages_a": len(after_a), "messages_b": after_b},
                   "empty hidden and swept, both populated sessions and messages retained",
                   empty not in before and empty in swept and a in after and b in after and
                   [r["content"] for r in after_a] == [f"R2-A-{n:02}" for n in range(25)] and
                   after_b == [{"role": "user", "content": "R2-B-ONLY"}])
        finally:
            database.close()
        # All synthetic handles closed before TemporaryDirectory cleanup.
        serialized = json.dumps(rows, ensure_ascii=False).replace(str(root).replace("\\", "\\\\"), "{TEMP_R2}")
        rows = json.loads(serialized)
    report = {"layer": "isolated direct implementation branches, not frontend acceptance", "api_calls": 0,
              "live_database_access": False, "temporary_objects_cleaned": True,
              "source_hashes": {name: hashlib.sha256((source / "agent_core" / name).read_bytes()).hexdigest()
                                for name in ("tools.py", "storage.py")}, "rows": rows}
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps({"cases": len(rows), "matched": sum(row["matched"] for row in rows),
                      "unmatched": [row["case"] for row in rows if not row["matched"]]}))


if __name__ == "__main__":
    main()
