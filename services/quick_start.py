from sqlalchemy.orm import Session
from datetime import datetime, date
from models import Trip, CrewMember, LogbookEntry, UserPreferences, Currency, TripStatus

class TripQuickStartService:
    @staticmethod
    def create_quick_start_trip(db: Session, user_id: int) -> Trip:
        """
        Create a new trip with user's default preferences and auto-generate first logbook entry.
        
        Args:
            db: Database session
            user_id: ID of the user creating the trip
            
        Returns:
            Created Trip object with skipper added as crew and first logbook entry created
        """
        prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        
        if not prefs:
            prefs = UserPreferences(
                user_id=user_id,
                skipper_name="Skipper",
                skipper_code="SK",
                boat_name="Boat",
                home_port="Home Port",
                home_lat=None,
                home_lon=None,
                default_currency=Currency.EUR
            )
        
        today = date.today()
        trip_name = f"{prefs.boat_name} - {today.strftime('%d.%m.%Y')}"
        
        trip = Trip(
            name=trip_name,
            start_date=today,
            end_date=None,
            status=TripStatus.active,
            is_closed=0
        )
        db.add(trip)
        db.flush()
        
        skipper_code = prefs.skipper_code if prefs.skipper_code is not None else "SK"
        skipper_name = prefs.skipper_name if prefs.skipper_name is not None else "Skipper"
        
        skipper = CrewMember(
            trip_id=trip.id,
            code=skipper_code,
            name=skipper_name,
            is_trip_admin=1
        )
        db.add(skipper)
        db.flush()
        
        now_utc = datetime.utcnow()
        
        departure_entry = LogbookEntry(
            trip_id=trip.id,
            date_time_utc=now_utc,
            maneuver_type="departure",
            latitude=prefs.home_lat,
            longitude=prefs.home_lon,
            departure_port=prefs.home_port,
            motor_on_time_utc=now_utc,
            created_at=now_utc,
            updated_at=now_utc
        )
        db.add(departure_entry)
        
        db.commit()
        db.refresh(trip)
        
        return trip
