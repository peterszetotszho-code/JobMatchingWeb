"""SQLite-backed persistence for match history, keyed per user."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "app.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init() -> None:
    """Create tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                resume TEXT NOT NULL,
                jd TEXT NOT NULL,
                analysis TEXT NOT NULL,
                fit_score INTEGER NOT NULL,
                matched INTEGER NOT NULL,
                partial INTEGER NOT NULL,
                gap INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
            );
            """
        )


def _default_title(jd: str) -> str:
    for line in jd.splitlines():
        line = line.strip()
        if line:
            return line[:60]
    return "未命名紀錄"


def save_record(user_id, resume, jd, analysis, fit_score, matched, partial, gap, title=None) -> int:
    """Insert a record and return its id."""
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO records (user_id, title, resume, jd, analysis, fit_score, matched, partial, gap, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user_id, title or _default_title(jd), resume, jd, analysis, fit_score, matched, partial, gap, _now()),
        )
        return cur.lastrowid


def list_records(user_id: str) -> list[dict]:
    """Return lightweight rows (no resume/jd/analysis) for the given user, newest first."""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, title, fit_score, matched, partial, gap, created_at "
            "FROM records WHERE user_id=? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_record(user_id: str, record_id: int) -> dict | None:
    """Return a full record (with messages) if it belongs to the user, else None."""
    with _conn() as c:
        row = c.execute(
            "SELECT id, title, resume, jd, analysis, fit_score, matched, partial, gap, created_at "
            "FROM records WHERE id=? AND user_id=?",
            (record_id, user_id),
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        msgs = c.execute(
            "SELECT id, role, content, created_at FROM messages WHERE record_id=? ORDER BY id ASC",
            (record_id,),
        ).fetchall()
        record["messages"] = [dict(m) for m in msgs]
        return record


def delete_record(user_id: str, record_id: int) -> bool:
    """Delete a record (and its messages via cascade) if it belongs to the user."""
    with _conn() as c:
        cur = c.execute("DELETE FROM records WHERE id=? AND user_id=?", (record_id, user_id))
        return cur.rowcount > 0


def add_message(record_id: int, role: str, content: str) -> int:
    """Append a chat message to a record."""
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO messages (record_id, role, content, created_at) VALUES (?,?,?,?)",
            (record_id, role, content, _now()),
        )
        return cur.lastrowid
