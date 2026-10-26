"""Access management business logic: onboarding, role changes, offboarding, and access reviews."""

from __future__ import annotations

import sqlite3

from app import repository as repo
from app.access import access_to_add, access_to_remove
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

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "LOW": 2}


def onboard_employee(
    conn: sqlite3.Connection,
    name: str,
    email: str,
    department: str,
    role: str,
    actor: str,
) -> Employee:
    if not is_valid_role(role):
        raise UnknownRoleError(role)

    if repo.email_exists(conn, email):
        raise DuplicateEmployeeError(email)

    employee_id = repo.insert_employee(conn, name, email, department, role)

    systems = access_for(role)
    repo.grant_access(conn, employee_id, systems)

    log_entry = f"Onboarded {name} ({email}) to {role} in {department}. Granted access to: {', '.join(sorted(systems))}"
    repo.add_audit(conn, actor, "onboard", employee_id, log_entry)

    return repo.get_employee(conn, employee_id)


def get_active_employee(conn: sqlite3.Connection, employee_id: int) -> Employee:
    employee = repo.get_employee(conn, employee_id)
    if employee is None:
        raise EmployeeNotFoundError(employee_id)
    if employee.status != "active":
        raise EmployeeNotActiveError(employee_id)
    return employee


def change_role(
    conn: sqlite3.Connection,
    employee_id: int,
    new_role: str,
    actor: str,
) -> RoleChangeResult:
    if not is_valid_role(new_role):
        raise UnknownRoleError(new_role)

    employee = get_active_employee(conn, employee_id)

    current = repo.get_access(conn, employee_id)
    allowed = access_for(new_role)

    to_remove = access_to_remove(current, allowed)
    to_add = access_to_add(current, allowed)

    repo.apply_access_changes(conn, employee_id, to_remove, to_add)
    repo.set_role(conn, employee_id, new_role)

    log_entry = (
        f"Changed {employee.name} from {employee.role} to {new_role}. "
        f"Granted: {', '.join(sorted(to_add)) or 'none'}. Revoked: {', '.join(sorted(to_remove)) or 'none'}"
    )
    repo.add_audit(conn, actor, "role_change", employee_id, log_entry)

    return RoleChangeResult(
        employee_id=employee_id,
        old_role=employee.role,
        new_role=new_role,
        added=sorted(to_add),
        removed=sorted(to_remove),
    )


def offboard_employee(
    conn: sqlite3.Connection,
    employee_id: int,
    actor: str,
) -> list[str]:
    employee = get_active_employee(conn, employee_id)

    current = repo.get_access(conn, employee_id)

    repo.apply_access_changes(conn, employee_id, to_remove=current, to_add=set())
    repo.set_terminated(conn, employee_id)

    log_entry = f"Offboarded {employee.name}. Revoked: {', '.join(sorted(current)) or 'none'}"
    repo.add_audit(conn, actor, "offboard", employee_id, log_entry)

    return sorted(current)


def review_access(conn: sqlite3.Connection) -> list[Finding]:
    findings = []

    for employee in repo.list_employees(conn):
        current = set(employee.access)

        if employee.status == "terminated":
            if current:
                findings.append(Finding(employee.id, employee.name, "terminated_with_access", "CRITICAL", sorted(current)))
            continue

        allowed = ROLE_ACCESS.get(employee.role, frozenset())

        excess = access_to_remove(current, allowed)
        if excess:
            findings.append(Finding(employee.id, employee.name, "excess_access", "HIGH", sorted(excess)))

        missing = access_to_add(current, allowed)
        if missing:
            findings.append(Finding(employee.id, employee.name, "missing_access", "LOW", sorted(missing)))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.employee_id))
    return findings