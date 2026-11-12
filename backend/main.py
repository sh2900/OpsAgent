


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

from backend import auth, db
from backend.models import TicketCreate, TicketStatus, EmployeeCreate
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
        description=payload.description
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


# ---------- Dashboard Statistics ----------

@app.get("/stats")
def get_dashboard_stats(
    current_user: dict = Depends(
        auth.require_role("admin")
    )
):
    """Only administrators can view system-wide statistics."""

    return db.get_stats()
