from sqlalchemy.orm import Session
from models import Trip, TripStatus
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
    def is_trip_editable(trip: Trip, user_role: str, request: Optional[Request] = None) -> bool:
        """
        Check if a trip is editable by the current user.
        
        Args:
            trip: The trip to check
            user_role: User's role ("admin" or "crew")
            request: Optional Request object to check trip admin status
            
        Returns:
            True if user can edit this trip, False otherwise
        """
        # Global admin can always edit everything
        if user_role == "admin":
            return True
        
        # Trip is open - anyone can edit
        if trip.is_closed == 0:
            return True
        
        # Check if user is a trip admin for this specific trip
        if request:
            trip_admin_trip_id = request.session.get("trip_admin_trip_id")
            if trip_admin_trip_id and trip_admin_trip_id == trip.id:
                return True
        
        # Closed trip, not admin, not trip admin
        return False
