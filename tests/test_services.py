import pytest

from app import repository as repo
from app.models import (
    DuplicateEmployeeError,
    EmployeeNotActiveError,
    EmployeeNotFoundError,
    UnknownRoleError,
)
from app.roles import ROLE_ACCESS
from app.services import change_role, offboard_employee, onboard_employee, review_access


def onboard(conn, email="maria.lopez@example.com", role="cashier", name="Maria Lopez", dept="Store 112"):
    return onboard_employee(conn, name, email, dept, role, actor="tester")



def test_onboard_creates_active_employee(conn):
    emp = onboard(conn)
    assert emp.id is not None
    assert emp.name == "Maria Lopez"
    assert emp.role == "cashier"
    assert emp.status == "active"


def test_onboard_grants_exactly_the_role_access(conn):
    emp = onboard(conn, role="store_manager")
    assert set(emp.access) == ROLE_ACCESS["store_manager"]
    assert repo.get_access(conn, emp.id) == ROLE_ACCESS["store_manager"]


def test_onboard_unknown_role_rejected(conn):
    with pytest.raises(UnknownRoleError):
        onboard(conn, role="ceo")
    assert repo.list_employees(conn) == []


def test_onboard_duplicate_email_rejected(conn):
    onboard(conn)
    with pytest.raises(DuplicateEmployeeError):
        onboard(conn, email="MARIA.LOPEZ@example.com")
    assert len(repo.list_employees(conn)) == 1


def test_onboard_is_audited(conn):
    emp = onboard(conn)
    log = repo.list_audit(conn, emp.id)
    assert len(log) == 1
    assert log[0]["action"] == "onboard"
    assert log[0]["actor"] == "tester"



def test_promotion_adds_new_access(conn):
    emp = onboard(conn, role="cashier")
    result = change_role(conn, emp.id, "store_manager", actor="tester")
    assert result.old_role == "cashier"
    assert result.new_role == "store_manager"
    assert result.added == ["inventory", "reports", "scheduling"]
    assert result.removed == []
    assert repo.get_access(conn, emp.id) == ROLE_ACCESS["store_manager"]
    assert repo.get_employee(conn, emp.id).role == "store_manager"


def test_role_change_removes_access_the_new_role_does_not_need(conn):
    emp = onboard(conn, role="store_manager")
    result = change_role(conn, emp.id, "stocker", actor="tester")
    assert result.added == []
    assert result.removed == ["pos", "reports", "scheduling"]
    assert repo.get_access(conn, emp.id) == ROLE_ACCESS["stocker"]


def test_role_change_to_unrelated_role_swaps_access(conn):
    emp = onboard(conn, role="cashier")
    result = change_role(conn, emp.id, "software_engineer", actor="tester")
    assert result.added == ["cloud_console", "github", "vpn"]
    assert result.removed == ["pos", "timeclock"]
    assert repo.get_access(conn, emp.id) == ROLE_ACCESS["software_engineer"]


def test_role_change_also_removes_access_that_was_never_part_of_the_old_role(conn):
    emp = onboard(conn, role="cashier")
    repo.grant_access(conn, emp.id, {"admin_console"})
    result = change_role(conn, emp.id, "stocker", actor="tester")
    assert "admin_console" in result.removed
    assert repo.get_access(conn, emp.id) == ROLE_ACCESS["stocker"]


def test_role_change_unknown_role(conn):
    emp = onboard(conn)
    with pytest.raises(UnknownRoleError):
        change_role(conn, emp.id, "ceo", actor="tester")
    assert repo.get_employee(conn, emp.id).role == "cashier"


def test_role_change_missing_employee(conn):
    with pytest.raises(EmployeeNotFoundError):
        change_role(conn, 999, "stocker", actor="tester")


def test_role_change_terminated_employee(conn):
    emp = onboard(conn)
    offboard_employee(conn, emp.id, actor="tester")
    with pytest.raises(EmployeeNotActiveError):
        change_role(conn, emp.id, "stocker", actor="tester")
    assert repo.get_access(conn, emp.id) == set()


def test_role_change_is_audited(conn):
    emp = onboard(conn)
    change_role(conn, emp.id, "store_manager", actor="hr.portal")
    log = repo.list_audit(conn, emp.id)
    assert [e["action"] for e in log] == ["onboard", "role_change"]
    assert log[-1]["actor"] == "hr.portal"



def test_offboard_revokes_everything(conn):
    emp = onboard(conn, role="store_manager")
    revoked = offboard_employee(conn, emp.id, actor="tester")
    assert revoked == sorted(ROLE_ACCESS["store_manager"])
    assert repo.get_access(conn, emp.id) == set()


def test_offboard_marks_terminated(conn):
    emp = onboard(conn)
    offboard_employee(conn, emp.id, actor="tester")
    after = repo.get_employee(conn, emp.id)
    assert after.status == "terminated"
    assert after.terminated_at is not None


def test_offboard_revokes_access_outside_the_role_too(conn):
    emp = onboard(conn, role="cashier")
    repo.grant_access(conn, emp.id, {"admin_console", "vpn"})
    revoked = offboard_employee(conn, emp.id, actor="tester")
    assert "admin_console" in revoked and "vpn" in revoked
    assert repo.get_access(conn, emp.id) == set()


def test_offboard_twice_rejected(conn):
    emp = onboard(conn)
    offboard_employee(conn, emp.id, actor="tester")
    with pytest.raises(EmployeeNotActiveError):
        offboard_employee(conn, emp.id, actor="tester")


def test_offboard_missing_employee(conn):
    with pytest.raises(EmployeeNotFoundError):
        offboard_employee(conn, 999, actor="tester")


def test_offboard_is_audited(conn):
    emp = onboard(conn)
    offboard_employee(conn, emp.id, actor="hr.portal")
    log = repo.list_audit(conn, emp.id)
    assert log[-1]["action"] == "offboard"
    assert log[-1]["actor"] == "hr.portal"



def findings_set(findings):
    return {(f.employee_id, f.issue, f.severity, tuple(f.systems)) for f in findings}


def test_review_clean_company_has_no_findings(conn):
    onboard(conn, "a@example.com", "cashier")
    onboard(conn, "b@example.com", "it_admin")
    assert review_access(conn) == []


def test_review_flags_excess_access(conn):
    emp = onboard(conn, role="cashier")
    repo.grant_access(conn, emp.id, {"admin_console", "vpn"})
    assert findings_set(review_access(conn)) == {(emp.id, "excess_access", "HIGH", ("admin_console", "vpn"))}


def test_review_flags_missing_access(conn):
    emp = onboard(conn, role="pharmacist")
    repo.revoke_access(conn, emp.id, {"pharmacy_system"})
    assert findings_set(review_access(conn)) == {(emp.id, "missing_access", "LOW", ("pharmacy_system",))}


def test_review_flags_terminated_with_access(conn):
    emp = onboard(conn)
    offboard_employee(conn, emp.id, actor="tester")
    repo.grant_access(conn, emp.id, {"vpn"})
    assert findings_set(review_access(conn)) == {(emp.id, "terminated_with_access", "CRITICAL", ("vpn",))}


def test_review_terminated_without_access_is_fine(conn):
    emp = onboard(conn)
    offboard_employee(conn, emp.id, actor="tester")
    assert review_access(conn) == []


def test_review_one_employee_can_have_excess_and_missing(conn):
    emp = onboard(conn, role="cashier")
    repo.revoke_access(conn, emp.id, {"pos"})
    repo.grant_access(conn, emp.id, {"inventory"})
    assert findings_set(review_access(conn)) == {
        (emp.id, "excess_access", "HIGH", ("inventory",)),
        (emp.id, "missing_access", "LOW", ("pos",)),
    }


def test_review_finding_includes_name(conn):
    emp = onboard(conn, name="Chris Walker")
    repo.grant_access(conn, emp.id, {"admin_console"})
    assert review_access(conn)[0].name == "Chris Walker"


def test_review_most_severe_first(conn):
    a = onboard(conn, "a@example.com", "pharmacist")
    repo.revoke_access(conn, a.id, {"pharmacy_system"})
    b = onboard(conn, "b@example.com", "cashier")
    repo.grant_access(conn, b.id, {"admin_console"})
    c = onboard(conn, "c@example.com", "stocker")
    offboard_employee(conn, c.id, actor="tester")
    repo.grant_access(conn, c.id, {"vpn"})
    assert [f.severity for f in review_access(conn)] == ["CRITICAL", "HIGH", "LOW"]
