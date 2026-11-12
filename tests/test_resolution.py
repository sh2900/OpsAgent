
import httpx
import pytest
from fastapi.testclient import TestClient

from sim_backend.main import sim
from agents import tools
from agents.resolution import run_resolution
from backend.models import DiagnosisResult


sim_client = TestClient(sim)


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    # Use the in-process simulator instead of a running server.
    monkeypatch.setattr(
        tools,
        "_http",
        lambda: TestClient(sim)
    )

    sim_client.post("/sim/reset")


def make_diagnosis(service, status, details, action=None):
    return DiagnosisResult(
        service=service,
        service_status=status,
        probable_cause="Test diagnosis",
        details=details,
        recommended_action=action
    )


# ---------- Successful automatic fixes ----------

def test_vpn_reset_success():
    sim_client.post("/sim/scenario/vpn_down")

    raw = tools.check_vpn()
    diagnosis = make_diagnosis(
        "VPN", raw["status"], raw, "reset_vpn"
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken == "reset_vpn"
    assert result.fix_succeeded is True
    assert result.verified is True
    assert result.escalated is False
    assert tools.check_vpn()["status"] == "up"


def test_account_unlock_success():
    sim_client.post("/sim/scenario/account_locked")

    raw = tools.check_account("alice")
    diagnosis = make_diagnosis(
        "Account", raw["status"], raw, "unlock_account"
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken == "unlock_account"
    assert result.fix_succeeded is True
    assert result.verified is True
    assert result.escalated is False
    assert tools.check_account("alice")["status"] == "active"


def test_password_reset_success():
    sim_client.post("/sim/scenario/password_expired")

    raw = tools.check_account("bob")
    diagnosis = make_diagnosis(
        "Account", raw["status"], raw, "reset_password"
    )

    result = run_resolution(diagnosis, "bob")

    assert result.action_taken == "reset_password"
    assert result.fix_succeeded is True
    assert result.verified is True
    assert result.escalated is False
    assert tools.check_account("bob")["status"] == "active"


def test_disk_cleanup_success():
    sim_client.post("/sim/scenario/disk_full")

    raw = tools.check_disk()
    diagnosis = make_diagnosis(
        "Disk", raw["level"], raw, "cleanup_disk"
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken == "cleanup_disk"
    assert result.fix_succeeded is True
    assert result.verified is True
    assert result.escalated is False
    assert tools.check_disk()["level"] != "critical"


# ---------- Human escalation ----------

def test_expired_vpn_certificate_escalates():
    sim_client.post("/sim/scenario/vpn_cert_expired")

    raw = tools.check_vpn()
    diagnosis = make_diagnosis(
        "VPN", raw["status"], raw
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken is None
    assert result.escalated is True
    assert result.fix_succeeded is False
    assert tools.check_vpn()["status"] == "down"


def test_hr_disabled_account_escalates():
    sim_client.post("/sim/scenario/account_disabled_by_hr")

    raw = tools.check_account("alice")
    diagnosis = make_diagnosis(
        "Account", raw["status"], raw
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken is None
    assert result.escalated is True
    assert result.fix_succeeded is False
    assert tools.check_account("alice")["status"] == "disabled"


def test_failed_disk_cleanup_escalates():
    sim_client.post("/sim/scenario/disk_full_unfixable")

    raw = tools.check_disk()
    diagnosis = make_diagnosis(
        "Disk", raw["level"], raw, "cleanup_disk"
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken == "cleanup_disk"
    assert result.fix_succeeded is False
    assert result.verified is False
    assert result.escalated is True
    assert tools.check_disk()["level"] == "critical"


# ---------- Safety validation ----------

def test_unapproved_action_is_rejected():
    sim_client.post("/sim/scenario/vpn_down")

    raw = tools.check_vpn()
    diagnosis = make_diagnosis(
        "VPN", raw["status"], raw, "cleanup_disk"
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken is None
    assert result.escalated is True
    assert "not approved" in result.escalation_reason
    assert tools.check_vpn()["status"] == "down"


def test_action_incompatible_with_diagnostic_details():
    sim_client.post("/sim/scenario/vpn_cert_expired")

    raw = tools.check_vpn()

    # Deliberately provide an unsafe recommendation.
    diagnosis = make_diagnosis(
        "VPN", raw["status"], raw, "reset_vpn"
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken is None
    assert result.escalated is True
    assert "not supported" in result.escalation_reason
    assert tools.check_vpn()["status"] == "down"


# ---------- Backend failure ----------

def test_backend_unreachable(monkeypatch):
    def boom():
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(tools, "_http", boom)

    diagnosis = make_diagnosis(
        "VPN",
        "down",
        {
            "status": "down",
            "cause": "gateway_timeout",
            "fixable": True
        },
        "reset_vpn"
    )

    result = run_resolution(diagnosis, "alice")

    assert result.action_taken == "reset_vpn"
    assert result.fix_succeeded is False
    assert result.escalated is True
    assert "Cannot reach simulated backend" in result.escalation_reason
