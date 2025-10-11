from sqlalchemy.orm import Session
from models import CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum, User, UserRole, Trip, TripStatus, Currency
from datetime import date, timedelta
import os

def seed_database(db: Session):
    existing_user = db.query(User).first()
    if not existing_user:
        admin_password = os.getenv("ADMIN_PASSWORD")
        crew_password = os.getenv("CREW_PASSWORD")
        
        if not admin_password or not crew_password:
            raise RuntimeError("ADMIN_PASSWORD and CREW_PASSWORD environment variables are required!")
        
        admin_user = User(username="Sven", role=UserRole.admin)
        admin_user.set_password(admin_password)
        
        crew_user = User(username="crew", role=UserRole.crew)
        crew_user.set_password(crew_password)
        
        db.add(admin_user)
        db.add(crew_user)
        db.commit()
        print("Users seeded: Admin 'Sven' and Crew 'crew'")
    
    existing_trip = db.query(Trip).first()
    if existing_trip:
        print("Database already seeded, skipping...")
        return
    
    today = date.today()
    
    trip = Trip(
        name="Ostsee Segeltörn 2025",
        start_date=today - timedelta(days=7),
        status=TripStatus.active
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    
    crew_members = [
        CrewMember(trip_id=trip.id, code="SN", name="Sarah Nielsen", iban_or_handle="DE89370400440532013000"),
        CrewMember(trip_id=trip.id, code="AB", name="Alex Berger", iban_or_handle="PayPal: alex.b@email.com"),
        CrewMember(trip_id=trip.id, code="CD", name="Chris Decker", iban_or_handle="DE89370400440532013001"),
        CrewMember(trip_id=trip.id, code="MK", name="Maria Klein", iban_or_handle="Revolut: +49 170 123456"),
    ]
    
    for member in crew_members:
        db.add(member)
    db.commit()
    
    for member in crew_members:
        db.refresh(member)
    
    deposits = [
        Deposit(trip_id=trip.id, member_id=crew_members[0].id, amount=400.00, currency=Currency.EUR, amount_eur=400.00, date=today - timedelta(days=7), note="Initial deposit"),
        Deposit(trip_id=trip.id, member_id=crew_members[1].id, amount=400.00, currency=Currency.EUR, amount_eur=400.00, date=today - timedelta(days=7), note="Initial deposit"),
        Deposit(trip_id=trip.id, member_id=crew_members[2].id, amount=400.00, currency=Currency.EUR, amount_eur=400.00, date=today - timedelta(days=6), note="Initial deposit"),
        Deposit(trip_id=trip.id, member_id=crew_members[3].id, amount=400.00, currency=Currency.EUR, amount_eur=400.00, date=today - timedelta(days=6), note="Initial deposit"),
    ]
    
    for deposit in deposits:
        db.add(deposit)
    db.commit()
    
    expense1 = Expense(
        trip_id=trip.id,
        payer_id=crew_members[0].id,
        date=today - timedelta(days=5),
        category="Proviant",
        description="Groceries for the week",
        amount=180.00,
        currency=Currency.EUR,
        amount_eur=180.00,
        paid_from=PaidFromEnum.wallet,
        split_mode=SplitModeEnum.equal
    )
    db.add(expense1)
    db.commit()
    db.refresh(expense1)
    
    for member in crew_members:
        db.add(ExpenseParticipant(expense_id=expense1.id, member_id=member.id))
    
    expense2 = Expense(
        trip_id=trip.id,
        payer_id=crew_members[1].id,
        date=today - timedelta(days=3),
        category="Mooring",
        description="Marina overnight fee",
        amount=48.00,
        currency=Currency.EUR,
        amount_eur=48.00,
        paid_from=PaidFromEnum.wallet,
        split_mode=SplitModeEnum.equal
    )
    db.add(expense2)
    db.commit()
    db.refresh(expense2)
    
    for member in crew_members:
        db.add(ExpenseParticipant(expense_id=expense2.id, member_id=member.id))
    
    expense3 = Expense(
        trip_id=trip.id,
        payer_id=crew_members[2].id,
        date=today - timedelta(days=1),
        category="Restaurant",
        description="Dinner at harbor restaurant",
        amount=160.00,
        currency=Currency.EUR,
        amount_eur=160.00,
        paid_from=PaidFromEnum.private,
        split_mode=SplitModeEnum.participants
    )
    db.add(expense3)
    db.commit()
    db.refresh(expense3)
    
    for i in [0, 1, 2]:
        db.add(ExpenseParticipant(expense_id=expense3.id, member_id=crew_members[i].id))
    
    db.commit()
    print(f"Database seeded: Trip '{trip.name}', 4 crew members, 4 deposits, 3 expenses!")
