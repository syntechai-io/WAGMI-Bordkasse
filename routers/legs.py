from datetime import date

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from db import get_db
from template_helpers import create_templates
from services.trip import TripService
from services import legs as LegService

router = APIRouter(tags=["legs"])
templates = create_templates()


def _parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@router.get("/legs", response_class=HTMLResponse)
async def list_legs(request: Request, db: Session = Depends(get_db)):
    """Show all legs (Etappen) for the active trip (visible to all users)."""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    trip_legs = LegService.list_legs_for_trip(db, active_trip.id)
    user_role = request.session.get("role", "crew")

    return templates.TemplateResponse("trip_legs.html", {
        "request": request,
        "active_trip": active_trip,
        "legs": trip_legs,
        "is_editable": TripService.is_trip_editable(active_trip, user_role, request),
    })


@router.post("/legs/create")
async def create_leg(
    request: Request,
    name: str = Form(""),
    departure_port: str = Form(""),
    destination_port: str = Form(""),
    planned_start: str = Form(""),
    planned_end: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/legs", status_code=303)

    LegService.create_leg(
        db,
        trip_id=active_trip.id,
        name=name.strip(),
        departure_port=departure_port.strip(),
        destination_port=destination_port.strip(),
        planned_start=_parse_date(planned_start),
        planned_end=_parse_date(planned_end),
        notes=notes.strip(),
    )
    request.session["success"] = "Etappe angelegt."
    return RedirectResponse(url="/legs", status_code=303)


@router.post("/legs/{leg_id}/edit")
async def update_leg(
    request: Request,
    leg_id: int,
    name: str = Form(""),
    departure_port: str = Form(""),
    destination_port: str = Form(""),
    planned_start: str = Form(""),
    planned_end: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/legs", status_code=303)

    updated = LegService.update_leg(
        db,
        trip_id=active_trip.id,
        leg_id=leg_id,
        name=name.strip() or None,
        departure_port=departure_port.strip() or None,
        destination_port=destination_port.strip() or None,
        planned_start=_parse_date(planned_start),
        planned_end=_parse_date(planned_end),
        notes=notes.strip() or None,
    )
    if not updated:
        return RedirectResponse(url="/legs", status_code=303)

    request.session["success"] = "Etappe aktualisiert."
    return RedirectResponse(url="/legs", status_code=303)


@router.post("/legs/{leg_id}/delete")
async def delete_leg(request: Request, leg_id: int, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/legs", status_code=303)

    try:
        LegService.delete_leg(db, active_trip.id, leg_id)
        request.session["success"] = "Etappe gelöscht."
    except ValueError as e:
        request.session["error"] = str(e)

    return RedirectResponse(url="/legs", status_code=303)
