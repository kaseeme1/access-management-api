"""FastAPI application exposing the access management service."""

from __future__ import annotations

import os
import secrets
import sqlite3
from collections.abc import Iterator
from dataclasses import asdict

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app import __version__, repository as repo, services
from app.database import connect
from app.models import (
    AccessError,
    DuplicateEmployeeError,
    EmployeeNotActiveError,
    EmployeeNotFoundError,
    UnknownRoleError,
)
from app.roles import ROLE_ACCESS

app = FastAPI(
    title="Employee Access Management API",
    version=__version__,
    description="Onboard, re-role, and offboard employees under a least-privilege access policy, with audit logging and access reviews.",
)

ERROR_STATUS = {
    UnknownRoleError: status.HTTP_400_BAD_REQUEST,
    EmployeeNotFoundError: status.HTTP_404_NOT_FOUND,
    DuplicateEmployeeError: status.HTTP_409_CONFLICT,
    EmployeeNotActiveError: status.HTTP_409_CONFLICT,
}


class OnboardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    department: str = Field(min_length=1, max_length=100)
    role: str


class RoleChangeRequest(BaseModel):
    role: str


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = os.environ.get("ACCESS_API_KEY", "")
    if not expected or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing API key")


def run(conn: sqlite3.Connection, fn, *args):
    try:
        result = fn(conn, *args)
    except AccessError as exc:
        conn.rollback()
        raise HTTPException(status_code=ERROR_STATUS.get(type(exc), 400), detail=str(exc) or type(exc).__name__)
    conn.commit()
    return result


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/roles", dependencies=[Depends(require_api_key)])
def list_roles() -> dict:
    return {role: sorted(systems) for role, systems in ROLE_ACCESS.items()}


@app.get("/employees", dependencies=[Depends(require_api_key)])
def list_employees(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return [asdict(e) for e in repo.list_employees(conn)]


@app.post("/employees", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
def onboard(body: OnboardRequest, x_actor: str = Header(default="api"), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    employee = run(conn, services.onboard_employee, body.name, body.email, body.department, body.role, x_actor)
    return asdict(employee)


@app.get("/employees/{employee_id}", dependencies=[Depends(require_api_key)])
def get_employee(employee_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    employee = repo.get_employee(conn, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="employee not found")
    return asdict(employee)


@app.patch("/employees/{employee_id}/role", dependencies=[Depends(require_api_key)])
def change_role(employee_id: int, body: RoleChangeRequest, x_actor: str = Header(default="api"),
                conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return asdict(run(conn, services.change_role, employee_id, body.role, x_actor))


@app.post("/employees/{employee_id}/offboard", dependencies=[Depends(require_api_key)])
def offboard(employee_id: int, x_actor: str = Header(default="api"), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    revoked = run(conn, services.offboard_employee, employee_id, x_actor)
    return {"employee_id": employee_id, "revoked": revoked}


@app.get("/access-review", dependencies=[Depends(require_api_key)])
def access_review(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return [asdict(f) for f in services.review_access(conn)]


@app.get("/audit-log", dependencies=[Depends(require_api_key)])
def audit_log(employee_id: int | None = None, conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return repo.list_audit(conn, employee_id)
