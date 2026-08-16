from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from middleware.csrf import BootstrapFastAPICSRFJinjaMiddleware
from sqlalchemy import func
from db import init_db, get_db
from sqlalchemy.orm import Session, joinedload
from models import Deposit, Expense, PaidFromEnum, Trip, CrewMember, LogbookEntry
from seed_data import seed_database
from services.trip import TripService
from services.track import compute_track_summary
from services import legs as LegService
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from limiter_config import limiter
import os

from routers.crew import router as crew_router
from routers.deposits import router as deposits_router
from routers.expenses import router as expenses_router
from routers.receipts import router as receipts_router
from routers.balances import router as balances_router
from routers.export import router as export_router
from routers.auth import router as auth_router
from routers.trips import router as trips_router
from routers.logbook import router as logbook_router
from routers.templates import router as templates_router
from routers.groups import router as groups_router
from routers.legs import router as legs_router
from routers.api import router as api_router
from routers.widget import router as widget_router
from routes_auth import router as saas_auth_router
from routes_billing import router as billing_router
from routes_billing_ui import router as billing_ui_router
from routes_boat import router as boat_router
from routes_password_reset import router as password_reset_router
from i18n import set_lang, SUPPORTED_LANGS

app = FastAPI(title="CrewLog - Maritime Logbook & Bordkasse")

# Use shared limiter instance
app.state.limiter = limiter

# Add custom exception handler for rate limiting to return proper 429 responses
from fastapi.responses import JSONResponse
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler that returns 429 Too Many Requests with Retry-After header"""
    response = JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later."
        }
    )
    # Add Retry-After header (60 seconds for minute-based limits)
    response.headers["Retry-After"] = "60"
    return response

# Add SlowAPI middleware
app.add_middleware(SlowAPIMiddleware)

# Auth middleware to protect all routes (must be added BEFORE SessionMiddleware)
from middleware.auth import AuthMiddleware
app.add_middleware(AuthMiddleware)

# Detect production environment (Replit deployment or explicit env var)
is_production = os.getenv("REPL_DEPLOYMENT") == "1" or os.getenv("ENVIRONMENT") == "production"

# Session middleware for authentication (must be added AFTER AuthMiddleware due to LIFO execution)
session_secret = os.getenv("SESSION_SECRET")
if not session_secret:
    raise RuntimeError("SESSION_SECRET environment variable is required for security!")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    max_age=86400,
    same_site='lax',
    https_only=is_production  # Force secure cookies in production for HTTPS
)

csrf_secret = os.getenv("CSRF_SECRET", session_secret)

import re
app.add_middleware(
    BootstrapFastAPICSRFJinjaMiddleware,
    secret=csrf_secret,
    cookie_name="csrftoken",
    header_name="x-csrftoken",
    sensitive_cookies={"session"},
    exempt_urls=[re.compile(r"^/stripe/webhook$")],
    cookie_samesite="lax",
    cookie_secure=is_production,
    cookie_domain=None
)

# Cache control middleware to prevent browser caching of HTML pages
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Only apply cache-control to HTML responses, not static files
        if isinstance(response, Response) and response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(CacheControlMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

from template_helpers import create_templates
templates = create_templates()

init_db()

with next(get_db()) as db:
    seed_database(db)

app.include_router(auth_router)
app.include_router(api_router, prefix="/api")
app.include_router(widget_router, prefix="/api")
app.include_router(trips_router)
app.include_router(crew_router)
app.include_router(deposits_router)
app.include_router(expenses_router)
app.include_router(receipts_router)
app.include_router(balances_router)
app.include_router(export_router)
app.include_router(logbook_router)
app.include_router(templates_router)
app.include_router(groups_router)
app.include_router(legs_router)
app.include_router(saas_auth_router)
app.include_router(billing_router)
app.include_router(billing_ui_router)
app.include_router(boat_router)
app.include_router(password_reset_router)

@app.get("/privacy")
async def privacy_policy(request: Request):
    from i18n import get_lang, t as _t
    lang = get_lang(request)
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/terms")
async def terms_of_service(request: Request):
    from i18n import get_lang, t as _t
    lang = get_lang(request)
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/ios/return")
async def ios_return(request: Request):
    return templates.TemplateResponse("ios_return.html", {"request": request})

@app.get("/diagnostics/theme")
async def theme_diagnostics(request: Request, theme: str = "night"):
    """Standalone visual smoke-test page for the active theme.
    Loads cl_design.css + ui_night_mode.css fresh (no cookies, no auth)
    and renders one of every primitive so the user can confirm the
    Night Mode palette is correctly applied. ?theme=light to compare.
    """
    safe_theme = theme if theme in ("night", "light", "auto") else "night"
    response = templates.TemplateResponse(
        "theme_diagnostics.html",
        {"request": request, "theme": safe_theme},
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/.well-known/apple-app-site-association")
async def apple_app_site_association():
    from fastapi.responses import JSONResponse
    aasa = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": "TEAMID.app.crewlog.mobile",
                    "paths": ["/ios/return", "/ios/*"]
                }
            ]
        },
        "webcredentials": {
            "apps": ["TEAMID.app.crewlog.mobile"]
        }
    }
    return JSONResponse(content=aasa, media_type="application/json")

@app.post("/api/preferences/theme")
async def set_theme_preference(request: Request, db: Session = Depends(get_db)):
    """Persist the user's theme choice. Body: {"theme": "auto"|"light"|"night"}.
    Upserts UserPreferences.theme keyed by legacy user_id OR saas_user_id, depending
    on the active session. Anonymous callers get a 200 ack (localStorage only).
    CSRF-protected by global middleware."""
    try:
        body = await request.json()
        theme = (body or {}).get("theme")
    except Exception:
        theme = None
    if theme not in ("auto", "light", "night"):
        return JSONResponse({"error": "invalid theme"}, status_code=400)

    user_id = request.session.get("user_id")
    saas_user_id = request.session.get("saas_user_id")
    if user_id or saas_user_id:
        from models import UserPreferences
        if user_id:
            pref = db.query(UserPreferences).filter_by(user_id=user_id).first()
        else:
            pref = db.query(UserPreferences).filter_by(saas_user_id=saas_user_id).first()
        if pref is None:
            pref = UserPreferences(
                user_id=user_id or None,
                saas_user_id=saas_user_id or None,
                theme=theme,
            )
            db.add(pref)
        else:
            pref.theme = theme
        db.commit()
    return JSONResponse({"ok": True, "theme": theme})


@app.get("/about")
async def about_page(request: Request, db: Session = Depends(get_db)):
    from i18n import get_lang
    lang = get_lang(request)
    saas_user_id = request.session.get("saas_user_id")
    account_id = request.session.get("account_id")
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    session_mode = "saas" if saas_user_id else ("legacy" if user_id else "none")

    widget_enabled = False
    widget_issued_at = None
    widget_last_used_at = None
    if saas_user_id:
        from models import WidgetToken
        active = (
            db.query(WidgetToken)
            .filter(
                WidgetToken.user_id == saas_user_id,
                WidgetToken.revoked_at.is_(None),
            )
            .order_by(WidgetToken.created_at.desc())
            .first()
        )
        if active:
            widget_enabled = True
            widget_issued_at = active.created_at
            widget_last_used_at = active.last_used_at

    return templates.TemplateResponse("about.html", {
        "request": request,
        "app_version": "1.0.0",
        "build_number": "1",
        "session_mode": session_mode,
        "account_id": account_id,
        "current_lang": lang,
        "widget_enabled": widget_enabled,
        "widget_issued_at": widget_issued_at,
        "widget_last_used_at": widget_last_used_at,
    })

@app.get("/set-language")
@app.post("/set-language")
async def set_language(request: Request):
    if request.method == "POST":
        form = await request.form()
        lang = form.get("lang", "de")
        next_url = form.get("next", "/")
    else:
        lang = request.query_params.get("lang", "de")
        next_url = request.query_params.get("next", "/")

    if lang in SUPPORTED_LANGS:
        set_lang(request, lang)

    if not next_url or not next_url.startswith("/"):
        next_url = "/"

    is_htmx = request.headers.get("hx-request") == "true"
    if is_htmx:
        response = HTMLResponse("")
        response.headers["HX-Redirect"] = next_url
        return response

    return RedirectResponse(url=next_url, status_code=303)


@app.post("/set-mode")
async def set_app_mode(request: Request, mode: str = Form(...)):
    """Toggle between 'full' and 'logbook' app modes. Stored in session."""
    if mode in ("logbook", "full"):
        request.session["app_mode"] = mode
    referer = request.headers.get("referer", "/")
    if not referer.startswith("/"):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(referer)
            referer = parsed.path or "/"
            if parsed.query:
                referer = f"{referer}?{parsed.query}"
        except Exception:
            referer = "/"
    return RedirectResponse(url=referer, status_code=303)


@app.get("/sw.js")
async def service_worker():
    """Serve the service worker with its CACHE_NAME bound to the current
    asset version. Substituting at request time means a CSS deploy
    rotates the SW cache without anyone editing static/sw.js."""
    from fastapi.responses import Response
    from pathlib import Path
    from asset_version import CACHE_NAME_PLACEHOLDER, cache_name
    sw_text = Path("static/sw.js").read_text(encoding="utf-8")
    sw_text = sw_text.replace(CACHE_NAME_PLACEHOLDER, cache_name())
    return Response(
        content=sw_text,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"}
    )


@app.get("/offline", response_class=HTMLResponse)
async def offline_page(request: Request):
    templates = create_templates()
    return templates.TemplateResponse("offline.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    selected_trip = TripService.get_selected_trip(request, db)
    if not selected_trip:
        return RedirectResponse(url="/trips/", status_code=303)
    
    trip_id = selected_trip.id
    user_role = request.session.get("role", "crew")
    is_editable = TripService.is_trip_editable(selected_trip, user_role, request)
    
    total_deposits = db.query(func.sum(Deposit.amount_eur)).filter(
        Deposit.trip_id == trip_id
    ).scalar() or 0.0
    
    wallet_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.trip_id == trip_id,
        Expense.paid_from == PaidFromEnum.wallet
    ).scalar() or 0.0
    
    private_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.trip_id == trip_id,
        Expense.paid_from == PaidFromEnum.private
    ).scalar() or 0.0
    
    total_expenses = wallet_expenses + private_expenses
    wallet_balance = total_deposits - wallet_expenses
    
    top_categories = db.query(
        Expense.category,
        func.sum(Expense.amount_eur).label('total')
    ).filter(Expense.trip_id == trip_id).group_by(Expense.category).order_by(func.sum(Expense.amount_eur).desc()).limit(5).all()
    
    expense_count = db.query(Expense).filter(Expense.trip_id == trip_id).count()

    # Törn hub summary: trip stats, legs/route, and recent logbook activity —
    # composed here so "/" is a single place showing this trip right now,
    # instead of splitting it across the dashboard/trips-list/logbook pages.
    track_summary = compute_track_summary(db, trip_id)
    crew_count = db.query(CrewMember).filter(
        CrewMember.trip_id == trip_id, CrewMember.departed_at.is_(None)
    ).count()
    trip_legs = LegService.list_legs_for_trip(db, trip_id)
    recent_entries = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.leg)
    ).filter(
        LogbookEntry.trip_id == trip_id, LogbookEntry.is_superseded.is_(False)
    ).order_by(LogbookEntry.entry_date.desc()).limit(5).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_trip": selected_trip,
        "is_editable": is_editable,
        "wallet_balance": round(wallet_balance, 2),
        "total_deposits": round(total_deposits, 2),
        "total_expenses": round(total_expenses, 2),
        "wallet_expenses": round(wallet_expenses, 2),
        "private_expenses": round(private_expenses, 2),
        "top_categories": top_categories,
        "expense_count": expense_count,
        "trip_total_nm": track_summary.get("total_nm"),
        "trip_day_count": len(track_summary.get("days") or []),
        "trip_entry_count": track_summary.get("entry_count"),
        "crew_count": crew_count,
        "trip_legs": trip_legs,
        "recent_entries": recent_entries,
    })
