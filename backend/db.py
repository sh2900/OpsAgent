
from functools import lru_cache
from typing import Optional

from pymongo import MongoClient, DESCENDING

from backend.config import settings
from backend.models import Ticket, now


@lru_cache(maxsize=1)
def _client() -> MongoClient:
    """Create and reuse a MongoDB client."""
    return MongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=5000
    )


def tickets():
    """Return the tickets collection."""
    return _client()[settings.mongo_db]["tickets"]

def users():
    """Return the users collection."""
    return _client()[settings.mongo_db]["users"]


def init_db() -> None:
    """Create indexes for faster ticket retrieval."""

    tickets().create_index("ticket_id", unique=True)

    tickets().create_index(
        [("created_at", DESCENDING)]
    )

    tickets().create_index("status")
    users().create_index("username", unique=True)


def _clean(doc: Optional[dict]) -> Optional[dict]:
    """Remove MongoDB's internal ObjectId before returning data."""

    if doc:
        doc.pop("_id", None)

    return doc


def create_ticket(ticket: Ticket) -> dict:
    """Insert a new ticket into MongoDB."""

    tickets().insert_one(
        ticket.model_dump(mode="python")
    )

    return _clean(
        ticket.model_dump(mode="python")
    )


def get_ticket(ticket_id: str) -> Optional[dict]:
    """Retrieve a ticket using its ID."""

    return _clean(
        tickets().find_one({"ticket_id": ticket_id})
    )


def update_ticket(ticket_id: str, fields: dict) -> Optional[dict]:
    """Update selected ticket fields."""

    fields = {
        **fields,
        "updated_at": now()
    }

    tickets().update_one(
        {"ticket_id": ticket_id},
        {"$set": fields}
    )

    return get_ticket(ticket_id)


def append_trace(ticket_id: str, step: dict) -> None:
    """Append an agent activity entry to the ticket."""

    tickets().update_one(
        {"ticket_id": ticket_id},
        {
            "$push": {"trace": step},
            "$set": {"updated_at": now()}
        }
    )



def list_tickets(
    status: Optional[str] = None,
    limit: int = 100,
    username: Optional[str] = None
) -> list[dict]:
    """Retrieve tickets, optionally filtered by status and employee."""

    query = {}

    if status:
        query["status"] = status

    if username:
        query["username"] = username

    cursor = (
        tickets()
        .find(query)
        .sort("created_at", DESCENDING)
        .limit(limit)
    )

    return [_clean(doc) for doc in cursor]

def get_stats() -> dict:
    """Generate statistics for the dashboard."""

    def group_by(field: str) -> dict:
        rows = tickets().aggregate([
            {
                "$group": {
                    "_id": f"${field}",
                    "n": {"$sum": 1}
                }
            }
        ])

        return {
            str(row["_id"]): row["n"]
            for row in rows
        }

    total = tickets().count_documents({})

    resolved = tickets().count_documents({
        "status": "resolved"
    })

    escalated = tickets().count_documents({
        "status": "escalated"
    })

    done = resolved + escalated

    avg = list(tickets().aggregate([
        {
            "$match": {
                "processing_seconds": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": None,
                "avg": {"$avg": "$processing_seconds"}
            }
        }
    ]))

    return {
        "total": total,

        "by_status": group_by("status"),

        "by_category": group_by("triage.category"),

        "by_urgency": group_by("triage.urgency"),

        "automated_resolution_rate": (
            round(resolved / done * 100, 1) if done else 0
        ),

        "escalation_rate": (
            round(escalated / done * 100, 1) if done else 0
        ),

        "avg_response_seconds": (
            round(avg[0]["avg"], 2) if avg else 0
        )
    }
