"""Domain objects and errors."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Employee:
    id: int
    name: str
    email: str
    department: str
    role: str
    status: str
    created_at: str
    terminated_at: str | None = None
    access: list[str] = field(default_factory=list)


@dataclass
class RoleChangeResult:
    employee_id: int
    old_role: str
    new_role: str
    added: list[str]
    removed: list[str]


@dataclass
class Finding:
    employee_id: int
    name: str
    issue: str
    severity: str
    systems: list[str]


class AccessError(Exception):
    """Base class for access management errors."""


class UnknownRoleError(AccessError):
    pass


class DuplicateEmployeeError(AccessError):
    pass


class EmployeeNotFoundError(AccessError):
    pass


class EmployeeNotActiveError(AccessError):
    pass
