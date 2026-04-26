"""
Regression tests for the password-reset brute-force throttle.

Mirrors the pattern in test_biometric_login.py::test_login_saas_is_rate_limited,
applied to:
  * POST /forgot-password  (request a reset link)
  * POST /reset-password   (submit a new password with a token)

Both endpoints must enforce 5/minute per IP, matching /login and /login-saas.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from datetime import datetime, timedelta

from db import Base, get_db
from limiter_config import limiter
from models import Account, PasswordResetToken, SaaSUser
from routes_password_reset import router as password_reset_router
from token_utils import generate_reset_token, hash_token


@pytest.fixture
def reset_app(monkeypatch):
    """Build a minimal app exposing /forgot-password + /reset-password."""
    # Don't actually try to send mail during tests.
    import routes_password_reset as prr
    monkeypatch.setattr(prr, "send_password_reset", lambda *a, **kw: None)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    db = SessionLocal()
    account = Account(name="Test Account")
    db.add(account)
    db.commit()
    db.refresh(account)
    user = SaaSUser(account_id=account.id, email="qa@example.com", is_owner=True)
    user.set_password("correct-horse-battery-staple")
    db.add(user)
    db.commit()
    db.refresh(user)
    test_user_id = user.id
    db.close()

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    # Reset the in-process limiter so prior tests don't leak rate-limit state.
    limiter.reset()

    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request, exc):  # noqa: ARG001
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.dependency_overrides[get_db] = _get_db
    app.include_router(password_reset_router)
    # Expose the session factory + seeded user id so tests can stage rows
    # (e.g. a valid PasswordResetToken for the happy-path submit test).
    app.state.session_factory = SessionLocal
    app.state.test_user_id = test_user_id
    return app


def test_forgot_password_is_rate_limited(reset_app):
    """5/minute matches /login-saas. The 6th attempt must be 429."""
    client = TestClient(reset_app)
    # Use an unknown email so the happy path's mailer + DB writes are skipped
    # (the endpoint still returns 200 to avoid account enumeration).
    for _ in range(5):
        r = client.post("/forgot-password", data={"email": "nobody@example.com"})
        assert r.status_code == 200, r.text
    r = client.post("/forgot-password", data={"email": "nobody@example.com"})
    assert r.status_code == 429, (
        f"6th /forgot-password within a minute should be rate-limited, got {r.status_code}"
    )


def test_reset_password_is_rate_limited(reset_app):
    """5/minute matches /login-saas. The 6th attempt must be 429."""
    client = TestClient(reset_app)
    # Bogus token so the endpoint short-circuits to the invalid_token branch
    # (HTTP 200 with the form re-rendered) rather than mutating any state.
    payload = {
        "token": "not-a-real-token",
        "password": "irrelevant-but-long-enough",
        "password_confirm": "irrelevant-but-long-enough",
    }
    for _ in range(5):
        r = client.post("/reset-password", data=payload)
        assert r.status_code == 200, r.text
    r = client.post("/reset-password", data=payload)
    assert r.status_code == 429, (
        f"6th /reset-password within a minute should be rate-limited, got {r.status_code}"
    )


def test_forgot_password_happy_path_within_limit(reset_app):
    """A single legitimate request must still succeed (HTTP 200, form re-rendered)."""
    client = TestClient(reset_app)
    r = client.post("/forgot-password", data={"email": "qa@example.com"})
    assert r.status_code == 200, r.text


def test_reset_password_happy_path_within_limit(reset_app):
    """A single legitimate submit with a valid token must still succeed (303 -> /login)."""
    SessionLocal = reset_app.state.session_factory
    user_id = reset_app.state.test_user_id

    raw_token = generate_reset_token()
    db = SessionLocal()
    try:
        db.add(PasswordResetToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
            request_ip="127.0.0.1",
            user_agent="pytest",
        ))
        db.commit()
    finally:
        db.close()

    client = TestClient(reset_app, follow_redirects=False)
    r = client.post(
        "/reset-password",
        data={
            "token": raw_token,
            "password": "new-strong-password",
            "password_confirm": "new-strong-password",
        },
    )
    assert r.status_code == 303, r.text
    assert r.headers["location"] == "/login?reset=success"

    # The token must be marked used so it can't be replayed.
    db = SessionLocal()
    try:
        record = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == hash_token(raw_token))
            .first()
        )
        assert record is not None
        assert record.used_at is not None, "successful reset must mark the token as used"
    finally:
        db.close()
