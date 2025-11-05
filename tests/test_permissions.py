"""
Test permissions and authorization.
"""
import pytest
from datetime import datetime, date
from models import Trip, CrewMember, Expense, PaidFromEnum, SplitModeEnum

class TestTripAdmin:
    """Test trip admin permissions."""
    
    def test_trip_admin_flag(self, db_session, test_trip):
        """Test that crew members can be designated as trip admins."""
        # Create trip admin
        admin = CrewMember(
            trip_id=test_trip.id,
            name="Admin User",
            code="AD",
            is_trip_admin=True
        )
        db_session.add(admin)
        
        # Create regular crew
        crew = CrewMember(
            trip_id=test_trip.id,
            name="Regular Crew",
            code="RC",
            is_trip_admin=False
        )
        db_session.add(crew)
        db_session.commit()
        
        assert admin.is_trip_admin == True
        assert crew.is_trip_admin == False
    
    def test_max_two_trip_admins(self, db_session, test_trip):
        """Test that a trip can have up to 2 trip admins."""
        # Create 2 trip admins
        admin1 = CrewMember(
            trip_id=test_trip.id,
            name="Admin 1",
            code="A1",
            is_trip_admin=True
        )
        admin2 = CrewMember(
            trip_id=test_trip.id,
            name="Admin 2",
            code="A2",
            is_trip_admin=True
        )
        db_session.add_all([admin1, admin2])
        db_session.commit()
        
        # Count trip admins
        admin_count = db_session.query(CrewMember).filter(
            CrewMember.trip_id == test_trip.id,
            CrewMember.is_trip_admin == True
        ).count()
        
        assert admin_count == 2


class TestClosedTripProtection:
    """Test that closed trips are protected from modification."""
    
    def test_closed_trip_flag(self, db_session, test_trip):
        """Test that trips can be marked as closed."""
        test_trip.is_closed = True
        db_session.commit()
        
        assert test_trip.is_closed == True
    
    def test_closed_trip_read_only_for_crew(self, db_session):
        """Test that closed trips should be read-only for regular crew."""
        # Create a closed trip
        closed_trip = Trip(
            name="Closed Trip",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 10),
            is_closed=True
        )
        db_session.add(closed_trip)
        db_session.commit()
        
        # The is_closed flag should be True
        assert closed_trip.is_closed == True
        
        # Note: Actual permission checks are done in route handlers via TripService.is_trip_editable()
        # This test just verifies the database state


class TestDataScoping:
    """Test that data is properly scoped to trips."""
    
    def test_crew_scoped_to_trip(self, db_session):
        """Test that crew members belong to specific trips."""
        # Create two trips
        trip1 = Trip(name="Trip 1", start_date=date(2025, 11, 1), end_date=date(2025, 11, 10), is_closed=False)
        trip2 = Trip(name="Trip 2", start_date=date(2025, 12, 1), end_date=date(2025, 12, 10), is_closed=False)
        db_session.add_all([trip1, trip2])
        db_session.commit()
        
        # Add crew to each trip
        crew1 = CrewMember(trip_id=trip1.id, name="Alice", code="A", is_trip_admin=False)
        crew2 = CrewMember(trip_id=trip2.id, name="Bob", code="B", is_trip_admin=False)
        db_session.add_all([crew1, crew2])
        db_session.commit()
        
        # Verify crew are scoped correctly
        trip1_crew = db_session.query(CrewMember).filter(CrewMember.trip_id == trip1.id).all()
        trip2_crew = db_session.query(CrewMember).filter(CrewMember.trip_id == trip2.id).all()
        
        assert len(trip1_crew) == 1
        assert trip1_crew[0].name == "Alice"
        assert len(trip2_crew) == 1
        assert trip2_crew[0].name == "Bob"
    
    def test_expenses_scoped_to_trip(self, db_session):
        """Test that expenses belong to specific trips."""
        # Create two trips with crew
        trip1 = Trip(name="Trip 1", start_date=date(2025, 11, 1), end_date=date(2025, 11, 10), is_closed=False)
        trip2 = Trip(name="Trip 2", start_date=date(2025, 12, 1), end_date=date(2025, 12, 10), is_closed=False)
        db_session.add_all([trip1, trip2])
        db_session.commit()
        
        crew1 = CrewMember(trip_id=trip1.id, name="Alice", code="A", is_trip_admin=False)
        crew2 = CrewMember(trip_id=trip2.id, name="Bob", code="B", is_trip_admin=False)
        db_session.add_all([crew1, crew2])
        db_session.commit()
        
        # Add expenses to each trip
        expense1 = Expense(
            trip_id=trip1.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Diesel",
            amount_eur=100.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=crew1.id
        )
        expense2 = Expense(
            trip_id=trip2.id,
            date=date(2025, 12, 3),
            occurred_at=datetime(2025, 12, 3, 12, 0, 0),
            category="Proviant",
            amount_eur=200.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=crew2.id
        )
        db_session.add_all([expense1, expense2])
        db_session.commit()
        
        # Verify expenses are scoped correctly
        trip1_expenses = db_session.query(Expense).filter(Expense.trip_id == trip1.id).all()
        trip2_expenses = db_session.query(Expense).filter(Expense.trip_id == trip2.id).all()
        
        assert len(trip1_expenses) == 1
        assert trip1_expenses[0].category == "Diesel"
        assert len(trip2_expenses) == 1
        assert trip2_expenses[0].category == "Proviant"
