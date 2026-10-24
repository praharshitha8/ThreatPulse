import os

os.environ["THREATPULSE_USERNAME"] = "student"
os.environ["THREATPULSE_PASSWORD"] = "Demo123!"

import pytest
import app as threatpulse


@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory application data before each test."""
    threatpulse.failed_attempts.clear()
    threatpulse.blocked_until.clear()
    threatpulse.events.clear()

    for key in threatpulse.totals:
        threatpulse.totals[key] = 0


@pytest.fixture
def client():
    threatpulse.app.config["TESTING"] = True
    return threatpulse.app.test_client()


def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ThreatPulse" in response.data


def test_successful_login():
    message, result_type = threatpulse.check_login(
        "student", "Demo123!"
    )
    assert message == "Login successful!"
    assert result_type == "success"
    assert threatpulse.totals["success"] == 1


def test_invalid_password():
    message, result_type = threatpulse.check_login(
        "student", "wrong-password"
    )
    assert "Login failed" in message
    assert result_type == "error"
    assert threatpulse.totals["failed"] == 1


def test_account_blocked_after_five_failures():
    for _ in range(5):
        threatpulse.check_login("student", "wrong-password")

    assert threatpulse.totals["blocked"] == 1
    assert "student" in threatpulse.blocked_until


def test_blocked_account_cannot_login():
    for _ in range(5):
        threatpulse.check_login("student", "wrong-password")

    message, result_type = threatpulse.check_login(
        "student", "Demo123!"
    )
    assert "temporarily blocked" in message
    assert result_type == "error"


def test_login_form_route(client):
    response = client.post(
        "/simulate",
        data={"username": "student", "password": "Demo123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Login successful!" in response.data
