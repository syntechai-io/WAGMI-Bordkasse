from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import LogbookEntry, LogbookPhoto, CrewOnWatch, CrewMember, SeaStateEnum
from services.trip import TripService
from services.audit import AuditService
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import uuid

router = APIRouter(prefix="/logbook", tags=["logbook"])
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}
MAX_FILE_SIZE = 10 * 1024 * 1024

@router.get("", response_class=HTMLResponse)
async def list_logbook_entries(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    entries = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.photos),
        joinedload(LogbookEntry.crew_on_watch).joinedload(CrewOnWatch.member)
    ).filter(LogbookEntry.trip_id == active_trip.id).order_by(LogbookEntry.entry_date.desc()).all()
    
    return templates.TemplateResponse("logbook.html", {
        "request": request,
        "entries": entries,
        "active_trip": active_trip
    })

@router.get("/new", response_class=HTMLResponse)
async def new_entry_form(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.name).all()
    sea_states = [s.value for s in SeaStateEnum]
    
    return templates.TemplateResponse("logbook_form.html", {
        "request": request,
        "crew_members": crew_members,
        "sea_states": sea_states,
        "active_trip": active_trip,
        "entry": None
    })

@router.post("/new")
async def create_entry(
    request: Request,
    entry_date: str = Form(...),
    entry_time: str = Form("12:00"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    wind_direction: Optional[str] = Form(None),
    wind_strength: Optional[str] = Form(None),
    sea_state: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    sail_plan: Optional[str] = Form(None),
    engine_hours: Optional[float] = Form(None),
    departure: Optional[str] = Form(None),
    destination: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    safety_checks: Optional[str] = Form(None),
    crew_on_watch_ids: List[int] = Form([]),
    clientTempId: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)
    
    # Check for duplicate using clientTempId (prevents duplicate entries during sync)
    if clientTempId:
        existing_entry = db.query(LogbookEntry).filter(
            LogbookEntry.client_temp_id == clientTempId
        ).first()
        if existing_entry:
            # Entry already exists, return success
            return RedirectResponse(url="/logbook", status_code=303)
    
    try:
        # Combine date and time
        entry_datetime = datetime.fromisoformat(f"{entry_date}T{entry_time}")
        # For now, use the same datetime for UTC (no timezone conversion available)
        # In future, could add timezone field to Trip model
        entry_datetime_utc = entry_datetime
        
        # Parse sea state enum
        sea_state_enum = SeaStateEnum(sea_state) if sea_state else None
        
        entry = LogbookEntry(
            trip_id=active_trip.id,
            client_temp_id=clientTempId,
            entry_date=entry_datetime,
            entry_date_utc=entry_datetime_utc,
            latitude=latitude,
            longitude=longitude,
            wind_direction=wind_direction,
            wind_strength=wind_strength,
            sea_state=sea_state_enum,
            visibility=visibility,
            temperature=temperature,
            sail_plan=sail_plan,
            engine_hours=engine_hours,
            departure=departure,
            destination=destination,
            notes=notes,
            safety_checks_completed=safety_checks
        )
        db.add(entry)
        db.flush()
        
        # Add crew on watch
        for crew_id in crew_on_watch_ids:
            crew_watch = CrewOnWatch(entry_id=entry.id, member_id=crew_id)
            db.add(crew_watch)
        
        db.commit()
        
        # Audit log
        AuditService.log(
            db=db,
            request=request,
            trip_id=active_trip.id,
            action="create",
            entity_type="logbook_entry",
            entity_id=entry.id,
            details=f"Created logbook entry for {entry_date}"
        )
        
        return RedirectResponse(url=f"/logbook/{entry.id}", status_code=303)
        
    except Exception as e:
        db.rollback()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.name).all()
        sea_states = [s.value for s in SeaStateEnum]
        return templates.TemplateResponse("logbook_form.html", {
            "request": request,
            "crew_members": crew_members,
            "sea_states": sea_states,
            "active_trip": active_trip,
            "entry": None,
            "error": f"Fehler beim Erstellen des Eintrags: {str(e)}"
        }, status_code=400)

@router.get("/{entry_id}", response_class=HTMLResponse)
async def view_entry(request: Request, entry_id: int, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    entry = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.photos),
        joinedload(LogbookEntry.crew_on_watch).joinedload(CrewOnWatch.member)
    ).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
    
    if not entry:
        return RedirectResponse(url="/logbook", status_code=303)
    
    return templates.TemplateResponse("logbook_detail.html", {
        "request": request,
        "entry": entry,
        "active_trip": active_trip
    })

@router.get("/{entry_id}/edit", response_class=HTMLResponse)
async def edit_entry_form(request: Request, entry_id: int, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    entry = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.crew_on_watch)
    ).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
    
    if not entry:
        return RedirectResponse(url="/logbook", status_code=303)
    
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.name).all()
    sea_states = [s.value for s in SeaStateEnum]
    
    return templates.TemplateResponse("logbook_form.html", {
        "request": request,
        "crew_members": crew_members,
        "sea_states": sea_states,
        "active_trip": active_trip,
        "entry": entry
    })

@router.post("/{entry_id}/edit")
async def update_entry(
    request: Request,
    entry_id: int,
    entry_date: str = Form(...),
    entry_time: str = Form("12:00"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    wind_direction: Optional[str] = Form(None),
    wind_strength: Optional[str] = Form(None),
    sea_state: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    sail_plan: Optional[str] = Form(None),
    engine_hours: Optional[float] = Form(None),
    departure: Optional[str] = Form(None),
    destination: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    safety_checks: Optional[str] = Form(None),
    crew_on_watch_ids: List[int] = Form([]),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
    if not entry:
        return RedirectResponse(url="/logbook", status_code=303)
    
    try:
        # Combine date and time
        entry_datetime = datetime.fromisoformat(f"{entry_date}T{entry_time}")
        # Update UTC datetime to match (no timezone conversion)
        entry_datetime_utc = entry_datetime
        
        # Parse sea state enum
        sea_state_enum = SeaStateEnum(sea_state) if sea_state else None
        
        # Update entry fields
        entry.entry_date = entry_datetime
        entry.entry_date_utc = entry_datetime_utc
        entry.latitude = latitude
        entry.longitude = longitude
        entry.wind_direction = wind_direction
        entry.wind_strength = wind_strength
        entry.sea_state = sea_state_enum
        entry.visibility = visibility
        entry.temperature = temperature
        entry.sail_plan = sail_plan
        entry.engine_hours = engine_hours
        entry.departure = departure
        entry.destination = destination
        entry.notes = notes
        entry.safety_checks_completed = safety_checks
        entry.updated_at = datetime.utcnow()
        
        # Update crew on watch
        db.query(CrewOnWatch).filter(CrewOnWatch.entry_id == entry_id).delete()
        for crew_id in crew_on_watch_ids:
            crew_watch = CrewOnWatch(entry_id=entry.id, member_id=crew_id)
            db.add(crew_watch)
        
        db.commit()
        
        # Audit log
        AuditService.log(
            db=db,
            request=request,
            trip_id=active_trip.id,
            action="update",
            entity_type="logbook_entry",
            entity_id=entry.id,
            details=f"Updated logbook entry for {entry_date}"
        )
        
        return RedirectResponse(url=f"/logbook/{entry.id}", status_code=303)
        
    except Exception as e:
        db.rollback()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.name).all()
        sea_states = [s.value for s in SeaStateEnum]
        return templates.TemplateResponse("logbook_form.html", {
            "request": request,
            "crew_members": crew_members,
            "sea_states": sea_states,
            "active_trip": active_trip,
            "entry": entry,
            "error": f"Fehler beim Aktualisieren des Eintrags: {str(e)}"
        }, status_code=400)

@router.post("/{entry_id}/delete")
async def delete_entry(request: Request, entry_id: int, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
    if not entry:
        return RedirectResponse(url="/logbook", status_code=303)
    
    # Delete associated photo files
    photos = db.query(LogbookPhoto).filter(LogbookPhoto.entry_id == entry_id).all()
    for photo in photos:
        filepath = Path("uploads") / photo.stored_filename
        if filepath.exists():
            filepath.unlink()
    
    # Audit log before deletion
    AuditService.log(
        db=db,
        request=request,
        trip_id=active_trip.id,
        action="delete",
        entity_type="logbook_entry",
        entity_id=entry.id,
        details=f"Deleted logbook entry from {entry.entry_date.strftime('%Y-%m-%d')}"
    )
    
    db.delete(entry)
    db.commit()
    
    return RedirectResponse(url="/logbook", status_code=303)

@router.post("/{entry_id}/photos/upload")
async def upload_photo(
    request: Request,
    entry_id: int,
    photo: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
    if not entry:
        return RedirectResponse(url="/logbook", status_code=303)
    
    # Validate file
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG and PNG images are allowed")
    
    content = await photo.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    # Save file
    ext = ".jpg" if "jpeg" in photo.content_type else ".png"
    filename = str(uuid.uuid4()) + ext
    filepath = Path("uploads") / filename
    filepath.write_bytes(content)
    
    # Create photo record
    photo_record = LogbookPhoto(
        entry_id=entry_id,
        stored_filename=filename,
        original_name=photo.filename or "unknown",
        caption=caption,
        content_type=photo.content_type,
        size_bytes=len(content)
    )
    db.add(photo_record)
    db.commit()
    
    # Audit log
    AuditService.log(
        db=db,
        request=request,
        trip_id=active_trip.id,
        action="upload",
        entity_type="logbook_photo",
        entity_id=photo_record.id,
        details=f"Uploaded photo to logbook entry {entry_id}"
    )
    
    return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)

@router.post("/photos/{photo_id}/delete")
async def delete_photo(request: Request, photo_id: int, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    photo = db.query(LogbookPhoto).join(LogbookEntry).filter(
        LogbookPhoto.id == photo_id,
        LogbookEntry.trip_id == active_trip.id
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    entry_id = photo.entry_id
    
    # Delete file
    filepath = Path("uploads") / photo.stored_filename
    if filepath.exists():
        filepath.unlink()
    
    # Audit log before deletion
    AuditService.log(
        db=db,
        request=request,
        trip_id=active_trip.id,
        action="delete",
        entity_type="logbook_photo",
        entity_id=photo.id,
        details=f"Deleted photo from logbook entry {entry_id}"
    )
    
    db.delete(photo)
    db.commit()
    
    return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)

@router.get("/photos/{photo_id}/view")
async def view_photo(request: Request, photo_id: int, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        raise HTTPException(status_code=403, detail="No active trip")
    
    # Security: Only allow viewing photos from the active trip
    photo = db.query(LogbookPhoto).join(LogbookEntry).filter(
        LogbookPhoto.id == photo_id,
        LogbookEntry.trip_id == active_trip.id
    ).first()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    filepath = Path("uploads") / photo.stored_filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Photo file not found")
    
    return FileResponse(str(filepath), media_type=photo.content_type)
