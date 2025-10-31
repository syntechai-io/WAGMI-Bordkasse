from sqlalchemy.orm import Session
from models import Trip, TripStatus, CrewMember
from typing import Optional
from fastapi import Request

class TripService:
    @staticmethod
    def get_active_trip(db: Session) -> Optional[Trip]:
        """Get the currently active trip"""
        return db.query(Trip).filter(Trip.status == TripStatus.active).first()
    
    @staticmethod
    def get_active_trip_id(db: Session) -> Optional[int]:
        """Get the ID of the currently active trip"""
        trip = TripService.get_active_trip(db)
        return trip.id if trip else None
    
    @staticmethod
    def get_selected_trip(request: Request, db: Session) -> Optional[Trip]:
        """Get the trip selected by user (from session) or fall back to active trip"""
        selected_trip_id = request.session.get("selected_trip_id")
        
        if selected_trip_id:
            trip = db.query(Trip).filter(Trip.id == selected_trip_id).first()
            if trip:
                return trip
        
        # Fall back to active trip
        return TripService.get_active_trip(db)
    
    @staticmethod
    def set_selected_trip(request: Request, trip_id: int):
        """Set the selected trip in session"""
        request.session["selected_trip_id"] = trip_id
    
    @staticmethod
    def is_trip_admin(db: Session, trip_id: int, username: str) -> bool:
        """Check if a user is a trip admin for a specific trip"""
        # Find crew member by username (code) for this trip
        crew_member = db.query(CrewMember).filter(
            CrewMember.trip_id == trip_id,
            CrewMember.code == username
        ).first()
        
        if crew_member and crew_member.is_trip_admin:
            return True
        
        return False
    
    @staticmethod
    def is_trip_editable(trip: Trip, user_role: str, db: Session = None, username: str = None) -> bool:
        """Check if a trip is editable by the current user"""
        # Global admin can always edit
        if user_role == "admin":
            return True
        
        # Check if user is trip admin for this specific trip
        if db and username and TripService.is_trip_admin(db, trip.id, username):
            return True
        
        # Regular crew can only edit if trip is not closed
        return trip.is_closed == 0
    
    @staticmethod
    def has_admin_permission(request: Request, db: Session, trip: Trip) -> bool:
        """Check if current user has admin permissions (global admin or trip admin)"""
        user_role = request.session.get("role", "crew")
        username = request.session.get("username", "")
        
        # Global admin
        if user_role == "admin":
            return True
        
        # Trip admin for this trip
        if TripService.is_trip_admin(db, trip.id, username):
            return True
        
        return False
    
    @staticmethod
    def can_edit_trip(request: Request, db: Session, trip: Trip) -> bool:
        """Convenience method to check if current user can edit a trip"""
        user_role = request.session.get("role", "crew")
        username = request.session.get("username", "")
        return TripService.is_trip_editable(trip, user_role, db, username)
