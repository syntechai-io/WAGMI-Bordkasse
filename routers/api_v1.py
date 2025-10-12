from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from db import get_db
from models import User, Trip, TripStatus
from services.trip import TripService
from jwt_auth import create_token_pair, verify_token, get_current_user, get_admin_user

router = APIRouter(prefix="/api/v1", tags=["API v1"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not user.check_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    tokens = create_token_pair(str(user.username), user.role.value)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user={"username": user.username, "role": user.role.value}
    )

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshRequest):
    try:
        payload = verify_token(refresh_request.refresh_token, "refresh")
        username = payload.get("sub")
        role = payload.get("role")
        
        if not username or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        tokens = create_token_pair(username, role)
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            user={"username": username, "role": role}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/auth/verify")
async def verify_auth(current_user: dict = Depends(get_current_user)):
    return {
        "authenticated": True,
        "user": current_user
    }

# Pydantic schemas for Trips
class TripCreate(BaseModel):
    name: str
    start_date: date
    end_date: Optional[date] = None

class TripResponse(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: Optional[date]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Trip endpoints
@router.get("/trips", response_model=List[TripResponse])
async def list_trips(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all trips, optionally filtered by status"""
    query = db.query(Trip)
    if status:
        query = query.filter(Trip.status == status)
    trips = query.order_by(Trip.created_at.desc()).all()
    return trips

@router.post("/trips", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_data: TripCreate,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new trip (admin only). Archives the current active trip if exists."""
    active_trip = TripService.get_active_trip(db)
    if active_trip:
        active_trip.status = TripStatus.archived
    
    new_trip = Trip(
        name=trip_data.name,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        status=TripStatus.active
    )
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
    return new_trip

@router.get("/trips/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific trip by ID"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.put("/trips/{trip_id}/archive", response_model=TripResponse)
async def archive_trip(
    trip_id: int,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Archive a trip (admin only)"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.status = TripStatus.archived
    db.commit()
    db.refresh(trip)
    return trip

@router.get("/trips/active/current", response_model=Optional[TripResponse])
async def get_active_trip(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the currently active trip"""
    active_trip = TripService.get_active_trip(db)
    return active_trip
