from fastapi.templating import Jinja2Templates
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi import Request
from typing import Dict, Any
from sqlalchemy.orm import Session
from db import get_db
from models import Trip, BoatProfile
from services.trip import TripService
from i18n import get_lang, t as i18n_t
from constants.logbook_enums import (
    normalize_wind, normalize_visibility, normalize_sail_plan,
    display_wind, display_visibility, display_sail_plan,
)


def trip_context_processor(request: Request) -> Dict[str, Any]:
    """Add trip information and branding to all template contexts"""
    context = {
        "all_trips": [],
        "selected_trip": None,
        "boat_brand_name": None,
        "show_brand": False,
        "brand_label": "CrewLog",
        "brand_is_default": True,
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
            if bp and not bp.boat_name_is_default:
                context["boat_brand_name"] = bp.boat_name
                context["show_brand"] = True
                context["brand_label"] = bp.boat_name
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

    return {
        "lang": lang,
        "t": _t,
        "display_wind": _display_wind,
        "display_visibility": _display_visibility,
        "display_sail_plan": _display_sail_plan,
        "norm_wind": _normalize_wind_val,
        "norm_vis": _normalize_visibility_val,
        "norm_sail": _normalize_sail_plan_val,
    }


def create_templates() -> Jinja2Templates:
    """Create Jinja2Templates instance with CSRF token processor and trip context"""
    templates = Jinja2Templates(
        directory="templates",
        context_processors=[
            csrf_token_processor("csrftoken", "x-csrftoken"),
            trip_context_processor,
            i18n_context_processor,
        ]
    )
    return templates
