"""SQLite connection and schema."""

from __future__ import annotations

import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    department    TEXT NOT NULL,
    role          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'terminated')),
    created_at    TEXT NOT NULL,
    terminated_at TEXT
);

CREATE TABLE IF NOT EXISTS access_grants (
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    system      TEXT NOT NULL,
    granted_at  TEXT NOT NULL,
    PRIMARY KEY (employee_id, system)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    employee_id INTEGER,
    details     TEXT NOT NULL DEFAULT ''
);
"""


def default_db_path() -> str:
    return os.environ.get("ACCESS_DB_PATH", "access.db")


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or default_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
