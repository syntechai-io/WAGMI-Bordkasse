from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import Deposit, CrewMember
from datetime import date

router = APIRouter(prefix="/deposits", tags=["deposits"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
async def list_deposits(request: Request, db: Session = Depends(get_db)):
    deposits = db.query(Deposit).order_by(Deposit.date.desc()).all()
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    
    return templates.TemplateResponse("deposits.html", {
        "request": request,
        "deposits": deposits,
        "crew_members": crew_members
    })

@router.post("/new")
async def create_deposit(
    request: Request,
    member_id: int = Form(...),
    amount_eur: float = Form(...),
    deposit_date: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db)
):
    deposit = Deposit(
        member_id=member_id,
        amount_eur=amount_eur,
        date=date.fromisoformat(deposit_date),
        note=note or None
    )
    db.add(deposit)
    db.commit()
    return RedirectResponse(url="/deposits", status_code=303)
