from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from template_helpers import create_templates
from sqlalchemy.orm import Session
from db import get_db
from models import Trip, TripStatus, CrewMember, UserPreferences, TripMember, TripRole
from services.trip import TripService
from services.quick_start import TripQuickStartService
from services.wagmi_report import WagmiAnnualReportService
from services.track import compute_track_summary
from auth_saas import enforce_free_limits_for_trip_creation, get_active_account_id, get_effective_plan
from models import SaaSUser, PlanEnum
from datetime import date, datetime
from typing import Optional


def _get_account_id(request: Request) -> int:
    account_id = request.session.get("account_id")
    if not account_id:
        return 1
    return int(account_id)


def _is_admin_or_owner(request: Request, db: Session) -> bool:
    if request.session.get("role") == "admin":
        return True
    saas_uid = request.session.get("saas_user_id")
    session_account = request.session.get("account_id")
    if saas_uid and session_account:
        saas_user = db.query(SaaSUser).filter(
            SaaSUser.id == saas_uid,
            SaaSUser.account_id == session_account
        ).first()
        if saas_user and saas_user.is_owner:
            return True
    return False


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
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can create trips")
    
    user_id = request.session.get("user_id") or request.session.get("saas_user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    account_id = _get_account_id(request)
    if request.session.get("role") != "admin":
        try:
            enforce_free_limits_for_trip_creation(db, account_id)
        except HTTPException as e:
            if isinstance(e.detail, dict) and e.detail.get("code") == "UPGRADE_REQUIRED":
                return RedirectResponse(url="/trips?upgrade_required=1", status_code=303)
            raise

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
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can create trips")
    
    account_id = _get_account_id(request)
    if request.session.get("role") != "admin":
        try:
            enforce_free_limits_for_trip_creation(db, account_id)
        except HTTPException as e:
            if isinstance(e.detail, dict) and e.detail.get("code") == "UPGRADE_REQUIRED":
                return RedirectResponse(url="/trips?upgrade_required=1", status_code=303)
            raise

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
    if not _is_admin_or_owner(request, db):
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
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can archive trips")
    
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.status = TripStatus.archived
    if not trip.end_date:
        trip.end_date = date.today()
    
    db.commit()
    
    return RedirectResponse(url="/trips/", status_code=303)

@router.get("/{trip_id}/finalize", response_class=HTMLResponse)
async def finalize_trip_form(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Render finalize summary + confirmation page before closing the trip."""
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can finalize trips")

    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Compute summary stats from logbook entries
    from models import LogbookEntry, LogbookPhoto, Expense
    from sqlalchemy import func
    entry_count = db.query(func.count(LogbookEntry.id)).filter(LogbookEntry.trip_id == trip.id).scalar() or 0
    total_nm = db.query(func.coalesce(func.sum(LogbookEntry.dist_day_nm), 0)).filter(
        LogbookEntry.trip_id == trip.id
    ).scalar() or 0
    photo_count = db.query(func.count(LogbookPhoto.id)).join(
        LogbookEntry, LogbookEntry.id == LogbookPhoto.entry_id
    ).filter(LogbookEntry.trip_id == trip.id).scalar() or 0
    expense_count = db.query(func.count(Expense.id)).filter(Expense.trip_id == trip.id).scalar() or 0
    expense_total = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.trip_id == trip.id
    ).scalar() or 0

    eng_readings = db.query(LogbookEntry.eng_hours_total).filter(
        LogbookEntry.trip_id == trip.id,
        LogbookEntry.eng_hours_total.isnot(None)
    ).all()
    eng_values = [r[0] for r in eng_readings if r[0] is not None]
    motor_hours = (max(eng_values) - min(eng_values)) if len(eng_values) >= 2 else 0

    first_entry = db.query(LogbookEntry).filter(
        LogbookEntry.trip_id == trip.id
    ).order_by(LogbookEntry.entry_date.asc()).first()
    last_entry = db.query(LogbookEntry).filter(
        LogbookEntry.trip_id == trip.id
    ).order_by(LogbookEntry.entry_date.desc()).first()

    # Sail hours = total active hours between first and last entry minus motor hours
    sail_hours = 0.0
    if first_entry and last_entry and last_entry.entry_date and first_entry.entry_date:
        total_active = (last_entry.entry_date - first_entry.entry_date).total_seconds() / 3600.0
        sail_hours = max(total_active - float(motor_hours), 0.0)

    summary = {
        "entry_count": entry_count,
        "photo_count": photo_count,
        "expense_count": expense_count,
        "expense_total": float(expense_total),
        "total_nm": round(float(total_nm), 1),
        "motor_hours": round(float(motor_hours), 1),
        "sail_hours": round(float(sail_hours), 1),
        "first_date": first_entry.entry_date if first_entry else None,
        "last_date": last_entry.entry_date if last_entry else None,
    }

    return templates.TemplateResponse("trip_finalize.html", {
        "request": request,
        "trip": trip,
        "summary": summary,
    })


@router.post("/{trip_id}/close")
async def close_trip(
    trip_id: int,
    request: Request,
    confirm: str = Form(default=""),
    db: Session = Depends(get_db)
):
    """Close a trip — scoped to account. Requires explicit confirm=yes from finalize form."""
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can close trips")

    if (confirm or "").strip().lower() != "yes":
        return RedirectResponse(url=f"/trips/{trip_id}/finalize", status_code=303)

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
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can reopen trips")
    
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.is_closed = 0
    db.commit()
    
    return RedirectResponse(url="/trips/", status_code=303)

@router.post("/{trip_id}/rename")
async def rename_trip(
    trip_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Rename a trip — scoped to account"""
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can rename trips")

    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip.name = name.strip() or trip.name
    db.commit()

    return RedirectResponse(url="/trips/", status_code=303)


@router.get("/{trip_id}/track", response_class=HTMLResponse)
async def trip_track_page(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Trip track page: Leaflet map + per-day distances + totals."""
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    summary = compute_track_summary(db, trip.id)

    return templates.TemplateResponse("trip_track.html", {
        "request": request,
        "trip": trip,
        "summary": summary,
    })


@router.get("/{trip_id}/track.json")
async def trip_track_json(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """JSON endpoint feeding the Leaflet map."""
    trip = _scoped_trip_query(db, request).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return compute_track_summary(db, trip.id)


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
    if not _is_admin_or_owner(request, db):
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
    if not _is_admin_or_owner(request, db):
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

@router.get("/yearly/report", response_class=HTMLResponse)
async def yearly_annual_report(request: Request, db: Session = Depends(get_db)):
    """Yearly sailing report (admin only)"""
    if not _is_admin_or_owner(request, db):
        raise HTTPException(status_code=403, detail="Only admin can view reports")
    
    account_id = _get_account_id(request)
    yearly_stats = WagmiAnnualReportService.get_yearly_report(db, account_id=account_id)
    
    sorted_years = sorted(yearly_stats.keys(), reverse=True)
    
    return templates.TemplateResponse("yearly_report.html", {
        "request": request,
        "yearly_stats": yearly_stats,
        "sorted_years": sorted_years
    })

@router.get("/wagmi/report", response_class=HTMLResponse)
async def wagmi_report_redirect(request: Request):
    """Backward-compatible redirect from old WAGMI report URL"""
    return RedirectResponse(url="/trips/yearly/report", status_code=301)
