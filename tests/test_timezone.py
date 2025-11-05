"""
Test timezone handling and crew departure filtering.
"""
import pytest
from datetime import datetime, timedelta, date
from models import CrewMember, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum
from routers.balances import calculate_balances

class TestTimezoneConversion:
    """Test UTC timezone conversion for crew departures."""
    
    def test_utc_conversion_cet_timezone(self, db_session, test_trip):
        """Test that CET (UTC+1) departure time is correctly converted to UTC."""
        # Simulate: User in CET deactivates crew at 14:00 local time
        # CET offset is -60 minutes (negative for ahead of UTC)
        local_time_cet = datetime(2025, 11, 5, 14, 0, 0)
        timezone_offset = -60  # CET is UTC+1
        
        # Backend conversion: local + offset = UTC
        utc_time = local_time_cet + timedelta(minutes=timezone_offset)
        
        # Should be 13:00 UTC
        assert utc_time == datetime(2025, 11, 5, 13, 0, 0)
        
        # Store in database
        member = CrewMember(
            trip_id=test_trip.id,
            name="TestMember",
            code="TM",
            departed_at=utc_time
        )
        db_session.add(member)
        db_session.commit()
        
        # Verify stored correctly
        assert member.departed_at == datetime(2025, 11, 5, 13, 0, 0)
    
    def test_utc_conversion_pst_timezone(self, db_session, test_trip):
        """Test that PST (UTC-8) departure time is correctly converted to UTC."""
        # Simulate: User in PST deactivates crew at 10:00 local time
        # PST offset is +480 minutes (positive for behind UTC)
        local_time_pst = datetime(2025, 11, 5, 10, 0, 0)
        timezone_offset = 480  # PST is UTC-8
        
        # Backend conversion: local + offset = UTC
        utc_time = local_time_pst + timedelta(minutes=timezone_offset)
        
        # Should be 18:00 UTC (10:00 + 8 hours)
        assert utc_time == datetime(2025, 11, 5, 18, 0, 0)


class TestCrewDepartureFiltering:
    """Test that expenses correctly filter departed crew members."""
    
    def test_expense_after_departure_excludes_crew(self, db_session, test_trip, test_crew):
        """Test that crew member departed at 10:00 is excluded from expense at 10:30."""
        # Alice departs at 10:00 UTC
        test_crew[0].departed_at = datetime(2025, 11, 5, 10, 0, 0)
        db_session.commit()
        
        # Create expense at 10:30 UTC (30 minutes later)
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 5),
            occurred_at=datetime(2025, 11, 5, 10, 30, 0),
            category="Diesel",
            amount_eur=1000.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[1].id
        )
        db_session.add(expense)
        db_session.commit()
        
        # Calculate balances
        balances = calculate_balances(db_session, test_trip.id)
        
        # Alice should have no share (she departed before expense)
        alice_balance = next(b for b in balances if b['member'].id == test_crew[0].id)
        assert alice_balance['share_owed'] == 0.0
        
        # Other 3 crew members should split equally: 1000/3 = 333.33
        for i in range(1, 4):
            member_balance = next(b for b in balances if b['member'].id == test_crew[i].id)
            assert abs(member_balance['share_owed'] - 333.33) < 0.01
    
    def test_expense_before_departure_includes_crew(self, db_session, test_trip, test_crew):
        """Test that crew member departed at 10:00 is included in expense at 09:30."""
        # Bob departs at 10:00 UTC
        test_crew[1].departed_at = datetime(2025, 11, 5, 10, 0, 0)
        db_session.commit()
        
        # Create expense at 09:30 UTC (30 minutes before departure)
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 5),
            occurred_at=datetime(2025, 11, 5, 9, 30, 0),
            category="Diesel",
            amount_eur=1000.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        # Calculate balances
        balances = calculate_balances(db_session, test_trip.id)
        
        # All 4 crew members should split equally: 1000/4 = 250.00
        for i in range(4):
            member_balance = next(b for b in balances if b['member'].id == test_crew[i].id)
            assert abs(member_balance['share_owed'] - 250.0) < 0.01


class TestBackdatedExpenses:
    """Test that backdated expenses use start-of-day timestamps."""
    
    def test_backdated_expense_includes_departed_crew(self, db_session, test_trip, test_crew):
        """Test that expense dated 2 days ago includes crew who departed today."""
        # Charlie departed today at 10:00 UTC
        test_crew[2].departed_at = datetime(2025, 11, 5, 10, 0, 0)
        db_session.commit()
        
        # Create expense dated 2 days ago (Nov 3) - uses start of day
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 0, 0, 0),  # Midnight
            category="Proviant",
            amount_eur=400.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        # Calculate balances
        balances = calculate_balances(db_session, test_trip.id)
        
        # All 4 crew members should be included (Charlie was aboard on Nov 3)
        for i in range(4):
            member_balance = next(b for b in balances if b['member'].id == test_crew[i].id)
            assert abs(member_balance['share_owed'] - 100.0) < 0.01  # 400/4 = 100
    
    def test_realtime_expense_excludes_departed_crew(self, db_session, test_trip, test_crew):
        """Test that today's expense created after departure excludes departed crew."""
        # Diana departed 1 hour ago
        departure_time = datetime.utcnow() - timedelta(hours=1)
        test_crew[3].departed_at = departure_time
        db_session.commit()
        
        # Create expense now (today)
        expense = Expense(
            trip_id=test_trip.id,
            date=date.today(),
            occurred_at=datetime.utcnow(),
            category="Diesel",
            amount_eur=600.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        # Calculate balances
        balances = calculate_balances(db_session, test_trip.id)
        
        # Diana should have no share (she departed before expense)
        diana_balance = next(b for b in balances if b['member'].id == test_crew[3].id)
        assert diana_balance['share_owed'] == 0.0
        
        # Other 3 crew members should split: 600/3 = 200
        for i in range(3):
            member_balance = next(b for b in balances if b['member'].id == test_crew[i].id)
            assert abs(member_balance['share_owed'] - 200.0) < 0.01
