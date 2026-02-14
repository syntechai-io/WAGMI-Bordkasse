import os
import stripe
from datetime import datetime
from sqlalchemy.orm import Session

from models import Subscription, PlanEnum, SubscriptionStatus, SaaSUser

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "")
PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY", "")


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
    sub = get_or_create_subscription_row(db, account_id)
    sub.plan = plan
    sub.status = status
    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id
    if current_period_end:
        sub.current_period_end = current_period_end
    sub.updated_at = datetime.utcnow()
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
