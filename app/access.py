"""Helpers for working out access changes."""

from __future__ import annotations

from collections.abc import Set


def access_to_remove(current: Set[str], allowed: Set[str]) -> set[str]:
    """Systems the employee has that `allowed` does not include."""
    return set(current) - set(allowed)


def access_to_add(current: Set[str], allowed: Set[str]) -> set[str]:
    """Systems in `allowed` that the employee does not have yet."""
    return set(allowed) - set(current)
