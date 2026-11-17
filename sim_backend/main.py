
from fastapi import FastAPI, HTTPException
from sim_backend import state
from sim_backend.state import SCENARIOS

sim = FastAPI(title="Simulated IT Backend")


# ---------- Health ----------
@sim.get("/health")
def health():
    return {
        "status": "sim ok",
        "scenario": state.current_scenario()
    }


# ---------- VPN Services ----------

@sim.get("/vpn/status")
def vpn_status():
    return state.get_state()["vpn"] | {"service": "vpn"}


@sim.post("/vpn/reset")
def vpn_reset():
    vpn = state.get_state()["vpn"]

    if vpn["status"] == "up":
        return {
            "service": "vpn",
            "success": True,
            "message": "VPN already up, nothing to do"
        }

    if vpn["fixable"]:
        vpn.update(status="up", cause=None)

        return {
            "service": "vpn",
            "success": True,
            "message": "VPN gateway reset, service restored"
        }

    return {
        "service": "vpn",
        "success": False,
        "message": f"Reset failed: {vpn['cause']} needs manual intervention"
    }


# ---------- Account Services ----------

def _get_user(username: str) -> dict:
    accounts = state.get_state()["accounts"]
    user = accounts.get(username)

    if not user:
        # Explicit test case for missing user
        if username.lower() == "nobody":
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found"
            )

        # Dynamically provision user matching active scenario
        curr = state.current_scenario()
        if curr in {"account_locked", "multi_failure"}:
            user = {"status": "locked", "failed_attempts": 5, "fixable": True}
        elif curr == "password_expired":
            user = {"status": "password_expired", "failed_attempts": 0, "fixable": True}
        elif curr == "account_disabled_by_hr":
            user = {"status": "disabled", "failed_attempts": 0, "fixable": False}
        else:
            user = {"status": "active", "failed_attempts": 0, "fixable": True}

        accounts[username] = user

    return user


@sim.get("/account/{username}")
def account_status(username: str):
    return _get_user(username) | {
        "service": "account",
        "username": username
    }


@sim.post("/account/{username}/unlock")
def account_unlock(username: str):
    user = _get_user(username)

    if user["status"] == "active":
        return {
            "service": "account",
            "success": True,
            "message": "Account already active"
        }

    if user["status"] == "locked" and user["fixable"]:
        user.update(status="active", failed_attempts=0)

        return {
            "service": "account",
            "success": True,
            "message": f"Account '{username}' unlocked"
        }

    return {
        "service": "account",
        "success": False,
        "message": f"Cannot unlock: account is '{user['status']}'"
    }


@sim.post("/account/{username}/reset-password")
def account_reset_password(username: str):
    user = _get_user(username)

    if user["status"] == "password_expired" and user["fixable"]:
        user.update(status="active")

        return {
            "service": "account",
            "success": True,
            "message": f"Temporary password issued for '{username}'"
        }

    return {
        "service": "account",
        "success": False,
        "message": f"Password reset not applicable: account is '{user['status']}'"
    }


# ---------- Disk Services ----------

def _disk_view(d: dict) -> dict:
    pct = round(d["used_gb"] / d["total_gb"] * 100, 1)

    level = (
        "critical" if pct >= 90
        else "warning" if pct >= 75
        else "ok"
    )

    return {
        "service": "disk",
        "total_gb": d["total_gb"],
        "used_gb": d["used_gb"],
        "usage_percent": pct,
        "level": level
    }


@sim.get("/disk/status")
def disk_status():
    return _disk_view(state.get_state()["disk"])


@sim.post("/disk/cleanup")
def disk_cleanup():
    d = state.get_state()["disk"]

    before = _disk_view(d)["usage_percent"]

    d["used_gb"] = max(
        0,
        d["used_gb"] - d["cleanup_frees_gb"]
    )

    after = _disk_view(d)

    return {
        "service": "disk",
        "success": after["level"] != "critical",
        "message": (
            f"Cleanup freed {d['cleanup_frees_gb']} GB "
            f"({before}% -> {after['usage_percent']}%)"
        ),
        "after": after
    }


# ---------- Simulation Control ----------

@sim.get("/sim/scenarios")
def list_scenarios():
    return {
        "current": state.current_scenario(),
        "available": list(SCENARIOS)
    }


@sim.get("/sim/state")
def sim_state():
    return {
        "scenario": state.current_scenario(),
        "state": state.get_state()
    }


@sim.post("/sim/scenario/{name}")
def set_scenario(name: str):
    try:
        state.load_scenario(name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario. Options: {list(SCENARIOS)}"
        )

    return {
        "scenario": name,
        "state": state.get_state()
    }


@sim.post("/sim/reset")
def sim_reset():
    state.load_scenario("healthy")
    return {"scenario": "healthy"}
