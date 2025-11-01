from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import Trip, TripStatus, CrewMember
from services.trip import TripService
from datetime import date

router = APIRouter(prefix="/trips", tags=["trips"])
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

@router.get("/", response_class=HTMLResponse)
async def trips_page(request: Request, db: Session = Depends(get_db)):
    """Display all trips"""
    trips = db.query(Trip).order_by(Trip.start_date.desc()).all()
    active_trip = db.query(Trip).filter(Trip.status == TripStatus.active).first()
    
    return templates.TemplateResponse("trips.html", {
        "request": request,
        "trips": trips,
        "active_trip": active_trip
    })

@router.post("/new")
async def create_trip(
    request: Request,
    name: str = Form(...),
    start_date: date = Form(...),
    db: Session = Depends(get_db)
):
    """Create a new trip"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create trips")
    
    trip = Trip(
        name=name,
        start_date=start_date,
        status=TripStatus.active
    )
    
    current_active = db.query(Trip).filter(Trip.status == TripStatus.active).first()
    if current_active:
        current_active.status = TripStatus.archived
        current_active.end_date = date.today()
    
    db.add(trip)
    db.commit()
    
    return RedirectResponse(url="/trips", status_code=303)

@router.post("/{trip_id}/activate")
async def activate_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Set a trip as active"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can activate trips")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    current_active = db.query(Trip).filter(Trip.status == TripStatus.active).first()
    if current_active:
        current_active.status = TripStatus.archived
        if not current_active.end_date:
            current_active.end_date = date.today()
    
    trip.status = TripStatus.active
    trip.end_date = None
    
    db.commit()
    
    return RedirectResponse(url="/trips", status_code=303)

@router.post("/{trip_id}/archive")
async def archive_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Archive a trip"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can archive trips")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.status = TripStatus.archived
    if not trip.end_date:
        trip.end_date = date.today()
    
    db.commit()
    
    return RedirectResponse(url="/trips", status_code=303)

@router.post("/{trip_id}/close")
async def close_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Close a trip (admin only - prevents crew from making changes)"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can close trips")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.is_closed = 1
    db.commit()
    
    return RedirectResponse(url="/trips", status_code=303)

@router.post("/{trip_id}/reopen")
async def reopen_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Reopen a trip (admin only - allows crew to make changes again)"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can reopen trips")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.is_closed = 0
    db.commit()
    
    return RedirectResponse(url="/trips", status_code=303)

@router.post("/{trip_id}/select")
async def select_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Select a trip to view/work with"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    TripService.set_selected_trip(request, trip_id)
    
    return RedirectResponse(url="/", status_code=303)

@router.get("/passwords", response_class=HTMLResponse)
async def passwords_page(request: Request, db: Session = Depends(get_db)):
    """Password management page (admin only)"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage passwords")
    
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Get trip admins for this trip
    trip_admins = db.query(CrewMember).filter(
        CrewMember.trip_id == active_trip.id,
        CrewMember.is_trip_admin == 1
    ).all()
    
    success = request.session.pop("success", None)
    error = request.session.pop("error", None)
    
    return templates.TemplateResponse("passwords.html", {
        "request": request,
        "trip": active_trip,
        "trip_admins": trip_admins,
        "has_trip_admin_password": bool(active_trip.trip_admin_password_hash),
        "has_crew_password": bool(active_trip.crew_password_hash),
        "success": success,
        "error": error
    })

@router.post("/passwords")
async def update_passwords(
    request: Request,
    trip_admin_password: str = Form(""),
    crew_password: str = Form(""),
    db: Session = Depends(get_db)
):
    """Update trip passwords (admin only)"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage passwords")
    
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    try:
        # Update trip admin password if provided
        if trip_admin_password.strip():
            active_trip.set_trip_admin_password(trip_admin_password.strip())
        
        # Update crew password if provided
        if crew_password.strip():
            active_trip.set_crew_password(crew_password.strip())
        
        db.commit()
        request.session["success"] = "Passwörter erfolgreich gespeichert."
        
    except Exception as e:
        db.rollback()
        request.session["error"] = f"Fehler beim Speichern: {str(e)}"
    
    return RedirectResponse(url="/trips/passwords", status_code=303)
