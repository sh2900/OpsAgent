
import httpx


API_BASE_URL = "http://localhost:8000"


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
    token: str
) -> dict:
    """Submit a ticket using the authenticated user's identity."""

    try:
        response = httpx.post(
            f"{API_BASE_URL}/tickets",
            json={
                "username": username,
                "description": description
            },
            headers=_headers(token),
            timeout=180
        )

        return _handle_response(response, "Ticket submission")

    except httpx.RequestError as e:
        raise RuntimeError(
            "Could not connect to the OpsAgent backend."
        ) from e


# ---------- Individual Ticket Retrieval ----------

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
