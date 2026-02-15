import os
import logging
from datetime import datetime, timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import get_db
from models import SaaSUser, Subscription, Account, PlanEnum, SubscriptionStatus, Trip
from billing_stripe import (
    get_or_create_subscription_row,
    get_or_create_stripe_customer,
    check_over_limit_state,
    reconcile_subscription_from_stripe,
    PRICE_MONTHLY,
    PRICE_YEARLY,
)
from template_helpers import create_templates

logger = logging.getLogger(__name__)
router = APIRouter()
templates = create_templates()

APP_BASE_URL = os.getenv("APP_BASE_URL", "")


def _get_saas_session(request: Request, db: Session):
    saas_user_id = request.session.get("saas_user_id")
    account_id = request.session.get("account_id")
    if not saas_user_id or not account_id:
        return None, None
    user = db.query(SaaSUser).filter(SaaSUser.id == saas_user_id).first()
    if not user or user.account_id != int(account_id):
        return None, None
    return user, int(account_id)


def _require_saas_session(request: Request, db: Session):
    user, account_id = _get_saas_session(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="SaaS login required")
    return user, account_id


def _require_owner(request: Request, db: Session):
    user, account_id = _require_saas_session(request, db)
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Only the account owner may manage billing")
    return user, account_id


def _require_global_admin(request: Request):
    if request.session.get("role") == "admin":
        return True
    saas_user_id = request.session.get("saas_user_id")
    if saas_user_id:
        return False
    raise HTTPException(status_code=403, detail="Admin access required")


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


@router.get("/billing")
async def billing_page(request: Request, db: Session = Depends(get_db)):
    user, account_id = _require_saas_session(request, db)

    account = db.query(Account).filter(Account.id == account_id).first()
    sub = get_or_create_subscription_row(db, account_id)
    db.commit()

    period_end_str = "—"
    if sub.current_period_end:
        period_end_str = sub.current_period_end.strftime("%d.%m.%Y")

    plan_value = sub.plan.value if sub.plan else PlanEnum.FREE.value
    over_limit = {}
    if plan_value == "FREE":
        over_limit = check_over_limit_state(db, account_id)

    return templates.TemplateResponse("billing.html", {
        "request": request,
        "account_name": account.name if account else f"Account {account_id}",
        "is_owner": user.is_owner,
        "plan": plan_value,
        "status": sub.status.value if sub.status else SubscriptionStatus.CANCELED.value,
        "current_period_end": period_end_str,
        "over_limit": over_limit,
    })


@router.post("/billing/ui/checkout")
async def billing_ui_checkout(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    interval = form.get("interval", "monthly")
    if interval not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="interval must be monthly or yearly")

    price_id = PRICE_MONTHLY if interval == "monthly" else PRICE_YEARLY
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe price not configured")

    user, account_id = _require_owner(request, db)
    get_or_create_subscription_row(db, account_id)
    customer_id = get_or_create_stripe_customer(db, account_id, user)
    db.commit()

    base = APP_BASE_URL.rstrip("/") or str(request.base_url).rstrip("/")
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{base}/billing/ui/success",
        cancel_url=f"{base}/billing/ui/cancel",
        allow_promotion_codes=True,
        metadata={"account_id": str(account_id)},
        subscription_data={"metadata": {"account_id": str(account_id)}},
    )

    if _is_htmx(request):
        from starlette.responses import Response
        resp = Response(status_code=204)
        resp.headers["HX-Redirect"] = session.url
        return resp

    return RedirectResponse(session.url, status_code=303)


@router.post("/billing/ui/portal")
async def billing_ui_portal(request: Request, db: Session = Depends(get_db)):
    user, account_id = _require_owner(request, db)
    customer_id = get_or_create_stripe_customer(db, account_id, user)
    db.commit()

    base = APP_BASE_URL.rstrip("/") or str(request.base_url).rstrip("/")
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{base}/billing",
    )

    if _is_htmx(request):
        from starlette.responses import Response
        resp = Response(status_code=204)
        resp.headers["HX-Redirect"] = session.url
        return resp

    return RedirectResponse(session.url, status_code=303)


@router.get("/billing/ui/success")
async def billing_ui_success(request: Request):
    return templates.TemplateResponse("billing_result.html", {
        "request": request,
        "title": "Abo aktiviert",
        "icon": "🎉",
        "message": "Vielen Dank! Ihr Abonnement wird in Kürze aktiviert.",
        "sub_message": "Stripe verarbeitet die Zahlung — dies kann einige Sekunden dauern.",
        "link_text": "Zum Billing",
        "link_url": "/billing",
    })


@router.get("/billing/ui/cancel")
async def billing_ui_cancel(request: Request):
    return templates.TemplateResponse("billing_result.html", {
        "request": request,
        "title": "Checkout abgebrochen",
        "icon": "↩️",
        "message": "Der Checkout wurde abgebrochen.",
        "sub_message": "Sie können jederzeit erneut ein Upgrade starten.",
        "link_text": "Zum Billing",
        "link_url": "/billing",
    })


@router.get("/admin/billing")
async def admin_billing(request: Request, db: Session = Depends(get_db)):
    is_admin = request.session.get("role") == "admin"
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    status_filter = request.query_params.get("status")
    plan_filter = request.query_params.get("plan")
    q = request.query_params.get("q", "").strip()

    query = (
        db.query(
            Account.id.label("account_id"),
            Account.name.label("account_name"),
            SaaSUser.email.label("owner_email"),
            Subscription.plan,
            Subscription.status,
            Subscription.current_period_end,
            Subscription.stripe_customer_id,
            Subscription.stripe_subscription_id,
            Subscription.updated_at,
            Subscription.webhook_received_at,
        )
        .outerjoin(Subscription, Subscription.account_id == Account.id)
        .outerjoin(
            SaaSUser,
            (SaaSUser.account_id == Account.id) & (SaaSUser.is_owner.is_(True)),
        )
    )

    if status_filter:
        try:
            status_enum = SubscriptionStatus(status_filter)
            query = query.filter(Subscription.status == status_enum)
        except ValueError:
            pass

    if plan_filter:
        try:
            plan_enum = PlanEnum(plan_filter)
            query = query.filter(Subscription.plan == plan_enum)
        except ValueError:
            pass

    if q:
        query = query.filter(Account.name.ilike(f"%{q}%"))

    rows = query.order_by(Account.id).all()

    total_accounts = db.query(func.count(Account.id)).scalar() or 0
    active_subs = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.status == SubscriptionStatus.ACTIVE)
        .scalar() or 0
    )
    past_due_subs = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.status == SubscriptionStatus.PAST_DUE)
        .scalar() or 0
    )
    free_accounts = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.plan == PlanEnum.FREE)
        .scalar() or 0
    )
    canceled_subs = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.status == SubscriptionStatus.CANCELED)
        .scalar() or 0
    )

    stale_cutoff = datetime.utcnow() - timedelta(days=7)
    stale_webhook_count = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.stripe_subscription_id.isnot(None),
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .filter(
            (Subscription.webhook_received_at == None) |
            (Subscription.webhook_received_at < stale_cutoff)
        )
        .scalar() or 0
    )

    return templates.TemplateResponse("admin_billing.html", {
        "request": request,
        "rows": rows,
        "total_accounts": total_accounts,
        "active_subs": active_subs,
        "past_due_subs": past_due_subs,
        "free_accounts": free_accounts,
        "canceled_subs": canceled_subs,
        "stale_webhook_count": stale_webhook_count,
        "status_filter": status_filter or "",
        "plan_filter": plan_filter or "",
        "q": q,
    })


@router.get("/admin/billing/account/{account_id}")
async def admin_billing_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    is_admin = request.session.get("role") == "admin"
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    sub = (
        db.query(Subscription)
        .filter(Subscription.account_id == account_id)
        .first()
    )

    owner = (
        db.query(SaaSUser)
        .filter(SaaSUser.account_id == account_id, SaaSUser.is_owner.is_(True))
        .first()
    )

    members = (
        db.query(SaaSUser)
        .filter(SaaSUser.account_id == account_id)
        .all()
    )

    trip_count = (
        db.query(func.count(Trip.id))
        .filter(Trip.account_id == account_id)
        .scalar() or 0
    )

    return templates.TemplateResponse("admin_billing_account.html", {
        "request": request,
        "account": account,
        "sub": sub,
        "owner": owner,
        "members": members,
        "trip_count": trip_count,
    })


@router.post("/admin/billing/reconcile/{account_id}")
async def admin_reconcile(account_id: int, request: Request, db: Session = Depends(get_db)):
    is_admin = request.session.get("role") == "admin"
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = reconcile_subscription_from_stripe(db, account_id)
    db.commit()
    logger.info("Admin reconcile account %s: %s", account_id, result)

    if _is_htmx(request):
        status_text = result.get("status", "unknown")
        if status_text == "reconciled":
            html = f'<span class="text-green-600 font-semibold">Reconciled: {result.get("old_plan")} -> {result.get("new_plan")}, {result.get("old_status")} -> {result.get("new_status")}</span>'
        elif status_text == "no_stripe_subscription":
            html = '<span class="text-gray-500">No Stripe subscription linked</span>'
        elif status_text == "stripe_subscription_not_found":
            html = '<span class="text-amber-600">Stripe sub not found, reset to FREE</span>'
        else:
            html = f'<span class="text-red-600">{result.get("error", "Unknown error")}</span>'
        from starlette.responses import HTMLResponse
        return HTMLResponse(html)

    from fastapi.responses import JSONResponse
    return JSONResponse(result)
