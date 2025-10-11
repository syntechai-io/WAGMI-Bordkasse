from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import CrewMember, Deposit, Expense
from services.trip import TripService
import io
import csv

router = APIRouter(prefix="/export", tags=["export"])
templates = Jinja2Templates(directory="templates")

@router.get("/csv", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    return templates.TemplateResponse("export.html", {
        "request": request,
        "active_trip": active_trip
    })

@router.get("/download")
async def download_csv(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([])
    writer.writerow(["CREW MEMBERS"])
    writer.writerow(["ID", "Code", "Name", "IBAN/Handle"])
    for member in db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).all():
        writer.writerow([member.id, member.code, member.name, member.iban_or_handle or ""])
    
    writer.writerow([])
    writer.writerow(["DEPOSITS"])
    writer.writerow(["ID", "Member Code", "Member Name", "Amount EUR", "Date", "Note"])
    for deposit in db.query(Deposit).filter(Deposit.trip_id == active_trip.id).all():
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
    for expense in db.query(Expense).filter(Expense.trip_id == active_trip.id).all():
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
