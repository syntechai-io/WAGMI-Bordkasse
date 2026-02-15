import os
import logging
import stripe
from datetime import datetime
from sqlalchemy.orm import Session

from models import Subscription, PlanEnum, SubscriptionStatus, SaaSUser, Trip

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "")
PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY", "")

logger = logging.getLogger(__name__)


def get_or_create_subscription_row(db: Session, account_id: int) -> Subscription:
    sub = (
        db.query(Subscription)
        .filter(Subscription.account_id == account_id)
        .first()
    )
    if sub:
        return sub

    sub = Subscription(
        account_id=account_id,
        plan=PlanEnum.FREE,
        status=SubscriptionStatus.CANCELED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(sub)
    db.flush()
    return sub


def get_or_create_stripe_customer(
    db: Session, account_id: int, owner_user: SaaSUser
) -> str:
    sub = get_or_create_subscription_row(db, account_id)

    if sub.stripe_customer_id:
        return sub.stripe_customer_id

    customer = stripe.Customer.create(
        email=owner_user.email,
        metadata={"account_id": str(account_id)},
    )
    sub.stripe_customer_id = customer.id
    sub.updated_at = datetime.utcnow()
    db.flush()
    return customer.id


def set_subscription_state(
    db: Session,
    account_id: int,
    plan: PlanEnum,
    status: SubscriptionStatus,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    current_period_end: datetime | None = None,
):
    if not account_id:
        logger.warning("set_subscription_state called with no account_id, skipping")
        return None

    sub = None

    if stripe_subscription_id:
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
            .first()
        )

    if not sub:
        sub = (
            db.query(Subscription)
            .filter(Subscription.account_id == account_id)
            .first()
        )

    if not sub:
        sub = Subscription(
            account_id=account_id,
            plan=plan,
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(sub)

    sub.plan = plan
    sub.status = status
    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id
    if current_period_end is not None:
        sub.current_period_end = current_period_end
    sub.updated_at = datetime.utcnow()
    sub.webhook_received_at = datetime.utcnow()
    db.flush()
    return sub


def resolve_plan_and_status(stripe_status: str):
    if stripe_status in ("active", "trialing"):
        return PlanEnum.SKIPPER_PLUS, SubscriptionStatus.ACTIVE
    elif stripe_status in ("past_due", "unpaid"):
        return PlanEnum.SKIPPER_PLUS, SubscriptionStatus.PAST_DUE
    else:
        return PlanEnum.FREE, SubscriptionStatus.CANCELED


def get_account_id_from_metadata(event_obj: dict) -> int | None:
    meta = event_obj.get("metadata", {})
    aid = meta.get("account_id")
    if aid:
        return int(aid)
    return None


def get_account_id_from_customer(db: Session, customer_id: str) -> int | None:
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_customer_id == customer_id)
        .first()
    )
    return sub.account_id if sub else None


def check_over_limit_state(db: Session, account_id: int) -> dict:
    from models import TripMember, TripStatus
    active_trips = (
        db.query(Trip)
        .filter(Trip.account_id == account_id, Trip.status == TripStatus.active)
        .all()
    )
    active_trip_count = len(active_trips)

    max_crew = 0
    over_limit_trips = []
    for trip in active_trips:
        member_count = (
            db.query(TripMember)
            .filter(TripMember.trip_id == trip.id)
            .count()
        )
        if member_count > max_crew:
            max_crew = member_count
        if member_count > 4:
            over_limit_trips.append({"trip_id": trip.id, "trip_name": trip.name, "crew_count": member_count})

    trips_over = active_trip_count > 1
    crew_over = len(over_limit_trips) > 0

    return {
        "active_trip_count": active_trip_count,
        "max_crew_in_any_trip": max_crew,
        "trips_over_limit": trips_over,
        "crew_over_limit": crew_over,
        "over_limit": trips_over or crew_over,
        "over_limit_trips": over_limit_trips,
    }


def reconcile_subscription_from_stripe(db: Session, account_id: int) -> dict:
    sub = (
        db.query(Subscription)
        .filter(Subscription.account_id == account_id)
        .first()
    )
    if not sub:
        return {"error": "No subscription row for this account"}

    if not sub.stripe_subscription_id:
        return {"status": "no_stripe_subscription", "plan": sub.plan.value if sub.plan else "FREE"}

    try:
        stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
    except stripe.InvalidRequestError:
        sub.plan = PlanEnum.FREE
        sub.status = SubscriptionStatus.CANCELED
        sub.stripe_subscription_id = None
        sub.updated_at = datetime.utcnow()
        db.flush()
        return {"status": "stripe_subscription_not_found", "action": "set_to_FREE"}
    except Exception as e:
        logger.error("Stripe API error during reconcile for account %s: %s", account_id, e)
        return {"error": f"Stripe API error: {str(e)}"}

    plan, status = resolve_plan_and_status(stripe_sub.status)
    period_end = None
    if stripe_sub.current_period_end:
        period_end = datetime.utcfromtimestamp(stripe_sub.current_period_end)

    old_plan = sub.plan.value if sub.plan else None
    old_status = sub.status.value if sub.status else None

    sub.plan = plan
    sub.status = status
    sub.stripe_customer_id = stripe_sub.customer
    if period_end:
        sub.current_period_end = period_end
    sub.updated_at = datetime.utcnow()
    db.flush()

    return {
        "status": "reconciled",
        "old_plan": old_plan,
        "new_plan": plan.value,
        "old_status": old_status,
        "new_status": status.value,
        "stripe_status": stripe_sub.status,
    }
