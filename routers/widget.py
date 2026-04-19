"""iOS Home/Lock Screen widget API.

Three endpoints:

    POST   /api/widget/token       (session auth)  — issue a new bearer token
    DELETE /api/widget/token       (session auth)  — revoke all tokens for the user
    GET    /api/widget/snapshot    (Bearer auth)   — JSON snapshot for the widget

The token is a 32-byte URL-safe random string. The plain value is returned
once at issuance; only its SHA-256 hash is persisted. The iOS app stores the
plain value in the Keychain (App Group) so the WidgetKit extension can read it.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from db import get_db
from models import (
    LogbookEntry,
    SaaSUser,
    Trip,
    TripStatus,
    WidgetToken,
)

router = APIRouter()


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _require_session_user(request: Request, db: Session) -> SaaSUser:
    saas_user_id = request.session.get("saas_user_id")
    account_id = request.session.get("account_id")
    if not saas_user_id or not account_id:
        raise HTTPException(status_code=401, detail="Login required")
    user = (
        db.query(SaaSUser)
        .filter(SaaSUser.id == saas_user_id, SaaSUser.account_id == account_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def _require_bearer_token(authorization: Optional[str], db: Session) -> WidgetToken:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    plain = authorization.split(" ", 1)[1].strip()
    if not plain:
        raise HTTPException(status_code=401, detail="Bearer token required")
    digest = _hash_token(plain)
    tok = (
        db.query(WidgetToken)
        .filter(WidgetToken.token_hash == digest, WidgetToken.revoked_at.is_(None))
        .first()
    )
    if not tok:
        raise HTTPException(status_code=401, detail="Invalid or revoked token")
    tok.last_used_at = datetime.utcnow()
    db.commit()
    return tok


@router.post("/widget/token")
def issue_widget_token(request: Request, db: Session = Depends(get_db)):
    """Revoke any existing tokens for this user, then issue and return a new one.
    The plain value is returned ONCE — store it in the Keychain client-side."""
    user = _require_session_user(request, db)

    # Revoke previous tokens (one widget at a time per device pair, simple & safe)
    now = datetime.utcnow()
    db.query(WidgetToken).filter(
        WidgetToken.user_id == user.id,
        WidgetToken.revoked_at.is_(None),
    ).update({WidgetToken.revoked_at: now}, synchronize_session=False)

    plain = secrets.token_urlsafe(32)
    tok = WidgetToken(
        user_id=user.id,
        account_id=user.account_id,
        token_hash=_hash_token(plain),
        label="ios-widget",
        created_at=now,
    )
    db.add(tok)
    db.commit()

    return {"token": plain, "issued_at": now.isoformat() + "Z"}


@router.delete("/widget/token")
def revoke_widget_tokens(request: Request, db: Session = Depends(get_db)):
    user = _require_session_user(request, db)
    now = datetime.utcnow()
    revoked = db.query(WidgetToken).filter(
        WidgetToken.user_id == user.id,
        WidgetToken.revoked_at.is_(None),
    ).update({WidgetToken.revoked_at: now}, synchronize_session=False)
    db.commit()
    return {"revoked": int(revoked)}


@router.get("/widget/status")
def widget_status(request: Request, db: Session = Depends(get_db)):
    """Tell the /about page whether widget access is currently enabled."""
    user = _require_session_user(request, db)
    active = (
        db.query(WidgetToken)
        .filter(
            WidgetToken.user_id == user.id,
            WidgetToken.revoked_at.is_(None),
        )
        .order_by(WidgetToken.created_at.desc())
        .first()
    )
    if not active:
        return {"enabled": False}
    return {
        "enabled": True,
        "issued_at": active.created_at.isoformat() + "Z",
        "last_used_at": (active.last_used_at.isoformat() + "Z") if active.last_used_at else None,
    }


@router.get("/widget/snapshot")
def widget_snapshot(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    """Compact JSON for the iOS widget. Stable shape — bump version if it changes."""
    tok = _require_bearer_token(authorization, db)

    trip = (
        db.query(Trip)
        .filter(
            Trip.account_id == tok.account_id,
            Trip.status == TripStatus.active,
        )
        .order_by(Trip.start_date.desc())
        .first()
    )

    if not trip:
        return JSONResponse({
            "v": 1,
            "state": "no_active_trip",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        })

    last_entry = (
        db.query(LogbookEntry)
        .filter(LogbookEntry.trip_id == trip.id)
        .order_by(LogbookEntry.entry_date.desc())
        .first()
    )

    total_nm = (
        db.query(func.coalesce(func.sum(LogbookEntry.dist_day_nm), 0.0))
        .filter(LogbookEntry.trip_id == trip.id)
        .scalar()
        or 0.0
    )

    eng_readings = (
        db.query(LogbookEntry.eng_hours_total)
        .filter(
            LogbookEntry.trip_id == trip.id,
            LogbookEntry.eng_hours_total.isnot(None),
        )
        .all()
    )
    eng_values = [r[0] for r in eng_readings if r[0] is not None]
    motor_hours = (max(eng_values) - min(eng_values)) if len(eng_values) >= 2 else 0.0

    today = datetime.utcnow().date()
    day_of_trip = None
    if trip.start_date:
        day_of_trip = max(1, (today - trip.start_date).days + 1)

    last_pos = None
    if last_entry and last_entry.latitude is not None and last_entry.longitude is not None:
        last_pos = {
            "lat": float(last_entry.latitude),
            "lon": float(last_entry.longitude),
        }

    return JSONResponse({
        "v": 1,
        "state": "ok",
        "trip": {
            "id": trip.id,
            "name": trip.name,
            "is_closed": bool(trip.is_closed),
            "day": day_of_trip,
        },
        "totals": {
            "distance_nm": round(float(total_nm), 1),
            "motor_hours": round(float(motor_hours), 1),
        },
        "last_entry": {
            "at": last_entry.entry_date.isoformat() + "Z" if last_entry else None,
            "position": last_pos,
        } if last_entry else None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    })
