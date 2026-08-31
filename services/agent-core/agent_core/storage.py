from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def default_data_dir() -> Path:
    configured = os.getenv("ANIME_AGENT_DATA_DIR", "").strip()
    if configured:
        return Path(configured)
    local_app_data = os.getenv("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "AnimeAgent" / "data"
    return Path("data")


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
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def latest_session_id(self) -> int | None:
        row = self.connection.execute(
            "SELECT id FROM sessions ORDER BY updated_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return int(row["id"]) if row else None

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
            "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [
            {
                "role": str(row["role"]),
                "text": str(row["content"]),
                "createdAt": str(row["created_at"]),
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

    def add_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        import json

        self.connection.execute(
            "INSERT INTO events (event_type, payload) VALUES (?, ?)",
            (event_type, json.dumps(payload or {}, ensure_ascii=False)),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
