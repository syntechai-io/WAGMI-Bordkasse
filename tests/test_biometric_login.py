"""
Regression tests for the SaaS Face ID / Touch ID sign-in flow.

These tests lock in the moving parts that future edits could silently break:
  * i18n keys consumed by templates/login.html exist in both locales.
  * iOS plugin manifest declares the biometric + secure-storage plugins.
  * Info.plist additions include NSFaceIDUsageDescription.
  * The web bridge exposes window.CrewlogBiometric with the expected methods.
  * templates/login.html still wires the biometric UI hooks.
  * POST /login-saas honors its JSON contract AND its rate limit.

The actual biometric prompt cannot be exercised in CI — see
ios_app/FACEID_QA_CHECKLIST.md for the manual on-device checks.
"""

import json
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from db import Base, get_db
from limiter_config import limiter
from models import Account, SaaSUser
from routes_auth import router as saas_auth_router


REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Static-file & manifest assertions (no app needed)
# ---------------------------------------------------------------------------


BIOMETRIC_KEYS = [
    "auth.biometric_signin",
    "auth.biometric_signin_face",
    "auth.biometric_signin_touch",
    "auth.biometric_forget",
    "auth.biometric_forget_confirm",
    "auth.biometric_save_prompt",
    "auth.biometric_reason",
]


@pytest.mark.parametrize("locale", ["de", "en"])
def test_biometric_i18n_keys_present(locale):
    """Every key the login template renders must exist and be non-empty."""
    path = REPO_ROOT / "locales" / f"{locale}.json"
    assert path.exists(), f"missing locale file: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in BIOMETRIC_KEYS:
        assert key in data, f"{locale}: missing i18n key {key!r}"
        assert isinstance(data[key], str) and data[key].strip(), (
            f"{locale}: i18n key {key!r} must be a non-empty string"
        )


def test_ios_package_declares_biometric_plugins():
    """Capacitor manifest must keep both @aparajita plugins."""
    pkg = json.loads((REPO_ROOT / "ios_app" / "package.json").read_text())
    deps = pkg.get("dependencies", {})
    assert "@aparajita/capacitor-biometric-auth" in deps, (
        "biometric plugin removed from ios_app/package.json"
    )
    assert "@aparajita/capacitor-secure-storage" in deps, (
        "secure-storage plugin removed from ios_app/package.json"
    )


def test_info_plist_has_face_id_usage_description():
    """Apple requires NSFaceIDUsageDescription whenever LocalAuthentication is linked."""
    plist = (REPO_ROOT / "ios_app" / "ios-plist-additions.xml").read_text()
    assert "NSFaceIDUsageDescription" in plist, (
        "NSFaceIDUsageDescription missing — Face ID will crash on launch"
    )


def test_capacitor_bridge_exposes_crewlog_biometric():
    """The bridge must keep the public API the login template calls into."""
    src = (REPO_ROOT / "static" / "capacitor-bridge.js").read_text()
    assert "window.CrewlogBiometric" in src
    for method in ("isAvailable", "hasSaved", "authenticateAndLoad", "save", "clear"):
        assert re.search(rf"\b{method}\s*:", src), (
            f"window.CrewlogBiometric.{method} no longer exposed"
        )
    assert "BIO_KEY_EMAIL" in src and "BIO_KEY_PASSWORD" in src
    # Bug-fix #2: SecureStorage.get() must run BEFORE BiometricAuth.authenticate()
    # so a wiped Keychain doesn't trigger a Face ID prompt that can only fail.
    get_idx = src.find("s.get({ key: BIO_KEY_EMAIL })")
    auth_idx = src.find("p.authenticate(")
    assert get_idx != -1 and auth_idx != -1, "bridge no longer reads Keychain or calls authenticate"
    assert get_idx < auth_idx, (
        "bioAuthenticateAndLoad must check SecureStorage BEFORE prompting Face ID"
    )


def test_ios_app_bridge_is_stub_pointing_at_canonical_source():
    """The ios_app/ copy must NOT contain a real bridge (it's served from /static)."""
    src = (REPO_ROOT / "ios_app" / "capacitor-bridge.js").read_text()
    assert "static/capacitor-bridge.js" in src, (
        "ios_app/capacitor-bridge.js should point at the canonical static bridge"
    )
    assert "CrewlogBiometric" not in src, (
        "ios_app/capacitor-bridge.js must not contain a duplicate biometric implementation"
    )


def test_login_template_wires_biometric_ui():
    """The IDs and JS hooks the bridge depends on must remain in the template."""
    html = (REPO_ROOT / "templates" / "login.html").read_text()
    for el_id in ("biometric-login-block", "biometric-login-btn", "biometric-clear-btn"):
        assert f'id="{el_id}"' in html, f"#{el_id} missing from login.html"
    assert "maybeOfferBiometricSave" in html
    assert "initBiometricLogin" in html
    # Enrollment prompt must still be invoked from the SaaS submit handler.
    assert re.search(r"handleSaasLogin[\s\S]+?maybeOfferBiometricSave", html), (
        "handleSaasLogin no longer calls maybeOfferBiometricSave after success"
    )
    # Bug-fix #4: 429 (rate limit) must NOT wipe the Keychain — the saved
    # credentials are still valid, the user is just throttled.
    assert "result.status === 429" in html, (
        "biometric login handler must distinguish 429 from 401 to avoid wiping "
        "valid Keychain credentials when the rate limit kicks in"
    )


# ---------------------------------------------------------------------------
# /login-saas behavior (JSON contract + rate limit)
# ---------------------------------------------------------------------------


@pytest.fixture
def saas_app():
    """Build a minimal app exposing /login-saas with a fresh SQLite + limiter."""
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
    app.include_router(saas_auth_router)
    return app


def test_login_saas_returns_ok_json_for_valid_credentials(saas_app):
    """The JS in templates/login.html relies on this exact JSON shape."""
    client = TestClient(saas_app)
    r = client.post(
        "/login-saas",
        data={"email": "qa@example.com", "password": "correct-horse-battery-staple"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}


def test_login_saas_returns_401_json_for_invalid_credentials(saas_app):
    """Stale-Keychain branch in initBiometricLogin depends on a JSON 401."""
    client = TestClient(saas_app)
    r = client.post(
        "/login-saas", data={"email": "qa@example.com", "password": "wrong"}
    )
    assert r.status_code == 401
    body = r.json()
    assert "detail" in body and body["detail"] == "Invalid credentials"


def test_login_saas_is_rate_limited(saas_app):
    """5/minute matches /login. Use distinct client IPs per fixture run."""
    client = TestClient(saas_app)
    # SlowAPI keys by remote address; TestClient defaults to 'testclient'. Send 5
    # bad attempts (each a 401), then expect the 6th to be 429 from the limiter.
    for _ in range(5):
        r = client.post(
            "/login-saas", data={"email": "qa@example.com", "password": "wrong"}
        )
        assert r.status_code == 401, r.text
    r = client.post(
        "/login-saas", data={"email": "qa@example.com", "password": "wrong"}
    )
    assert r.status_code == 429, (
        f"6th attempt within a minute should be rate-limited, got {r.status_code}"
    )
