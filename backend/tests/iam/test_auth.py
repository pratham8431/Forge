import pytest
from unittest.mock import patch


BASE = "/api/v1/auth"

VALID_USER = {
    "email": "dev@atlas.internal",
    "password": "Secure123",
    "full_name": "Atlas Developer",
}


# ─── Registration ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    with patch("app.workers.email_tasks.send_verification_email.delay"):
        with patch("app.workers.audit_tasks.log_audit_event.delay"):
            resp = await client.post(f"{BASE}/register", json=VALID_USER)
    assert resp.status_code == 201
    assert "verify your email" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    with patch("app.workers.email_tasks.send_verification_email.delay"):
        with patch("app.workers.audit_tasks.log_audit_event.delay"):
            await client.post(f"{BASE}/register", json=VALID_USER)
            resp = await client.post(f"{BASE}/register", json=VALID_USER)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client):
    resp = await client.post(f"{BASE}/register", json={
        **VALID_USER, "email": "other@atlas.internal", "password": "weak"
    })
    assert resp.status_code == 422


# ─── Login ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_unverified_user(client):
    with patch("app.workers.email_tasks.send_verification_email.delay"):
        with patch("app.workers.audit_tasks.log_audit_event.delay"):
            await client.post(f"{BASE}/register", json={
                **VALID_USER, "email": "unverified@atlas.internal"
            })
    with patch("app.workers.audit_tasks.log_audit_event.delay"):
        resp = await client.post(f"{BASE}/login", json={
            "email": "unverified@atlas.internal",
            "password": VALID_USER["password"],
        })
    assert resp.status_code == 403
    assert "verify your email" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    with patch("app.workers.audit_tasks.log_audit_event.delay"):
        resp = await client.post(f"{BASE}/login", json={
            "email": VALID_USER["email"],
            "password": "WrongPass99",
        })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    with patch("app.workers.audit_tasks.log_audit_event.delay"):
        resp = await client.post(f"{BASE}/login", json={
            "email": "ghost@atlas.internal",
            "password": "Whatever1",
        })
    assert resp.status_code == 401


# ─── Email Verification ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_invalid_token(client):
    resp = await client.post(f"{BASE}/verify-email", json={"token": "invalidtoken"})
    assert resp.status_code == 400


# ─── Forgot Password ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_unknown_email(client):
    with patch("app.workers.audit_tasks.log_audit_event.delay"):
        resp = await client.post(f"{BASE}/forgot-password", json={"email": "nobody@atlas.internal"})
    # Always 200 to prevent user enumeration
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client):
    resp = await client.post(f"{BASE}/reset-password", json={
        "token": "faketoken",
        "new_password": "NewSecure1",
    })
    assert resp.status_code == 400


# ─── Protected routes ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get(f"{BASE}/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sessions_requires_auth(client):
    resp = await client.get(f"{BASE}/sessions")
    assert resp.status_code == 403


# ─── Security headers ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_security_headers_present(client):
    resp = await client.get("/health")
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert "strict-transport-security" in resp.headers


# ─── Rate limiting ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_login(client, mock_redis):
    # Simulate rate limit exceeded
    mock_redis.pipeline = lambda: type("P", (), {
        "zremrangebyscore": lambda *a, **k: None,
        "zadd": lambda *a, **k: None,
        "zcard": lambda *a, **k: None,
        "expire": lambda *a, **k: None,
        "execute": lambda self: [0, None, 999, None],
        "__aenter__": lambda self: self,
        "__aexit__": lambda *a: None,
    })()

    with patch("app.iam.security.rate_limiter.check_login_rate_limit", return_value=False):
        with patch("app.workers.audit_tasks.log_audit_event.delay"):
            resp = await client.post(f"{BASE}/login", json={
                "email": VALID_USER["email"],
                "password": VALID_USER["password"],
            })
    assert resp.status_code == 429
