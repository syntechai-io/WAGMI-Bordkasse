from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from template_helpers import create_templates
from sqlalchemy.orm import Session
from db import get_db
from models import Trip, TripStatus, CrewMember, UserPreferences, TripMember, TripRole
from services.trip import TripService
from services.quick_start import TripQuickStartService
from services.wagmi_report import WagmiAnnualReportService
from auth_saas import enforce_free_limits_for_trip_creation, get_active_account_id, get_effective_plan
from models import SaaSUser, PlanEnum
from datetime import date, datetime
from typing import Optional


def _get_account_id(request: Request) -> int:
    account_id = request.session.get("account_id")
    if not account_id:
        return 1
    return int(account_id)


def _scoped_trip_query(db, request):
    """Return a Trip query scoped to account_id when SaaS session exists."""
    q = db.query(Trip)
    account_id = get_active_account_id(request)
    if account_id:
        q = q.filter(Trip.account_id == account_id)
    return q

router = APIRouter(prefix="/trips", tags=["trips"])
templates = create_templates()

@router.get("/", response_class=HTMLResponse)
async def trips_page(request: Request, db: Session = Depends(get_db)):
    """Display all trips — scoped to account when SaaS session exists"""
    trips = _scoped_trip_query(db, request).order_by(Trip.start_date.desc()).all()
    active_trip = _scoped_trip_query(db, request).filter(Trip.status == TripStatus.active).first()
    
    account_id = get_active_account_id(request)
    current_plan = None
    is_saas_owner = False
    is_legacy_admin = request.session.get("role") == "admin"

    if account_id:
        current_plan = get_effective_plan(account_id, db).value
        saas_uid = request.session.get("saas_user_id")
        if saas_uid:
            saas_user = db.query(SaaSUser).filter(SaaSUser.id == saas_uid).first()
            is_saas_owner = bool(saas_user and saas_user.is_owner)
    elif is_legacy_admin:
        current_plan = get_effective_plan(1, db).value
        is_saas_owner = True

    return templates.TemplateResponse("trips.html", {
        "request": request,
        "trips": trips,
        "active_trip": active_trip,
        "current_plan": current_plan,
        "is_saas_owner": is_saas_owner,
    })

@router.post("/quick-start")
async def quick_start_trip(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a quick start trip with user's defaults and first logbook entry"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create trips")
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    account_id = _get_account_id(request)
    enforce_free_limits_for_trip_creation(db, account_id)

    # Scope active trip lookup to account to avoid cross-tenant archiving
    current_active = _scoped_trip_query(db, request).filter(Trip.status == TripStatus.active).first()
    if current_active:
        current_active.status = TripStatus.archived
        if not current_active.end_date:
            current_active.end_date = date.today()
        db.commit()
    
    saas_user_id = request.session.get("saas_user_id")
    trip = TripQuickStartService.create_quick_start_trip(db, user_id, account_id, saas_user_id)
    
    TripService.set_selected_trip(request, trip.id)
    
    return RedirectResponse(url="/", status_code=303)

@router.post("/new")
async def create_trip(
    request: Request,
    name: str = Form(...),
    start_date: date = Form(...),
    solo_sailing: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new trip"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create trips")
    
    account_id = _get_account_id(request)
    enforce_free_limits_for_trip_creation(db, account_id)
    
    trip = Trip(
        name=name,
        start_date=start_date,
        status=TripStatus.active,
        account_id=account_id
    )
    
    # If solo sailing, get user preferences once and use for both trip and crew
    prefs = None
    if solo_sailing == "true":
        user_id = request.session.get("user_id")
        if user_id:
            prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        
        # Always set skipper and vessel defaults from preferences
        # Note: call_sign and imo_mmsi are not in UserPreferences, must be set manually
        trip.skipper_name = (prefs.skipper_name if prefs and prefs.skipper_name else "Skipper")
        trip.skipper_code = (prefs.skipper_code if prefs and prefs.skipper_code else "SK")
        trip.home_port = (prefs.home_port if prefs and prefs.home_port else None)
    
    # Scope active trip lookup to account to avoid cross-tenant archiving
    current_active = _scoped_trip_query(db, request).filter(Trip.status == TripStatus.active).first()
    if current_active:
        current_active.status = TripStatus.archived
        current_active.end_date = date.today()
    
    db.add(trip)
    db.commit()
    db.refresh(trip)
    
    saas_user_id = request.session.get("saas_user_id")
    if saas_user_id:
        db.add(TripMember(
            trip_id=trip.id,
            user_id=saas_user_id,
            role=TripRole.skipper,
            created_at=datetime.utcnow(),
        ))
        db.commit()

    if solo_sailing == "true":
        crew_code = (prefs.skipper_code if prefs and prefs.skipper_code else "SK")
        crew_name = (prefs.skipper_name if prefs and prefs.skipper_name else "Skipper")
        
        crew_member = CrewMember(
            trip_id=trip.id,
            code=crew_code,
            name=crew_name,
            is_trip_admin=1
        )
        db.add(crew_member)
        db.commit()
    
    return RedirectResponse(url="/trips/", status_code=303)

@router.post("/{trip_id}/activate")
async def activate_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Set a trip as active — scoped to account when SaaS session exists"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can activate trips")
    
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    current_active = _scoped_trip_query(db, request).filter(Trip.status == TripStatus.active).first()
    if current_active:
        current_active.status = TripStatus.archived
        if not current_active.end_date:
            current_active.end_date = date.today()
    
    trip.status = TripStatus.active
    trip.end_date = None
    
    db.commit()
    
    return RedirectResponse(url="/trips/", status_code=303)

@router.post("/{trip_id}/archive")
async def archive_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Archive a trip — scoped to account"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can archive trips")
    
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.status = TripStatus.archived
    if not trip.end_date:
        trip.end_date = date.today()
    
    db.commit()
    
    return RedirectResponse(url="/trips/", status_code=303)

@router.post("/{trip_id}/close")
async def close_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Close a trip — scoped to account"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can close trips")
    
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.is_closed = 1
    db.commit()
    
    return RedirectResponse(url="/trips/", status_code=303)

@router.post("/{trip_id}/reopen")
async def reopen_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Reopen a trip — scoped to account"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can reopen trips")
    
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.is_closed = 0
    db.commit()
    
    return RedirectResponse(url="/trips/", status_code=303)

@router.post("/{trip_id}/select")
async def select_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Select a trip to view/work with — scoped to account"""
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
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
        return RedirectResponse(url="/trips/", status_code=303)
    
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
        return RedirectResponse(url="/trips/", status_code=303)
    
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

@router.get("/wagmi/report", response_class=HTMLResponse)
async def wagmi_annual_report(request: Request, db: Session = Depends(get_db)):
    """WAGMI yearly sailing report (admin only)"""
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can view reports")
    
    yearly_stats = WagmiAnnualReportService.get_yearly_report(db, start_year=2026)
    
    # Sort years in descending order (most recent first)
    sorted_years = sorted(yearly_stats.keys(), reverse=True)
    
    return templates.TemplateResponse("wagmi_report.html", {
        "request": request,
        "yearly_stats": yearly_stats,
        "sorted_years": sorted_years
    })
