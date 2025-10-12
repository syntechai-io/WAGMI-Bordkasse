from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import Trip, TripStatus
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
    db: Session = Depends(get_db)
):
    """Set a trip as active"""
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
    db: Session = Depends(get_db)
):
    """Archive a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.status = TripStatus.archived
    if not trip.end_date:
        trip.end_date = date.today()
    
    db.commit()
    
    return RedirectResponse(url="/trips", status_code=303)
