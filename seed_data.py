from sqlalchemy.orm import Session
from models import CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum
from datetime import date, timedelta

def seed_database(db: Session):
    existing_crew = db.query(CrewMember).first()
    if existing_crew:
        print("Database already seeded, skipping...")
        return
    
    today = date.today()
    
    crew_members = [
        CrewMember(code="SN", name="Sarah Nielsen", iban_or_handle="DE89370400440532013000"),
        CrewMember(code="AB", name="Alex Berger", iban_or_handle="PayPal: alex.b@email.com"),
        CrewMember(code="CD", name="Chris Decker", iban_or_handle="DE89370400440532013001"),
        CrewMember(code="MK", name="Maria Klein", iban_or_handle="Revolut: +49 170 123456"),
    ]
    
    for member in crew_members:
        db.add(member)
    db.commit()
    
    for member in crew_members:
        db.refresh(member)
    
    deposits = [
        Deposit(member_id=crew_members[0].id, amount_eur=400.00, date=today - timedelta(days=7), note="Initial deposit"),
        Deposit(member_id=crew_members[1].id, amount_eur=400.00, date=today - timedelta(days=7), note="Initial deposit"),
        Deposit(member_id=crew_members[2].id, amount_eur=400.00, date=today - timedelta(days=6), note="Initial deposit"),
        Deposit(member_id=crew_members[3].id, amount_eur=400.00, date=today - timedelta(days=6), note="Initial deposit"),
    ]
    
    for deposit in deposits:
        db.add(deposit)
    db.commit()
    
    expense1 = Expense(
        payer_id=crew_members[0].id,
        date=today - timedelta(days=5),
        category="Proviant",
        description="Groceries for the week",
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
        payer_id=crew_members[1].id,
        date=today - timedelta(days=3),
        category="Mooring",
        description="Marina overnight fee",
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
        payer_id=crew_members[2].id,
        date=today - timedelta(days=1),
        category="Restaurant",
        description="Dinner at harbor restaurant",
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
    print("Database seeded successfully with 4 crew members, 4 deposits, and 3 expenses!")
