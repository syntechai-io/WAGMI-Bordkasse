"""
Test configuration and fixtures for Crew Wallet tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os

from db import Base, get_db
from models import Trip, CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum

# Use test database URL
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/test")

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

@pytest.fixture
def test_trip(db_session):
    """Create a test trip."""
    trip = Trip(
        name="Test Trip 2025",
        start_date=datetime(2025, 11, 1).date(),
        end_date=datetime(2025, 11, 10).date(),
        is_closed=False
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)
    return trip

@pytest.fixture
def test_crew(db_session, test_trip):
    """Create test crew members."""
    crew = []
    names = ["Alice", "Bob", "Charlie", "Diana"]
    
    for i, name in enumerate(names):
        member = CrewMember(
            trip_id=test_trip.id,
            name=name,
            code=name[0],
            is_trip_admin=False,
            departed_at=None
        )
        db_session.add(member)
        crew.append(member)
    
    db_session.commit()
    for member in crew:
        db_session.refresh(member)
    
    return crew

@pytest.fixture
def departed_crew_member(db_session, test_trip):
    """Create a crew member who has departed."""
    member = CrewMember(
        trip_id=test_trip.id,
        name="Tom",
        code="T",
        is_trip_admin=False,
        departed_at=datetime.utcnow() - timedelta(hours=1)  # Departed 1 hour ago
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)
    return member
