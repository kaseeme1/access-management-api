"""Access management business logic: onboarding, role changes, offboarding, and access reviews."""

from __future__ import annotations

import sqlite3

from app import repository as repo
from app.models import (
    DuplicateEmployeeError,
    Employee,
    EmployeeNotActiveError,
    EmployeeNotFoundError,
    Finding,
    RoleChangeResult,
    UnknownRoleError,
)
from app.roles import ROLE_ACCESS, access_for, is_valid_role


def onboard_employee(
    conn: sqlite3.Connection,
    name: str,
    email: str,
    department: str,
    role: str,
    actor: str,
) -> Employee:
    """Create an employee and grant the access their role requires.

    Raises:
        UnknownRoleError: role is not in the access policy.
        DuplicateEmployeeError: an employee with this email already exists.
    """
    raise NotImplementedError


def change_role(
    conn: sqlite3.Connection,
    employee_id: int,
    new_role: str,
    actor: str,
) -> RoleChangeResult:
    """Move an employee to a new role, granting new access and revoking access the new role doesn't include.

    Raises:
        UnknownRoleError: new_role is not in the access policy.
        EmployeeNotFoundError: no employee with this id.
        EmployeeNotActiveError: the employee has been terminated.
    """
    raise NotImplementedError


def offboard_employee(
    conn: sqlite3.Connection,
    employee_id: int,
    actor: str,
) -> list[str]:
    """Terminate an employee and revoke all of their access. Returns the revoked systems, sorted.

    Raises:
        EmployeeNotFoundError: no employee with this id.
        EmployeeNotActiveError: the employee is already terminated.
    """
    raise NotImplementedError


def review_access(conn: sqlite3.Connection) -> list[Finding]:
    """Compare every employee's actual access against their role's policy and report mismatches.

    Issues reported:
        terminated_with_access  CRITICAL  a terminated employee still holds access
        excess_access           HIGH      an active employee holds access their role doesn't include
        missing_access          LOW       an active employee lacks access their role requires
    """
    raise NotImplementedError
