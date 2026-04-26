from fastapi.templating import Jinja2Templates
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi import Request
from typing import Dict, Any
from sqlalchemy.orm import Session
from asset_version import asset_version
from db import get_db
from models import Trip, BoatProfile
from services.trip import TripService
from i18n import get_lang, t as i18n_t
from constants.logbook_enums import (
    normalize_wind, normalize_visibility, normalize_sail_plan,
    normalize_event_category,
    display_wind, display_visibility, display_sail_plan,
    display_event_category, display_sea_state,
)
from constants.expense_enums import (
    normalize_expense_category, display_expense_category,
)


def _build_branding(bp=None):
    defaults = {
        "brand_name": "CrewLog",
        "brand_subtitle": None,
        "brand_logo_url": None,
        "accent_color": None,
        "home_port_name": None,
        "home_port_lat": None,
        "home_port_lon": None,
        "is_default": True,
    }
    if not bp:
        return defaults
    if bp.boat_name and not bp.boat_name_is_default:
        defaults["brand_name"] = bp.boat_name
        defaults["is_default"] = False
    boat_parts = []
    if bp.boat_make:
        boat_parts.append(bp.boat_make)
    if bp.boat_model:
        boat_parts.append(bp.boat_model)
    if bp.boat_type:
        boat_parts.append(bp.boat_type)
    defaults["brand_subtitle"] = " ".join(boat_parts) if boat_parts else (bp.boat_type if bp.boat_type else None)
    defaults["brand_logo_url"] = bp.logo_url if bp.logo_url else None
    if bp.accent_color and bp.accent_color.startswith("#") and len(bp.accent_color) == 7:
        defaults["accent_color"] = bp.accent_color
    defaults["home_port_name"] = bp.home_port_name
    defaults["home_port_lat"] = bp.home_port_lat
    defaults["home_port_lon"] = bp.home_port_lon
    return defaults


def trip_context_processor(request: Request) -> Dict[str, Any]:
    """Add trip information and branding to all template contexts"""
    context = {
        "app_mode": request.session.get("app_mode", "full"),
        "all_trips": [],
        "selected_trip": None,
        "boat_brand_name": None,
        "show_brand": False,
        "brand_label": "CrewLog",
        "brand_is_default": True,
        "branding": _build_branding(),
    }
    
    db_generator = get_db()
    try:
        db = next(db_generator)
        
        if request.session.get("role") == "admin":
            all_trips = db.query(Trip).order_by(Trip.start_date.desc()).all()
            context["all_trips"] = all_trips
        
        selected_trip = TripService.get_selected_trip(request, db)
        context["selected_trip"] = selected_trip

        account_id = request.session.get("account_id")
        if account_id:
            bp = db.query(BoatProfile).filter(BoatProfile.account_id == account_id).first()
            branding = _build_branding(bp)
            context["branding"] = branding
            if not branding["is_default"]:
                context["boat_brand_name"] = branding["brand_name"]
                context["show_brand"] = True
                context["brand_label"] = branding["brand_name"]
                context["brand_is_default"] = False
        
    except Exception:
        pass
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass
    
    return context


def i18n_context_processor(request: Request) -> Dict[str, Any]:
    """Add i18n helpers to all template contexts"""
    lang = get_lang(request)

    def _t(key: str, **kwargs) -> str:
        return i18n_t(lang, key, **kwargs)

    def _display_wind(value):
        return display_wind(value, _t)

    def _display_visibility(value):
        return display_visibility(value, _t)

    def _display_sail_plan(value):
        return display_sail_plan(value, _t)

    def _normalize_wind_val(value):
        return normalize_wind(value) if value else ""

    def _normalize_visibility_val(value):
        return normalize_visibility(value) if value else ""

    def _normalize_sail_plan_val(value):
        return normalize_sail_plan(value) if value else ""

    def _normalize_event_category_val(value):
        return normalize_event_category(value) if value else ""

    def _display_event_category(value):
        return display_event_category(value, _t)

    def _display_sea_state(value):
        return display_sea_state(value, _t)

    def _display_expense_category(value):
        return display_expense_category(value, _t)

    def _normalize_expense_category_val(value):
        return normalize_expense_category(value) if value else ""

    # Resolve user's saved theme preference (legacy or SaaS users via UserPreferences row).
    # 'auto' is the default; client-side JS resolves Auto -> Day/Night via prefers-color-scheme.
    # theme_authoritative=True iff signed-in user has an explicit stored value -> server wins
    # over localStorage on the client. Otherwise client falls back to localStorage.
    saved_theme = "auto"
    theme_authoritative = False
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    saas_user_id = request.session.get("saas_user_id") if hasattr(request, "session") else None
    theme_signed_in = bool(user_id or saas_user_id)
    try:
        if user_id or saas_user_id:
            from db import SessionLocal
            from models import UserPreferences
            _db = SessionLocal()
            try:
                if user_id:
                    pref = _db.query(UserPreferences).filter_by(user_id=user_id).first()
                else:
                    pref = _db.query(UserPreferences).filter_by(saas_user_id=saas_user_id).first()
                if pref and pref.theme in ("auto", "light", "night"):
                    saved_theme = pref.theme
                    theme_authoritative = True
            finally:
                _db.close()
    except Exception:
        pass

    return {
        "lang": lang,
        "t": _t,
        "saved_theme": saved_theme,
        "theme_authoritative": theme_authoritative,
        "theme_signed_in": theme_signed_in,
        "display_wind": _display_wind,
        "display_visibility": _display_visibility,
        "display_sail_plan": _display_sail_plan,
        "display_event_category": _display_event_category,
        "display_sea_state": _display_sea_state,
        "norm_wind": _normalize_wind_val,
        "norm_vis": _normalize_visibility_val,
        "norm_sail": _normalize_sail_plan_val,
        "norm_event": _normalize_event_category_val,
        "display_expense_cat": _display_expense_category,
        "norm_expense_cat": _normalize_expense_category_val,
    }


def asset_version_context_processor(request: Request) -> Dict[str, Any]:
    """Expose the content-derived CSS cache-buster to every template.

    Templates render `?v={{ asset_version }}` on `<link>` tags so a CSS
    deploy automatically invalidates the browser cache. The same value
    drives the service-worker cache name (see `/sw.js` in `main.py`).
    """
    return {"asset_version": asset_version()}


def create_templates() -> Jinja2Templates:
    """Create Jinja2Templates instance with CSRF token processor and trip context"""
    templates = Jinja2Templates(
        directory="templates",
        context_processors=[
            csrf_token_processor("csrftoken", "x-csrftoken"),
            trip_context_processor,
            i18n_context_processor,
            asset_version_context_processor,
        ]
    )
    return templates
