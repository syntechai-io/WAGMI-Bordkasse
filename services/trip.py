from sqlalchemy.orm import Session
from models import Trip, TripStatus
from typing import Optional

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
