#!/usr/bin/env python
"""
Test Trip Creator for Crew Wallet
Creates a test trip with crew departures to test the settlement feature
"""
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from db import SessionLocal
from models import Trip, CrewMember, Deposit, Expense, PaidFromEnum, SplitModeEnum
from werkzeug.security import generate_password_hash

def create_test_trip(db: Session):
    """Create a comprehensive test trip with crew departures"""
    
    # Create test trip
    trip_start = date(2025, 6, 1)
    trip_end = date(2025, 6, 15)
    
    trip = Trip(
        name="TEST - Crew Departure Demo",
        start_date=trip_start,
        end_date=trip_end,
        status="active",
        is_closed=0
    )
    trip.set_crew_password("crew123")
    trip.set_trip_admin_password("admin123")
    
    db.add(trip)
    db.flush()
    
    print(f"✓ Created test trip: {trip.name} (ID: {trip.id})")
    
    # Create crew members with different scenarios
    crew_data = [
        {"code": "A", "name": "Alice (Full Trip)", "departed": None},
        {"code": "B", "name": "Bob (Left June 8)", "departed": datetime(2025, 6, 8, 10, 0)},
        {"code": "C", "name": "Charlie (Left June 10)", "departed": datetime(2025, 6, 10, 14, 30)},
        {"code": "D", "name": "Diana (Full Trip)", "departed": None},
    ]
    
    crew_members = []
    for data in crew_data:
        member = CrewMember(
            trip_id=trip.id,
            code=data["code"],
            name=data["name"],
            departed_at=data["departed"]
        )
        db.add(member)
        crew_members.append(member)
    
    db.flush()
    print(f"✓ Created {len(crew_members)} crew members")
    for m in crew_members:
        status = f"departed {m.departed_at.strftime('%b %d')}" if m.departed_at else "active"
        print(f"  - {m.code}: {m.name} ({status})")
    
    # Create deposits (everyone contributes at start)
    deposits = [
        (crew_members[0], 500.0),  # Alice
        (crew_members[1], 400.0),  # Bob
        (crew_members[2], 450.0),  # Charlie
        (crew_members[3], 500.0),  # Diana
    ]
    
    for member, amount in deposits:
        deposit = Deposit(
            trip_id=trip.id,
            member_id=member.id,
            amount=amount,
            currency="EUR",
            amount_eur=amount,
            date=trip_start,
            note=f"Initial deposit from {member.name}"
        )
        db.add(deposit)
    
    db.flush()
    print(f"✓ Created {len(deposits)} deposits (Total: €{sum(d[1] for d in deposits)})")
    
    # Create expenses at different dates to test departure logic
    expenses = [
        # June 3 - All 4 crew active
        {
            "date": date(2025, 6, 3),
            "description": "Groceries (all 4 active)",
            "amount": 200.0,
            "payer": crew_members[0],
            "paid_from": PaidFromEnum.private,
            "split_mode": SplitModeEnum.equal,
            "note": "All 4 crew should split equally: €50 each"
        },
        # June 7 - All 4 crew still active
        {
            "date": date(2025, 6, 7),
            "description": "Fuel (all 4 active)",
            "amount": 400.0,
            "payer": crew_members[1],
            "paid_from": PaidFromEnum.wallet,
            "split_mode": SplitModeEnum.equal,
            "note": "All 4 crew should split equally: €100 each"
        },
        # June 9 - Only 3 crew (Bob left June 8)
        {
            "date": date(2025, 6, 9),
            "description": "Marina fees (3 crew)",
            "amount": 300.0,
            "payer": crew_members[0],
            "paid_from": PaidFromEnum.private,
            "split_mode": SplitModeEnum.equal,
            "note": "Only Alice, Charlie, Diana: €100 each"
        },
        # June 11 - Only 2 crew (Bob & Charlie both left)
        {
            "date": date(2025, 6, 11),
            "description": "Dinner (2 crew)",
            "amount": 100.0,
            "payer": crew_members[3],
            "paid_from": PaidFromEnum.private,
            "split_mode": SplitModeEnum.equal,
            "note": "Only Alice and Diana: €50 each"
        },
    ]
    
    for exp_data in expenses:
        expense = Expense(
            trip_id=trip.id,
            date=exp_data["date"],
            description=exp_data["description"],
            amount=exp_data["amount"],
            currency="EUR",
            amount_eur=exp_data["amount"],
            category="Proviant",
            paid_from=exp_data["paid_from"],
            split_mode=exp_data["split_mode"],
            payer_id=exp_data["payer"].id
        )
        db.add(expense)
    
    db.flush()
    print(f"✓ Created {len(expenses)} expenses")
    for exp in expenses:
        print(f"  - {exp['date'].strftime('%b %d')}: {exp['description']} (€{exp['amount']})")
    
    db.commit()
    
    print("\n" + "="*60)
    print("TEST TRIP CREATED SUCCESSFULLY!")
    print("="*60)
    print(f"\nTrip Name: {trip.name}")
    print(f"Trip ID: {trip.id}")
    print(f"Crew Password: crew123")
    print(f"Trip Admin Password: admin123")
    print("\nExpected Settlement Calculations:")
    print("-" * 60)
    print("Alice: Paid €700 (€500 deposit + €200 + €0), Owes €300 (€50+€100+€100+€50)")
    print("  Net: +€400 (receives)")
    print("\nBob: Paid €400 (deposit only), Owes €150 (€50+€100 only)")
    print("  Net: +€250 (receives)")
    print("\nCharlie: Paid €450 (deposit only), Owes €250 (€50+€100+€100)")
    print("  Net: +€200 (receives)")
    print("\nDiana: Paid €600 (€500 deposit + €100), Owes €300 (€50+€100+€100+€50)")
    print("  Net: +€300 (receives)")
    print("\nNote: This is a balanced scenario - adjust expenses to create")
    print("      realistic debtor/creditor situations for settlement testing.")
    print("\n" + "="*60)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        create_test_trip(db)
    except Exception as e:
        print(f"\n❌ Error creating test trip: {e}")
        db.rollback()
        raise
    finally:
        db.close()
