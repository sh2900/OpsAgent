
import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.models import TicketCreate


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


def test_submit_ticket(monkeypatch):
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


def test_list_tickets(monkeypatch):
    def fake_list_tickets(status=None, limit=100):
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


def test_list_tickets_with_status_filter(monkeypatch):
    captured = {}

    def fake_list_tickets(status=None, limit=100):
        captured["status"] = status
        captured["limit"] = limit
        return [SAMPLE_TICKET]

    monkeypatch.setattr(
        main.db,
        "list_tickets",
        fake_list_tickets
    )

    response = client.get(
        "/tickets?status=resolved&limit=10"
    )

    assert response.status_code == 200
    assert captured["status"] == "resolved"
    assert captured["limit"] == 10


def test_get_ticket_by_id(monkeypatch):
    monkeypatch.setattr(
        main.db,
        "get_ticket",
        lambda ticket_id: SAMPLE_TICKET
    )

    response = client.get("/tickets/test1234")

    assert response.status_code == 200
    assert response.json()["ticket_id"] == "test1234"


def test_get_missing_ticket(monkeypatch):
    monkeypatch.setattr(
        main.db,
        "get_ticket",
        lambda ticket_id: None
    )

    response = client.get("/tickets/unknown")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def test_dashboard_stats(monkeypatch):
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


def test_invalid_ticket_submission():
    response = client.post(
        "/tickets",
        json={
            "username": "alice"
        }
    )

    assert response.status_code == 422
