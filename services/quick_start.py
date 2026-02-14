from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional
from models import Trip, CrewMember, LogbookEntry, UserPreferences, Currency, TripStatus, TripMember, TripRole

class TripQuickStartService:
    @staticmethod
    def create_quick_start_trip(db: Session, user_id: int, account_id: int = 1, saas_user_id: Optional[int] = None) -> Trip:
        """
        Create a new trip with user's default preferences and auto-generate first logbook entry.
        
        Args:
            db: Database session
            user_id: ID of the user creating the trip
            account_id: Account (tenant) ID to scope the trip
            saas_user_id: SaaS user ID to add as trip member
            
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
            is_closed=0,
            skipper_name=prefs.skipper_name or "Skipper",
            skipper_code=prefs.skipper_code or "SK",
            home_port=prefs.home_port or "Home Port",
            account_id=account_id
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

        if saas_user_id:
            db.add(TripMember(
                trip_id=trip.id,
                user_id=saas_user_id,
                role=TripRole.skipper,
                created_at=datetime.utcnow(),
            ))
        
        now_utc = datetime.utcnow()
        
        departure_entry = LogbookEntry(
            trip_id=trip.id,
            entry_date=now_utc,
            entry_date_utc=now_utc,
            maneuver_type="departure",
            latitude=prefs.home_lat,
            longitude=prefs.home_lon,
            departure=prefs.home_port,
            engine_on_time=now_utc,
            created_at=now_utc,
            updated_at=now_utc
        )
        db.add(departure_entry)
        
        db.commit()
        db.refresh(trip)
        
        return trip
