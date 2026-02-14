import os
import logging
from datetime import datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db import get_db
from models import SaaSUser, PlanEnum, SubscriptionStatus
from billing_stripe import (
    get_or_create_subscription_row,
    get_or_create_stripe_customer,
    set_subscription_state,
    resolve_plan_and_status,
    get_account_id_from_metadata,
    get_account_id_from_customer,
    PRICE_MONTHLY,
    PRICE_YEARLY,
)

logger = logging.getLogger(__name__)

router = APIRouter()

APP_BASE_URL = os.getenv("APP_BASE_URL", "")


def _require_saas_owner(request: Request, db: Session) -> tuple[SaaSUser, int]:
    saas_user_id = request.session.get("saas_user_id")
    account_id = request.session.get("account_id")
    if not saas_user_id or not account_id:
        raise HTTPException(status_code=401, detail="SaaS login required")
    user = db.query(SaaSUser).filter(SaaSUser.id == saas_user_id).first()
    if not user or user.account_id != account_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Only the account owner may manage billing")
    return user, int(account_id)


@router.post("/billing/checkout")
async def billing_checkout(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    interval = form.get("interval", "monthly")
    if interval not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="interval must be monthly or yearly")

    price_id = PRICE_MONTHLY if interval == "monthly" else PRICE_YEARLY
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe price not configured")

    user, account_id = _require_saas_owner(request, db)
    get_or_create_subscription_row(db, account_id)
    customer_id = get_or_create_stripe_customer(db, account_id, user)
    db.commit()

    base = APP_BASE_URL.rstrip("/")
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{base}/billing/success",
        cancel_url=f"{base}/billing/cancel",
        allow_promotion_codes=True,
        metadata={"account_id": str(account_id)},
        subscription_data={"metadata": {"account_id": str(account_id)}},
    )
    return JSONResponse({"checkout_url": session.url})


@router.get("/billing/success")
def billing_success():
    return JSONResponse({"message": "Thanks — your subscription will activate shortly."})


@router.get("/billing/cancel")
def billing_cancel():
    return JSONResponse({"message": "Checkout canceled."})


@router.post("/billing/portal")
async def billing_portal(request: Request, db: Session = Depends(get_db)):
    user, account_id = _require_saas_owner(request, db)
    customer_id = get_or_create_stripe_customer(db, account_id, user)
    db.commit()

    base = APP_BASE_URL.rstrip("/")
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{base}/",
    )
    return JSONResponse({"portal_url": session.url})


def _handle_subscription_event(db: Session, stripe_sub_id: str, account_id: int | None):
    sub_obj = stripe.Subscription.retrieve(stripe_sub_id)
    stripe_status = sub_obj.status
    plan, status = resolve_plan_and_status(stripe_status)

    period_end = None
    if sub_obj.current_period_end:
        period_end = datetime.utcfromtimestamp(sub_obj.current_period_end)

    if not account_id:
        account_id = get_account_id_from_metadata(sub_obj)
    if not account_id:
        account_id = get_account_id_from_customer(db, sub_obj.customer)
    if not account_id:
        logger.warning("Webhook: could not resolve account_id for subscription %s", stripe_sub_id)
        return

    set_subscription_state(
        db,
        account_id=account_id,
        plan=plan,
        status=status,
        stripe_customer_id=sub_obj.customer,
        stripe_subscription_id=stripe_sub_id,
        current_period_end=period_end,
    )
    db.commit()
    logger.info("Subscription %s updated: plan=%s status=%s account=%s", stripe_sub_id, plan, status, account_id)


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("Webhook parse error: %s", e)
        raise HTTPException(status_code=400, detail="Bad payload")

    event_type = event["type"]
    obj = event["data"]["object"]

    try:
        if event_type == "checkout.session.completed":
            if obj.get("mode") == "subscription" and obj.get("subscription"):
                account_id = get_account_id_from_metadata(obj)
                _handle_subscription_event(db, obj["subscription"], account_id)

        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            account_id = get_account_id_from_metadata(obj)
            _handle_subscription_event(db, obj["id"], account_id)

        elif event_type == "invoice.paid":
            sub_id = obj.get("subscription")
            if sub_id:
                account_id = get_account_id_from_metadata(obj)
                _handle_subscription_event(db, sub_id, account_id)

        elif event_type == "invoice.payment_failed":
            sub_id = obj.get("subscription")
            if sub_id:
                account_id = get_account_id_from_metadata(obj)
                _handle_subscription_event(db, sub_id, account_id)

    except Exception as e:
        logger.exception("Webhook handler error for %s: %s", event_type, e)
        raise HTTPException(status_code=500, detail="Internal error processing event")

    return JSONResponse({"received": True})
