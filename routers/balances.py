from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import get_db
from models import CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum
from settlement import compute_settlement

router = APIRouter(tags=["balances"])
templates = Jinja2Templates(directory="templates")

def calculate_balances(db: Session):
    crew_members = db.query(CrewMember).all()
    balances = []
    net_map = {}
    
    for member in crew_members:
        deposits_total = db.query(func.sum(Deposit.amount_eur)).filter(
            Deposit.member_id == member.id
        ).scalar() or 0.0
        
        private_paid = db.query(func.sum(Expense.amount_eur)).filter(
            Expense.payer_id == member.id,
            Expense.paid_from == PaidFromEnum.private
        ).scalar() or 0.0
        
        participations = db.query(ExpenseParticipant).filter(
            ExpenseParticipant.member_id == member.id
        ).all()
        
        share_owed = 0.0
        for participation in participations:
            expense = participation.expense
            total_participants = db.query(ExpenseParticipant).filter(
                ExpenseParticipant.expense_id == expense.id
            ).count()
            share_owed += expense.amount_eur / total_participants if total_participants > 0 else 0
        
        paid_total = deposits_total + private_paid
        net = paid_total - share_owed
        status = "receives" if net > 0.01 else "pays" if net < -0.01 else "settled"
        
        balances.append({
            "member": member,
            "paid_total": round(paid_total, 2),
            "share_owed": round(share_owed, 2),
            "net": round(net, 2),
            "status": status
        })
        net_map[member.code] = round(net, 2)
    
    return balances, net_map

@router.get("/balances", response_class=HTMLResponse)
async def show_balances(request: Request, db: Session = Depends(get_db)):
    balances, _ = calculate_balances(db)
    
    total_deposits = db.query(func.sum(Deposit.amount_eur)).scalar() or 0.0
    wallet_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.paid_from == PaidFromEnum.wallet
    ).scalar() or 0.0
    wallet_balance = total_deposits - wallet_expenses
    
    return templates.TemplateResponse("balances.html", {
        "request": request,
        "balances": balances,
        "wallet_balance": round(wallet_balance, 2)
    })

@router.get("/settlement", response_class=HTMLResponse)
async def show_settlement(request: Request, db: Session = Depends(get_db)):
    balances, net_map = calculate_balances(db)
    transfers = compute_settlement(net_map)
    
    member_map = {m.code: m for m in db.query(CrewMember).all()}
    
    settlement_data = []
    for from_code, to_code, amount in transfers:
        settlement_data.append({
            "from_code": from_code,
            "from_name": member_map[from_code].name,
            "to_code": to_code,
            "to_name": member_map[to_code].name,
            "amount": amount
        })
    
    return templates.TemplateResponse("settlement.html", {
        "request": request,
        "transfers": settlement_data
    })
