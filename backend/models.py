
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# Allowed ticket categories
Category = Literal["VPN", "Account", "Disk", "Other"]

# Allowed urgency levels
Urgency = Literal["Low", "Medium", "High"]

# Allowed ticket statuses
TicketStatus = Literal[
    "open",
    "processing",
    "resolved",
    "escalated",
    "closed"
]


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- API Input ----------

class TicketCreate(BaseModel):
    """Information submitted by the employee."""

    username: str = Field(..., examples=["alice"])
    description: str = Field(..., min_length=5)
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None

class EmployeeCreate(BaseModel):
    """Information required to create an employee account."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=64
    )

    password: str = Field(
        ...,
        min_length=12,
        max_length=128
    )

class PasswordResetRequest(BaseModel):
    """Information required to reset an account password."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=64
    )

    new_password: str = Field(
        ...,
        min_length=12,
        max_length=128
    )

class TicketAdminAction(BaseModel):
    """Action taken by an IT administrator on an escalated ticket."""

    status: Literal["resolved", "escalated", "closed"] = "resolved"
    admin_notes: str = Field(..., min_length=2, description="Explanation of manual resolution or action taken")

# ---------- Agent Outputs ----------

class TriageResult(BaseModel):
    """Output from the Ticket Triage Agent."""

    category: Category = Field(
        description="Which IT service the issue relates to"
    )

    urgency: Urgency = Field(
        description="How urgent the issue is"
    )

    reasoning: str = Field(
        description="One short sentence explaining the choice"
    )


class DiagnosisResult(BaseModel):
    """Output from the Diagnostic Agent."""

    service: str

    service_status: str = Field(
        description="For example: down, locked, critical or ok"
    )

    probable_cause: str

    details: dict = Field(
        default_factory=dict,
        description="Raw backend response"
    )

    recommended_action: Optional[str] = Field(
        default=None,
        description="One approved fix, or null if none applies"
    )


class ResolutionResult(BaseModel):
    """Output from the Resolution Agent."""

    action_taken: Optional[str] = None
    fix_succeeded: bool = False
    verified: bool = False
    escalated: bool = False
    escalation_reason: Optional[str] = None
    message: str = ""


# ---------- Agent Activity Tracking ----------

class TraceStep(BaseModel):
    """One entry in the ticket's activity history."""

    agent: str
    summary: str
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=now)


# ---------- Complete Stored Ticket ----------

class Ticket(BaseModel):

    ticket_id: str = Field(
        default_factory=lambda: uuid4().hex[:8]
    )

    username: str
    description: str

    status: TicketStatus = "open"

    triage: Optional[TriageResult] = None
    diagnosis: Optional[DiagnosisResult] = None
    resolution: Optional[ResolutionResult] = None

    trace: list[TraceStep] = Field(default_factory=list)

    processing_seconds: Optional[float] = None
    admin_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
