"""Role-based access policy: the systems each job role is entitled to."""

ROLE_ACCESS: dict[str, frozenset[str]] = {
    "cashier": frozenset({"pos", "timeclock", "email"}),
    "stocker": frozenset({"inventory", "timeclock", "email"}),
    "pharmacist": frozenset({"pharmacy_system", "timeclock", "email"}),
    "store_manager": frozenset({"pos", "inventory", "scheduling", "reports", "timeclock", "email"}),
    "software_engineer": frozenset({"github", "cloud_console", "vpn", "email"}),
    "it_admin": frozenset({"admin_console", "vpn", "email"}),
}


def is_valid_role(role: str) -> bool:
    return role in ROLE_ACCESS


def access_for(role: str) -> frozenset[str]:
    return ROLE_ACCESS[role]
