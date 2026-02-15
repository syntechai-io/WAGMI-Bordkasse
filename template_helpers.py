from fastapi.templating import Jinja2Templates
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi import Request
from typing import Dict, Any
from sqlalchemy.orm import Session
from db import get_db
from models import Trip
from services.trip import TripService
from i18n import get_lang, t as i18n_t


def trip_context_processor(request: Request) -> Dict[str, Any]:
    """Add trip information to all template contexts"""
    context = {
        "all_trips": [],
        "selected_trip": None
    }
    
    db_generator = get_db()
    try:
        db = next(db_generator)
        
        if request.session.get("role") == "admin":
            all_trips = db.query(Trip).order_by(Trip.start_date.desc()).all()
            context["all_trips"] = all_trips
        
        selected_trip = TripService.get_selected_trip(request, db)
        context["selected_trip"] = selected_trip
        
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

    return {
        "lang": lang,
        "t": _t,
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
