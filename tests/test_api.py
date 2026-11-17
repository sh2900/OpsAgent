

from fastapi.testclient import TestClient

from backend import main


client = TestClient(main.app)


SAMPLE_TICKET = {
    "ticket_id": "test1234",
    "username": "alice",
    "description": "VPN is not connecting",
    "status": "resolved",
    "triage": {
        "category": "VPN",
        "urgency": "Medium",
        "reasoning": "VPN connection issue"
    },
    "diagnosis": None,
    "resolution": None,
    "trace": [],
    "processing_seconds": 2.5
}


def authenticate(monkeypatch, username="alice", role="employee"):
    """Override JWT authentication with a test user."""

    test_user = {
        "username": username,
        "role": role,
        "active": True
    }

    monkeypatch.setitem(
        main.app.dependency_overrides,
        main.auth.get_current_user,
        lambda: test_user
    )


def test_submit_ticket(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    captured = {}

    def fake_process_ticket(username, description):
        captured["username"] = username
        captured["description"] = description
        return SAMPLE_TICKET

    monkeypatch.setattr(
        main,
        "process_ticket",
        fake_process_ticket
    )

    response = client.post(
        "/tickets",
        json={
            "username": "alice",
            "description": "VPN is not connecting"
        }
    )

    assert response.status_code == 201
    assert response.json()["ticket_id"] == "test1234"
    assert captured["username"] == "alice"
    assert captured["description"] == "VPN is not connecting"


def test_employee_cannot_submit_for_another_user(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    response = client.post(
        "/tickets",
        json={
            "username": "bob",
            "description": "VPN is not connecting"
        }
    )

    assert response.status_code == 403


def test_list_tickets(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    captured = {}

    def fake_list_tickets(status=None, limit=100, username=None):
        captured["username"] = username
        return [SAMPLE_TICKET]

    monkeypatch.setattr(
        main.db,
        "list_tickets",
        fake_list_tickets
    )

    response = client.get("/tickets")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["ticket_id"] == "test1234"
    assert captured["username"] == "alice"


def test_list_tickets_with_status_filter(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    captured = {}

    def fake_list_tickets(status=None, limit=100, username=None):
        captured["status"] = status
        captured["limit"] = limit
        captured["username"] = username
        return [SAMPLE_TICKET]

    monkeypatch.setattr(
        main.db,
        "list_tickets",
        fake_list_tickets
    )

    response = client.get(
        "/tickets?status_filter=resolved&limit=10"
    )

    assert response.status_code == 200
    assert captured["status"] == "resolved"
    assert captured["limit"] == 10
    assert captured["username"] == "alice"


def test_admin_can_list_all_tickets(monkeypatch):
    authenticate(monkeypatch, "admin", "admin")

    captured = {}

    def fake_list_tickets(status=None, limit=100, username=None):
        captured["username"] = username
        return [SAMPLE_TICKET]

    monkeypatch.setattr(
        main.db,
        "list_tickets",
        fake_list_tickets
    )

    response = client.get("/tickets")

    assert response.status_code == 200
    assert captured["username"] is None


def test_get_ticket_by_id(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    monkeypatch.setattr(
        main.db,
        "get_ticket",
        lambda ticket_id: SAMPLE_TICKET
    )

    response = client.get("/tickets/test1234")

    assert response.status_code == 200
    assert response.json()["ticket_id"] == "test1234"


def test_get_another_employees_ticket_returns_404(monkeypatch):
    authenticate(monkeypatch, "bob", "employee")

    monkeypatch.setattr(
        main.db,
        "get_ticket",
        lambda ticket_id: SAMPLE_TICKET
    )

    response = client.get("/tickets/test1234")

    assert response.status_code == 404


def test_get_missing_ticket(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    monkeypatch.setattr(
        main.db,
        "get_ticket",
        lambda ticket_id: None
    )

    response = client.get("/tickets/unknown")

    assert response.status_code == 404


def test_dashboard_stats(monkeypatch):
    authenticate(monkeypatch, "admin", "admin")

    expected_stats = {
        "total": 1,
        "by_status": {"resolved": 1},
        "by_category": {"VPN": 1},
        "by_urgency": {"Medium": 1},
        "automated_resolution_rate": 100,
        "escalation_rate": 0,
        "avg_response_seconds": 2.5
    }

    monkeypatch.setattr(
        main.db,
        "get_stats",
        lambda: expected_stats
    )

    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json() == expected_stats


def test_employee_cannot_access_dashboard_stats(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    response = client.get("/stats")

    assert response.status_code == 403


def test_unauthenticated_user_cannot_list_tickets():
    response = client.get("/tickets")

    assert response.status_code == 401


def test_invalid_ticket_submission(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    response = client.post(
        "/tickets",
        json={
            "username": "alice"
        }
    )

    assert response.status_code == 422


def test_admin_update_escalated_ticket(monkeypatch):
    authenticate(monkeypatch, "admin", "admin")

    fake_ticket = {
        "ticket_id": "esc123",
        "username": "alice",
        "description": "VPN cert expired",
        "status": "escalated"
    }

    monkeypatch.setattr(main.db, "get_ticket", lambda tid: fake_ticket)
    monkeypatch.setattr(main.db, "append_trace", lambda tid, step: None)
    monkeypatch.setattr(
        main.db,
        "update_ticket",
        lambda tid, fields: {**fake_ticket, **fields}
    )

    response = client.patch(
        "/tickets/esc123",
        json={
            "status": "resolved",
            "admin_notes": "Certificate renewed manually"
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["admin_notes"] == "Certificate renewed manually"


def test_employee_cannot_update_ticket(monkeypatch):
    authenticate(monkeypatch, "alice", "employee")

    response = client.patch(
        "/tickets/esc123",
        json={
            "status": "resolved",
            "admin_notes": "Attempting unauthorized resolve"
        }
    )

    assert response.status_code == 403


def test_public_registration(monkeypatch):
    monkeypatch.setattr(
        main.auth,
        "create_employee_user",
        lambda u, p: {"username": u, "role": "employee", "active": True}
    )

    response = client.post(
        "/auth/register",
        json={
            "username": "new_user",
            "password": "Password123456!"
        }
    )

    assert response.status_code == 201
    assert response.json()["username"] == "new_user"


def test_public_forgot_password(monkeypatch):
    monkeypatch.setattr(
        main.auth,
        "reset_user_password",
        lambda u, p: {"username": u, "message": "Password reset successful"}
    )

    response = client.post(
        "/auth/forgot-password",
        json={
            "username": "existing_user",
            "new_password": "NewPassword123456!"
        }
    )

    assert response.status_code == 200
    assert "Password reset successful" in response.json()["message"]
