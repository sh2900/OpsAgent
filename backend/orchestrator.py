
import logging
from time import perf_counter
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END

from agents import diagnostic, resolution, triage
from backend import db
from backend.models import (
    DiagnosisResult,
    ResolutionResult,
    Ticket,
    TraceStep,
    TriageResult,
    now,
)


log = logging.getLogger(__name__)


# ---------- Trace Logging Helper ----------

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


# ---------- LangGraph State Definition ----------

class TicketWorkflowState(TypedDict, total=False):
    ticket_id: str
    username: str
    description: str
    start_time: float
    triage: Optional[dict]
    diagnosis: Optional[dict]
    resolution: Optional[dict]
    status: str
    error: Optional[str]


# ---------- LangGraph Node Implementations ----------

def _triage_node(state: TicketWorkflowState) -> dict:
    """Node 1: Execute Ticket Triage Agent (Category & Urgency)."""
    ticket_id = state["ticket_id"]
    description = state["description"]

    triage_result = triage.run_triage(description)
    triage_dict = triage_result.model_dump()

    db.update_ticket(
        ticket_id,
        {
            "triage": triage_dict,
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
        triage_dict
    )

    return {"triage": triage_dict}


def _diagnostic_node(state: TicketWorkflowState) -> dict:
    """Node 2: Execute Diagnostic Agent (Checks simulated IT services)."""
    ticket_id = state["ticket_id"]
    username = state["username"]
    description = state["description"]
    category = (state.get("triage") or {}).get("category", "Other")

    diagnosis_result = diagnostic.run_diagnosis(
        category,
        username,
        description
    )
    diagnosis_dict = diagnosis_result.model_dump()

    db.update_ticket(
        ticket_id,
        {
            "diagnosis": diagnosis_dict,
            "status": "processing"
        }
    )

    _record_trace(
        ticket_id,
        "diagnostic",
        f"Identified service status: {diagnosis_result.service_status}.",
        diagnosis_dict
    )

    return {"diagnosis": diagnosis_dict}


def _route_after_diagnosis(state: TicketWorkflowState) -> str:
    """
    Conditional Edge:
    Determine whether a safe predefined fix is available.
    Matches Activity Diagram decision diamond: 'Safe predefined fix available?'
    """
    diagnosis = state.get("diagnosis") or {}
    action = diagnosis.get("recommended_action")

    if action:
        return "resolution_agent"
    return "finalize"


def _resolution_node(state: TicketWorkflowState) -> dict:
    """Node 3: Execute Resolution Agent (Applies fix and verifies outcome)."""
    username = state["username"]
    diag_dict = state.get("diagnosis") or {}
    diagnosis_result = DiagnosisResult(**diag_dict)

    resolution_result = resolution.run_resolution(
        diagnosis_result,
        username
    )

    return {"resolution": resolution_result.model_dump()}


def _finalize_node(state: TicketWorkflowState) -> dict:
    """
    Node 4: Evaluate outcome, verify resolution, and set final ticket status.
    Determines whether ticket is Auto-resolved or Escalated to Human IT Admin.
    """
    ticket_id = state["ticket_id"]
    start_time = state.get("start_time", perf_counter())
    res_dict = state.get("resolution")

    if res_dict:
        resolution_result = ResolutionResult(**res_dict)
    else:
        # No resolution action executed (service healthy, unfixable, or outside scope)
        diag = state.get("diagnosis") or {}
        service_status = diag.get("service_status")

        if service_status in {"up", "active", "ok"}:
            category = (state.get("triage") or {}).get("category", "")
            action_advice = {
                "VPN": "VPN server infrastructure is confirmed operational. Client guidance issued: restart local VPN client, verify local internet, and flush DNS cache.",
                "Account": "Account is confirmed active and in good standing in directory service. Advised employee to verify credentials.",
                "Disk": "System storage capacity is optimal. Advised employee on clearing local workstation temporary files and recycle bin."
            }
            msg = action_advice.get(
                category,
                "Automated diagnostic verification confirmed the service is fully operational."
            )
            resolution_result = ResolutionResult(
                action_taken="automated_diagnostic_verification",
                fix_succeeded=True,
                verified=True,
                escalated=False,
                message=msg
            )
        else:
            reason = diag.get("probable_cause") or "No automatic fix is available. Human review is required."
            resolution_result = ResolutionResult(
                escalated=True,
                escalation_reason=reason,
                message="No automatic fix is available. The issue requires human review."
            )

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
                    or "No verified automatic fix was completed. Human review is required."
                ),
                "message": (
                    "No verified automatic fix was completed. "
                    "The issue requires human review."
                )
            }
        )

    final_status = "resolved" if resolved else "escalated"
    elapsed = round(perf_counter() - start_time, 2)

    fields_to_update = {
        "resolution": resolution_result.model_dump(),
        "status": final_status,
        "processing_seconds": elapsed
    }
    if final_status == "escalated":
        fields_to_update["escalated_at"] = now()

    db.update_ticket(ticket_id, fields_to_update)

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

    return {
        "resolution": resolution_result.model_dump(),
        "status": final_status
    }


# ---------- LangGraph Workflow Builder ----------

def build_orchestrator_graph():
    """
    Build and compile the LangGraph StateGraph coordinating OpsAgent workflow:
    START -> triage_agent -> diagnostic_agent -> [decision diamond]
             -> resolution_agent -> finalize -> END
             -> finalize (escalation) -> END
    """
    builder = StateGraph(TicketWorkflowState)

    builder.add_node("triage_agent", _triage_node)
    builder.add_node("diagnostic_agent", _diagnostic_node)
    builder.add_node("resolution_agent", _resolution_node)
    builder.add_node("finalize", _finalize_node)

    builder.add_edge(START, "triage_agent")
    builder.add_edge("triage_agent", "diagnostic_agent")

    builder.add_conditional_edges(
        "diagnostic_agent",
        _route_after_diagnosis,
        {
            "resolution_agent": "resolution_agent",
            "finalize": "finalize"
        }
    )

    builder.add_edge("resolution_agent", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


# ---------- Orchestrator Class (Matches UML Class Diagram Slide 16) ----------

class Orchestrator:
    """Orchestrator class coordinating agents through LangGraph."""

    def __init__(self):
        self.workflow = build_orchestrator_graph()

    def call_triage_agent(self, description: str) -> TriageResult:
        return triage.run_triage(description)

    def call_diagnostic_agent(
        self,
        category: str,
        username: str,
        description: str
    ) -> DiagnosisResult:
        return diagnostic.run_diagnosis(category, username, description)

    def call_resolution_agent(
        self,
        diagnosis: DiagnosisResult,
        username: str
    ) -> ResolutionResult:
        return resolution.run_resolution(diagnosis, username)

    def process_ticket(
        self,
        username: str,
        description: str,
        attachment_name: Optional[str] = None,
        attachment_size: Optional[int] = None
    ) -> dict:
        """Execute the LangGraph workflow for a newly submitted ticket."""
        start_time = perf_counter()

        # 1. Create initial ticket in processing state
        ticket = Ticket(
            username=username,
            description=description,
            attachment_name=attachment_name,
            attachment_size=attachment_size,
            status="processing"
        )
        db.create_ticket(ticket)
        ticket_id = ticket.ticket_id

        trace_summary = "Ticket received. Automated processing started via LangGraph orchestration."
        if attachment_name:
            kb = round((attachment_size or 0) / 1024, 1)
            trace_summary += f" Attached file: {attachment_name} ({kb} KB)."

        _record_trace(
            ticket_id,
            "system",
            trace_summary
        )

        initial_state: TicketWorkflowState = {
            "ticket_id": ticket_id,
            "username": username,
            "description": description,
            "start_time": start_time,
            "triage": None,
            "diagnosis": None,
            "resolution": None,
            "status": "processing",
            "error": None
        }

        try:
            self.workflow.invoke(initial_state)

        except Exception as e:
            log.exception("Orchestration failed for ticket %s", ticket_id)
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
                "Unexpected processing error in LangGraph execution. Ticket escalated.",
                {"error": str(e)}
            )

        result = db.get_ticket(ticket_id)
        if result is None:
            raise RuntimeError(f"Could not retrieve processed ticket {ticket_id}")

        return result


# Singleton instance
_orchestrator = Orchestrator()


def process_ticket(
    username: str,
    description: str,
    attachment_name: Optional[str] = None,
    attachment_size: Optional[int] = None
) -> dict:
    """Top-level entry point used by FastAPI routes and external callers."""
    return _orchestrator.process_ticket(
        username,
        description,
        attachment_name,
        attachment_size
    )
