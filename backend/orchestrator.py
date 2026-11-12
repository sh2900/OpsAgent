
import logging
from time import perf_counter

from agents import diagnostic, resolution, triage
from backend import db
from backend.models import Ticket, TraceStep


log = logging.getLogger(__name__)


def _record_trace(
    ticket_id: str,
    agent: str,
    summary: str,
    data: dict | None = None
) -> None:
    """Record one agent's activity in the ticket history."""

    step = TraceStep(
        agent=agent,
        summary=summary,
        data=data or {}
    )

    db.append_trace(
        ticket_id,
        step.model_dump(mode="python")
    )


def process_ticket(username: str, description: str) -> dict:
    """
    Execute the complete OpsAgent workflow:

    Ticket → Triage → Diagnosis → Resolution

    Save every agent result and activity in MongoDB.
    """

    start_time = perf_counter()

    # 1. Create a ticket and mark it as processing.
    ticket = Ticket(
        username=username,
        description=description,
        status="processing"
    )

    db.create_ticket(ticket)
    ticket_id = ticket.ticket_id

    _record_trace(
        ticket_id,
        "system",
        "Ticket received. Automated processing started."
    )

    try:
        # 2. Run the Triage Agent.
        triage_result = triage.run_triage(description)

        db.update_ticket(
            ticket_id,
            {
                "triage": triage_result.model_dump(),
                "status": "processing"
            }
        )

        _record_trace(
            ticket_id,
            "triage",
            (
                f"Ticket classified as {triage_result.category} "
                f"with {triage_result.urgency} urgency."
            ),
            triage_result.model_dump()
        )

        # 3. Run the Diagnostic Agent.
        diagnosis_result = diagnostic.run_diagnosis(
            triage_result.category,
            username,
            description
        )

        db.update_ticket(
            ticket_id,
            {
                "diagnosis": diagnosis_result.model_dump(),
                "status": "processing"
            }
        )

        _record_trace(
            ticket_id,
            "diagnostic",
            (
                f"Identified service status: "
                f"{diagnosis_result.service_status}."
            ),
            diagnosis_result.model_dump()
        )

        # 4. Run the Resolution Agent.
        resolution_result = resolution.run_resolution(
            diagnosis_result,
            username
        )

        # 5. Determine the final ticket status.
        # A ticket is resolved only when the fix succeeds
        # and verification confirms the expected state.

        resolved = (
            resolution_result.fix_succeeded
            and resolution_result.verified
            and not resolution_result.escalated
        )

        if not resolved and not resolution_result.escalated:
            resolution_result = resolution_result.model_copy(
                update={
                    "escalated": True,
                    "escalation_reason": (
                        resolution_result.escalation_reason
                        or "No verified automatic fix was completed. "
                           "Human review is required."
                    ),
                    "message": (
                        "No verified automatic fix was completed. "
                        "The issue requires human review."
                    )
                }
            )

        final_status = "resolved" if resolved else "escalated"

        # 6. Save the resolution and final ticket status.
        elapsed = round(perf_counter() - start_time, 2)

        db.update_ticket(
            ticket_id,
            {
                "resolution": resolution_result.model_dump(),
                "status": final_status,
                "processing_seconds": elapsed
            }
        )

        _record_trace(
            ticket_id,
            "resolution",
            (
                "Ticket automatically resolved."
                if resolved
                else "Automatic resolution unsuccessful. Ticket escalated."
            ),
            resolution_result.model_dump()
        )

    except Exception as e:
        # 7. Handle unexpected orchestration failures.
        log.exception(
            "Orchestration failed for ticket %s",
            ticket_id
        )

        elapsed = round(perf_counter() - start_time, 2)

        db.update_ticket(
            ticket_id,
            {
                "status": "escalated",
                "processing_seconds": elapsed
            }
        )

        _record_trace(
            ticket_id,
            "orchestrator",
            "Unexpected processing error. Ticket escalated.",
            {"error": str(e)}
        )

    # 8. Return the complete stored ticket.
    result = db.get_ticket(ticket_id)

    if result is None:
        raise RuntimeError(
            f"Could not retrieve processed ticket {ticket_id}"
        )

    return result
