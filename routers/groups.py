from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from template_helpers import create_templates
from sqlalchemy.orm import Session
from db import get_db
from models import CrewMember, CrewGroup
from services.group import GroupService
from services.trip import TripService
from typing import Optional

router = APIRouter(tags=["groups"])
templates = create_templates()

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
    
    user_role = request.session.get("role", "crew")
    is_admin_or_trip_admin = TripService.is_admin_or_trip_admin(request, active_trip.id)
    return templates.TemplateResponse("groups.html", {
        "request": request,
        "active_trip": active_trip,
        "groups": group_data,
        "crew_members": crew_members,
        "ungrouped_members": ungrouped_members,
        "is_editable": TripService.is_trip_editable(active_trip, user_role, request),
        "is_admin": is_admin_or_trip_admin
    })

@router.post("/groups/create")
async def create_group(
    request: Request,
    db: Session = Depends(get_db),
    group_name: str = Form(...),
    representative_id: int = Form(...),
    member_ids: Optional[str] = Form(None)
):
    """Create a new settlement group (admin or trip admin)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can create groups
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        return RedirectResponse(url="/groups", status_code=303)
    
    # Check if trip is editable
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
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
    """Update group membership (admin or trip admin)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can update groups
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        return RedirectResponse(url="/groups", status_code=303)
    
    # Check if trip is editable
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        return RedirectResponse(url="/groups?error=trip_closed", status_code=303)

    # Ensure the group actually belongs to the caller's active trip, not
    # some other trip's group_id (trip-admin access is per-trip, not global)
    group = GroupService.get_group_by_id(db, group_id)
    if not group or group.trip_id != active_trip.id:
        return RedirectResponse(url="/groups?error=not_found", status_code=303)

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
    """Change group representative (admin or trip admin)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can change representatives
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        return RedirectResponse(url="/groups", status_code=303)
    
    # Check if trip is editable
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        return RedirectResponse(url="/groups?error=trip_closed", status_code=303)

    # Ensure the group actually belongs to the caller's active trip, not
    # some other trip's group_id (trip-admin access is per-trip, not global)
    group = GroupService.get_group_by_id(db, group_id)
    if not group or group.trip_id != active_trip.id:
        return RedirectResponse(url="/groups?error=not_found", status_code=303)

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
    """Delete a settlement group (admin or trip admin)"""
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Only admin or trip admin can delete groups
    if not TripService.is_admin_or_trip_admin(request, active_trip.id):
        return RedirectResponse(url="/groups", status_code=303)
    
    # Check if trip is editable
    user_role = request.session.get("role", "crew")
    if not TripService.is_trip_editable(active_trip, user_role, request):
        return RedirectResponse(url="/groups?error=trip_closed", status_code=303)

    # Ensure the group actually belongs to the caller's active trip, not
    # some other trip's group_id (trip-admin access is per-trip, not global)
    group = GroupService.get_group_by_id(db, group_id)
    if not group or group.trip_id != active_trip.id:
        return RedirectResponse(url="/groups?error=not_found", status_code=303)

    try:
        GroupService.delete_group(db=db, group_id=group_id)
        return RedirectResponse(url="/groups?success=deleted", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/groups?error={str(e)}", status_code=303)
