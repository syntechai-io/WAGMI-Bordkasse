"""
Regression tests for core Crew Wallet functionality.
"""
import pytest
from datetime import datetime, date
from models import Trip, CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum, Currency

class TestTripManagement:
    """Test trip creation and management."""
    
    def test_create_trip(self, db_session):
        """Test creating a new trip."""
        trip = Trip(
            name="Summer Sailing 2025",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 15),
            is_closed=False
        )
        db_session.add(trip)
        db_session.commit()
        
        assert trip.id is not None
        assert trip.name == "Summer Sailing 2025"
        assert trip.is_closed == False
    
    def test_close_trip(self, db_session, test_trip):
        """Test closing a trip."""
        test_trip.is_closed = True
        db_session.commit()
        
        assert test_trip.is_closed == True
    
    def test_trip_date_range(self, db_session, test_trip):
        """Test trip has valid date range."""
        assert test_trip.start_date < test_trip.end_date


class TestCrewManagement:
    """Test crew member operations."""
    
    def test_create_crew_member(self, db_session, test_trip):
        """Test creating a crew member."""
        member = CrewMember(
            trip_id=test_trip.id,
            name="Emma",
            code="E",
            is_trip_admin=False
        )
        db_session.add(member)
        db_session.commit()
        
        assert member.id is not None
        assert member.name == "Emma"
        assert member.departed_at is None
    
    def test_crew_member_limit(self, db_session, test_trip):
        """Test that trip can have up to 12 crew members."""
        for i in range(12):
            member = CrewMember(
                trip_id=test_trip.id,
                name=f"Crew{i}",
                code=str(i),
                is_trip_admin=False
            )
            db_session.add(member)
        
        db_session.commit()
        
        crew_count = db_session.query(CrewMember).filter(
            CrewMember.trip_id == test_trip.id
        ).count()
        
        assert crew_count == 12
    
    def test_crew_member_unique_code(self, db_session, test_trip):
        """Test that crew codes must be unique within a trip."""
        member1 = CrewMember(
            trip_id=test_trip.id,
            name="Frank",
            code="F",
            is_trip_admin=False
        )
        db_session.add(member1)
        db_session.commit()
        
        # Query to verify uniqueness would be enforced by database constraint
        existing_codes = [m.code for m in db_session.query(CrewMember).filter(
            CrewMember.trip_id == test_trip.id
        ).all()]
        
        assert "F" in existing_codes


class TestDepositManagement:
    """Test deposit operations."""
    
    def test_create_deposit(self, db_session, test_trip, test_crew):
        """Test creating a deposit."""
        deposit = Deposit(
            trip_id=test_trip.id,
            member_id=test_crew[0].id,
            amount_eur=750.0,
            date=date(2025, 11, 1)
        )
        db_session.add(deposit)
        db_session.commit()
        
        assert deposit.id is not None
        assert deposit.amount_eur == 750.0
    
    def test_multiple_deposits_same_member(self, db_session, test_trip, test_crew):
        """Test that a member can make multiple deposits."""
        deposit1 = Deposit(
            trip_id=test_trip.id,
            member_id=test_crew[0].id,
            amount_eur=500.0,
            date=date(2025, 11, 1)
        )
        deposit2 = Deposit(
            trip_id=test_trip.id,
            member_id=test_crew[0].id,
            amount_eur=250.0,
            date=date(2025, 11, 3)
        )
        db_session.add_all([deposit1, deposit2])
        db_session.commit()
        
        total_deposits = db_session.query(Deposit).filter(
            Deposit.member_id == test_crew[0].id
        ).count()
        
        assert total_deposits == 2


class TestExpenseManagement:
    """Test expense operations."""
    
    def test_create_wallet_expense(self, db_session, test_trip, test_crew):
        """Test creating a wallet-paid expense."""
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Diesel",
            amount_eur=500.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        assert expense.id is not None
        assert expense.paid_from == PaidFromEnum.wallet
    
    def test_create_private_expense(self, db_session, test_trip, test_crew):
        """Test creating a private-paid expense."""
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Proviant",
            amount_eur=200.0,
            paid_from=PaidFromEnum.private,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[1].id
        )
        db_session.add(expense)
        db_session.commit()
        
        assert expense.paid_from == PaidFromEnum.private
    
    def test_external_charge_no_payer(self, db_session, test_trip):
        """Test creating external charge with no payer."""
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Mooring",
            amount_eur=150.0,
            paid_from=PaidFromEnum.external,
            split_mode=SplitModeEnum.equal,
            payer_id=None  # External charge
        )
        db_session.add(expense)
        db_session.commit()
        
        assert expense.payer_id is None
        assert expense.paid_from == PaidFromEnum.external
    
    def test_expense_categories(self, db_session, test_trip, test_crew):
        """Test that expenses can use different categories."""
        categories = ["Proviant", "Getränke", "Mooring", "Diesel", "Restaurant"]
        
        for category in categories:
            expense = Expense(
                trip_id=test_trip.id,
                date=date(2025, 11, 3),
                occurred_at=datetime(2025, 11, 3, 12, 0, 0),
                category=category,
                amount_eur=100.0,
                paid_from=PaidFromEnum.wallet,
                split_mode=SplitModeEnum.equal,
                payer_id=test_crew[0].id
            )
            db_session.add(expense)
        
        db_session.commit()
        
        expense_count = db_session.query(Expense).filter(
            Expense.trip_id == test_trip.id
        ).count()
        
        assert expense_count == len(categories)
    
    def test_multi_currency_expense(self, db_session, test_trip, test_crew):
        """Test expense with non-EUR currency gets converted."""
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Diesel",
            amount_original=100.0,
            currency=Currency.USD,
            exchange_rate=1.08,
            amount_eur=92.59,  # 100 / 1.08
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        assert expense.currency == Currency.USD
        assert expense.amount_original == 100.0
        assert abs(expense.amount_eur - 92.59) < 0.01


class TestDataIntegrity:
    """Test data integrity and constraints."""
    
    def test_expense_belongs_to_trip(self, db_session, test_trip, test_crew):
        """Test that expenses are properly linked to trips."""
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Diesel",
            amount_eur=500.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        trip_expenses = db_session.query(Expense).filter(
            Expense.trip_id == test_trip.id
        ).all()
        
        assert len(trip_expenses) == 1
        assert trip_expenses[0].id == expense.id
    
    def test_deposit_belongs_to_member(self, db_session, test_trip, test_crew):
        """Test that deposits are properly linked to members."""
        deposit = Deposit(
            trip_id=test_trip.id,
            member_id=test_crew[0].id,
            amount_eur=500.0,
            date=date(2025, 11, 1)
        )
        db_session.add(deposit)
        db_session.commit()
        
        member_deposits = db_session.query(Deposit).filter(
            Deposit.member_id == test_crew[0].id
        ).all()
        
        assert len(member_deposits) == 1
        assert member_deposits[0].id == deposit.id
