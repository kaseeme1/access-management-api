from app.roles import ROLE_ACCESS

MARIA = {"name": "Maria Lopez", "email": "maria.lopez@example.com", "department": "Store 112", "role": "cashier"}


def test_health_needs_no_key(client):
    client.headers.pop("X-API-Key")
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_api_key_rejected(client):
    client.headers.pop("X-API-Key")
    assert client.get("/employees").status_code == 401


def test_wrong_api_key_rejected(client):
    assert client.get("/employees", headers={"X-API-Key": "nope"}).status_code == 401


def test_roles_endpoint(client):
    body = client.get("/roles").json()
    assert body["cashier"] == sorted(ROLE_ACCESS["cashier"])


def test_onboard_endpoint(client):
    r = client.post("/employees", json=MARIA, headers={"X-Actor": "hr.portal"})
    assert r.status_code == 201
    body = r.json()
    assert body["access"] == sorted(ROLE_ACCESS["cashier"])
    assert client.get(f"/employees/{body['id']}").json()["email"] == MARIA["email"]


def test_onboard_bad_email_rejected(client):
    assert client.post("/employees", json={**MARIA, "email": "not-an-email"}).status_code == 422


def test_onboard_unknown_role_is_400(client):
    assert client.post("/employees", json={**MARIA, "role": "ceo"}).status_code == 400


def test_onboard_duplicate_is_409(client):
    client.post("/employees", json=MARIA)
    assert client.post("/employees", json=MARIA).status_code == 409


def test_missing_employee_is_404(client):
    assert client.get("/employees/999").status_code == 404
    assert client.post("/employees/999/offboard").status_code == 404


def test_change_role_endpoint(client):
    emp_id = client.post("/employees", json=MARIA).json()["id"]
    r = client.patch(f"/employees/{emp_id}/role", json={"role": "store_manager"})
    assert r.status_code == 200
    assert r.json()["added"] == ["inventory", "reports", "scheduling"]


def test_offboard_endpoint_and_audit_trail(client):
    emp_id = client.post("/employees", json=MARIA, headers={"X-Actor": "hr.portal"}).json()["id"]
    r = client.post(f"/employees/{emp_id}/offboard", headers={"X-Actor": "hr.portal"})
    assert r.status_code == 200
    assert r.json()["revoked"] == sorted(ROLE_ACCESS["cashier"])
    assert client.post(f"/employees/{emp_id}/offboard").status_code == 409

    log = client.get("/audit-log", params={"employee_id": emp_id}).json()
    assert [e["action"] for e in log] == ["onboard", "offboard"]
    assert all(e["actor"] == "hr.portal" for e in log)


def test_failed_request_changes_nothing(client):
    client.post("/employees", json=MARIA)
    client.post("/employees", json=MARIA)
    assert len(client.get("/employees").json()) == 1
    assert len(client.get("/audit-log").json()) == 1


def test_access_review_endpoint(client):
    client.post("/employees", json=MARIA)
    assert client.get("/access-review").json() == []
