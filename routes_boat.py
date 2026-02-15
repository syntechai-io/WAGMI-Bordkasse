from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from template_helpers import create_templates
from db import get_db
from auth_saas import get_current_saas_user, get_active_account_id
from models import SaaSUser
from services.boat import get_or_create_boat_profile
from typing import Optional
from datetime import datetime

router = APIRouter(tags=["boat"])
templates = create_templates()


@router.get("/admin/boat", response_class=HTMLResponse)
async def boat_setup_page(request: Request, db: Session = Depends(get_db)):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)

    user = get_current_saas_user(request, db)
    bp = get_or_create_boat_profile(db, account_id)
    sp = bp.sail_profile

    return templates.TemplateResponse("admin_boat.html", {
        "request": request,
        "boat_profile": bp,
        "sail_profile": sp,
        "is_owner": user.is_owner,
    })


@router.post("/admin/boat", response_class=HTMLResponse)
async def save_boat_setup(
    request: Request,
    boat_name: str = Form(...),
    home_port_name: Optional[str] = Form(None),
    home_port_lat: Optional[str] = Form(None),
    home_port_lon: Optional[str] = Form(None),
    boat_make: Optional[str] = Form(None),
    boat_model: Optional[str] = Form(None),
    boat_year: Optional[str] = Form(None),
    main_type: str = Form("FURLING"),
    headsail_genoa: Optional[str] = Form(None),
    headsail_jib: Optional[str] = Form(None),
    headsail_furling: Optional[str] = Form(None),
    has_code0: Optional[str] = Form(None),
    has_gennaker: Optional[str] = Form(None),
    has_spinnaker: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)

    user = get_current_saas_user(request, db)
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Only the account owner can edit boat settings")

    bp = get_or_create_boat_profile(db, account_id)

    if not boat_name or not boat_name.strip():
        raise HTTPException(status_code=400, detail="Boat name is required")

    bp.boat_name = boat_name.strip()
    bp.boat_name_is_default = False
    bp.home_port_name = home_port_name.strip() if home_port_name and home_port_name.strip() else None
    bp.boat_make = boat_make.strip() if boat_make and boat_make.strip() else None
    bp.boat_model = boat_model.strip() if boat_model and boat_model.strip() else None
    bp.updated_at = datetime.utcnow()

    try:
        bp.home_port_lat = float(home_port_lat) if home_port_lat and home_port_lat.strip() else None
    except (ValueError, TypeError):
        bp.home_port_lat = None

    try:
        bp.home_port_lon = float(home_port_lon) if home_port_lon and home_port_lon.strip() else None
    except (ValueError, TypeError):
        bp.home_port_lon = None

    try:
        bp.boat_year = int(boat_year) if boat_year and boat_year.strip() else None
    except (ValueError, TypeError):
        bp.boat_year = None

    sp = bp.sail_profile
    if sp:
        sp.main_type = main_type if main_type in ("FURLING", "SLAB_REEFING") else "FURLING"
        sp.headsail_genoa = headsail_genoa == "on"
        sp.headsail_jib = headsail_jib == "on"
        sp.headsail_furling = headsail_furling == "on"
        sp.has_code0 = has_code0 == "on"
        sp.has_gennaker = has_gennaker == "on"
        sp.has_spinnaker = has_spinnaker == "on"
        sp.updated_at = datetime.utcnow()

    db.commit()

    request.session["success"] = "boat_saved"
    return RedirectResponse(url="/admin/boat", status_code=303)


@router.post("/admin/boat/fetch-gps")
async def fetch_gps(request: Request, db: Session = Depends(get_db)):
    account_id = get_active_account_id(request)
    if not account_id:
        return JSONResponse({"ok": False, "error": "No account"}, status_code=401)

    user = get_current_saas_user(request, db)
    if not user.is_owner:
        return JSONResponse({"ok": False, "error": "Owner only"}, status_code=403)

    body = await request.json()
    lat = body.get("lat")
    lon = body.get("lon")

    if lat is None or lon is None:
        return JSONResponse({"ok": False, "error": "Missing coordinates"}, status_code=400)

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return JSONResponse({"ok": False, "error": "Invalid coordinates"}, status_code=400)

    bp = get_or_create_boat_profile(db, account_id)
    bp.home_port_lat = lat
    bp.home_port_lon = lon
    bp.updated_at = datetime.utcnow()
    db.commit()

    return JSONResponse({"ok": True, "lat": lat, "lon": lon})
