import io
import time
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.security.authentication import create_access_token, hash_password, verify_password
from app.security.rate_limiter import limiter

client = TestClient(app)


def test_password_hashing_and_verification():
    """Verify bcrypt salt, hashing, and matching logic."""
    raw_pass = "TestSecurePassword#2026!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_login_successful_admin(mock_db):
    """Verify successful authentication returns valid JWT access token and user metadata."""
    res = client.post(
        "/api/auth/login",
        json={"username": settings.admin_default_username, "password": settings.admin_default_password},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == settings.admin_default_username
    assert data["user"]["role"] == "admin"
    assert "password" not in str(data)


def test_login_successful_analyst(mock_db):
    """Verify analyst authentication."""
    res = client.post(
        "/api/auth/login",
        json={"username": settings.analyst_default_username, "password": settings.analyst_default_password},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["username"] == settings.analyst_default_username
    assert data["user"]["role"] == "analyst"


def test_login_invalid_password(mock_db):
    """Verify invalid password returns 401 Unauthorized without leaking account existence."""
    res = client.post(
        "/api/auth/login",
        json={"username": settings.admin_default_username, "password": "WrongPassword999!"},
    )
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_login_nonexistent_user(mock_db):
    """Verify unknown user returns 401 Unauthorized."""
    res = client.post(
        "/api/auth/login",
        json={"username": "ghost_user", "password": "AnyPassword123!"},
    )
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_me_endpoint_requires_auth():
    """Verify /api/auth/me rejects unauthenticated requests."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_endpoint_with_valid_token(analyst_headers):
    """Verify /api/auth/me returns profile when presented with valid Bearer token."""
    res = client.get("/api/auth/me", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == settings.analyst_default_username
    assert data["role"] == "analyst"


def test_invalid_bearer_token():
    """Verify malformed or forged JWT is rejected with 401."""
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer forged.token.signature"})
    assert res.status_code == 401
    assert "Could not validate credentials" in res.json()["detail"]


def test_expired_bearer_token():
    """Verify expired JWT is rejected with 401."""
    expired_token = create_access_token(
        data={"sub": settings.analyst_default_username, "role": "analyst"},
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_admin_registers_new_user(mock_db, admin_headers):
    """Verify administrator can provision a new analyst account."""
    new_user = {
        "username": "tier2_analyst",
        "email": "tier2@cybersentinel.local",
        "password": "SecurePassword123!",
        "role": "analyst",
    }
    res = client.post("/api/auth/register", json=new_user, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "tier2_analyst"
    assert data["role"] == "analyst"
    assert "password" not in str(data)

    # Verify newly created user can log in
    login_res = client.post(
        "/api/auth/login",
        json={"username": "tier2_analyst", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200


def test_analyst_cannot_register_user(mock_db, analyst_headers):
    """Verify non-admin analyst receives 403 Forbidden when trying to register new user."""
    payload = {
        "username": "rogue_user",
        "email": "rogue@test.local",
        "password": "Password123!",
        "role": "admin",
    }
    res = client.post("/api/auth/register", json=payload, headers=analyst_headers)
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_rate_limiting_enforcement():
    """Verify endpoint enforces rate limit and returns HTTP 429."""
    limiter.reset()
    # auth_rate_limit_per_minute is 15. Sending 16 requests should trigger 429
    last_res = None
    for _ in range(16):
        last_res = client.post(
            "/api/auth/login",
            json={"username": "test_rl", "password": "BadPassword123!"},
        )
    assert last_res is not None
    assert last_res.status_code == 429
    assert "Retry-After" in last_res.headers
    assert "Rate limit exceeded" in last_res.json()["detail"]
    limiter.reset()


def test_security_headers_present():
    """Verify defense-in-depth security headers and X-Request-ID are present."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["X-XSS-Protection"] == "1; mode=block"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_healthz_endpoint():
    """Verify lightweight /healthz endpoint for container orchestrators."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_oversized_upload_rejection_413(analyst_headers):
    """Verify files exceeding 10MB are rejected with HTTP 413."""
    # Create an in-memory stream exceeding 10MB (11MB)
    oversized_data = b"0" * (11 * 1024 * 1024)
    file_obj = io.BytesIO(oversized_data)
    res = client.post(
        "/api/events/upload",
        files={"file": ("large_log.json", file_obj, "application/json")},
        headers=analyst_headers,
    )
    assert res.status_code == 413
    assert "exceeds maximum allowed limit" in res.json()["detail"]


def test_audit_log_records_auth_failures(mock_db):
    """Verify failed logins produce audit records without storing the attempted password."""
    client.post(
        "/api/auth/login",
        json={"username": "hacker_target", "password": "MySuperSecretPasswordAttempt"},
    )
    failed_logs = list(mock_db.audit_logs.find({"action": "auth_failure"}))
    assert len(failed_logs) >= 1
    recent = failed_logs[-1]
    assert recent["resource_id"] == "hacker_target"
    # Verify password was NEVER recorded in audit logs
    assert "MySuperSecretPasswordAttempt" not in str(recent)
