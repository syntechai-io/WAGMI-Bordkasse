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
    def is_trip_editable(trip: Trip, user_role: str) -> bool:
        """Check if a trip is editable by the current user"""
        # Admin can always edit
        if user_role == "admin":
            return True
        
        # Crew can only edit if trip is not closed
        return trip.is_closed == 0
