from fastapi import APIRouter, Request, Depends, Form
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import CrewMember, User, UserRole
from services.trip import TripService
from services.group import GroupService
from typing import Optional

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
    is_trip_admin: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    if not TripService.can_edit_trip(request, db, active_trip):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Password is REQUIRED for new crew members
    if not password:
        return templates.TemplateResponse("crew_form.html", {
            "request": request,
            "member": None,
            "error": "Passwort ist erforderlich. Bitte geben Sie ein Passwort ein."
        }, status_code=400)
    
    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse("crew_form.html", {
            "request": request,
            "member": None,
            "error": "Passwort muss mindestens 6 Zeichen lang sein."
        }, status_code=400)
    
    try:
        # Check if username (code) already exists
        existing_user = db.query(User).filter(User.username == code).first()
        if existing_user:
            return templates.TemplateResponse("crew_form.html", {
                "request": request,
                "member": None,
                "error": f"Der Benutzername '{code}' existiert bereits. Bitte wählen Sie einen anderen Code."
            }, status_code=400)
        
        # Create user account (always required for new crew)
        user_role = UserRole.admin if is_trip_admin == "true" else UserRole.crew
        user = User(username=code, role=user_role)
        user.set_password(password)
        db.add(user)
        db.flush()  # Get user.id before creating crew member
        
        # Create crew member
        member = CrewMember(
            trip_id=active_trip.id,
            user_id=user.id if user else None,
            code=code,
            name=name,
            iban_or_handle=iban_or_handle or None,
            is_trip_admin=is_trip_admin == "true"
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
    is_trip_admin: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    if not TripService.can_edit_trip(request, db, active_trip):
        request.session["error"] = "Dieser Törn wurde geschlossen. Nur der Admin kann Änderungen vornehmen."
        return RedirectResponse(url="/crew", status_code=303)
    
    # Validate password if provided
    if password and len(password) < 6:
        member = db.query(CrewMember).filter(
            CrewMember.id == member_id,
            CrewMember.trip_id == active_trip.id
        ).first()
        return templates.TemplateResponse("crew_form.html", {
            "request": request,
            "member": member,
            "error": "Passwort muss mindestens 6 Zeichen lang sein."
        }, status_code=400)
    
    try:
        member = db.query(CrewMember).filter(
            CrewMember.id == member_id,
            CrewMember.trip_id == active_trip.id
        ).first()
        
        # Check if username changed and conflicts
        if code != member.code:
            existing_user = db.query(User).filter(User.username == code).first()
            if existing_user and (not member.user or existing_user.id != member.user.id):
                return templates.TemplateResponse("crew_form.html", {
                    "request": request,
                    "member": member,
                    "error": f"Der Benutzername '{code}' existiert bereits. Bitte wählen Sie einen anderen Code."
                }, status_code=400)
        
        # Update or create user account
        is_admin = is_trip_admin == "true"
        if member.user:
            # Update existing user
            member.user.username = code
            member.user.role = UserRole.admin if is_admin else UserRole.crew
            if password:
                member.user.set_password(password)
        elif password:
            # Create new user if password provided
            user_role = UserRole.admin if is_admin else UserRole.crew
            user = User(username=code, role=user_role)
            user.set_password(password)
            db.add(user)
            db.flush()
            member.user_id = user.id
        
        # Update crew member
        member.code = code
        member.name = name
        member.iban_or_handle = iban_or_handle or None
        member.is_trip_admin = is_admin
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
    
    if not TripService.can_edit_trip(request, db, active_trip):
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
        # Delete associated user account if exists
        if member.user:
            user_to_delete = member.user
            db.delete(user_to_delete)
        
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
