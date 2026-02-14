from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash
from datetime import datetime

from db import get_db
from models import SaaSUser, Trip, TripMember, TripRole

router = APIRouter()

@router.post("/login-saas")
def login_saas(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(SaaSUser).filter(SaaSUser.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not check_password_hash(str(user.password_hash), password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    request.session["saas_user_id"] = user.id
    request.session["account_id"] = user.account_id

    request.session.pop("user_id", None)
    request.session.pop("role", None)

    return {"ok": True}


@router.get("/api/whoami")
def whoami(request: Request, db: Session = Depends(get_db)):
    saas_user_id = request.session.get("saas_user_id")
    account_id = request.session.get("account_id")

    if saas_user_id and account_id:
        user = db.query(SaaSUser).filter(SaaSUser.id == saas_user_id).first()
        return {
            "mode": "saas",
            "saas_user_id": saas_user_id,
            "account_id": account_id,
            "email": user.email if user else None,
            "is_owner": bool(user.is_owner) if user else None,
        }

    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if user_id:
        return {
            "mode": "legacy",
            "user_id": user_id,
            "role": role,
        }

    return {"mode": "none"}


@router.post("/logout-saas")
def logout_saas(request: Request):
    request.session.pop("saas_user_id", None)
    request.session.pop("account_id", None)
    return {"ok": True}


@router.post("/admin/saas/backfill")
def admin_backfill(request: Request, db: Session = Depends(get_db)):
    """One-time idempotent backfill: assign NULL account_ids to 1, ensure owners are trip members."""
    # Guard: require legacy admin session
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    report = {
        "trips_total": 0,
        "trips_updated_from_null": 0,
        "trip_members_inserted": 0,
        "already_present": 0,
        "owners_missing": 0,
        "skipped_no_account_id": 0,
    }

    # Step 1: assign NULL account_id trips to Default Account (id=1)
    null_trips = db.query(Trip).filter(Trip.account_id.is_(None)).all()
    for trip in null_trips:
        trip.account_id = 1
        report["trips_updated_from_null"] += 1
    db.flush()

    # Step 2: ensure account owner is trip_member(skipper) for every trip
    all_trips = db.query(Trip).all()
    report["trips_total"] = len(all_trips)

    for trip in all_trips:
        if not trip.account_id:
            report["skipped_no_account_id"] += 1
            continue

        owner = (
            db.query(SaaSUser)
            .filter(SaaSUser.account_id == trip.account_id, SaaSUser.is_owner.is_(True))
            .first()
        )
        if not owner:
            report["owners_missing"] += 1
            continue

        exists = (
            db.query(TripMember)
            .filter(TripMember.trip_id == trip.id, TripMember.user_id == owner.id)
            .first()
        )
        if exists:
            report["already_present"] += 1
            continue

        db.add(TripMember(
            trip_id=trip.id,
            user_id=owner.id,
            role=TripRole.skipper,
            created_at=datetime.utcnow(),
        ))
        report["trip_members_inserted"] += 1

    db.commit()
    return report
