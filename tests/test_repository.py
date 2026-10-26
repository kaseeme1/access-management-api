from app import repository as repo


def test_insert_and_get_employee(conn):
    emp_id = repo.insert_employee(conn, "Maria Lopez", "Maria.Lopez@Example.com", "Store 112", "cashier")
    emp = repo.get_employee(conn, emp_id)
    assert emp.name == "Maria Lopez"
    assert emp.email == "maria.lopez@example.com"
    assert emp.status == "active"
    assert emp.access == []


def test_email_exists_is_case_insensitive(conn):
    repo.insert_employee(conn, "Maria Lopez", "maria.lopez@example.com", "Store 112", "cashier")
    assert repo.email_exists(conn, "MARIA.LOPEZ@example.com")
    assert not repo.email_exists(conn, "someone.else@example.com")


def test_grant_and_revoke_access(conn):
    emp_id = repo.insert_employee(conn, "A", "a@example.com", "X", "cashier")
    repo.grant_access(conn, emp_id, {"pos", "email"})
    repo.grant_access(conn, emp_id, {"pos"})
    assert repo.get_access(conn, emp_id) == {"pos", "email"}
    repo.revoke_access(conn, emp_id, {"pos"})
    assert repo.get_access(conn, emp_id) == {"email"}


def test_get_missing_employee_returns_none(conn):
    assert repo.get_employee(conn, 999) is None


def test_audit_log(conn):
    repo.add_audit(conn, "alice", "onboard", 1, "role=cashier")
    repo.add_audit(conn, "bob", "offboard", 2)
    assert [e["action"] for e in repo.list_audit(conn)] == ["onboard", "offboard"]
    assert [e["actor"] for e in repo.list_audit(conn, employee_id=2)] == ["bob"]
