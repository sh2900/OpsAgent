
import httpx


API_BASE_URL = "http://localhost:8000"
SIM_BASE_URL = "http://localhost:8001"


# ---------- Shared Helpers ----------

def _headers(token: str) -> dict:
    if not token:
        raise RuntimeError("Please log in to continue.")

    return {"Authorization": f"Bearer {token}"}


def _handle_response(response, operation: str):
    if response.status_code == 401:
        raise RuntimeError(
            "Your session has expired. Please log in again."
        )

    if response.status_code == 403:
        raise RuntimeError(
            "You do not have permission to perform this action."
        )

    if response.status_code == 404:
        raise RuntimeError("The requested resource was not found.")

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text

        raise RuntimeError(
            f"{operation} failed: {detail}"
        ) from e

    return response.json()


# ---------- Authentication ----------

def login(username: str, password: str) -> dict:
    """Authenticate a user and obtain a JWT token."""

    try:
        response = httpx.post(
            f"{API_BASE_URL}/auth/login",
            data={
                "username": username,
                "password": password
            },
            timeout=15
        )

        return _handle_response(response, "Login")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


def register_user(username: str, password: str) -> dict:
    """Register a new employee account from the login portal."""

    try:
        response = httpx.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "username": username,
                "password": password
            },
            timeout=15
        )

        return _handle_response(response, "Account registration")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


def reset_password_request(username: str, new_password: str) -> dict:
    """Self-service password reset from the login portal."""

    try:
        response = httpx.post(
            f"{API_BASE_URL}/auth/forgot-password",
            json={
                "username": username,
                "new_password": new_password
            },
            timeout=15
        )

        return _handle_response(response, "Password reset")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


def get_me(token: str) -> dict:
    """Retrieve the logged-in user's profile."""

    try:
        response = httpx.get(
            f"{API_BASE_URL}/auth/me",
            headers=_headers(token),
            timeout=15
        )

        return _handle_response(response, "Profile retrieval")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


# ---------- Ticket Submission ----------

def submit_ticket(
    username: str,
    description: str,
    token: str,
    attachment_name: str | None = None,
    attachment_size: int | None = None,
) -> dict:
    """Submit a ticket using the authenticated user's identity."""

    payload = {
        "username": username,
        "description": description,
    }
    if attachment_name is not None:
        payload["attachment_name"] = attachment_name
    if attachment_size is not None:
        payload["attachment_size"] = attachment_size

    try:
        response = httpx.post(
            f"{API_BASE_URL}/tickets",
            json=payload,
            headers=_headers(token),
            timeout=180
        )

        return _handle_response(response, "Ticket submission")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


# ---------- Individual Ticket Retrieval and Update ----------

def get_ticket(ticket_id: str, token: str) -> dict:
    """Retrieve a ticket with authentication."""

    try:
        response = httpx.get(
            f"{API_BASE_URL}/tickets/{ticket_id}",
            headers=_headers(token),
            timeout=15
        )

        return _handle_response(response, "Ticket retrieval")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


def update_ticket_admin(
    ticket_id: str,
    status: str,
    admin_notes: str,
    token: str
) -> dict:
    """Allow administrators to update ticket status and add resolution remarks."""

    try:
        response = httpx.patch(
            f"{API_BASE_URL}/tickets/{ticket_id}",
            json={
                "status": status,
                "admin_notes": admin_notes
            },
            headers=_headers(token),
            timeout=15
        )

        return _handle_response(response, "Ticket update")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


def create_employee_user(
    username: str,
    password: str,
    token: str
) -> dict:
    """Allow administrators to create a new employee account."""

    try:
        response = httpx.post(
            f"{API_BASE_URL}/auth/users",
            json={
                "username": username,
                "password": password
            },
            headers=_headers(token),
            timeout=15
        )

        return _handle_response(response, "Employee creation")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


# ---------- Ticket Listing ----------

def list_tickets(
    token: str,
    status=None,
    limit=100
) -> list:
    """Retrieve tickets accessible to the logged-in user."""

    try:
        params = {"limit": limit}

        if status:
            params["status_filter"] = status

        response = httpx.get(
            f"{API_BASE_URL}/tickets",
            params=params,
            headers=_headers(token),
            timeout=15
        )

        return _handle_response(response, "Ticket listing")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


# ---------- Dashboard Statistics ----------

def get_stats(token: str) -> dict:
    """Retrieve administrator dashboard statistics."""

    try:
        response = httpx.get(
            f"{API_BASE_URL}/stats",
            headers=_headers(token),
            timeout=15
        )

        return _handle_response(response, "Dashboard statistics")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e
# ---------- Demo Mode / Simulator ----------

def get_sim_scenarios() -> dict:
    try:
        response = httpx.get(
            f"{SIM_BASE_URL}/sim/scenarios",
            timeout=10
        )
        return _handle_response(response, "Scenario retrieval")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the simulator. "
            "Make sure the simulator is running on port 8001."
        ) from e


def get_sim_state() -> dict:
    try:
        response = httpx.get(
            f"{SIM_BASE_URL}/sim/state",
            timeout=10
        )
        return _handle_response(response, "Simulator state retrieval")

    except httpx.RequestError as e:
        raise RuntimeError("Could not connect to the simulator.") from e


def set_sim_scenario(name: str) -> dict:
    try:
        response = httpx.post(
            f"{SIM_BASE_URL}/sim/scenario/{name}",
            timeout=10
        )
        return _handle_response(response, "Applying scenario")

    except httpx.RequestError as e:
        raise RuntimeError("Could not connect to the simulator.") from e


def reset_sim_scenario() -> dict:
    try:
        response = httpx.post(
            f"{SIM_BASE_URL}/sim/reset",
            timeout=10
        )
        return _handle_response(response, "Simulator reset")

    except httpx.RequestError as e:
        raise RuntimeError("Could not connect to the simulator.") from e


def seed_demo_tickets(token: str) -> dict:
    """Seed realistic enterprise demo tickets into the database."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/admin/seed-demo-tickets",
            headers=_headers(token),
            timeout=30
        )
        return _handle_response(response, "Seeding demo tickets")

    except httpx.RequestError as e:
        raise RuntimeError("Could not connect to the OpsAgent backend.") from e
