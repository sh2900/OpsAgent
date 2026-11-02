
import httpx

from backend.config import settings


# Only these fixes are allowed for each service.
ALLOWED_ACTIONS = {
    "VPN": ["reset_vpn"],
    "Account": ["unlock_account", "reset_password"],
    "Disk": ["cleanup_disk"],
}


class BackendUnreachable(Exception):
    """Raised when the simulated IT backend cannot be reached."""
    pass


def _http() -> httpx.Client:
    return httpx.Client(
        base_url=settings.sim_backend_url,
        timeout=5
    )


def _call(method: str, path: str) -> dict:
    """Make a request to the simulated IT backend."""

    try:
        with _http() as client:
            resp = client.request(method, path)

    except httpx.HTTPError as e:
        raise BackendUnreachable(
            f"Cannot reach simulated backend: {e}"
        ) from e

    if resp.status_code == 404:
        return {
            "error": "not_found",
            "detail": resp.json().get("detail", "")
        }

    resp.raise_for_status()
    return resp.json()


# ---------- Status checks (Diagnostic Agent) ----------

def check_vpn() -> dict:
    return _call("GET", "/vpn/status")


def check_account(username: str) -> dict:
    return _call("GET", f"/account/{username}")


def check_disk() -> dict:
    return _call("GET", "/disk/status")


# ---------- Fix operations (Resolution Agent) ----------

def reset_vpn() -> dict:
    return _call("POST", "/vpn/reset")


def unlock_account(username: str) -> dict:
    return _call("POST", f"/account/{username}/unlock")


def reset_password(username: str) -> dict:
    return _call("POST", f"/account/{username}/reset-password")


def cleanup_disk() -> dict:
    return _call("POST", "/disk/cleanup")
