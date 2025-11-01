from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import User, CrewMember, Trip, TripStatus
from limiter_config import limiter
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor

router = APIRouter()
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Display login page"""
    error = request.session.pop("login_error", None)
    
    # Get all trips for trip selection (for trip admin/crew login)
    trips = db.query(Trip).order_by(Trip.start_date.desc()).all()
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "trips": trips
    })

@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    trip_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """Process login with rate limiting (5 attempts per minute per IP)
    
    Supports three authentication methods:
    1. Global Admin (Sven) - username + admin password
    2. Trip Admin - crew username + trip admin password + trip selection
    3. Crew - crew username + crew password + trip selection
    """
    
    # Check 1: Global Admin login (User table)
    user = db.query(User).filter(User.username == username).first()
    if user and user.check_password(password):
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["role"] = user.role.value
        return RedirectResponse(url="/", status_code=303)
    
    # Check 2 & 3: Trip Admin or Crew login (CrewMember table)
    if trip_id:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            request.session["login_error"] = "Ungültiger Törn ausgewählt"
            return RedirectResponse(url="/login", status_code=303)
        
        # Find crew member by username (code) in this trip
        crew_member = db.query(CrewMember).filter(
            CrewMember.code == username,
            CrewMember.trip_id == trip_id
        ).first()
        
        if crew_member:
            # Check if trip admin password matches
            if crew_member.is_trip_admin and trip.check_trip_admin_password(password):
                # Trip Admin login successful
                request.session["user_id"] = f"crew_{crew_member.id}"
                request.session["crew_member_id"] = crew_member.id
                request.session["username"] = crew_member.code
                request.session["role"] = "crew"
                request.session["trip_admin_trip_id"] = trip_id  # Mark as trip admin for this trip
                return RedirectResponse(url="/", status_code=303)
            
            # Check if crew password matches
            if trip.check_crew_password(password):
                # Crew login successful
                request.session["user_id"] = f"crew_{crew_member.id}"
                request.session["crew_member_id"] = crew_member.id
                request.session["username"] = crew_member.code
                request.session["role"] = "crew"
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
