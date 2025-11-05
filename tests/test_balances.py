"""
Test balance calculation and settlement logic.
"""
import pytest
from datetime import datetime, date
from models import CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum
from routers.balances import calculate_balances
from settlement import compute_settlement

class TestBalanceCalculation:
    """Test basic balance calculations."""
    
    def test_simple_deposit_balance(self, db_session, test_trip, test_crew):
        """Test that deposits are correctly added to balances."""
        # Alice deposits 500€
        deposit = Deposit(
            trip_id=test_trip.id,
            member_id=test_crew[0].id,
            amount=500.0,
            amount_eur=500.0,
            date=date(2025, 11, 1)
        )
        db_session.add(deposit)
        db_session.commit()
        
        balances, settlement_net_map = calculate_balances(db_session, test_trip.id)
        alice_balance = next(b for b in balances if b['member'].id == test_crew[0].id)
        
        assert alice_balance['paid_total'] == 500.0
        assert alice_balance['net'] == 500.0
    
    def test_equal_split_calculation(self, db_session, test_trip, test_crew):
        """Test equal split mode divides expense evenly."""
        # Create equal-split expense for 400€
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Proviant",
            description="Test proviant expense",
            amount=400.0,
            amount_eur=400.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        balances, settlement_net_map = calculate_balances(db_session, test_trip.id)
        
        # Each of 4 crew members should owe 100€
        for crew_member in test_crew:
            member_balance = next(b for b in balances if b['member'].id == crew_member.id)
            assert abs(member_balance['share_owed'] - 100.0) < 0.01
    
    def test_participants_split_calculation(self, db_session, test_trip, test_crew):
        """Test participants split mode divides among selected crew."""
        # Create expense with only Alice and Bob as participants
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Restaurant",
            description="Test restaurant expense",
            amount=200.0,
            amount_eur=200.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.participants,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.flush()
        
        # Add participants
        for i in range(2):  # Only Alice and Bob
            participant = ExpenseParticipant(
                expense_id=expense.id,
                member_id=test_crew[i].id
            )
            db_session.add(participant)
        
        db_session.commit()
        
        balances, settlement_net_map = calculate_balances(db_session, test_trip.id)
        
        # Alice and Bob should each owe 100€
        for i in range(2):
            member_balance = next(b for b in balances if b['member'].id == test_crew[i].id)
            assert abs(member_balance['share_owed'] - 100.0) < 0.01
        
        # Charlie and Diana should owe 0€
        for i in range(2, 4):
            member_balance = next(b for b in balances if b['member'].id == test_crew[i].id)
            assert member_balance['share_owed'] == 0.0
    
    def test_percentage_split_calculation(self, db_session, test_trip, test_crew):
        """Test percentage split mode uses custom percentages."""
        # Create expense with custom percentages
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Diesel",
            description="Test diesel expense",
            amount=1000.0,
            amount_eur=1000.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.percentage,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.flush()
        
        # Add participants with percentages: Alice 50%, Bob 30%, Charlie 20%
        # Note: Diana (index 3) is excluded because 0% is not allowed
        percentages = [50, 30, 20]
        for i in range(3):
            participant = ExpenseParticipant(
                expense_id=expense.id,
                member_id=test_crew[i].id,
                percentage=percentages[i]
            )
            db_session.add(participant)
        
        db_session.commit()
        
        balances, settlement_net_map = calculate_balances(db_session, test_trip.id)
        
        # Verify shares: Alice 500€, Bob 300€, Charlie 200€, Diana 0€
        expected_shares = [500.0, 300.0, 200.0, 0.0]
        for i in range(4):
            member_balance = next(b for b in balances if b['member'].id == test_crew[i].id)
            assert abs(member_balance['share_owed'] - expected_shares[i]) < 0.01
    
    def test_private_expense_calculation(self, db_session, test_trip, test_crew):
        """Test that private expenses reduce the payer's balance."""
        # Alice pays 100€ from private funds
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Proviant",
            description="Test proviant expense",
            amount=100.0,
            amount_eur=100.0,
            paid_from=PaidFromEnum.private,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        balances, settlement_net_map = calculate_balances(db_session, test_trip.id)
        alice_balance = next(b for b in balances if b['member'].id == test_crew[0].id)
        
        # Alice paid 100€ private (included in paid_total) and owes 25€ share = 75€ net
        assert alice_balance['paid_total'] == 100.0
        assert abs(alice_balance['share_owed'] - 25.0) < 0.01
        assert abs(alice_balance['net'] - 75.0) < 0.01


class TestSettlementAlgorithm:
    """Test settlement transfer calculation."""
    
    def test_simple_settlement(self, db_session, test_trip, test_crew):
        """Test basic settlement with one debtor and one creditor."""
        # Alice deposits 1000€
        deposit = Deposit(
            trip_id=test_trip.id,
            member_id=test_crew[0].id,
            amount=1000.0,
            amount_eur=1000.0,
            date=date(2025, 11, 1)
        )
        db_session.add(deposit)
        
        # Create expense for 400€ (100€ each)
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Proviant",
            description="Test proviant expense",
            amount=400.0,
            amount_eur=400.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        balances, settlement_net_map = calculate_balances(db_session, test_trip.id)
        settlements = compute_settlement(settlement_net_map)
        
        # Alice should receive from the other 3 (they each owe 100€)
        # settlements are tuples: (from_code, to_code, amount)
        assert len(settlements) == 3
        for from_code, to_code, amount in settlements:
            assert to_code == "A"  # Alice's code
            assert abs(amount - 100.0) < 0.01
    
    def test_complex_settlement_minimizes_transfers(self, db_session, test_trip, test_crew):
        """Test that settlement algorithm minimizes number of transfers."""
        # Alice deposits 500€, Bob deposits 300€
        db_session.add(Deposit(trip_id=test_trip.id, member_id=test_crew[0].id, amount=500.0, amount_eur=500.0, date=date(2025, 11, 1)))
        db_session.add(Deposit(trip_id=test_trip.id, member_id=test_crew[1].id, amount=300.0, amount_eur=300.0, date=date(2025, 11, 1)))
        
        # Create expense for 800€
        expense = Expense(
            trip_id=test_trip.id,
            date=date(2025, 11, 3),
            occurred_at=datetime(2025, 11, 3, 12, 0, 0),
            category="Proviant",
            description="Test proviant expense",
            amount=800.0,
            amount_eur=800.0,
            paid_from=PaidFromEnum.wallet,
            split_mode=SplitModeEnum.equal,
            payer_id=test_crew[0].id
        )
        db_session.add(expense)
        db_session.commit()
        
        balances, settlement_net_map = calculate_balances(db_session, test_trip.id)
        settlements = compute_settlement(settlement_net_map)
        
        # Should have minimal transfers (greedy algorithm optimizes)
        assert len(settlements) <= 3  # At most n-1 transfers for n people
        
        # Total outgoing should equal total incoming
        # settlements are tuples: (from_code, to_code, amount)
        total_amount = sum(amount for from_code, to_code, amount in settlements)
        assert abs(total_amount - 400.0) < 0.1  # Charlie and Diana each owe 200€
