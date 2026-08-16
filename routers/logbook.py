from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse, StreamingResponse, JSONResponse, Response
from template_helpers import create_templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import LogbookEntry, LogbookPhoto, CrewOnWatch, CrewMember, SeaStateEnum, Trip
from services.trip import TripService
from services.audit import AuditService
from services.boat import get_or_create_boat_profile, get_boat_profile_for_account
from datetime import datetime, date
from typing import List, Optional
from pathlib import Path
import uuid
import io
import json as _json
from logbook_pdf_template import render_logbook_pdf
from weather_service import WeatherService
from constants.logbook_enums import (
    normalize_wind, normalize_visibility, normalize_sail_plan,
    normalize_event_category, display_event_category, display_sea_state,
)
from i18n import get_lang, t as i18n_t


def _t(request, key, **kw):
    """Localize a message using the request's current language (DE/EN)."""
    try:
        return i18n_t(get_lang(request), key, **kw)
    except Exception:
        return key

router = APIRouter(prefix="/logbook", tags=["logbook"])
templates = create_templates()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_PHOTOS_PER_UPLOAD = 10


def build_logbook_entry(*, trip_id: int, entry_dt: datetime, **fields) -> LogbookEntry:
    """Shared helper used by /new and /day-new to construct a LogbookEntry
    with consistent normalization and the entry_date_utc compliance field.

    Pass already-validated values; this only applies normalize_* functions
    and ensures entry_date / entry_date_utc are set together.
    """
    sea_state_val = fields.get("sea_state")
    if sea_state_val is not None and not isinstance(sea_state_val, SeaStateEnum):
        sea_state_val = SeaStateEnum(sea_state_val)
    return LogbookEntry(
        trip_id=trip_id,
        client_temp_id=fields.get("client_temp_id"),
        watch_leader_id=fields.get("watch_leader_id"),
        entry_date=entry_dt,
        entry_date_utc=entry_dt,
        latitude=fields.get("latitude"),
        longitude=fields.get("longitude"),
        wind_direction=fields.get("wind_direction"),
        wind_strength=normalize_wind(fields.get("wind_strength")),
        sea_state=sea_state_val,
        visibility=normalize_visibility(fields.get("visibility")),
        temperature=fields.get("temperature"),
        sail_plan=normalize_sail_plan(fields.get("sail_plan")),
        engine_hours=fields.get("engine_hours"),
        departure=fields.get("departure"),
        destination=fields.get("destination"),
        notes=fields.get("notes"),
        safety_checks_completed=fields.get("safety_checks"),
        cog_deg=fields.get("cog_deg"),
        sog_kn=fields.get("sog_kn"),
        log_kn=fields.get("log_kn"),
        dist_day_nm=fields.get("dist_day_nm"),
        pressure_hpa=fields.get("pressure_hpa"),
        pressure_trend=fields.get("pressure_trend"),
        weather_source=fields.get("weather_source"),
        engine_on=fields.get("engine_on"),
        engine_on_time=fields.get("engine_on_time"),
        engine_off_time=fields.get("engine_off_time"),
        eng_hours_total=fields.get("eng_hours_total"),
        fuel_level_l=fields.get("fuel_level_l"),
        main_furl_pct=fields.get("main_furl_pct"),
        headsail=fields.get("headsail"),
        sail_action=fields.get("sail_action"),
        main_reef_level=fields.get("main_reef_level"),
        headsail_type=fields.get("headsail_type") or None,
        headsail_furl_percent=fields.get("headsail_furl_percent"),
        extra_sail=fields.get("extra_sail") or None,
        event_category=normalize_event_category(fields.get("event_category")) if fields.get("event_category") else None,
        event_details=fields.get("event_details"),
        maneuver_type=fields.get("maneuver_type") or "full",
    )

# Helper functions to convert empty strings to None for optional fields
def optional_float(value: str = Form(None)) -> Optional[float]:
    """Convert empty string to None, otherwise parse as float"""
    if value == "" or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def optional_int(value: str = Form(None)) -> Optional[int]:
    """Convert empty string to None, otherwise parse as int"""
    if value == "" or value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def optional_bool(value: str = Form(None)) -> Optional[bool]:
    """Convert string to bool"""
    if value == "" or value is None:
        return None
    return value.lower() in ("true", "1", "yes", "on")

@router.get("/day-recap", response_class=HTMLResponse)
async def day_recap_form(request: Request, db: Session = Depends(get_db)):
    """Render the Day Recap form — log multiple maneuvers for one day at once."""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips/", status_code=303)
    crew = db.query(CrewMember).filter(
        CrewMember.trip_id == active_trip.id
    ).order_by(CrewMember.name).all()
    today = date.today().isoformat()
    return templates.TemplateResponse("logbook_day_recap.html", {
        "request": request,
        "active_trip": active_trip,
        "crew": crew,
        "today": today,
    })


@router.post("/day-recap")
async def day_recap_submit(
    request: Request,
    recap_date: str = Form(...),
    departure_port: str = Form(""),
    destination_port: str = Form(""),
    total_nm_str: str = Form(""),
    events_json: str = Form(...),
    db: Session = Depends(get_db),
):
    """Save multiple logbook entries from a Day Recap submission."""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips/", status_code=303)

    # Parse + validate events_json defensively
    try:
        parsed = _json.loads(events_json)
    except Exception:
        parsed = []
    if not isinstance(parsed, list):
        parsed = []
    events = [ev for ev in parsed if isinstance(ev, dict)]

    if not events:
        request.session["error"] = "Bitte mindestens ein gültiges Ereignis hinzufügen."
        return RedirectResponse(url="/logbook/day-recap", status_code=303)

    try:
        recap_dt_date = date.fromisoformat(recap_date)
    except ValueError:
        recap_dt_date = date.today()

    total_nm = None
    try:
        if total_nm_str.strip():
            total_nm = float(total_nm_str.strip())
    except (ValueError, TypeError):
        pass

    saved_entries = []
    skipped = 0
    for ev in events:
        time_str = str(ev.get("time") or "12:00").strip()
        parts = time_str.split(":")
        try:
            hh = int(parts[0])
            mm = int(parts[1]) if len(parts) > 1 else 0
            if not (0 <= hh <= 23 and 0 <= mm <= 59):
                raise ValueError("time out of range")
        except (ValueError, IndexError):
            hh, mm = 12, 0
        try:
            entry_dt = datetime(
                recap_dt_date.year, recap_dt_date.month, recap_dt_date.day,
                hh, mm, 0
            )
        except (ValueError, TypeError):
            skipped += 1
            continue

        # Defensive lat/lon parsing
        lat_val = None
        lon_val = None
        try:
            raw_lat = ev.get("lat")
            if raw_lat not in (None, "", []):
                lat_val = float(raw_lat)
        except (ValueError, TypeError):
            lat_val = None
        try:
            raw_lon = ev.get("lon")
            if raw_lon not in (None, "", []):
                lon_val = float(raw_lon)
        except (ValueError, TypeError):
            lon_val = None

        # Combine maneuver label + notes into event_details
        maneuver_label = (ev.get("maneuver") or "").strip()
        notes = (ev.get("notes") or "").strip()
        if maneuver_label and notes:
            event_details = f"{maneuver_label}: {notes}"
        else:
            event_details = maneuver_label or notes or None

        # Category is the canonical code (e.g., "maneuver", "weather_change")
        category_raw = (ev.get("category") or "").strip() or None

        try:
            entry = build_logbook_entry(
                trip_id=active_trip.id,
                entry_dt=entry_dt,
                maneuver_type="recap",
                event_category=category_raw,
                event_details=event_details,
                latitude=lat_val,
                longitude=lon_val,
            )
            saved_entries.append(entry)
        except Exception:
            skipped += 1
            continue

    # Attach trip-level fields to the first / last successfully built entries
    # so the values aren't lost when trailing rows are malformed.
    if saved_entries:
        if departure_port:
            saved_entries[0].departure = departure_port
        if destination_port:
            saved_entries[-1].destination = destination_port
        if total_nm is not None:
            saved_entries[-1].dist_day_nm = total_nm
        for entry in saved_entries:
            db.add(entry)

    saved = len(saved_entries)
    if saved > 0:
        try:
            db.commit()
        except Exception:
            db.rollback()
            request.session["error"] = "Fehler beim Speichern der Einträge."
            return RedirectResponse(url="/logbook/day-recap", status_code=303)
        if skipped > 0:
            request.session["success"] = f"{saved} Einträge gespeichert, {skipped} übersprungen."
        else:
            request.session["success"] = f"{saved} Logbuch-Einträge gespeichert."
    else:
        request.session["error"] = "Keine gültigen Einträge gefunden."
        return RedirectResponse(url="/logbook/day-recap", status_code=303)

    return RedirectResponse(url="/logbook", status_code=303)


@router.get("/weather")
async def weather_proxy(
    request: Request,
    lat: float,
    lon: float,
    db: Session = Depends(get_db),
):
    """Auth-gated weather lookup for the logbook form. Calls Open-Meteo and
    maps the response to the field shape expected by the form JS."""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)

    data = WeatherService.fetch_weather_data(lat, lon)
    if not data:
        return JSONResponse({"error": "weather_unavailable"}, status_code=502)

    # Map wind speed (kn) to canonical Beaufort key (bft0..bft12) so the
    # hybrid select in the form can pick the matching option.
    speed = data.get("wind_speed_kn")
    bft_key = None
    if speed is not None:
        try:
            s = float(speed)
            cutoffs = [
                (1, "bft0"), (4, "bft1"), (7, "bft2"), (11, "bft3"),
                (17, "bft4"), (22, "bft5"), (28, "bft6"), (34, "bft7"),
                (41, "bft8"), (48, "bft9"), (56, "bft10"), (64, "bft11"),
            ]
            bft_key = "bft12"
            for max_speed, key in cutoffs:
                if s < max_speed:
                    bft_key = key
                    break
        except (ValueError, TypeError):
            bft_key = None

    return JSONResponse({
        "temperature": data.get("temperature"),
        "wind_direction": data.get("wind_direction_compass"),
        "wind_strength": bft_key,
        "pressure_hpa": data.get("pressure_hpa"),
    })


@router.get("", response_class=HTMLResponse)
async def list_logbook_entries(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    entries = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.photos),
        joinedload(LogbookEntry.crew_on_watch).joinedload(CrewOnWatch.member)
    ).filter(LogbookEntry.trip_id == active_trip.id).order_by(LogbookEntry.entry_date.desc()).all()

    from services.track import compute_entry_legs
    trip_leg_map = compute_entry_legs(db, active_trip.id)
    entry_legs = {e.id: trip_leg_map.get(e.id) for e in entries if not e.is_superseded}

    return templates.TemplateResponse("logbook.html", {
        "request": request,
        "entries": entries,
        "entry_legs": entry_legs,
        "active_trip": active_trip
    })

@router.get("/daily", response_class=HTMLResponse)
async def daily_logbook_view(request: Request, date: Optional[str] = None, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Parse selected date or use today
    if date:
        try:
            selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    # Calculate prev/next dates
    from datetime import timedelta
    prev_date = (selected_date - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (selected_date + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Get entries for this day
    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = datetime.combine(selected_date, datetime.max.time())
    
    entries = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.watch_leader)
    ).filter(
        LogbookEntry.trip_id == active_trip.id,
        LogbookEntry.entry_date >= start_datetime,
        LogbookEntry.entry_date <= end_datetime
    ).order_by(LogbookEntry.entry_date.asc()).all()

    # Compute haversine leg distance per entry. Use the trip-wide leg map so the
    # first leg of the day is measured from the previous day's last positioned
    # entry (matching the trip Track view).
    from services.track import compute_entry_legs
    trip_leg_map = compute_entry_legs(db, active_trip.id)
    entry_legs = {e.id: trip_leg_map.get(e.id) for e in entries if not e.is_superseded}
    auto_total = round(sum(v for v in entry_legs.values() if v is not None), 2) or None

    # Calculate summary stats. Auto (haversine across non-superseded entries)
    # is the canonical day total; manual `dist_day_nm` is shown alongside as a
    # secondary value when the skipper logged it. Use max() so multiple entries
    # on the same day don't double-count a manually entered total.
    manual_values = [e.dist_day_nm for e in entries if e.dist_day_nm and not e.is_superseded]
    manual_distance = max(manual_values) if manual_values else None
    summary = {
        "total_entries": len(entries),
        "total_distance": auto_total if auto_total is not None else manual_distance,
        "auto_distance": auto_total,
        "manual_distance": manual_distance,
        "total_engine_hours": None,
        "route": None
    }
    
    # Calculate engine hours from entries (delta for the day)
    engine_hours = []
    for entry in entries:
        if entry.eng_hours_total is not None:
            engine_hours.append(entry.eng_hours_total)
    if len(engine_hours) >= 2:
        # Calculate delta: last reading - first reading
        summary["total_engine_hours"] = max(engine_hours) - min(engine_hours)
    else:
        # Not enough readings to calculate daily delta
        summary["total_engine_hours"] = None
    
    # Get route (first departure -> last destination)
    departures = [e.departure for e in entries if e.departure]
    destinations = [e.destination for e in entries if e.destination]
    if departures and destinations:
        summary["route"] = f"{departures[0]} → {destinations[-1]}"
    elif departures:
        summary["route"] = departures[0]
    elif destinations:
        summary["route"] = destinations[-1]
    
    # Format date for display
    selected_date_formatted = selected_date.strftime("%A, %d. %B %Y")
    # German day and month names
    day_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    month_names = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", 
                   "Juli", "August", "September", "Oktober", "November", "Dezember"]
    selected_date_formatted = f"{day_names[selected_date.weekday()]}, {selected_date.day}. {month_names[selected_date.month]} {selected_date.year}"
    
    return templates.TemplateResponse("logbook_daily.html", {
        "request": request,
        "entries": entries,
        "active_trip": active_trip,
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "selected_date_formatted": selected_date_formatted,
        "prev_date": prev_date,
        "next_date": next_date,
        "summary": summary,
        "entry_legs": entry_legs
    })

def _render_day_form(
    request: Request,
    db: Session,
    active_trip,
    *,
    header=None,
    submitted_rows=None,
    row_errors=None,
    general_errors=None,
    status_code: int = 200,
):
    """Shared renderer for the Day Logbook form. Used by GET and by POST when
    validation fails so the user keeps everything they typed and sees per-row
    errors inline."""
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.name).all()
    sea_states = [s.value for s in SeaStateEnum]
    now = datetime.utcnow()
    return templates.TemplateResponse(
        "logbook_day_form.html",
        {
            "request": request,
            "active_trip": active_trip,
            "crew_members": crew_members,
            "sea_states": sea_states,
            "default_date": now.strftime("%Y-%m-%d"),
            "default_time": now.strftime("%H:%M"),
            "header": header or {},
            "submitted_rows": submitted_rows or [],
            "row_errors": row_errors or [],
            "general_errors": general_errors or [],
        },
        status_code=status_code,
    )


@router.get("/day-new", response_class=HTMLResponse)
async def new_day_form(request: Request, db: Session = Depends(get_db)):
    """Render multi-row Day Logbook form."""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)

    return _render_day_form(request, db, active_trip)


@router.post("/day-new")
async def create_day_entries(request: Request, db: Session = Depends(get_db)):
    """Create multiple LogbookEntry rows from a single Day Logbook submission.

    Transactional: either all rows are saved or none.
    """
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)

    form = await request.form()

    row_keys = [
        "row_time", "row_maneuver_type", "row_latitude", "row_longitude",
        "row_wind_direction", "row_wind_strength", "row_sea_state",
        "row_visibility", "row_temperature", "row_sail_plan",
        "row_engine_on", "row_eng_hours_total",
        "row_event_category", "row_event_details", "row_notes",
    ]
    rows_data = {k: form.getlist(k) for k in row_keys}
    row_count = len(rows_data["row_time"])

    # Snapshot of every submitted row (raw strings) so we can re-render the form
    # with the user's data intact when validation fails.
    submitted_rows = [
        {k: ((rows_data[k][i] if i < len(rows_data[k]) else "") or "") for k in row_keys}
        for i in range(row_count)
    ]

    entry_date_str = (form.get("entry_date") or "").strip()
    header_departure_raw = (form.get("departure") or "").strip()
    header_destination_raw = (form.get("destination") or "").strip()
    header_notes_raw = (form.get("summary_notes") or "").strip()
    header = {
        "entry_date": entry_date_str,
        "departure": header_departure_raw,
        "destination": header_destination_raw,
        "summary_notes": header_notes_raw,
    }

    general_errors = []
    row_errors = [{} for _ in range(row_count)]

    base_date = None
    if not entry_date_str:
        general_errors.append(_t(request, "logbook.day_err_date_required"))
    else:
        try:
            base_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
        except ValueError:
            general_errors.append(_t(request, "logbook.day_err_date_invalid"))

    header_departure = header_departure_raw or None
    header_destination = header_destination_raw or None
    header_notes = header_notes_raw or None

    # Build entry list, collecting per-row/per-field errors instead of bailing.
    parsed_rows = []
    last_lat = None
    last_lon = None
    last_time = None

    def _row_get(key, i, cast=None):
        v = (submitted_rows[i].get(key, "") or "").strip()
        if not v:
            return None
        if cast is None:
            return v
        try:
            return cast(v)
        except (ValueError, TypeError):
            return None

    for i in range(row_count):
        row = submitted_rows[i]
        time_str = (row.get("row_time", "") or "").strip()
        if not time_str:
            # Empty row — skipped silently like before.
            continue

        # Need a valid base_date to build a datetime; skip parsing rows when the
        # date is bad but still let row-level errors collect for visibility.
        entry_dt = None
        if base_date is not None:
            try:
                hh, mm = time_str.split(":")
                entry_dt = datetime.combine(base_date, datetime.min.time()).replace(
                    hour=int(hh), minute=int(mm)
                )
            except (ValueError, IndexError):
                row_errors[i]["row_time"] = f"Ungültige Uhrzeit: '{time_str}'"

        if entry_dt is not None:
            if last_time and entry_dt < last_time:
                row_errors[i]["row_time"] = (
                    f"Zeit ({time_str}) liegt vor der vorherigen Zeile."
                )
            else:
                last_time = entry_dt

        # Latitude
        lat = None
        lat_raw = (row.get("row_latitude", "") or "").strip()
        if lat_raw:
            try:
                lat = float(lat_raw)
            except ValueError:
                row_errors[i]["row_latitude"] = f"Ungültiger Wert: '{lat_raw}'"
                lat = None
            if lat is not None and not (-90.0 <= lat <= 90.0):
                row_errors[i]["row_latitude"] = (
                    f"Latitude {lat} liegt außerhalb des gültigen Bereichs (-90..90)."
                )
                lat = None

        # Longitude
        lon = None
        lon_raw = (row.get("row_longitude", "") or "").strip()
        if lon_raw:
            try:
                lon = float(lon_raw)
            except ValueError:
                row_errors[i]["row_longitude"] = f"Ungültiger Wert: '{lon_raw}'"
                lon = None
            if lon is not None and not (-180.0 <= lon <= 180.0):
                row_errors[i]["row_longitude"] = (
                    f"Longitude {lon} liegt außerhalb des gültigen Bereichs (-180..180)."
                )
                lon = None

        # Carry-forward GPS position if not provided
        if lat is None:
            lat = last_lat
        else:
            last_lat = lat
        if lon is None:
            lon = last_lon
        else:
            last_lon = lon

        engine_on_raw = _row_get("row_engine_on", i)
        engine_on_val = None
        if engine_on_raw is not None:
            engine_on_val = engine_on_raw.lower() in ("true", "1", "yes", "on")

        sea_state_raw = _row_get("row_sea_state", i)
        sea_state_val = None
        if sea_state_raw:
            try:
                sea_state_val = SeaStateEnum(sea_state_raw)
            except ValueError:
                row_errors[i]["row_sea_state"] = f"Ungültiger Seegang '{sea_state_raw}'."

        parsed_rows.append({
            "row_index": i,
            "entry_dt": entry_dt,
            "maneuver_type": _row_get("row_maneuver_type", i) or "full",
            "latitude": lat,
            "longitude": lon,
            "wind_direction": _row_get("row_wind_direction", i),
            "wind_strength": normalize_wind(_row_get("row_wind_strength", i)),
            "sea_state": sea_state_val,
            "visibility": normalize_visibility(_row_get("row_visibility", i)),
            "temperature": _row_get("row_temperature", i, float),
            "sail_plan": normalize_sail_plan(_row_get("row_sail_plan", i)),
            "engine_on": engine_on_val,
            "eng_hours_total": _row_get("row_eng_hours_total", i, float),
            "event_category": normalize_event_category(_row_get("row_event_category", i)) if _row_get("row_event_category", i) else None,
            "event_details": _row_get("row_event_details", i),
            "notes": _row_get("row_notes", i),
        })

    has_row_errors = any(bool(re_) for re_ in row_errors)

    # Need at least one non-empty row to save; only flag this when there are no
    # other validation errors (otherwise users see a confusing extra message).
    if not parsed_rows and not has_row_errors and not general_errors:
        general_errors.append(_t(request, "logbook.day_err_row_required"))

    if general_errors or has_row_errors:
        return _render_day_form(
            request,
            db,
            active_trip,
            header=header,
            submitted_rows=submitted_rows,
            row_errors=row_errors,
            general_errors=general_errors,
            status_code=400,
        )

    # All validations passed — drop synthetic helper key before persisting.
    for r in parsed_rows:
        r.pop("row_index", None)

    created_ids = []
    try:
        for idx, r in enumerate(parsed_rows):
            is_first = idx == 0
            is_last = idx == len(parsed_rows) - 1
            entry = build_logbook_entry(
                trip_id=active_trip.id,
                entry_dt=r["entry_dt"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                wind_direction=r["wind_direction"],
                wind_strength=r["wind_strength"],
                sea_state=r["sea_state"],
                visibility=r["visibility"],
                temperature=r["temperature"],
                sail_plan=r["sail_plan"],
                engine_on=r["engine_on"],
                eng_hours_total=r["eng_hours_total"],
                event_category=r["event_category"],
                event_details=r["event_details"],
                notes=(header_notes if is_first and not r["notes"] else r["notes"]),
                departure=(header_departure if is_first else None),
                destination=(header_destination if is_last else None),
                maneuver_type=r["maneuver_type"],
            )
            db.add(entry)
            db.flush()
            created_ids.append(entry.id)
        db.commit()
    except Exception as e:
        db.rollback()
        return _render_day_form(
            request,
            db,
            active_trip,
            header=header,
            submitted_rows=submitted_rows,
            row_errors=row_errors,
            general_errors=[f"Fehler beim Speichern: {str(e)}"],
            status_code=500,
        )

    # Optional multi-photo upload attached to the first created entry
    photo_files = (await request.form()).getlist("day_photos")
    valid_photos = [f for f in photo_files if hasattr(f, "filename") and f.filename]
    photo_summary = None
    if valid_photos and created_ids:
        first_entry_id = created_ids[0]
        saved, failed = await _save_photos_for_entry(db, valid_photos, first_entry_id, request, active_trip.id)
        if failed:
            photo_summary = (
                _t(request, "logbook.photo_msg_partial")
                .replace("{n}", str(len(saved)))
                .replace("{total}", str(len(valid_photos)))
                + " " + ", ".join(failed)
            )
        else:
            photo_summary = _t(request, "logbook.photo_msg_added").replace("{n}", str(len(saved)))

    msg = _t(request, "logbook.day_msg_saved").replace("{n}", str(len(created_ids)))
    if photo_summary:
        msg += " " + photo_summary
    request.session["success"] = msg

    # Audit log per entry
    for eid in created_ids:
        AuditService.log(
            db=db,
            request=request,
            trip_id=active_trip.id,
            action="create",
            entity_type="logbook_entry",
            entity_id=eid,
            details=f"Created via day-logbook batch ({len(created_ids)} entries) for {entry_date_str}"
        )

    return RedirectResponse(url=f"/logbook/daily?date={entry_date_str}", status_code=303)


@router.get("/new", response_class=HTMLResponse)
async def new_entry_form(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.name).all()
    sea_states = [s.value for s in SeaStateEnum]

    sail_profile = None
    account_id = request.session.get("account_id")
    if account_id:
        bp = get_boat_profile_for_account(db, account_id)
        if bp:
            sail_profile = bp.sail_profile
    
    now = datetime.utcnow()
    return templates.TemplateResponse("logbook_form.html", {
        "request": request,
        "crew_members": crew_members,
        "sea_states": sea_states,
        "active_trip": active_trip,
        "entry": None,
        "sail_profile": sail_profile,
        "default_date": now.strftime("%Y-%m-%d"),
        "default_time": now.strftime("%H:%M"),
    })

@router.post("/new")
async def create_entry(
    request: Request,
    entry_date: str = Form(...),
    entry_time: str = Form("12:00"),
    latitude: Optional[float] = Depends(optional_float),
    longitude: Optional[float] = Depends(optional_float),
    wind_direction: Optional[str] = Form(None),
    wind_strength: Optional[str] = Form(None),
    sea_state: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
    temperature: Optional[float] = Depends(optional_float),
    sail_plan: Optional[str] = Form(None),
    engine_hours: Optional[float] = Depends(optional_float),
    departure: Optional[str] = Form(None),
    destination: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    safety_checks: Optional[str] = Form(None),
    crew_on_watch_ids: List[int] = Form([]),
    watch_leader_id: Optional[int] = Depends(optional_int),
    clientTempId: Optional[str] = Form(None),
    # Phase A: Navigation fields
    cog_deg: Optional[int] = Depends(optional_int),
    sog_kn: Optional[float] = Depends(optional_float),
    log_kn: Optional[float] = Depends(optional_float),
    dist_day_nm: Optional[float] = Depends(optional_float),
    # Phase A: Weather fields
    pressure_hpa: Optional[int] = Depends(optional_int),
    pressure_trend: Optional[str] = Form(None),
    weather_source: Optional[str] = Form(None),
    # Phase A: Engine fields
    engine_on: Optional[bool] = Depends(optional_bool),
    engine_on_time: Optional[str] = Form(None),
    engine_off_time: Optional[str] = Form(None),
    eng_hours_total: Optional[float] = Depends(optional_float),
    fuel_level_l: Optional[float] = Depends(optional_float),
    # Phase A: Sails fields (in-mast furling)
    main_furl_pct: Optional[int] = Depends(optional_int),
    headsail: Optional[str] = Form(None),
    sail_action: Optional[str] = Form(None),
    # Sail Change structured fields
    main_reef_level: Optional[int] = Depends(optional_int),
    headsail_type: Optional[str] = Form(None),
    headsail_furl_percent: Optional[int] = Depends(optional_int),
    extra_sail: Optional[str] = Form(None),
    # Phase A: Events fields
    event_category: Optional[str] = Form(None),
    event_details: Optional[str] = Form(None),
    # Phase B: Quick Entry
    maneuver_type: Optional[str] = Form("full"),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
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
        
        # Parse engine timestamps
        engine_on_dt = datetime.fromisoformat(engine_on_time) if engine_on_time else None
        engine_off_dt = datetime.fromisoformat(engine_off_time) if engine_off_time else None

        # watch_leader_id is client-supplied and must belong to this trip's crew
        valid_member_ids = {
            row[0] for row in db.query(CrewMember.id).filter(CrewMember.trip_id == active_trip.id).all()
        }
        if watch_leader_id not in valid_member_ids:
            watch_leader_id = None

        entry = LogbookEntry(
            trip_id=active_trip.id,
            client_temp_id=clientTempId,
            watch_leader_id=watch_leader_id,
            entry_date=entry_datetime,
            entry_date_utc=entry_datetime_utc,
            latitude=latitude,
            longitude=longitude,
            wind_direction=wind_direction,
            wind_strength=normalize_wind(wind_strength),
            sea_state=sea_state_enum,
            visibility=normalize_visibility(visibility),
            temperature=temperature,
            sail_plan=normalize_sail_plan(sail_plan),
            engine_hours=engine_hours,
            departure=departure,
            destination=destination,
            notes=notes,
            safety_checks_completed=safety_checks,
            # Phase A: Navigation
            cog_deg=cog_deg,
            sog_kn=sog_kn,
            log_kn=log_kn,
            dist_day_nm=dist_day_nm,
            # Phase A: Weather
            pressure_hpa=pressure_hpa,
            pressure_trend=pressure_trend,
            weather_source=weather_source,
            # Phase A: Engine
            engine_on=engine_on,
            engine_on_time=engine_on_dt,
            engine_off_time=engine_off_dt,
            eng_hours_total=eng_hours_total,
            fuel_level_l=fuel_level_l,
            # Phase A: Sails (in-mast furling)
            main_furl_pct=main_furl_pct,
            headsail=headsail,
            sail_action=sail_action,
            # Sail Change structured fields
            main_reef_level=main_reef_level,
            headsail_type=headsail_type if headsail_type else None,
            headsail_furl_percent=headsail_furl_percent,
            extra_sail=extra_sail if extra_sail else None,
            # Phase A: Events
            event_category=normalize_event_category(event_category) if event_category else None,
            event_details=event_details,
            # Phase B: Quick Entry
            maneuver_type=maneuver_type
        )
        db.add(entry)
        db.flush()

        # Add crew on watch (only members that actually belong to this trip —
        # crew_on_watch_ids is client-supplied and must not be trusted to
        # reference this trip's own crew).
        for crew_id in crew_on_watch_ids:
            if crew_id not in valid_member_ids:
                continue
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
    active_trip = TripService.get_selected_trip(request, db)
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
    user_role = request.session.get("role", "crew")

    # Admin can edit entries from any trip (including archived/closed).
    # Crew can only edit entries that belong to their currently selected trip.
    if user_role == "admin":
        entry = db.query(LogbookEntry).options(
            joinedload(LogbookEntry.crew_on_watch)
        ).filter(LogbookEntry.id == entry_id).first()
        if not entry:
            return RedirectResponse(url="/logbook", status_code=303)
        active_trip = db.query(Trip).filter(Trip.id == entry.trip_id).first()
    else:
        active_trip = TripService.get_selected_trip(request, db)
        if not active_trip:
            return RedirectResponse(url="/trips", status_code=303)
        entry = db.query(LogbookEntry).options(
            joinedload(LogbookEntry.crew_on_watch)
        ).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
        if not entry:
            return RedirectResponse(url="/logbook", status_code=303)

    if not active_trip:
        return RedirectResponse(url="/logbook", status_code=303)

    if not TripService.is_trip_editable(active_trip, user_role, request):
        return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)

    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.name).all()
    sea_states = [s.value for s in SeaStateEnum]

    sail_profile = None
    account_id = request.session.get("account_id")
    if account_id:
        bp = get_boat_profile_for_account(db, account_id)
        if bp:
            sail_profile = bp.sail_profile

    return templates.TemplateResponse("logbook_form.html", {
        "request": request,
        "crew_members": crew_members,
        "sea_states": sea_states,
        "active_trip": active_trip,
        "entry": entry,
        "sail_profile": sail_profile,
    })

@router.post("/{entry_id}/edit")
async def update_entry(
    request: Request,
    entry_id: int,
    entry_date: str = Form(...),
    entry_time: str = Form("12:00"),
    latitude: Optional[float] = Depends(optional_float),
    longitude: Optional[float] = Depends(optional_float),
    wind_direction: Optional[str] = Form(None),
    wind_strength: Optional[str] = Form(None),
    sea_state: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
    temperature: Optional[float] = Depends(optional_float),
    sail_plan: Optional[str] = Form(None),
    engine_hours: Optional[float] = Depends(optional_float),
    departure: Optional[str] = Form(None),
    destination: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    safety_checks: Optional[str] = Form(None),
    crew_on_watch_ids: List[int] = Form([]),
    # Phase A: Navigation fields
    cog_deg: Optional[int] = Depends(optional_int),
    sog_kn: Optional[float] = Depends(optional_float),
    log_kn: Optional[float] = Depends(optional_float),
    dist_day_nm: Optional[float] = Depends(optional_float),
    # Phase A: Weather fields
    pressure_hpa: Optional[int] = Depends(optional_int),
    pressure_trend: Optional[str] = Form(None),
    weather_source: Optional[str] = Form(None),
    # Phase A: Engine fields
    engine_on: Optional[bool] = Depends(optional_bool),
    engine_on_time: Optional[str] = Form(None),
    engine_off_time: Optional[str] = Form(None),
    eng_hours_total: Optional[float] = Depends(optional_float),
    fuel_level_l: Optional[float] = Depends(optional_float),
    # Phase A: Sails fields (in-mast furling)
    main_furl_pct: Optional[int] = Depends(optional_int),
    headsail: Optional[str] = Form(None),
    sail_action: Optional[str] = Form(None),
    # Sail Change structured fields
    main_reef_level: Optional[int] = Depends(optional_int),
    headsail_type: Optional[str] = Form(None),
    headsail_furl_percent: Optional[int] = Depends(optional_int),
    extra_sail: Optional[str] = Form(None),
    # Phase A: Events fields
    event_category: Optional[str] = Form(None),
    event_details: Optional[str] = Form(None),
    # Phase B: Quick Entry
    maneuver_type: Optional[str] = Form("full"),
    db: Session = Depends(get_db)
):
    user_role = request.session.get("role", "crew")

    # Admin can update entries from any trip (including archived/closed).
    if user_role == "admin":
        entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id).first()
        if not entry:
            return RedirectResponse(url="/logbook", status_code=303)
        active_trip = db.query(Trip).filter(Trip.id == entry.trip_id).first()
    else:
        active_trip = TripService.get_selected_trip(request, db)
        if not active_trip:
            return RedirectResponse(url="/trips", status_code=303)
        entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
        if not entry:
            return RedirectResponse(url="/logbook", status_code=303)

    if not active_trip:
        return RedirectResponse(url="/logbook", status_code=303)

    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)

    try:
        # Combine date and time
        entry_datetime = datetime.fromisoformat(f"{entry_date}T{entry_time}")
        # Update UTC datetime to match (no timezone conversion)
        entry_datetime_utc = entry_datetime
        
        # Parse sea state enum
        sea_state_enum = SeaStateEnum(sea_state) if sea_state else None
        
        # Parse engine timestamps
        engine_on_dt = datetime.fromisoformat(engine_on_time) if engine_on_time else None
        engine_off_dt = datetime.fromisoformat(engine_off_time) if engine_off_time else None
        
        # Update entry fields
        entry.entry_date = entry_datetime
        entry.entry_date_utc = entry_datetime_utc
        entry.latitude = latitude
        entry.longitude = longitude
        entry.wind_direction = wind_direction
        entry.wind_strength = normalize_wind(wind_strength)
        entry.sea_state = sea_state_enum
        entry.visibility = normalize_visibility(visibility)
        entry.temperature = temperature
        entry.sail_plan = normalize_sail_plan(sail_plan)
        entry.engine_hours = engine_hours
        entry.departure = departure
        entry.destination = destination
        entry.notes = notes
        entry.safety_checks_completed = safety_checks
        # Phase A: Navigation
        entry.cog_deg = cog_deg
        entry.sog_kn = sog_kn
        entry.log_kn = log_kn
        entry.dist_day_nm = dist_day_nm
        # Phase A: Weather
        entry.pressure_hpa = pressure_hpa
        entry.pressure_trend = pressure_trend
        entry.weather_source = weather_source
        # Phase A: Engine
        entry.engine_on = engine_on
        entry.engine_on_time = engine_on_dt
        entry.engine_off_time = engine_off_dt
        entry.eng_hours_total = eng_hours_total
        entry.fuel_level_l = fuel_level_l
        # Phase A: Sails (in-mast furling)
        entry.main_furl_pct = main_furl_pct
        entry.headsail = headsail
        entry.sail_action = sail_action
        # Sail Change structured fields
        entry.main_reef_level = main_reef_level
        entry.headsail_type = headsail_type if headsail_type else None
        entry.headsail_furl_percent = headsail_furl_percent
        entry.extra_sail = extra_sail if extra_sail else None
        # Phase A: Events
        entry.event_category = normalize_event_category(event_category) if event_category else None
        entry.event_details = event_details
        entry.updated_at = datetime.utcnow()
        
        # Update crew on watch (only members that actually belong to this trip —
        # crew_on_watch_ids is client-supplied and must not be trusted to
        # reference this trip's own crew).
        valid_member_ids = {
            row[0] for row in db.query(CrewMember.id).filter(CrewMember.trip_id == active_trip.id).all()
        }
        db.query(CrewOnWatch).filter(CrewOnWatch.entry_id == entry_id).delete()
        for crew_id in crew_on_watch_ids:
            if crew_id not in valid_member_ids:
                continue
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
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Check if trip is editable by current user
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)
    
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

@router.post("/{entry_id}/addendum")
async def create_addendum(
    request: Request,
    entry_id: int,
    change_note: str = Form(...),
    db: Session = Depends(get_db)
):
    """Create an addendum to an existing logbook entry (append-only compliance)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips/", status_code=303)
    
    # Check permissions
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)
    
    # Get the parent entry
    parent_entry = db.query(LogbookEntry).filter(
        LogbookEntry.id == entry_id,
        LogbookEntry.trip_id == active_trip.id
    ).first()
    
    if not parent_entry:
        return RedirectResponse(url="/logbook", status_code=303)
    
    # Validate change note is provided
    if not change_note or change_note.strip() == "":
        request.session["error"] = "Änderungsnotiz ist erforderlich für einen Nachtrag."
        return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)
    
    try:
        # Mark parent as superseded
        parent_entry.is_superseded = True
        
        # Create a copy of the parent entry with the same data but as a new entry
        # Users will later be able to modify this in the frontend form
        addendum_entry = LogbookEntry(
            trip_id=active_trip.id,
            parent_id=parent_entry.id,
            change_note=change_note,
            # Copy all fields from parent
            entry_date=parent_entry.entry_date,
            entry_date_utc=parent_entry.entry_date_utc,
            latitude=parent_entry.latitude,
            longitude=parent_entry.longitude,
            wind_direction=parent_entry.wind_direction,
            wind_strength=normalize_wind(parent_entry.wind_strength),
            sea_state=parent_entry.sea_state,
            visibility=normalize_visibility(parent_entry.visibility),
            temperature=parent_entry.temperature,
            sail_plan=normalize_sail_plan(parent_entry.sail_plan),
            engine_hours=parent_entry.engine_hours,
            departure=parent_entry.departure,
            destination=parent_entry.destination,
            notes=parent_entry.notes,
            safety_checks_completed=parent_entry.safety_checks_completed,
            cog_deg=parent_entry.cog_deg,
            sog_kn=parent_entry.sog_kn,
            log_kn=parent_entry.log_kn,
            dist_day_nm=parent_entry.dist_day_nm,
            pressure_hpa=parent_entry.pressure_hpa,
            pressure_trend=parent_entry.pressure_trend,
            weather_source=parent_entry.weather_source,
            engine_on=parent_entry.engine_on,
            engine_on_time=parent_entry.engine_on_time,
            engine_off_time=parent_entry.engine_off_time,
            eng_hours_total=parent_entry.eng_hours_total,
            fuel_level_l=parent_entry.fuel_level_l,
            main_furl_pct=parent_entry.main_furl_pct,
            headsail=parent_entry.headsail,
            sail_action=parent_entry.sail_action,
            main_reef_level=parent_entry.main_reef_level,
            headsail_type=parent_entry.headsail_type,
            headsail_furl_percent=parent_entry.headsail_furl_percent,
            extra_sail=parent_entry.extra_sail,
            event_category=normalize_event_category(parent_entry.event_category) if parent_entry.event_category else None,
            event_details=parent_entry.event_details
        )
        db.add(addendum_entry)
        db.flush()
        
        # Copy crew on watch
        for crew_watch in parent_entry.crew_on_watch:
            new_crew_watch = CrewOnWatch(entry_id=addendum_entry.id, member_id=crew_watch.member_id)
            db.add(new_crew_watch)
        
        db.commit()
        
        # Audit log
        AuditService.log(
            db=db,
            request=request,
            trip_id=active_trip.id,
            action="addendum",
            entity_type="logbook_entry",
            entity_id=addendum_entry.id,
            details=f"Created addendum for entry {entry_id}: {change_note}"
        )
        
        request.session["success"] = f"Nachtrag erfolgreich erstellt"
        return RedirectResponse(url=f"/logbook/{addendum_entry.id}/edit", status_code=303)
        
    except Exception as e:
        db.rollback()
        request.session["error"] = f"Fehler beim Erstellen des Nachtrags: {str(e)}"
        return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)

async def _save_photos_for_entry(db: Session, files: list, entry_id: int, request: Request, trip_id: int, caption: Optional[str] = None):
    """Save a batch of photos with per-file success/failure handling.

    Valid files are committed; invalid ones are skipped and reported.
    Returns (saved_filenames, failed_descriptions).
    """
    saved = []
    failed = []
    saved_paths = []
    saved_records = []
    for f in files:
        try:
            if f.content_type not in ALLOWED_CONTENT_TYPES:
                failed.append(f"{f.filename} (Format)")
                continue
            content = await f.read()
            if len(content) > MAX_FILE_SIZE:
                failed.append(f"{f.filename} (>10MB)")
                continue
            ext = ".jpg" if "jpeg" in (f.content_type or "") else ".png"
            filename = str(uuid.uuid4()) + ext
            filepath = Path("uploads") / filename
            filepath.write_bytes(content)
            saved_paths.append(filepath)
            rec = LogbookPhoto(
                entry_id=entry_id,
                stored_filename=filename,
                original_name=f.filename or "unknown",
                caption=caption,
                content_type=f.content_type,
                size_bytes=len(content),
            )
            db.add(rec)
            db.flush()
            saved_records.append(rec)
            saved.append(f.filename)
        except Exception as e:
            failed.append(f"{getattr(f, 'filename', '?')} ({type(e).__name__})")
    try:
        db.commit()
    except Exception:
        db.rollback()
        for p in saved_paths:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        raise
    for rec in saved_records:
        AuditService.log(
            db=db,
            request=request,
            trip_id=trip_id,
            action="upload",
            entity_type="logbook_photo",
            entity_id=rec.id,
            details=f"Uploaded photo to logbook entry {entry_id} ({len(saved_records)} saved, {len(failed)} skipped)"
        )
    return saved, failed


@router.post("/{entry_id}/photos/upload")
async def upload_photo(
    request: Request,
    entry_id: int,
    photo: List[UploadFile] = File(...),
    caption: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload one or more photos. Per-file results surfaced via session message."""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)

    entry = db.query(LogbookEntry).filter(LogbookEntry.id == entry_id, LogbookEntry.trip_id == active_trip.id).first()
    if not entry:
        return RedirectResponse(url="/logbook", status_code=303)

    files = [f for f in (photo or []) if f and f.filename]
    if not files:
        return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)
    if len(files) > MAX_PHOTOS_PER_UPLOAD:
        request.session["error"] = _t(request, "logbook.photo_too_many").replace("{max}", str(MAX_PHOTOS_PER_UPLOAD))
        return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)

    saved, failed = await _save_photos_for_entry(db, files, entry_id, request, active_trip.id, caption)
    if saved and not failed:
        request.session["success"] = _t(request, "logbook.photo_msg_added").replace("{n}", str(len(saved)))
    elif saved and failed:
        request.session["success"] = (
            _t(request, "logbook.photo_msg_partial")
            .replace("{n}", str(len(saved)))
            .replace("{total}", str(len(files)))
            + " " + ", ".join(failed)
        )
    elif failed and not saved:
        request.session["error"] = _t(request, "logbook.photo_msg_none") + " " + ", ".join(failed)

    return RedirectResponse(url=f"/logbook/{entry_id}", status_code=303)

@router.post("/photos/{photo_id}/delete")
async def delete_photo(request: Request, photo_id: int, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Check if trip is editable by current user
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/logbook", status_code=303)
    
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
    active_trip = TripService.get_selected_trip(request, db)
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

@router.get("/export/pdf/entry/{entry_id}")
async def export_single_entry_pdf(request: Request, entry_id: int, db: Session = Depends(get_db)):
    """Export single logbook entry as official German/European standard PDF"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        raise HTTPException(status_code=403, detail="No active trip")
    
    entry = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.crew_on_watch).joinedload(CrewOnWatch.member)
    ).filter(
        LogbookEntry.id == entry_id,
        LogbookEntry.trip_id == active_trip.id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    vessel_info = {
        'name': active_trip.name or 'Unbekannt',
        'home_port': getattr(active_trip, 'home_port', '-'),
        'call_sign': getattr(active_trip, 'call_sign', '-'),
        'imo_mmsi': getattr(active_trip, 'imo_mmsi', '-')
    }
    
    # Get crew roster (exclude departed crew)
    crew_members = db.query(CrewMember).filter(
        CrewMember.trip_id == active_trip.id,
        CrewMember.departed_at.is_(None)
    ).order_by(CrewMember.code).all()
    
    crew_list = [{'code': member.code, 'name': member.name} for member in crew_members]
    
    # Get skipper info (with fallback for trips created before skipper fields were added)
    skipper_info = {
        'name': getattr(active_trip, 'skipper_name', None) or '-',
        'code': getattr(active_trip, 'skipper_code', None) or '-'
    }
    
    pdf_buffer = io.BytesIO()
    
    try:
        render_logbook_pdf(
            entries=[entry],
            vessel=vessel_info,
            scope='single_entry',
            outfile=pdf_buffer,
            meta={
                'title': f'Logbuch-Eintrag {entry.entry_date.strftime("%Y-%m-%d %H:%M")}',
                'creator': 'CrewLog Bordkasse'
            },
            entry_id=entry.id,
            trip_name=active_trip.name,
            crew_list=crew_list,
            skipper=skipper_info
        )
        
        pdf_buffer.seek(0)
        
        filename = f"logbuch_eintrag_{entry.entry_date.strftime('%Y%m%d_%H%M')}.pdf"
        
        AuditService.log(
            db=db,
            request=request,
            trip_id=active_trip.id,
            action="export_pdf",
            entity_type="logbook_entry",
            entity_id=entry.id,
            details=f"PDF export: {filename}"
        )
        
        return Response(
            content=pdf_buffer.read(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@router.get("/export/pdf/daily")
async def export_daily_pdf(
    request: Request,
    export_date: str,
    db: Session = Depends(get_db)
):
    """Export all logbook entries for a specific date as PDF"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        raise HTTPException(status_code=403, detail="No active trip")
    
    try:
        target_date = datetime.strptime(export_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    entries = db.query(LogbookEntry).options(
        joinedload(LogbookEntry.crew_on_watch).joinedload(CrewOnWatch.member)
    ).filter(
        LogbookEntry.trip_id == active_trip.id,
        LogbookEntry.entry_date >= datetime.combine(target_date, datetime.min.time()),
        LogbookEntry.entry_date < datetime.combine(target_date, datetime.max.time())
    ).order_by(LogbookEntry.entry_date.asc()).all()
    
    if not entries:
        raise HTTPException(status_code=404, detail=f"No logbook entries found for {export_date}")
    
    vessel_info = {
        'name': active_trip.name or 'Unbekannt',
        'home_port': getattr(active_trip, 'home_port', '-'),
        'call_sign': getattr(active_trip, 'call_sign', '-'),
        'imo_mmsi': getattr(active_trip, 'imo_mmsi', '-')
    }
    
    # Get crew roster (exclude departed crew)
    crew_members = db.query(CrewMember).filter(
        CrewMember.trip_id == active_trip.id,
        CrewMember.departed_at.is_(None)
    ).order_by(CrewMember.code).all()
    
    crew_list = [{'code': member.code, 'name': member.name} for member in crew_members]
    
    # Get skipper info (with fallback for trips created before skipper fields were added)
    skipper_info = {
        'name': getattr(active_trip, 'skipper_name', None) or '-',
        'code': getattr(active_trip, 'skipper_code', None) or '-'
    }
    
    total_dist = sum(e.dist_day_nm for e in entries if e.dist_day_nm is not None)
    total_eng_hours = sum(e.eng_hours_total for e in entries if e.eng_hours_total is not None)
    
    summary = {
        'total_nm': total_dist if total_dist > 0 else None,
        'total_engine_hours': total_eng_hours if total_eng_hours > 0 else None,
        'entry_count': len(entries)
    }
    
    pdf_buffer = io.BytesIO()
    
    try:
        render_logbook_pdf(
            entries=entries,
            vessel=vessel_info,
            scope='daily',
            outfile=pdf_buffer,
            meta={
                'title': f'Tageslogbuch {target_date.strftime("%d.%m.%Y")}',
                'creator': 'CrewLog Bordkasse'
            },
            summary=summary,
            trip_name=active_trip.name,
            crew_list=crew_list,
            skipper=skipper_info
        )
        
        pdf_buffer.seek(0)
        
        filename = f"tageslogbuch_{target_date.strftime('%Y%m%d')}.pdf"
        
        AuditService.log(
            db=db,
            request=request,
            trip_id=active_trip.id,
            action="export_pdf",
            entity_type="logbook_daily",
            entity_id=None,
            details=f"Daily PDF export: {filename} ({len(entries)} entries)"
        )
        
        return Response(
            content=pdf_buffer.read(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
