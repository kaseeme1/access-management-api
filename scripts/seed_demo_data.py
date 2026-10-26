"""
Load a demo company into the database, including a few planted access problems
for the access review to find.

Usage:
    python scripts/seed_demo_data.py [--db access.db]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import repository as repo  # noqa: E402
from app.database import connect  # noqa: E402
from app.services import change_role, offboard_employee, onboard_employee  # noqa: E402

EMPLOYEES = [
    ("Maria Lopez", "maria.lopez@example.com", "Store 112", "cashier"),
    ("James Carter", "james.carter@example.com", "Store 112", "stocker"),
    ("Aisha Khan", "aisha.khan@example.com", "Store 112", "store_manager"),
    ("Daniel Kim", "daniel.kim@example.com", "Pharmacy", "pharmacist"),
    ("Priya Patel", "priya.patel@example.com", "Engineering", "software_engineer"),
    ("Tom Nguyen", "tom.nguyen@example.com", "IT", "it_admin"),
    ("Chris Walker", "chris.walker@example.com", "Store 205", "cashier"),
    ("Sam Rivera", "sam.rivera@example.com", "Store 205", "stocker"),
]


def seed(db_path: str) -> None:
    conn = connect(db_path)
    ids = {}
    for name, email, dept, role in EMPLOYEES:
        ids[email] = onboard_employee(conn, name, email, dept, role, actor="seed").id

    change_role(conn, ids["james.carter@example.com"], "store_manager", actor="hr.portal")
    offboard_employee(conn, ids["sam.rivera@example.com"], actor="hr.portal")

    repo.grant_access(conn, ids["chris.walker@example.com"], {"admin_console"})
    repo.revoke_access(conn, ids["daniel.kim@example.com"], {"pharmacy_system"})
    repo.grant_access(conn, ids["sam.rivera@example.com"], {"vpn"})

    conn.commit()
    conn.close()
    print(f"seeded {len(EMPLOYEES)} employees into {db_path}")


def main() -> None:
    p = argparse.ArgumentParser(description="Seed the access database with demo data.")
    p.add_argument("--db", default="access.db")
    seed(p.parse_args().db)


if __name__ == "__main__":
    main()
