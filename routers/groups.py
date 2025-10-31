from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import CrewMember, CrewGroup
from services.group import GroupService
from services.trip import TripService
from typing import Optional

router = APIRouter(tags=["groups"])
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

def require_admin(request: Request):
    """Require trip admin role for group management (deprecated - use trip_role check instead)"""
    trip_role = request.session.get("trip_role", "crew")
    if trip_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

@router.get("/groups", response_class=HTMLResponse)
async def show_groups(request: Request, db: Session = Depends(get_db)):
    """Show all settlement groups for the active trip (visible to all users)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Get all groups for this trip
    groups = GroupService.get_groups_for_trip(db, active_trip.id)
    
    # Get all crew members for this trip
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).all()
    
    # Build group data with member details
    group_data = []
    for group in groups:
        member_names = [m.member.name for m in group.members]
        group_data.append({
            "id": group.id,
            "name": group.name,
            "representative": group.representative.name,
            "representative_id": group.representative_member_id,
            "member_count": len(group.members),
            "member_names": member_names,
            "member_ids": [m.member_id for m in group.members]
        })
    
    # Find crew members not in any group
    grouped_member_ids = set()
    for group in groups:
        grouped_member_ids.update([m.member_id for m in group.members])
    
    ungrouped_members = [m for m in crew_members if m.id not in grouped_member_ids]
    
    trip_role = request.session.get("trip_role", "crew")
    return templates.TemplateResponse("groups.html", {
        "request": request,
        "active_trip": active_trip,
        "groups": group_data,
        "crew_members": crew_members,
        "ungrouped_members": ungrouped_members,
        "is_editable": TripService.can_edit_trip(request, db, active_trip),
        "is_admin": trip_role == "admin",
        "has_admin_permission": TripService.has_admin_permission(request, db, active_trip)
    })

@router.post("/groups/create")
async def create_group(
    request: Request,
    db: Session = Depends(get_db),
    group_name: str = Form(...),
    representative_id: int = Form(...),
    member_ids: Optional[str] = Form(None)
):
    """Create a new settlement group (admin only)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    if not TripService.has_admin_permission(request, db, active_trip):
        return RedirectResponse(url="/", status_code=303)
    
    if not TripService.can_edit_trip(request, db, active_trip):
        return RedirectResponse(url="/groups?error=trip_closed", status_code=303)
    
    try:
        # Parse member IDs from comma-separated string
        if member_ids:
            member_id_list = [int(id.strip()) for id in member_ids.split(",") if id.strip()]
        else:
            member_id_list = []
        
        # Ensure representative is in the list
        if representative_id not in member_id_list:
            member_id_list.append(representative_id)
        
        # Create the group
        GroupService.create_group(
            db=db,
            trip_id=active_trip.id,
            name=group_name,
            representative_member_id=representative_id,
            member_ids=member_id_list
        )
        
        return RedirectResponse(url="/groups?success=created", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/groups?error={str(e)}", status_code=303)

@router.post("/groups/{group_id}/update")
async def update_group(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    member_ids: Optional[str] = Form(None)
):
    """Update group membership (admin only)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    if not TripService.has_admin_permission(request, db, active_trip):
        return RedirectResponse(url="/", status_code=303)
    
    if not TripService.can_edit_trip(request, db, active_trip):
        return RedirectResponse(url="/groups?error=trip_closed", status_code=303)
    
    try:
        # Parse member IDs
        if member_ids:
            member_id_list = [int(id.strip()) for id in member_ids.split(",") if id.strip()]
        else:
            member_id_list = []
        
        # Update the group
        GroupService.update_group_members(
            db=db,
            group_id=group_id,
            member_ids=member_id_list
        )
        
        return RedirectResponse(url="/groups?success=updated", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/groups?error={str(e)}", status_code=303)

@router.post("/groups/{group_id}/change-representative")
async def change_representative(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    new_representative_id: int = Form(...)
):
    """Change group representative (admin only)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    if not TripService.has_admin_permission(request, db, active_trip):
        return RedirectResponse(url="/", status_code=303)
    
    if not TripService.can_edit_trip(request, db, active_trip):
        return RedirectResponse(url="/groups?error=trip_closed", status_code=303)
    
    try:
        GroupService.change_representative(
            db=db,
            group_id=group_id,
            new_representative_id=new_representative_id
        )
        
        return RedirectResponse(url="/groups?success=representative_changed", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/groups?error={str(e)}", status_code=303)

@router.post("/groups/{group_id}/delete")
async def delete_group(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db)
):
    """Delete a settlement group (admin only)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    if not TripService.has_admin_permission(request, db, active_trip):
        return RedirectResponse(url="/", status_code=303)
    
    if not TripService.can_edit_trip(request, db, active_trip):
        return RedirectResponse(url="/groups?error=trip_closed", status_code=303)
    
    try:
        GroupService.delete_group(db=db, group_id=group_id)
        return RedirectResponse(url="/groups?success=deleted", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/groups?error={str(e)}", status_code=303)
