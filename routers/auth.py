from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from db import get_db
from models import User, CrewMember, Trip, TripStatus
from limiter_config import limiter
from services.trip import TripService
from template_helpers import create_templates

router = APIRouter()
templates = create_templates()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Display login page"""
    error = request.session.pop("login_error", None)
    reset_success = request.query_params.get("reset") == "success"
    
    trips = db.query(Trip).order_by(Trip.start_date.desc()).all()
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "trips": trips,
        "reset_success": reset_success,
    })

@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    trip_id: str = Form(""),
    db: Session = Depends(get_db)
):
    """Process login with rate limiting (5 attempts per minute per IP)
    
    Supports three authentication methods:
    1. Global Admin (Sven) - username + admin password (no trip selection needed)
    2. Trip Admin - crew username + trip admin password + trip selection
    3. Crew - crew username + crew password + trip selection
    """
    
    # Convert empty string to None for trip_id
    trip_id_int = None
    if trip_id and trip_id.strip():
        try:
            trip_id_int = int(trip_id)
        except ValueError:
            request.session["login_error"] = "Ungültiger Törn ausgewählt"
            return RedirectResponse(url="/login", status_code=303)
    
    # Check 1: Global Admin login (User table)
    user = db.query(User).filter(User.username == username).first()
    if user and user.check_password(password):
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["role"] = user.role.value
        
        # Auto-select active trip for admin (smooth UX, can switch later)
        active_trip = TripService.get_active_trip(db)
        if active_trip:
            TripService.set_selected_trip(request, int(active_trip.id))
            return RedirectResponse(url="/", status_code=303)
        else:
            # No active trip - send admin to trips page to select/create one
            return RedirectResponse(url="/trips/", status_code=303)
    
    # Check 2 & 3: Trip Admin or Crew login (CrewMember table)
    if trip_id_int:
        trip = db.query(Trip).filter(Trip.id == trip_id_int).first()
        if not trip:
            request.session["login_error"] = "Ungültiger Törn ausgewählt"
            return RedirectResponse(url="/login", status_code=303)
        
        # Find crew member by username (code) in this trip
        crew_member = db.query(CrewMember).filter(
            CrewMember.code == username,
            CrewMember.trip_id == trip_id_int
        ).first()
        
        if crew_member:
            # Check if trip admin password matches
            if int(crew_member.is_trip_admin) == 1 and trip.check_trip_admin_password(password):
                # Trip Admin login successful
                request.session["user_id"] = f"crew_{crew_member.id}"
                request.session["crew_member_id"] = crew_member.id
                request.session["username"] = crew_member.code
                request.session["role"] = "crew"
                request.session["trip_admin_trip_id"] = trip_id_int  # Mark as trip admin for this trip
                TripService.set_selected_trip(request, trip_id_int)  # Set selected trip
                return RedirectResponse(url="/", status_code=303)
            
            # Check if crew password matches
            if trip.check_crew_password(password):
                # Crew login successful
                request.session["user_id"] = f"crew_{crew_member.id}"
                request.session["crew_member_id"] = crew_member.id
                request.session["username"] = crew_member.code
                request.session["role"] = "crew"
                TripService.set_selected_trip(request, trip_id_int)  # Set selected trip
                return RedirectResponse(url="/", status_code=303)
    
    # Login failed
    request.session["login_error"] = "Ungültiger Benutzername, Passwort oder Törn"
    return RedirectResponse(url="/login", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    """Process logout"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    """Display help/guide page for crew"""
    return templates.TemplateResponse("help.html", {
        "request": request
    })
