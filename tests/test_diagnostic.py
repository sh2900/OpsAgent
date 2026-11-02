
import pytest
from fastapi.testclient import TestClient

from sim_backend.main import sim
from agents import diagnostic, tools
from agents.diagnostic import _LLMDiagnosis


sim_client = TestClient(sim)


class FakeChain:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def invoke(self, messages):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    # Use the in-process simulator instead of a running server.
    monkeypatch.setattr(
        tools,
        "_http",
        lambda: TestClient(sim)
    )

    monkeypatch.setattr(
        diagnostic.time,
        "sleep",
        lambda s: None
    )

    sim_client.post("/sim/reset")


def use_llm(monkeypatch, result=None, error=None):
    monkeypatch.setattr(
        diagnostic,
        "_get_chain",
        lambda: FakeChain(result, error)
    )


def test_vpn_down(monkeypatch):
    sim_client.post("/sim/scenario/vpn_down")

    use_llm(
        monkeypatch,
        _LLMDiagnosis(
            probable_cause="Gateway timeout",
            recommended_action="reset_vpn"
        )
    )

    d = diagnostic.run_diagnosis(
        "VPN", "alice", "VPN broken"
    )

    assert d.service_status == "down"
    assert d.recommended_action == "reset_vpn"


def test_cert_expired_needs_human(monkeypatch):
    sim_client.post("/sim/scenario/vpn_cert_expired")

    use_llm(
        monkeypatch,
        _LLMDiagnosis(
            probable_cause="Certificate expired",
            recommended_action=None
        )
    )

    d = diagnostic.run_diagnosis(
        "VPN", "alice", "cert error"
    )

    assert d.recommended_action is None


def test_account_locked(monkeypatch):
    sim_client.post("/sim/scenario/account_locked")

    use_llm(
        monkeypatch,
        _LLMDiagnosis(
            probable_cause="Too many failed logins",
            recommended_action="unlock_account"
        )
    )

    d = diagnostic.run_diagnosis(
        "Account", "alice", "locked out"
    )

    assert d.service_status == "locked"
    assert d.recommended_action == "unlock_account"


def test_unknown_user(monkeypatch):
    use_llm(monkeypatch, None)

    d = diagnostic.run_diagnosis(
        "Account", "nobody", "can't log in"
    )

    assert d.service_status == "user_not_found"
    assert d.recommended_action is None


def test_disk_full(monkeypatch):
    sim_client.post("/sim/scenario/disk_full")

    use_llm(
        monkeypatch,
        _LLMDiagnosis(
            probable_cause="Disk nearly full",
            recommended_action="cleanup_disk"
        )
    )

    d = diagnostic.run_diagnosis(
        "Disk", "alice", "disk full"
    )

    assert d.service_status == "critical"
    assert d.recommended_action == "cleanup_disk"


def test_healthy_service_makes_no_llm_call(monkeypatch):
    use_llm(
        monkeypatch,
        error=AssertionError("LLM should not be called")
    )

    d = diagnostic.run_diagnosis(
        "VPN", "alice", "VPN slow"
    )

    assert d.service_status == "up"
    assert d.recommended_action is None


def test_other_category_skips_checks(monkeypatch):
    use_llm(
        monkeypatch,
        error=AssertionError("LLM should not be called")
    )

    d = diagnostic.run_diagnosis(
        "Other", "alice", "printer jam"
    )

    assert d.service == "none"


def test_invalid_llm_action_is_rejected(monkeypatch):
    sim_client.post("/sim/scenario/account_locked")

    use_llm(
        monkeypatch,
        _LLMDiagnosis(
            probable_cause="Unknown issue",
            recommended_action="format_hard_drive"
        )
    )

    d = diagnostic.run_diagnosis(
        "Account", "alice", "locked"
    )

    assert d.recommended_action == "unlock_account"


def test_llm_failure_uses_rules(monkeypatch):
    sim_client.post("/sim/scenario/password_expired")

    use_llm(
        monkeypatch,
        error=RuntimeError("quota")
    )

    d = diagnostic.run_diagnosis(
        "Account", "bob", "can't log in"
    )

    assert d.recommended_action == "reset_password"


def test_backend_unreachable(monkeypatch):
    import httpx

    def boom():
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(tools, "_http", boom)

    d = diagnostic.run_diagnosis(
        "VPN", "alice", "vpn"
    )

    assert d.service_status == "unreachable"
    assert d.recommended_action is None
