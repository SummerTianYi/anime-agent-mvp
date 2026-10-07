"""Read-only source identity and SQLite transaction snapshot, audit round 02.

Run under the desktop's unpackaged namespace, using its existing Python.
Never repair, checkpoint, restore, or migrate the source database.
Output is PRIVATE until explicitly reduced and reviewed for publication.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from datetime import datetime, timezone
from urllib.request import ProxyHandler, build_opener


def file_identity(path: Path) -> dict:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
                                                wintypes.DWORD, wintypes.DWORD]
    class Info(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
                    ("accessed", wintypes.FILETIME), ("written", wintypes.FILETIME),
                    ("volume", wintypes.DWORD), ("size_hi", wintypes.DWORD),
                    ("size_lo", wintypes.DWORD), ("links", wintypes.DWORD),
                    ("index_hi", wintypes.DWORD), ("index_lo", wintypes.DWORD)]
    kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info)]
    handle = kernel.CreateFileW(str(path), 0x80, 7, None, 3, 0, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = Info()
        if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_unicode_buffer(32768)
        if not kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return {"requested": str(path), "final_path": buffer.value,
                "volume_serial": info.volume, "file_index": (info.index_hi << 32) | info.index_lo,
                "bytes": (info.size_hi << 32) | info.size_lo}
    finally:
        kernel.CloseHandle(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--require-unpackaged", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    record = {"schema": "round02-identity-v1", "utc": datetime.now(timezone.utc).isoformat(),
              "pid": os.getpid(), "source_mutations": [], "private": True}
    try:
        length = ctypes.c_uint32(0)
        package_status = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        record["package_status"] = package_status
        if args.require_unpackaged and package_status != 15700:
            raise RuntimeError("Not an unpackaged process; source snapshot refused")
        opener = build_opener(ProxyHandler({}))
        with opener.open("http://127.0.0.1:8765/health", timeout=15) as response:
            record["core_health"] = json.load(response)
        try:
            with opener.open("http://127.0.0.1:8770/health", timeout=5) as response:
                record["tts_health"] = json.load(response)
        except Exception as exc:
            record["tts_health"] = {"unavailable": True, "error_type": type(exc).__name__}
        with opener.open("http://127.0.0.1:8765/health/live", timeout=15) as response:
            record["core_live"] = json.load(response)
        path = Path(record["core_health"]["memory"]["path"])
        physical = Path("\\\\localhost\\" + str(path)[0].lower() + "$\\" + str(path)[3:])
        record["normal_identity"] = file_identity(path)
        record["unc_identity"] = file_identity(physical)
        keys = ("volume_serial", "file_index")
        record["same_physical_file"] = all(record["normal_identity"][k] == record["unc_identity"][k] for k in keys)
        if not record["same_physical_file"]:
            raise RuntimeError("Normal and physical namespace identify different database files")
        source = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
        source.execute("PRAGMA query_only=ON")
        source.execute("BEGIN")
        record["journal_mode"] = source.execute("PRAGMA journal_mode").fetchone()[0]
        record["database_list"] = source.execute("PRAGMA database_list").fetchall()
        id_columns = {"sessions": "id", "messages": "id", "events": "id", "facts": "fact_id"}
        record["source_watermarks"] = {table: source.execute(f"SELECT max({column}),count(*) FROM {table}").fetchone()
                                        for table, column in id_columns.items()}
        record["prior_audit_request_present"] = source.execute(
            "SELECT id,conversation_id,request_id,created_at FROM messages WHERE request_id=?",
            ("avatar-chat-1147549",)).fetchall()
        dest = args.output_dir / "transaction-snapshot.sqlite3"
        started = time.monotonic()
        def progress(status: int, remaining: int, total: int) -> None:
            if time.monotonic() - started > 30:
                raise TimeoutError("SQLite backup exceeded bounded 30 second deadline")
        try:
            with sqlite3.connect(dest) as target:
                source.backup(target, pages=64, progress=progress, sleep=0.02)
            record["snapshot_method"] = "SQLite backup from an explicit read transaction in verified unpackaged namespace"
        finally:
            source.rollback()
            source.close()
        with sqlite3.connect(dest.as_uri() + "?mode=ro", uri=True) as snapshot:
            snapshot.execute("PRAGMA query_only=ON")
            record["snapshot_watermarks"] = {table: snapshot.execute(f"SELECT max({column}),count(*) FROM {table}").fetchone()
                                              for table, column in id_columns.items()}
            record["quick_check"] = [row[0] for row in snapshot.execute("PRAGMA quick_check")]
            record["malformed_event_timestamps"] = snapshot.execute(
                "SELECT count(*) FROM events WHERE julianday(created_at) IS NULL").fetchone()[0]
        record["snapshot_sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
        record["snapshot_bytes"] = dest.stat().st_size
        record["normal_identity_after"] = file_identity(path)
        record["identity_stable"] = all(record["normal_identity"][k] == record["normal_identity_after"][k] for k in keys)
        record["watermarks_equal"] = record["source_watermarks"] == record["snapshot_watermarks"]
        record["status"] = "captured" if record["identity_stable"] and record["watermarks_equal"] else "rejected"
    except Exception as exc:
        record["status"] = "failed"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        with (args.output_dir / "identity.json").open("x", encoding="utf-8") as output:
            json.dump(record, output, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
