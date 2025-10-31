from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from models import User, CrewMember, Trip
from typing import Optional

class TripAuthService:
    """Service for trip-specific authentication and authorization"""
    
    @staticmethod
    def get_user_role_for_trip(user_id: int, trip_id: int, db: Session) -> Optional[str]:
        """
        Get user's role for a specific trip.
        Returns 'admin' if user is trip admin, 'crew' if regular crew, None if not in trip.
        """
        crew_member = db.query(CrewMember).filter(
            CrewMember.user_id == user_id,
            CrewMember.trip_id == trip_id
        ).first()
        
        if not crew_member:
            return None
        
        return "admin" if crew_member.is_trip_admin else "crew"
    
    @staticmethod
    def is_user_in_trip(user_id: int, trip_id: int, db: Session) -> bool:
        """Check if user is a member of the specified trip"""
        crew_member = db.query(CrewMember).filter(
            CrewMember.user_id == user_id,
            CrewMember.trip_id == trip_id
        ).first()
        return crew_member is not None
    
    @staticmethod
    def is_trip_admin(user_id: int, trip_id: int, db: Session) -> bool:
        """Check if user is an admin for the specified trip"""
        crew_member = db.query(CrewMember).filter(
            CrewMember.user_id == user_id,
            CrewMember.trip_id == trip_id,
            CrewMember.is_trip_admin.is_(True)
        ).first()
        return crew_member is not None
    
    @staticmethod
    def is_global_admin(user_id: int, db: Session) -> bool:
        """
        Check if user is an admin on ANY trip.
        Used for global features like creating new trips and managing templates.
        """
        admin_crew = db.query(CrewMember).filter(
            CrewMember.user_id == user_id,
            CrewMember.is_trip_admin.is_(True)
        ).first()
        return admin_crew is not None
    
    @staticmethod
    def require_trip_access(request: Request, required_role: Optional[str] = None):
        """
        Verify user has access to current trip with optional role requirement.
        
        Args:
            request: FastAPI request with session
            required_role: Optional role requirement ('admin' or 'crew')
        
        Raises:
            HTTPException: If user not logged in or lacks required permissions
        """
        if "user_id" not in request.session:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if "trip_id" not in request.session:
            raise HTTPException(status_code=400, detail="No trip selected")
        
        trip_role = request.session.get("trip_role")
        if trip_role is None:
            raise HTTPException(status_code=403, detail="Not a member of this trip")
        
        if required_role == "admin" and trip_role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
    
    @staticmethod
    def require_global_admin(request: Request, db: Session):
        """
        Verify user is admin on at least one trip (checked fresh from database).
        Used for global features like trip creation and template management.
        
        SECURITY: Always checks database in real-time to prevent stale session cache
        from allowing revoked admins to retain privileges.
        
        Raises:
            HTTPException: If user not logged in or not an admin
        """
        if "user_id" not in request.session:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_id = request.session["user_id"]
        if not TripAuthService.is_global_admin(user_id, db):
            raise HTTPException(status_code=403, detail="Admin access required")
    
    @staticmethod
    def update_session_for_trip(request: Request, user_id: int, trip_id: int, db: Session):
        """
        Update session with trip-specific role information.
        Call this when user selects a trip or logs in.
        """
        trip_role = TripAuthService.get_user_role_for_trip(user_id, trip_id, db)
        is_global_admin = TripAuthService.is_global_admin(user_id, db)
        
        request.session["trip_id"] = trip_id
        request.session["trip_role"] = trip_role
        request.session["is_global_admin"] = is_global_admin
    
    @staticmethod
    def get_user_trips(user_id: int, db: Session) -> list[dict]:
        """
        Get all trips the user is a member of, with their role in each.
        Returns list of dicts with trip info and role.
        """
        crew_memberships = db.query(CrewMember, Trip).join(
            Trip, CrewMember.trip_id == Trip.id
        ).filter(
            CrewMember.user_id == user_id
        ).all()
        
        result = []
        for crew_member, trip in crew_memberships:
            result.append({
                "trip_id": trip.id,
                "trip_name": trip.name,
                "role": "admin" if crew_member.is_trip_admin else "crew",
                "trip": trip
            })
        
        return result
