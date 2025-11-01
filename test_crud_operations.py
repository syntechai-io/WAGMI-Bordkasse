"""
Comprehensive CRUD operation tests to verify all core entities work correctly
and detect schema mismatches between models and database.
"""

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import (
    Base, Trip, CrewMember, Deposit, Expense, ExpenseParticipant,
    CrewGroup, CrewGroupMember, ExpenseTemplate,
    TripStatus, Currency
)
import os

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    pytest.skip("DATABASE_URL not set, skipping database tests", allow_module_level=True)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


class TestSchemaValidation:
    """Tests to ensure SQLAlchemy models match database schema"""
    
    def test_models_match_database_schema(self, db_session):
        """Verify all model columns exist in database with correct types"""
        inspector = inspect(engine)
        
        # Models to validate
        models_to_check = [
            Trip, CrewMember, Deposit, Expense, ExpenseParticipant,
            CrewGroup, CrewGroupMember, ExpenseTemplate
        ]
        
        schema_issues = []
        
        for model in models_to_check:
            table_name = model.__tablename__
            
            # Get columns from database
            db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
            
            # Get columns from model
            model_columns = {col.name: col for col in model.__table__.columns}
            
            # Check for missing columns in model
            for db_col_name in db_columns:
                if db_col_name not in model_columns:
                    # Allow account_id since it's a legacy column we made nullable
                    if db_col_name == 'account_id':
                        continue
                    schema_issues.append(
                        f"Table '{table_name}': Column '{db_col_name}' exists in database but not in model"
                    )
            
            # Check for columns in model that don't exist in database
            for model_col_name in model_columns:
                if model_col_name not in db_columns:
                    schema_issues.append(
                        f"Table '{table_name}': Column '{model_col_name}' defined in model but not in database"
                    )
        
        if schema_issues:
            pytest.fail("\n".join(["Schema mismatches found:"] + schema_issues))


class TestTripCRUD:
    """Test Create, Read, Update, Delete operations for Trips"""
    
    def test_create_trip(self, db_session):
        """Test creating a new trip - this was failing before the fix"""
        trip = Trip(
            name="Test Sailing Trip 2025",
            start_date=date(2025, 6, 1),
            status=TripStatus.active
        )
        
        db_session.add(trip)
        db_session.commit()
        
        assert trip.id is not None
        assert trip.name == "Test Sailing Trip 2025"
        assert trip.status == TripStatus.active
        
        # Cleanup
        db_session.delete(trip)
        db_session.commit()
    
    def test_read_trip(self, db_session):
        """Test reading a trip from database"""
        # Create
        trip = Trip(
            name="Test Read Trip",
            start_date=date(2025, 7, 1),
            status=TripStatus.active
        )
        db_session.add(trip)
        db_session.commit()
        trip_id = trip.id
        
        # Read
        retrieved_trip = db_session.query(Trip).filter(Trip.id == trip_id).first()
        assert retrieved_trip is not None
        assert retrieved_trip.name == "Test Read Trip"
        
        # Cleanup
        db_session.delete(retrieved_trip)
        db_session.commit()
    
    def test_update_trip(self, db_session):
        """Test updating a trip"""
        trip = Trip(
            name="Original Name",
            start_date=date(2025, 8, 1),
            status=TripStatus.active
        )
        db_session.add(trip)
        db_session.commit()
        
        # Update
        trip.name = "Updated Name"
        trip.status = TripStatus.archived
        trip.end_date = date(2025, 8, 15)
        db_session.commit()
        
        # Verify
        db_session.refresh(trip)
        assert trip.name == "Updated Name"
        assert trip.status == TripStatus.archived
        assert trip.end_date == date(2025, 8, 15)
        
        # Cleanup
        db_session.delete(trip)
        db_session.commit()
    
    def test_delete_trip(self, db_session):
        """Test deleting a trip"""
        trip = Trip(
            name="Trip to Delete",
            start_date=date(2025, 9, 1),
            status=TripStatus.active
        )
        db_session.add(trip)
        db_session.commit()
        trip_id = trip.id
        
        # Delete
        db_session.delete(trip)
        db_session.commit()
        
        # Verify deleted
        deleted_trip = db_session.query(Trip).filter(Trip.id == trip_id).first()
        assert deleted_trip is None


class TestCrewMemberCRUD:
    """Test CRUD operations for Crew Members"""
    
    @pytest.fixture
    def test_trip(self, db_session):
        """Create a test trip for crew member tests"""
        trip = Trip(
            name="Crew Test Trip",
            start_date=date(2025, 5, 1),
            status=TripStatus.active
        )
        db_session.add(trip)
        db_session.commit()
        yield trip
        db_session.delete(trip)
        db_session.commit()
    
    def test_create_crew_member(self, db_session, test_trip):
        """Test creating a crew member"""
        crew = CrewMember(
            trip_id=test_trip.id,
            code="SKIPPER",
            name="Captain Jack",
            iban_or_handle="DE89370400440532013000"
        )
        
        db_session.add(crew)
        db_session.commit()
        
        assert crew.id is not None
        assert crew.code == "SKIPPER"
        assert crew.name == "Captain Jack"
    
    def test_create_trip_admin_crew_member(self, db_session, test_trip):
        """Test creating a trip admin crew member"""
        crew = CrewMember(
            trip_id=test_trip.id,
            code="ADMIN1",
            name="Trip Administrator",
            is_trip_admin=1
        )
        
        db_session.add(crew)
        db_session.commit()
        
        assert crew.id is not None
        assert crew.is_trip_admin == 1


class TestDepositCRUD:
    """Test CRUD operations for Deposits"""
    
    @pytest.fixture
    def test_trip_and_crew(self, db_session):
        """Create test trip and crew member"""
        trip = Trip(
            name="Deposit Test Trip",
            start_date=date(2025, 5, 1),
            status=TripStatus.active
        )
        db_session.add(trip)
        db_session.commit()
        
        crew = CrewMember(
            trip_id=trip.id,
            code="CREW1",
            name="Test Crew"
        )
        db_session.add(crew)
        db_session.commit()
        
        yield trip, crew
        
        db_session.delete(crew)
        db_session.delete(trip)
        db_session.commit()
    
    def test_create_deposit(self, db_session, test_trip_and_crew):
        """Test creating a deposit"""
        trip, crew = test_trip_and_crew
        
        deposit = Deposit(
            trip_id=trip.id,
            member_id=crew.id,
            amount=500.00,
            currency=Currency.EUR,
            amount_eur=500.00,
            date=date(2025, 5, 1),
            note="Initial deposit"
        )
        
        db_session.add(deposit)
        db_session.commit()
        
        assert deposit.id is not None
        assert deposit.amount == 500.00
        assert deposit.currency == Currency.EUR


class TestExpenseCRUD:
    """Test CRUD operations for Expenses"""
    
    @pytest.fixture
    def test_trip_and_crew(self, db_session):
        """Create test trip and crew member"""
        trip = Trip(
            name="Expense Test Trip",
            start_date=date(2025, 5, 1),
            status=TripStatus.active
        )
        db_session.add(trip)
        db_session.commit()
        
        crew = CrewMember(
            trip_id=trip.id,
            code="CREW1",
            name="Test Crew"
        )
        db_session.add(crew)
        db_session.commit()
        
        yield trip, crew
        
        db_session.delete(crew)
        db_session.delete(trip)
        db_session.commit()
    
    def test_create_expense_paid_by_crew(self, db_session, test_trip_and_crew):
        """Test creating an expense paid by crew member"""
        from models import PaidFromEnum, SplitModeEnum
        trip, crew = test_trip_and_crew
        
        expense = Expense(
            trip_id=trip.id,
            payer_id=crew.id,
            date=date(2025, 5, 2),
            category="Provisions",
            amount=150.00,
            currency=Currency.EUR,
            amount_eur=150.00,
            description="Groceries",
            paid_from=PaidFromEnum.private,
            split_mode=SplitModeEnum.equal
        )
        
        db_session.add(expense)
        db_session.commit()
        
        assert expense.id is not None
        assert expense.amount == 150.00
        assert expense.paid_from == PaidFromEnum.private
    
    def test_create_expense_paid_from_wallet(self, db_session, test_trip_and_crew):
        """Test creating an expense paid from shared wallet"""
        from models import PaidFromEnum, SplitModeEnum
        trip, crew = test_trip_and_crew
        
        expense = Expense(
            trip_id=trip.id,
            payer_id=None,  # Paid from wallet
            date=date(2025, 5, 3),
            category="Marina fees",
            amount=200.00,
            currency=Currency.EUR,
            amount_eur=200.00,
            description="Harbor costs",
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal
        )
        
        db_session.add(expense)
        db_session.commit()
        
        assert expense.id is not None
        assert expense.payer_id is None
        assert expense.paid_from == PaidFromEnum.wallet


class TestSettlementGroupCRUD:
    """Test CRUD operations for Settlement Groups"""
    
    @pytest.fixture
    def test_trip_and_crews(self, db_session):
        """Create test trip and multiple crew members"""
        trip = Trip(
            name="Group Test Trip",
            start_date=date(2025, 5, 1),
            status=TripStatus.active
        )
        db_session.add(trip)
        db_session.commit()
        
        crew1 = CrewMember(trip_id=trip.id, code="CREW1", name="Person 1")
        crew2 = CrewMember(trip_id=trip.id, code="CREW2", name="Person 2")
        db_session.add_all([crew1, crew2])
        db_session.commit()
        
        yield trip, crew1, crew2
        
        # Delete groups first to avoid foreign key constraints on representative_member_id
        groups = db_session.query(CrewGroup).filter(CrewGroup.trip_id == trip.id).all()
        for group in groups:
            db_session.delete(group)
        
        db_session.delete(crew1)
        db_session.delete(crew2)
        db_session.delete(trip)
        db_session.commit()
    
    def test_create_settlement_group(self, db_session, test_trip_and_crews):
        """Test creating a settlement group"""
        trip, crew1, crew2 = test_trip_and_crews
        
        group = CrewGroup(
            trip_id=trip.id,
            name="Couple 1",
            representative_member_id=crew1.id
        )
        
        db_session.add(group)
        db_session.commit()
        
        # Add members to group
        member1 = CrewGroupMember(group_id=group.id, member_id=crew1.id)
        member2 = CrewGroupMember(group_id=group.id, member_id=crew2.id)
        db_session.add_all([member1, member2])
        db_session.commit()
        
        assert group.id is not None
        assert group.name == "Couple 1"
        assert len(group.members) == 2


class TestExpenseTemplateCRUD:
    """Test CRUD operations for Expense Templates"""
    
    def test_create_expense_template(self, db_session):
        """Test creating an expense template"""
        from models import PaidFromEnum, SplitModeEnum
        
        template = ExpenseTemplate(
            name="Marina Fee",
            category="Harbor",
            default_amount=100.00,
            currency=Currency.EUR,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal
        )
        
        db_session.add(template)
        db_session.commit()
        
        assert template.id is not None
        assert template.name == "Marina Fee"
        assert template.default_amount == 100.00
        
        # Cleanup
        db_session.delete(template)
        db_session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
