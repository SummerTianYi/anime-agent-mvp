from __future__ import annotations

import os
import json

import re
import sqlite3
from pathlib import Path
from typing import Any

from . import memory_correction


def default_data_dir() -> Path:
    configured = os.getenv("ANIME_AGENT_DATA_DIR", "").strip()
    if configured:
        return Path(configured)
    local_app_data = os.getenv("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "AnimeAgent" / "data"
    return Path("data")


# Pending facts are injected tagged so life events stay reachable before the
# review UI exists — except sensitive ones (the original privacy contract:
# bank-card style pending facts must never reach the prompt).
_PENDING_SENSITIVE_MARKERS = ("密码", "银行卡", "卡号", "身份证", "尾号", "验证码")
_SENSITIVE_DIGIT_RUN = re.compile(r"\d{6,}")


def _pending_recallable(content: str) -> bool:
    if any(marker in content for marker in _PENDING_SENSITIVE_MARKERS):
        return False
    return _SENSITIVE_DIGIT_RUN.search(content) is None


class MemoryStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        directory = data_dir or default_data_dir()
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "anime-agent.sqlite3"
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                request_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '新对话',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS facts (
                fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                scope TEXT NOT NULL DEFAULT 'global',
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                source_request_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS fact_corrections (
                correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                request_id TEXT NOT NULL,
                source_text TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, request_id)
            );
            CREATE TABLE IF NOT EXISTS fact_overrides (
                session_id INTEGER NOT NULL,
                entity TEXT NOT NULL,
                attribute TEXT NOT NULL,
                fact_id INTEGER NOT NULL,
                PRIMARY KEY(session_id, entity, attribute)
            );
            """
        )
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(messages)")}
        if "conversation_id" not in columns:
            self.connection.execute(
                "ALTER TABLE messages ADD COLUMN conversation_id INTEGER NOT NULL DEFAULT 0"
            )
        session_count = self.connection.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
        if session_count == 0:
            has_messages = self.connection.execute(
                "SELECT COUNT(*) AS n FROM messages"
            ).fetchone()["n"] > 0
            cursor = self.connection.execute(
                "INSERT INTO sessions (title) VALUES (?)",
                ("初始会话" if has_messages else "新对话",),
            )
            self.connection.execute(
                "UPDATE messages SET conversation_id = ? WHERE conversation_id = 0",
                (cursor.lastrowid,),
            )
        self.connection.commit()

    def get_session(self, session_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        return dict(row)

    def create_session(self, title: str = "新对话") -> dict[str, Any]:
        cursor = self.connection.execute(
            "INSERT INTO sessions (title, updated_at) VALUES (?, strftime('%Y-%m-%d %H:%M:%f', 'now'))",
            (title,),
        )
        self.connection.commit()
        return self.get_session(cursor.lastrowid)

    def delete_session(self, session_id: int) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return False
        self.connection.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (session_id,)
        )
        self.connection.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        self.connection.commit()
        if self.latest_session_id() is None:
            self.create_session()
        return True

    def rename_session(self, session_id: int, title: str) -> bool:
        clean = " ".join(str(title or "").split())
        if not clean:
            return False
        row = self.connection.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return False
        self.connection.execute(
            "UPDATE sessions SET title = ?, updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now') WHERE id = ?",
            (clean[:24], session_id),
        )
        self.connection.commit()
        return True

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT id, title, created_at, updated_at FROM sessions s WHERE EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = s.id) ORDER BY updated_at DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def latest_session_id(self) -> int | None:
        row = self.connection.execute(
            "SELECT id FROM sessions ORDER BY updated_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return int(row["id"]) if row else None


    def sweep_empty_sessions(self) -> list[int]:
        """Delete sessions with zero messages; wake and the new-chat button
        create shells eagerly, so empties must never linger (GPT-style)."""
        rows = self.connection.execute(
            "SELECT id FROM sessions WHERE NOT EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = sessions.id)"
        ).fetchall()
        swept = [int(row["id"]) for row in rows]
        if swept:
            self.connection.execute(
                "DELETE FROM sessions WHERE NOT EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = sessions.id)"
            )
            self.connection.commit()
        return swept

    def load_messages(
        self, limit: int = 20, conversation_id: int | None = None
    ) -> list[dict[str, str]]:
        session_id = conversation_id if conversation_id is not None else self.latest_session_id()
        if session_id is None:
            return []
        rows = self.connection.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [
            {"role": str(row["role"]), "content": str(row["content"])}
            for row in reversed(rows)
        ]

    def load_history(
        self, limit: int = 50, conversation_id: int | None = None
    ) -> list[dict[str, str]]:
        session_id = conversation_id if conversation_id is not None else self.latest_session_id()
        if session_id is None:
            return []
        rows = self.connection.execute(
            "SELECT role, content, request_id, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [
            {
                "role": str(row["role"]),
                "text": str(row["content"]),
                "createdAt": str(row["created_at"]),
                **({"requestId": str(row["request_id"])} if row["request_id"] else {}),
            }
            for row in reversed(rows)
        ]

    def add_message(
        self,
        role: str,
        content: str,
        request_id: str = "",
        conversation_id: int | None = None,
    ) -> int:
        session_id = conversation_id if conversation_id is not None else self.latest_session_id()
        if session_id is None:
            session_id = self.create_session()["id"]
        self.connection.execute(
            "INSERT INTO messages (role, content, request_id, conversation_id) VALUES (?, ?, ?, ?)",
            (role, content, request_id, session_id),
        )
        if role == "user":
            title = content.strip()[:12]
            if title:
                self.connection.execute(
                    "UPDATE sessions SET title = ? WHERE id = ? AND title = '新对话'",
                    (title, session_id),
                )
        self.connection.execute(
            "UPDATE sessions SET updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now') WHERE id = ?",
            (session_id,),
        )
        self.connection.commit()
        return session_id

    def delete_message(self, request_id: str) -> bool:
        """Remove the user row persisted for a request (superseded turns must
        not linger in history or feed the next LLM context)."""
        cursor = self.connection.execute(
            "DELETE FROM messages WHERE request_id = ? AND role = 'user'",
            (request_id,),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def add_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        import json

        self.connection.execute(
            "INSERT INTO events (event_type, payload) VALUES (?, ?)",
            (event_type, json.dumps(payload or {}, ensure_ascii=False)),
        )
        self.connection.commit()

    def add_fact(
        self,
        content: str,
        session_id: int | None = None,
        scope: str = "global",
        status: str = "pending",
        source_request_id: str = "",
    ) -> int:
        """Append a candidate. Only correct_fact may supersede existing facts.

        Similarity is not identity. This legacy entry point must not undo a
        verified correction or replace a different entity/attribute.
        """
        cursor = self.connection.execute(
            "INSERT INTO facts (session_id, scope, content, status, source_request_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (session_id, scope, content, status, source_request_id),
        )
        fact_id = int(cursor.lastrowid)
        self.connection.commit()
        return fact_id

    def visible_fact_rows(self, session_id: int | None) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT f.*, EXISTS(SELECT 1 FROM fact_overrides o WHERE o.fact_id=f.fact_id"
            " AND o.session_id=?) AS is_override FROM facts f"
            " WHERE status IN ('confirmed','pending') AND (scope='global' OR (scope='session' AND session_id=?))"
            " ORDER BY CASE status WHEN 'confirmed' THEN 0 ELSE 1 END, fact_id DESC",
            (session_id, session_id),
        ).fetchall()
        return [dict(r) for r in rows if r["status"] == "confirmed" or _pending_recallable(r["content"])]

    def prepare_correction(self, text: str, session_id: int) -> dict[str, Any] | None:
        return memory_correction.resolve(text, self.visible_fact_rows(session_id), session_id)

    def _read_correction(self, session_id: int, request_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT result FROM fact_corrections WHERE session_id=? AND request_id=?",
            (session_id, request_id),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def _verify_correction(self, result: dict[str, Any], *, historical: bool = False) -> None:
        if result.get("outcome") != "corrected":
            return
        row = self.connection.execute("SELECT * FROM facts WHERE fact_id=?", (result["new_fact_id"],)).fetchone()
        old = self.connection.execute("SELECT * FROM facts WHERE fact_id=?", (result["old_fact_id"],)).fetchone()
        expected_old = (result["old_status"] if result["scope"] == "session" and result["old_scope"] == "global"
                        else "superseded")
        expected_session = result["session_id"] if result["scope"] == "session" else result["old_session_id"]
        if (not row or not old or row["content"] != result["stored_content"] or row["scope"] != result["scope"]
                or row["session_id"] != expected_session or row["source_request_id"] != result["request_id"]
                or old["content"] != result["old_content"] or old["scope"] != result["old_scope"]
                or old["session_id"] != result["old_session_id"]
                or (not historical and (row["status"] != result["old_status"] or old["status"] != expected_old))):
            raise RuntimeError("Correction fact readback mismatch")
        if not historical and (result["is_override"] or (result["scope"] == "session" and result["old_scope"] == "global")):
            override = self.connection.execute(
                "SELECT fact_id FROM fact_overrides WHERE session_id=? AND entity=? AND attribute=?",
                (result["session_id"], result["entity"], result["attribute"])).fetchone()
            if not override or override[0] != result["new_fact_id"]:
                raise RuntimeError("Correction session override readback mismatch")

    def correct_fact(self, plan: dict[str, Any], request_id: str) -> dict[str, Any]:
        """CAS, replacement and provenance commit together; return only after readback.

        Re-resolve the original user text inside the transaction. The caller's
        fact ID, offsets and fields are never sufficient authorization.
        """
        session_id, text = plan["session_id"], plan["source_text"]
        committed = False
        try:
            with self.connection:
                self.connection.execute("BEGIN IMMEDIATE")
                prior = self._read_correction(session_id, request_id)
                if prior:
                    if prior["source_text"] != text:
                        return {"error": "尚未更正：请求标识已用于不同内容。"}
                    # A repeated request may refer to a historical success,
                    # but the persisted values must still match its receipt.
                    committed = True
                    self._verify_correction(prior, historical=True)
                    return {**prior, "outcome": "replayed"} if not prior.get("error") else prior
                current = self.prepare_correction(text, session_id)
                if current is None or current != plan:
                    result = {**plan, "outcome": "conflict", "error": "尚未更正：旧事实版本或作用域已变化，请核对后再更正。"}
                elif plan.get("error"):
                    result = {**plan, "outcome": "clarify"}
                elif not _pending_recallable(plan["new_value"]) or not _pending_recallable(plan["old_content"]):
                    result = {**plan, "outcome": "restricted", "error": "尚未更正：这项内容涉及敏感记忆，保留原有保护与确认要求。"}
                elif plan["old_value"] == plan["new_value"]:
                    result = {**plan, "outcome": "unchanged", "new_fact_id": plan["old_fact_id"]}
                else:
                    is_override = plan["is_override"] or (plan["scope"] == "session" and plan["old_scope"] == "global")
                    content = (f"{plan['entity']}{plan['attribute']}{plan['new_value']}"
                               if is_override else plan["new_content"])
                    cursor = self.connection.execute(
                        "INSERT INTO facts(session_id,scope,content,status,source_request_id) VALUES(?,?,?,?,?)",
                        (session_id if plan["scope"] == "session" else plan["old_session_id"],
                         plan["scope"], content, plan["old_status"], request_id))
                    new_id = int(cursor.lastrowid)
                    if not is_override or plan["is_override"]:
                        cursor = self.connection.execute(
                            "UPDATE facts SET status='superseded' WHERE fact_id=? AND content=? AND status=?"
                            " AND scope=? AND session_id IS ?",
                            (plan["old_fact_id"], plan["old_content"], plan["old_status"], plan["old_scope"], plan["old_session_id"]))
                        if cursor.rowcount != 1:
                            raise RuntimeError("Correction compare-and-swap failed")
                    if is_override:
                        self.connection.execute(
                            "INSERT INTO fact_overrides(session_id,entity,attribute,fact_id) VALUES(?,?,?,?)"
                            " ON CONFLICT(session_id,entity,attribute) DO UPDATE SET fact_id=excluded.fact_id",
                            (session_id, plan["entity"], plan["attribute"], new_id))
                    result = {**plan, "request_id": request_id, "new_fact_id": new_id, "stored_content": content, "outcome": "corrected"}
                    self._verify_correction(result)
                self.connection.execute(
                    "INSERT INTO fact_corrections(session_id,request_id,source_text,result) VALUES(?,?,?,?)",
                    (session_id, request_id, text, json.dumps(result, ensure_ascii=False)))
            committed = True
            readback = self._read_correction(session_id, request_id)
            if readback != result:
                raise RuntimeError("Correction receipt readback mismatch")
            self._verify_correction(result)
            return result
        except (sqlite3.Error, RuntimeError):
            # A post-commit read failure is unknown, not a claim of rollback.
            return {**plan, "outcome": "unverified" if committed else "failed",
                    "error": ("更正提交后的读回核验未完成，当前不能确认保存结果；请查询核对，未自动重试。" if committed
                              else "更正保存失败，事务已回滚，旧有效值保留；没有发布保存成功承诺。")}

    def correction_history(self, session_id: int | None) -> list[dict[str, Any]]:
        """History follows the same visibility/privacy boundary as active recall."""
        origins = {}
        for correction in self.connection.execute("SELECT result FROM fact_corrections ORDER BY correction_id"):
            saved = json.loads(correction[0])
            if saved.get("outcome") == "corrected":
                origins[saved["old_fact_id"]] = saved["old_status"]
        rows = self.connection.execute(
            "SELECT f.* FROM facts f WHERE status='superseded'"
            " AND (scope='global' OR (scope='session' AND session_id=?)) ORDER BY fact_id DESC", (session_id,)).fetchall()
        return [{"fact_id": r["fact_id"], "content": r["content"], "status": "superseded", "scope": r["scope"],
                 "original_status": origins.get(r["fact_id"], "unknown"),
                 "note": "旧值仍属待确认，不因被更正而确认为事实" if origins.get(r["fact_id"]) == "pending" else "已被替代的历史版本"}
                for r in rows if _pending_recallable(r["content"])]

    def candidate_conflicts(self, content: str, session_id: int) -> bool:
        """The old candidate branch cannot reintroduce a known key/value."""
        proposed = memory_correction.parts(content)
        rows = self.visible_fact_rows(session_id)
        known = {(p.entity, p.attribute) for r in rows for p in memory_correction.parts(r["content"])}
        if any((p.entity, p.attribute) in known for p in proposed):
            return True
        # Opaque candidates mentioning an existing precise key must not bypass
        # the correction boundary by attaching explanatory prose.
        return any(entity in content and attribute in content for entity, attribute in known)

    def set_fact_status(self, fact_id: int, status: str) -> bool:
        cursor = self.connection.execute(
            "UPDATE facts SET status = ? WHERE fact_id = ?",
            (status, fact_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def recall_facts(self, session_id: int | None = None) -> list[str]:
        """Facts visible to a session: confirmed facts verbatim plus the
        session's own pending facts tagged （待确认） (T2+ exam fix: life-event
        facts must stay reachable before the review UI exists). Superseded
        facts are never returned."""
        rows = self.visible_fact_rows(session_id)
        overrides = {(p.entity, p.attribute): (p.value, r["status"]) for r in rows if r["is_override"]
                     for p in memory_correction.parts(r["content"])}
        rendered = []
        consumed = set()
        for row in rows:
            if row["is_override"]:
                continue
            content = row["content"]
            # Replace just the matching scalar in the session's view of a
            # compound global record, preserving every other field verbatim.
            for p in reversed(memory_correction.parts(content)):
                key = (p.entity, p.attribute)
                if row["scope"] == "global" and key in overrides:
                    value, status = overrides[key]
                    value += "（待确认）" if status == "pending" else ""
                    content = content[:p.start] + value + content[p.end:]
                    consumed.add(key)
            rendered.append(content if row["status"] == "confirmed" else content + "（待确认）")
        for row in rows:
            if row["is_override"] and not any((p.entity, p.attribute) in consumed for p in memory_correction.parts(row["content"])):
                rendered.insert(0, row["content"] + ("（待确认）" if row["status"] == "pending" else ""))
        return rendered

    def pending_facts(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT fact_id, session_id, scope, content, source_request_id, created_at"
            " FROM facts WHERE status = 'pending' ORDER BY fact_id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.connection.close()
