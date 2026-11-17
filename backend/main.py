


from contextlib import asynccontextmanager
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from backend import auth, db, models
from backend.models import (
    EmployeeCreate,
    PasswordResetRequest,
    TicketAdminAction,
    TicketCreate,
    TicketStatus,
)
from backend.orchestrator import process_ticket


# ---------- Application Startup ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MongoDB and provision the initial administrator.
    db.init_db()
    auth.ensure_admin_user()
    yield


app = FastAPI(
    title="OpsAgent",
    description="Multi-Agent IT Helpdesk Automation System",
    version="1.0.0",
    lifespan=lifespan
)


# ---------- CORS ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Authentication ----------

@app.post("/auth/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Authenticate a user and return a JWT access token."""

    user = auth.authenticate_user(
        form_data.username,
        form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth.create_access_token(user["username"])

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.get("/auth/me")
def get_my_profile(
    current_user: dict = Depends(auth.get_current_user)
):
    """Return the identity and role of the logged-in user."""

    return current_user


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: EmployeeCreate):
    """Public registration endpoint for new employee accounts."""

    return auth.create_employee_user(
        payload.username,
        payload.password
    )


@app.post("/auth/forgot-password")
def forgot_password(payload: PasswordResetRequest):
    """Self-service password reset for employee accounts."""

    return auth.reset_user_password(
        payload.username,
        payload.new_password
    )


@app.post("/auth/users", status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    current_user: dict = Depends(
        auth.require_role("admin")
    )
):
    """Allow administrators to create employee accounts."""

    return auth.create_employee_user(
        payload.username,
        payload.password
    )


# ---------- Ticket Submission ----------

@app.post("/tickets", status_code=status.HTTP_201_CREATED)
def submit_ticket(
    payload: TicketCreate,
    current_user: dict = Depends(
        auth.require_role("employee", "admin")
    )
):
    """Submit and process a ticket for the authenticated user."""

    authenticated_username = current_user["username"]

    # Prevent users from submitting tickets under another identity.
    if payload.username.strip() != authenticated_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit tickets under your own username."
        )

    return process_ticket(
        username=authenticated_username,
        description=payload.description,
        attachment_name=payload.attachment_name,
        attachment_size=payload.attachment_size
    )


# ---------- Ticket Listing ----------

@app.get("/tickets")
def get_tickets(
    status_filter: Optional[TicketStatus] = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(auth.get_current_user)
):
    """Admins see all tickets; employees see only their own."""

    username = (
        None
        if current_user["role"] == "admin"
        else current_user["username"]
    )

    return db.list_tickets(
        status=status_filter,
        limit=limit,
        username=username
    )


# ---------- Individual Ticket Retrieval ----------

@app.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(auth.get_current_user)
):
    """Retrieve a ticket with role-based ownership checks."""

    ticket = db.get_ticket(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    if (
        current_user["role"] != "admin"
        and ticket["username"] != current_user["username"]
    ):
        # Return 404 rather than revealing another user's ticket.
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    return ticket


@app.patch("/tickets/{ticket_id}")
def update_ticket_by_admin(
    ticket_id: str,
    payload: TicketAdminAction,
    current_user: dict = Depends(
        auth.require_role("admin")
    )
):
    """Allow administrators to review, add notes, and manually resolve escalated tickets."""

    ticket = db.get_ticket(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    trace_step = {
        "agent": "admin",
        "summary": f"Admin '{current_user['username']}' updated ticket to '{payload.status}'. Notes: {payload.admin_notes}",
        "data": {
            "admin": current_user["username"],
            "notes": payload.admin_notes,
            "previous_status": ticket.get("status"),
            "new_status": payload.status,
        },
        "timestamp": models.now()
    }

    db.append_trace(ticket_id, trace_step)

    updated = db.update_ticket(
        ticket_id,
        {
            "status": payload.status,
            "admin_notes": payload.admin_notes,
            "resolved_by": current_user["username"],
            "resolved_at": models.now(),
        }
    )

    return updated


# ---------- Dashboard Statistics ----------

@app.get("/stats")
def get_dashboard_stats(
    current_user: dict = Depends(
        auth.require_role("admin")
    )
):
    """Only administrators can view system-wide statistics."""

    return db.get_stats()


# ---------- Seed Realistic Demo Tickets (Admin Utility) ----------

@app.post("/admin/seed-demo-tickets")
def seed_demo_tickets(
    current_user: dict = Depends(
        auth.require_role("admin")
    )
):
    """Seed realistic demonstration tickets across VPN, Account, Disk, and Other."""
    from datetime import timedelta

    base_time = models.now()
    demo_samples = [
        {
            "ticket_id": "vpn-01a",
            "username": "alice",
            "description": "VPN connection drops every 5 minutes while accessing internal git repositories.",
            "status": "resolved",
            "triage": {"category": "VPN", "urgency": "High", "reasoning": "VPN connection failure blocking work on internal repos."},
            "diagnosis": {"service": "VPN", "service_status": "down", "probable_cause": "VPN gateway connection timeout.", "recommended_action": "reset_vpn", "details": {"status": "down", "cause": "gateway_timeout", "fixable": True}},
            "resolution": {"action_taken": "reset_vpn", "fix_succeeded": True, "verified": True, "escalated": False, "message": "VPN gateway reset, service restored. The service status was verified successfully."},
            "processing_seconds": 3.8,
            "created_at": base_time - timedelta(hours=3),
            "updated_at": base_time - timedelta(hours=3)
        },
        {
            "ticket_id": "acc-02b",
            "username": "bob",
            "description": "I entered my password wrong 4 times and now my account is locked.",
            "status": "resolved",
            "triage": {"category": "Account", "urgency": "High", "reasoning": "Account lockout preventing access to systems."},
            "diagnosis": {"service": "Account", "service_status": "locked", "probable_cause": "Account locked after repeated failed logins.", "recommended_action": "unlock_account", "details": {"status": "locked", "failed_attempts": 4, "fixable": True}},
            "resolution": {"action_taken": "unlock_account", "fix_succeeded": True, "verified": True, "escalated": False, "message": "Account 'bob' unlocked. The service status was verified successfully."},
            "processing_seconds": 4.1,
            "created_at": base_time - timedelta(hours=2, minutes=30),
            "updated_at": base_time - timedelta(hours=2, minutes=30)
        },
        {
            "ticket_id": "dsk-03c",
            "username": "alice",
            "description": "Disk space warning on drive C: with only 2% free space left.",
            "status": "resolved",
            "triage": {"category": "Disk", "urgency": "Medium", "reasoning": "Low storage warning approaching critical threshold."},
            "diagnosis": {"service": "Disk", "service_status": "critical", "probable_cause": "Disk usage at 96% (critical).", "recommended_action": "cleanup_disk", "details": {"level": "critical", "usage_percent": 96.0}},
            "resolution": {"action_taken": "cleanup_disk", "fix_succeeded": True, "verified": True, "escalated": False, "message": "Cleanup freed 120 GB (96% -> 72%). The service status was verified successfully."},
            "processing_seconds": 3.2,
            "created_at": base_time - timedelta(hours=2),
            "updated_at": base_time - timedelta(hours=2)
        },
        {
            "ticket_id": "vpn-04e",
            "username": "employee1",
            "description": "VPN client error: SSL certificate expired yesterday, cannot establish tunnel.",
            "status": "escalated",
            "triage": {"category": "VPN", "urgency": "High", "reasoning": "Client SSL certificate expired completely preventing tunnel connection."},
            "diagnosis": {"service": "VPN", "service_status": "cert_expired", "probable_cause": "Client SSL/VPN certificate has expired and requires manual re-issuance by an IT administrator.", "recommended_action": None},
            "resolution": {"action_taken": None, "fix_succeeded": False, "verified": False, "escalated": True, "escalation_reason": "Client SSL/VPN certificate has expired and requires manual re-issuance by an IT administrator.", "message": "No automatic fix is available. The issue requires human review."},
            "processing_seconds": 4.5,
            "escalated_at": base_time - timedelta(hours=1, minutes=15),
            "created_at": base_time - timedelta(hours=1, minutes=15),
            "updated_at": base_time - timedelta(hours=1, minutes=15)
        },
        {
            "ticket_id": "acc-05h",
            "username": "john_doe",
            "description": "Cannot sign in to corporate systems, HR department placed account on hold during department transfer.",
            "status": "resolved",
            "triage": {"category": "Account", "urgency": "High", "reasoning": "Account disabled by administrative HR policy."},
            "diagnosis": {"service": "Account", "service_status": "disabled_by_hr", "probable_cause": "Account access restricted by HR department policy; requires HR administrative authorization.", "recommended_action": None},
            "resolution": {"action_taken": None, "fix_succeeded": False, "verified": False, "escalated": True, "escalation_reason": "Account access restricted by HR department policy; requires HR administrative authorization.", "message": "No automatic fix is available. The issue requires human review."},
            "processing_seconds": 3.9,
            "admin_notes": "Contacted HR department, verified department transfer completed, and removed administrative hold in Active Directory.",
            "resolved_by": current_user["username"],
            "resolved_at": base_time - timedelta(minutes=45),
            "created_at": base_time - timedelta(hours=1),
            "updated_at": base_time - timedelta(minutes=45)
        },
        {
            "ticket_id": "oth-06p",
            "username": "alice",
            "description": "The office network printer on the 3rd floor is jamming and out of toner.",
            "status": "escalated",
            "triage": {"category": "Other", "urgency": "Low", "reasoning": "Hardware printer paper jam and supplies replenishment."},
            "diagnosis": {"service": "none", "service_status": "not_applicable", "probable_cause": "Issue is outside the supported services (VPN, Account, Disk)", "recommended_action": None},
            "resolution": {"action_taken": None, "fix_succeeded": False, "verified": False, "escalated": True, "escalation_reason": "Issue is outside the supported services (VPN, Account, Disk)", "message": "This issue requires human support."},
            "processing_seconds": 2.1,
            "escalated_at": base_time - timedelta(minutes=30),
            "created_at": base_time - timedelta(minutes=30),
            "updated_at": base_time - timedelta(minutes=30)
        }
    ]

    inserted_count = 0
    for sample in demo_samples:
        existing = db.get_ticket(sample["ticket_id"])
        if not existing:
            ticket_obj = models.Ticket(**sample)
            db.create_ticket(ticket_obj)
            inserted_count += 1

    return {
        "message": f"Successfully seeded {inserted_count} demo tickets.",
        "seeded_count": inserted_count,
        "total_samples": len(demo_samples)
    }
