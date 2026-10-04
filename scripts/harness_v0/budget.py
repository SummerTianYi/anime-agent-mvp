"""Codex: cross-process hard HTTP budget, including retries, before network I/O."""
import sqlite3
from contextlib import closing


class BudgetExceeded(RuntimeError):
    pass


def initialize(path, cap=900):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS limits (cap INTEGER)")
        if not db.execute("SELECT * FROM limits").fetchone():
            db.execute("INSERT INTO limits VALUES (?)", (cap,))
        db.execute("CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, trial TEXT NOT NULL)")


def reserve(path, trial, per_trial=20):
    with closing(sqlite3.connect(path, timeout=30)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        total = db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        count = db.execute("SELECT COUNT(*) FROM calls WHERE trial=?", (trial,)).fetchone()[0]
        cap = db.execute("SELECT cap FROM limits").fetchone()[0]
        if total >= cap or count >= per_trial:
            raise BudgetExceeded("global_http_limit" if total >= cap else "trial_http_limit")
        return db.execute("INSERT INTO calls(trial) VALUES (?)", (trial,)).lastrowid
