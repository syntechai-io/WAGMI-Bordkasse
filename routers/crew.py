from fastapi import APIRouter, Request, Depends, Form
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import CrewMember
from services.trip import TripService
from services.group import GroupService

router = APIRouter(prefix="/crew", tags=["crew"])
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

@router.get("", response_class=HTMLResponse)
async def list_crew(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
    
    # Fetch group data for each member
    member_groups = {}
    for member in crew_members:
        group = GroupService.get_member_group(db, member.id)
        if group:
            member_groups[member.id] = {
                "name": group.name,
                "is_representative": group.representative_member_id == member.id
            }
    
    return templates.TemplateResponse("crew_list.html", {
        "request": request,
        "crew_members": crew_members,
        "member_groups": member_groups
    })

@router.get("/new", response_class=HTMLResponse)
async def new_crew_form(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can add crew members
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        request.session["error"] = "Nur Admins können Crew-Mitglieder hinzufügen."
        return RedirectResponse(url="/crew", status_code=303)
    
    return templates.TemplateResponse("crew_form.html", {
        "request": request,
        "member": None
    })

@router.post("/new")
async def create_crew(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    iban_or_handle: str = Form(""),
    is_trip_admin: int = Form(0),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can add crew members
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        request.session["error"] = "Nur Admins können Crew-Mitglieder hinzufügen."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Check if trip is editable by current user
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Only global admin (not trip admin) can set trip admin status
    if is_trip_admin and (user_role != "admin" or request.session.get("trip_admin_trip_id")):
        is_trip_admin = 0
    
    # Check max 2 trip admins limit
    if is_trip_admin:
        current_admins = db.query(CrewMember).filter(
            CrewMember.trip_id == active_trip.id,
            CrewMember.is_trip_admin == 1
        ).count()
        if current_admins >= 2:
            return templates.TemplateResponse("crew_form.html", {
                "request": request,
                "member": None,
                "error": "Maximal 2 Törn-Admins pro Törn erlaubt. Bitte entfernen Sie zuerst einen bestehenden Törn-Admin."
            }, status_code=400)
    
    try:
        member = CrewMember(
            trip_id=active_trip.id,
            code=code,
            name=name,
            iban_or_handle=iban_or_handle or None,
            is_trip_admin=is_trip_admin
        )
        db.add(member)
        db.commit()
        return RedirectResponse(url="/crew", status_code=303)
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse("crew_form.html", {
            "request": request,
            "member": None,
            "error": f"Der Code '{code}' existiert bereits. Bitte wählen Sie einen anderen Code."
        }, status_code=400)

@router.get("/{member_id}/edit", response_class=HTMLResponse)
async def edit_crew_form(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can edit crew members
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        request.session["error"] = "Nur Admins können Crew-Mitglieder bearbeiten."
        return RedirectResponse(url="/crew", status_code=303)
    
    member = db.query(CrewMember).filter(
        CrewMember.id == member_id,
        CrewMember.trip_id == active_trip.id
    ).first()
    return templates.TemplateResponse("crew_form.html", {
        "request": request,
        "member": member
    })

@router.post("/{member_id}/edit")
async def update_crew(
    request: Request,
    member_id: int,
    code: str = Form(...),
    name: str = Form(...),
    iban_or_handle: str = Form(""),
    is_trip_admin: int = Form(0),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can edit crew members
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        request.session["error"] = "Nur Admins können Crew-Mitglieder bearbeiten."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Check if trip is editable by current user
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/crew", status_code=303)
    
    member = db.query(CrewMember).filter(
        CrewMember.id == member_id,
        CrewMember.trip_id == active_trip.id
    ).first()
    
    # Only global admin (not trip admin) can modify trip admin status
    if user_role != "admin" or request.session.get("trip_admin_trip_id"):
        is_trip_admin = member.is_trip_admin
    
    # Check max 2 trip admins limit (if changing from non-admin to admin)
    if is_trip_admin and not member.is_trip_admin:
        current_admins = db.query(CrewMember).filter(
            CrewMember.trip_id == active_trip.id,
            CrewMember.is_trip_admin == 1,
            CrewMember.id != member_id
        ).count()
        if current_admins >= 2:
            return templates.TemplateResponse("crew_form.html", {
                "request": request,
                "member": member,
                "error": "Maximal 2 Törn-Admins pro Törn erlaubt. Bitte entfernen Sie zuerst einen bestehenden Törn-Admin."
            }, status_code=400)
    
    try:
        member.code = code
        member.name = name
        member.iban_or_handle = iban_or_handle or None
        member.is_trip_admin = is_trip_admin
        db.commit()
        return RedirectResponse(url="/crew", status_code=303)
    except IntegrityError:
        db.rollback()
        member = db.query(CrewMember).filter(
            CrewMember.id == member_id,
            CrewMember.trip_id == active_trip.id
        ).first()
        return templates.TemplateResponse("crew_form.html", {
            "request": request,
            "member": member,
            "error": f"Der Code '{code}' wird bereits verwendet. Bitte wählen Sie einen anderen Code."
        }, status_code=400)

@router.post("/{member_id}/delete")
async def delete_crew(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can delete crew members
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        request.session["error"] = "Nur Admins können Crew-Mitglieder löschen."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Check if trip is editable by current user
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/crew", status_code=303)
    
    member = db.query(CrewMember).filter(
        CrewMember.id == member_id,
        CrewMember.trip_id == active_trip.id
    ).first()
    
    if not member:
        return RedirectResponse(url="/crew", status_code=303)
    
    # Check if member can be deleted (group validation)
    can_delete, group_reason = GroupService.can_delete_member(db, member_id)
    if not can_delete:
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        # Build member_groups for template
        member_groups = {}
        for cm in crew_members:
            group = GroupService.get_member_group(db, cm.id)
            if group:
                member_groups[cm.id] = {
                    "name": group.name,
                    "is_representative": group.representative_member_id == cm.id
                }
        return templates.TemplateResponse("crew_list.html", {
            "request": request,
            "crew_members": crew_members,
            "member_groups": member_groups,
            "error": f"'{member.name}' kann nicht gelöscht werden: {group_reason}"
        }, status_code=400)
    
    has_deposits = len(member.deposits) > 0
    has_expenses = len(member.paid_expenses) > 0
    
    if has_deposits or has_expenses:
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        # Build member_groups for template
        member_groups = {}
        for cm in crew_members:
            group = GroupService.get_member_group(db, cm.id)
            if group:
                member_groups[cm.id] = {
                    "name": group.name,
                    "is_representative": group.representative_member_id == cm.id
                }
        error_msg = f"'{member.name}' kann nicht gelöscht werden, da "
        if has_deposits and has_expenses:
            error_msg += "Einzahlungen und Ausgaben existieren."
        elif has_deposits:
            error_msg += "Einzahlungen existieren."
        else:
            error_msg += "Ausgaben existieren."
        error_msg += " Bitte löschen Sie zuerst alle verknüpften Einträge."
        
        return templates.TemplateResponse("crew_list.html", {
            "request": request,
            "crew_members": crew_members,
            "member_groups": member_groups,
            "error": error_msg
        }, status_code=400)
    
    try:
        db.delete(member)
        db.commit()
        return RedirectResponse(url="/crew", status_code=303)
    except IntegrityError:
        db.rollback()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        # Build member_groups for template
        member_groups = {}
        for cm in crew_members:
            group = GroupService.get_member_group(db, cm.id)
            if group:
                member_groups[cm.id] = {
                    "name": group.name,
                    "is_representative": group.representative_member_id == cm.id
                }
        return templates.TemplateResponse("crew_list.html", {
            "request": request,
            "crew_members": crew_members,
            "member_groups": member_groups,
            "error": f"'{member.name}' kann nicht gelöscht werden. Bitte löschen Sie zuerst alle verknüpften Einträge."
        }, status_code=400)

@router.post("/{member_id}/deactivate")
async def deactivate_crew(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db),
    departed_at: str = Form(...)
):
    """Deactivate a crew member with departure timestamp"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can deactivate crew members
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        request.session["error"] = "Nur Admins können Crew-Mitglieder deaktivieren."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Check if trip is editable by current user
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/crew", status_code=303)
    
    member = db.query(CrewMember).filter(
        CrewMember.id == member_id,
        CrewMember.trip_id == active_trip.id
    ).first()
    
    if not member:
        return RedirectResponse(url="/crew", status_code=303)
    
    try:
        # Parse the datetime string (format: YYYY-MM-DDTHH:MM)
        from datetime import datetime
        departed_datetime = datetime.fromisoformat(departed_at)
        member.departed_at = departed_datetime
        db.commit()
        return RedirectResponse(url="/crew?success=deactivated", status_code=303)
    except ValueError:
        request.session["error"] = "Ungültiges Datum-/Zeitformat."
        return RedirectResponse(url="/crew", status_code=303)

@router.post("/{member_id}/reactivate")
async def reactivate_crew(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db)
):
    """Reactivate a departed crew member"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can reactivate crew members
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        request.session["error"] = "Nur Admins können Crew-Mitglieder reaktivieren."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Check if trip is editable by current user
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/crew", status_code=303)
    
    member = db.query(CrewMember).filter(
        CrewMember.id == member_id,
        CrewMember.trip_id == active_trip.id
    ).first()
    
    if not member:
        return RedirectResponse(url="/crew", status_code=303)
    
    member.departed_at = None
    db.commit()
    return RedirectResponse(url="/crew?success=reactivated", status_code=303)
