
import pytest

from backend.config import settings
from backend import db
from backend.models import Ticket, TriageResult


@pytest.fixture(autouse=True)
def test_database():
    """Use a separate database for testing."""

    original = settings.mongo_db
    settings.mongo_db = "opsagent_test"

    db.tickets().delete_many({})
    db.init_db()

    yield

    db.tickets().delete_many({})
    settings.mongo_db = original


def make_ticket(**kw):
    return Ticket(
        username="alice",
        description="Cannot connect to VPN",
        **kw
    )


# Test 1: Create a ticket and retrieve it
def test_create_and_get():
    ticket = make_ticket()

    db.create_ticket(ticket)

    got = db.get_ticket(ticket.ticket_id)

    assert got["username"] == "alice"
    assert got["status"] == "open"
    assert "_id" not in got


# Test 2: Check a ticket that doesn't exist
def test_get_missing_returns_none():
    assert db.get_ticket("doesnotexist") is None


# Test 3: Update a ticket with triage information
def test_update_with_nested_models():
    ticket = make_ticket()

    db.create_ticket(ticket)

    triage = TriageResult(
        category="VPN",
        urgency="High",
        reasoning="Remote access is unavailable"
    )

    db.update_ticket(
        ticket.ticket_id,
        {
            "triage": triage.model_dump(),
            "status": "processing"
        }
    )

    got = db.get_ticket(ticket.ticket_id)

    assert got["triage"]["category"] == "VPN"
    assert got["status"] == "processing"


# Test 4: Append agent activity to ticket history
def test_append_trace():
    ticket = make_ticket()

    db.create_ticket(ticket)

    db.append_trace(
        ticket.ticket_id,
        {
            "agent": "triage",
            "summary": "Classified as VPN"
        }
    )

    db.append_trace(
        ticket.ticket_id,
        {
            "agent": "diagnostic",
            "summary": "VPN is down"
        }
    )

    trace = db.get_ticket(ticket.ticket_id)["trace"]

    assert [step["agent"] for step in trace] == [
        "triage",
        "diagnostic"
    ]


# Test 5: List tickets and filter by status
def test_list_filter_by_status():
    a = make_ticket()
    b = make_ticket()

    db.create_ticket(a)
    db.create_ticket(b)

    db.update_ticket(
        b.ticket_id,
        {"status": "escalated"}
    )

    assert len(db.list_tickets()) == 2

    assert len(
        db.list_tickets(status="escalated")
    ) == 1


# Test 6: Generate ticket statistics
def test_stats():
    test_data = [
        ("resolved", "VPN"),
        ("resolved", "Disk"),
        ("escalated", "VPN")
    ]

    for status, category in test_data:
        ticket = make_ticket()

        db.create_ticket(ticket)

        db.update_ticket(
            ticket.ticket_id,
            {
                "status": status,
                "triage": {
                    "category": category,
                    "urgency": "Low",
                    "reasoning": ""
                },
                "processing_seconds": 2.0
            }
        )

    stats = db.get_stats()

    assert stats["total"] == 3
    assert stats["by_category"]["VPN"] == 2

    assert stats["automated_resolution_rate"] == 66.7
    assert stats["escalation_rate"] == 33.3

    assert stats["avg_response_seconds"] == 2.0
