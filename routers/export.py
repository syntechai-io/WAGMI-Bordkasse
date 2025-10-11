from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from db import get_db
from models import CrewMember, Deposit, Expense
import io
import csv

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/csv")
async def export_csv(request: Request, db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([])
    writer.writerow(["CREW MEMBERS"])
    writer.writerow(["ID", "Code", "Name", "IBAN/Handle"])
    for member in db.query(CrewMember).all():
        writer.writerow([member.id, member.code, member.name, member.iban_or_handle or ""])
    
    writer.writerow([])
    writer.writerow(["DEPOSITS"])
    writer.writerow(["ID", "Member Code", "Member Name", "Amount EUR", "Date", "Note"])
    for deposit in db.query(Deposit).all():
        writer.writerow([
            deposit.id,
            deposit.member.code,
            deposit.member.name,
            deposit.amount_eur,
            deposit.date,
            deposit.note or ""
        ])
    
    writer.writerow([])
    writer.writerow(["EXPENSES"])
    writer.writerow(["ID", "Payer Code", "Payer Name", "Date", "Category", "Description", "Amount EUR", "Paid From", "Split Mode", "Participants"])
    for expense in db.query(Expense).all():
        participants = ", ".join([p.member.code for p in expense.participants])
        writer.writerow([
            expense.id,
            expense.payer.code,
            expense.payer.name,
            expense.date,
            expense.category,
            expense.description,
            expense.amount_eur,
            expense.paid_from.value,
            expense.split_mode.value,
            participants
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crew_wallet_export.csv"}
    )

@router.get("/health")
async def health_check():
    return {"status": "ok"}
