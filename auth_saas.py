from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db import get_db
from models import SaaSUser, Subscription, PlanEnum, SubscriptionStatus, TripMember, TripRole, Trip


UPGRADE_REQUIRED = "UPGRADE_REQUIRED"


def get_active_account_id(request: Request):
    """Returns account_id from SaaS session if present, else None (legacy mode)."""
    return request.session.get("account_id")


def get_current_saas_user(request: Request, db: Session = Depends(get_db)) -> SaaSUser:
    saas_user_id = request.session.get("saas_user_id")
    account_id = request.session.get("account_id")

    if not saas_user_id or not account_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(SaaSUser).filter(SaaSUser.id == saas_user_id).first()
    if not user or user.account_id != account_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user


def get_current_account_id(request: Request) -> int:
    account_id = request.session.get("account_id")
    if not account_id:
        raise HTTPException(status_code=401, detail="No account in session")
    return int(account_id)


def require_trip_access(trip_id: int):
    def _guard(
        request: Request,
        db: Session = Depends(get_db),
        user: SaaSUser = Depends(get_current_saas_user),
    ):
        trip = (
            db.query(Trip)
            .filter(Trip.id == trip_id, Trip.account_id == user.account_id)
            .first()
        )
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")

        if user.is_owner:
            return trip

        member = (
            db.query(TripMember)
            .filter(TripMember.trip_id == trip_id, TripMember.user_id == user.id)
            .first()
        )
        if not member:
            raise HTTPException(status_code=403, detail="No access to this trip")

        return trip

    return _guard


def require_trip_edit(trip_id: int):
    def _guard(
        request: Request,
        db: Session = Depends(get_db),
        user: SaaSUser = Depends(get_current_saas_user),
    ):
        trip = (
            db.query(Trip)
            .filter(Trip.id == trip_id, Trip.account_id == user.account_id)
            .first()
        )
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")

        if user.is_owner:
            return trip

        member = (
            db.query(TripMember)
            .filter(TripMember.trip_id == trip_id, TripMember.user_id == user.id)
            .first()
        )
        if not member or member.role != TripRole.skipper:
            raise HTTPException(status_code=403, detail="Edit permission denied")

        return trip

    return _guard


def get_effective_plan(account_id: int, db: Session) -> PlanEnum:
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.account_id == account_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .order_by(Subscription.id.desc())
        .first()
    )
    return sub.plan if sub else PlanEnum.FREE


def require_pro_feature(feature_name: str):
    def _guard(
        request: Request,
        db: Session = Depends(get_db),
        user: SaaSUser = Depends(get_current_saas_user),
    ):
        plan = get_effective_plan(user.account_id, db)
        if plan != PlanEnum.SKIPPER_PLUS:
            raise HTTPException(
                status_code=403,
                detail={"code": UPGRADE_REQUIRED, "feature": feature_name},
            )
        return True

    return _guard


def enforce_free_limits_for_trip_creation(db: Session, account_id: int):
    plan = get_effective_plan(account_id, db)
    if plan == PlanEnum.SKIPPER_PLUS:
        return

    active_count = (
        db.query(Trip)
        .filter(Trip.account_id == account_id, Trip.status == "active", Trip.is_closed == 0)
        .count()
    )
    if active_count >= 1:
        raise HTTPException(
            status_code=403,
            detail={"code": UPGRADE_REQUIRED, "feature": "more_than_one_active_trip"},
        )


def enforce_free_limits_for_crew_add(db: Session, trip_id: int, account_id: int):
    plan = get_effective_plan(account_id, db)
    if plan == PlanEnum.SKIPPER_PLUS:
        return

    count_members = (
        db.query(TripMember)
        .join(Trip, Trip.id == TripMember.trip_id)
        .filter(TripMember.trip_id == trip_id, Trip.account_id == account_id)
        .count()
    )

    if count_members >= 4:
        raise HTTPException(
            status_code=403,
            detail={"code": UPGRADE_REQUIRED, "feature": "crew_limit"},
        )
