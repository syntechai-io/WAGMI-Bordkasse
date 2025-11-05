from fastapi.templating import Jinja2Templates
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi import Request
from typing import Dict, Any
from sqlalchemy.orm import Session
from db import get_db
from models import Trip
from services.trip import TripService


def trip_context_processor(request: Request) -> Dict[str, Any]:
    """Add trip information to all template contexts"""
    context = {
        "all_trips": [],
        "selected_trip": None
    }
    
    # Get database session and ensure proper cleanup
    db_generator = get_db()
    try:
        db = next(db_generator)
        
        # Get all trips for trip selector (admin only)
        if request.session.get("role") == "admin":
            all_trips = db.query(Trip).order_by(Trip.start_date.desc()).all()
            context["all_trips"] = all_trips
        
        # Get currently selected trip
        selected_trip = TripService.get_selected_trip(request, db)
        context["selected_trip"] = selected_trip
        
    except Exception:
        # Fallback if database is not available
        pass
    finally:
        # Properly close the database session generator
        try:
            next(db_generator)
        except StopIteration:
            pass
    
    return context


def create_templates() -> Jinja2Templates:
    """Create Jinja2Templates instance with CSRF token processor and trip context"""
    templates = Jinja2Templates(
        directory="templates",
        context_processors=[
            csrf_token_processor("csrftoken", "x-csrftoken"),
            trip_context_processor
        ]
    )
    return templates
