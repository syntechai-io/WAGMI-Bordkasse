from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import Expense, ExpenseParticipant, CrewMember, Receipt, PaidFromEnum, SplitModeEnum
from security import require_admin, generate_csrf_token
from datetime import date
from typing import List

router = APIRouter(prefix="/expenses", tags=["expenses"])
templates = Jinja2Templates(directory="templates")

CATEGORIES = ["Proviant", "Getränke", "Mooring", "Diesel", "Wasser", "Strom", "Gas", "Taxi/Transfer", "Restaurant", "Eintritte", "Sonstiges"]

@router.get("", response_class=HTMLResponse)
async def list_expenses(request: Request, db: Session = Depends(get_db), user = Depends(require_admin)):
    expenses = db.query(Expense).order_by(Expense.date.desc()).all()
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    
    return templates.TemplateResponse("expenses.html", {
        "request": request,
        "expenses": expenses,
        "crew_members": crew_members,
        "categories": CATEGORIES,
        "csrf_token": csrf_token
    })

@router.post("/new")
async def create_expense(
    request: Request,
    payer_id: int = Form(...),
    expense_date: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    amount_eur: float = Form(...),
    paid_from: str = Form(...),
    split_mode: str = Form(...),
    participant_ids: List[int] = Form([]),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    expense = Expense(
        payer_id=payer_id,
        date=date.fromisoformat(expense_date),
        category=category,
        description=description,
        amount_eur=amount_eur,
        paid_from=PaidFromEnum(paid_from),
        split_mode=SplitModeEnum(split_mode)
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    
    if split_mode == "participants" and participant_ids:
        for pid in participant_ids:
            db.add(ExpenseParticipant(expense_id=expense.id, member_id=pid))
    elif split_mode == "equal":
        all_members = db.query(CrewMember).all()
        for member in all_members:
            db.add(ExpenseParticipant(expense_id=expense.id, member_id=member.id))
    
    db.commit()
    return RedirectResponse(url="/expenses", status_code=303)

@router.get("/{expense_id}", response_class=HTMLResponse)
async def expense_detail(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    
    return templates.TemplateResponse("expense_detail.html", {
        "request": request,
        "expense": expense,
        "csrf_token": csrf_token
    })

@router.post("/{expense_id}/delete")
async def delete_expense(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    db.delete(expense)
    db.commit()
    return RedirectResponse(url="/expenses", status_code=303)
