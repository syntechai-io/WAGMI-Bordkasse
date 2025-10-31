from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import Trip, TripStatus
from services.trip import TripService
from services.auth import TripAuthService
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
    if "user_id" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    user_id = request.session["user_id"]
    
    TripService.set_selected_trip(request, trip_id)
    TripAuthService.update_session_for_trip(request, user_id, trip_id, db)
    
    return RedirectResponse(url="/", status_code=303)

@router.get("/{trip_id}/edit", response_class=HTMLResponse)
async def edit_trip_form(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Display edit form for a trip"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can edit trips")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    return templates.TemplateResponse("trip_edit.html", {
        "request": request,
        "trip": trip
    })

@router.post("/{trip_id}/edit")
async def update_trip(
    trip_id: int,
    request: Request,
    name: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(None),
    db: Session = Depends(get_db)
):
    """Update a trip"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can edit trips")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.name = name
    trip.start_date = start_date
    trip.end_date = end_date if end_date else None
    
    db.commit()
    
    return RedirectResponse(url="/trips", status_code=303)
