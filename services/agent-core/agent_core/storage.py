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
            """
        )
        self.connection.commit()

    def load_messages(self, limit: int = 20) -> list[dict[str, str]]:
        rows = self.connection.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"role": str(row["role"]), "content": str(row["content"])}
            for row in reversed(rows)
        ]

    def add_message(self, role: str, content: str, request_id: str = "") -> None:
        self.connection.execute(
            "INSERT INTO messages (role, content, request_id) VALUES (?, ?, ?)",
            (role, content, request_id),
        )
        self.connection.commit()

    def add_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        import json

        self.connection.execute(
            "INSERT INTO events (event_type, payload) VALUES (?, ?)",
            (event_type, json.dumps(payload or {}, ensure_ascii=False)),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
