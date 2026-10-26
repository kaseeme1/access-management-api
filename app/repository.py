"""Database reads and writes. All SQL lives here."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models import Employee


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_employee(conn: sqlite3.Connection, row: sqlite3.Row) -> Employee:
    return Employee(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        department=row["department"],
        role=row["role"],
        status=row["status"],
        created_at=row["created_at"],
        terminated_at=row["terminated_at"],
        access=sorted(get_access(conn, row["id"])),
    )


def insert_employee(conn: sqlite3.Connection, name: str, email: str, department: str, role: str) -> int:
    cur = conn.execute(
        "INSERT INTO employees (name, email, department, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, email.lower(), department, role, now()),
    )
    return cur.lastrowid


def email_exists(conn: sqlite3.Connection, email: str) -> bool:
    row = conn.execute("SELECT 1 FROM employees WHERE email = ?", (email.lower(),)).fetchone()
    return row is not None


def get_employee(conn: sqlite3.Connection, employee_id: int) -> Employee | None:
    row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    return _to_employee(conn, row) if row else None


def list_employees(conn: sqlite3.Connection) -> list[Employee]:
    rows = conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
    return [_to_employee(conn, r) for r in rows]


def set_role(conn: sqlite3.Connection, employee_id: int, role: str) -> None:
    conn.execute("UPDATE employees SET role = ? WHERE id = ?", (role, employee_id))


def set_terminated(conn: sqlite3.Connection, employee_id: int) -> None:
    conn.execute(
        "UPDATE employees SET status = 'terminated', terminated_at = ? WHERE id = ?",
        (now(), employee_id),
    )


def get_access(conn: sqlite3.Connection, employee_id: int) -> set[str]:
    rows = conn.execute("SELECT system FROM access_grants WHERE employee_id = ?", (employee_id,)).fetchall()
    return {r["system"] for r in rows}


def grant_access(conn: sqlite3.Connection, employee_id: int, systems: set[str] | frozenset[str]) -> None:
    ts = now()
    conn.executemany(
        "INSERT OR IGNORE INTO access_grants (employee_id, system, granted_at) VALUES (?, ?, ?)",
        [(employee_id, s, ts) for s in sorted(systems)],
    )


def revoke_access(conn: sqlite3.Connection, employee_id: int, systems: set[str] | frozenset[str]) -> None:
    conn.executemany(
        "DELETE FROM access_grants WHERE employee_id = ? AND system = ?",
        [(employee_id, s) for s in sorted(systems)],
    )


def add_audit(conn: sqlite3.Connection, actor: str, action: str, employee_id: int | None, details: str = "") -> None:
    conn.execute(
        "INSERT INTO audit_log (timestamp, actor, action, employee_id, details) VALUES (?, ?, ?, ?, ?)",
        (now(), actor, action, employee_id, details),
    )


def list_audit(conn: sqlite3.Connection, employee_id: int | None = None) -> list[dict]:
    if employee_id is None:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM audit_log WHERE employee_id = ? ORDER BY id", (employee_id,)).fetchall()
    return [dict(r) for r in rows]
