
import pytest
from fastapi.testclient import TestClient
from sim_backend.main import sim

client = TestClient(sim)


# Reset the environment before every test
@pytest.fixture(autouse=True)
def reset():
    client.post("/sim/reset")


# Test 1: VPN failure can be fixed
def test_vpn_down_is_fixed_by_reset():
    client.post("/sim/scenario/vpn_down")

    assert client.get("/vpn/status").json()["status"] == "down"

    assert client.post("/vpn/reset").json()["success"] is True

    assert client.get("/vpn/status").json()["status"] == "up"


# Test 2: Expired VPN certificate cannot be fixed automatically
def test_vpn_cert_expired_cannot_be_fixed():
    client.post("/sim/scenario/vpn_cert_expired")

    assert client.post("/vpn/reset").json()["success"] is False

    assert client.get("/vpn/status").json()["status"] == "down"


# Test 3: Locked account can be unlocked
def test_locked_account_unlock():
    client.post("/sim/scenario/account_locked")

    assert client.get("/account/alice").json()["status"] == "locked"

    assert client.post("/account/alice/unlock").json()["success"] is True

    assert client.get("/account/alice").json()["status"] == "active"


# Test 4: HR-disabled account cannot be unlocked
def test_disabled_account_cannot_be_unlocked():
    client.post("/sim/scenario/account_disabled_by_hr")

    assert client.post("/account/alice/unlock").json()["success"] is False


# Test 5: Unknown user returns 404
def test_unknown_user_404():
    assert client.get("/account/nobody").status_code == 404


# Test 6: Disk cleanup successfully fixes a full disk
def test_disk_cleanup_fixes_full_disk():
    client.post("/sim/scenario/disk_full")

    assert client.get("/disk/status").json()["level"] == "critical"

    assert client.post("/disk/cleanup").json()["success"] is True


# Test 7: Insufficient disk cleanup does not fix the problem
def test_disk_cleanup_insufficient():
    client.post("/sim/scenario/disk_full_unfixable")

    assert client.post("/disk/cleanup").json()["success"] is False


# Test 8: Unknown scenario returns 404
def test_unknown_scenario_404():
    assert client.post("/sim/scenario/nope").status_code == 404
