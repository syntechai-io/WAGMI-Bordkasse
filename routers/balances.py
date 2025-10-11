from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import get_db
from models import CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum
from services.trip import TripService
from settlement import compute_settlement

router = APIRouter(tags=["balances"])
templates = Jinja2Templates(directory="templates")

def calculate_balances(db: Session, trip_id: int):
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == trip_id).all()
    member_ids = [m.id for m in crew_members]
    
    # Pre-calculate deposits per member in one query
    deposits_by_member = {}
    deposit_sums = db.query(
        Deposit.member_id,
        func.sum(Deposit.amount_eur).label('total')
    ).filter(
        Deposit.trip_id == trip_id
    ).group_by(Deposit.member_id).all()
    for member_id, total in deposit_sums:
        deposits_by_member[member_id] = total or 0.0
    
    # Pre-calculate private expenses per member in one query
    private_expenses_by_member = {}
    private_sums = db.query(
        Expense.payer_id,
        func.sum(Expense.amount_eur).label('total')
    ).filter(
        Expense.trip_id == trip_id,
        Expense.paid_from == PaidFromEnum.private
    ).group_by(Expense.payer_id).all()
    for payer_id, total in private_sums:
        private_expenses_by_member[payer_id] = total or 0.0
    
    # Pre-calculate participant counts per expense in one query (filtered by trip)
    participant_counts = {}
    count_query = db.query(
        ExpenseParticipant.expense_id,
        func.count(ExpenseParticipant.member_id).label('count')
    ).join(Expense).filter(
        Expense.trip_id == trip_id
    ).group_by(ExpenseParticipant.expense_id).all()
    for expense_id, count in count_query:
        participant_counts[expense_id] = count
    
    # Get all participations for this trip's members in one query
    participations_by_member = {}
    participations = db.query(ExpenseParticipant, Expense).join(Expense).filter(
        Expense.trip_id == trip_id,
        ExpenseParticipant.member_id.in_(member_ids) if member_ids else False
    ).all()
    
    for participation, expense in participations:
        if participation.member_id not in participations_by_member:
            participations_by_member[participation.member_id] = []
        participations_by_member[participation.member_id].append((participation, expense))
    
    balances = []
    net_map = {}
    
    for member in crew_members:
        deposits_total = deposits_by_member.get(member.id, 0.0)
        private_paid = private_expenses_by_member.get(member.id, 0.0)
        
        share_owed = 0.0
        for participation, expense in participations_by_member.get(member.id, []):
            total_participants = participant_counts.get(expense.id, 0)
            if total_participants > 0:
                share_owed += expense.amount_eur / total_participants
        
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
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    balances, _ = calculate_balances(db, active_trip.id)
    
    total_deposits = db.query(func.sum(Deposit.amount_eur)).filter(
        Deposit.trip_id == active_trip.id
    ).scalar() or 0.0
    wallet_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.paid_from == PaidFromEnum.wallet,
        Expense.trip_id == active_trip.id
    ).scalar() or 0.0
    wallet_balance = total_deposits - wallet_expenses
    
    return templates.TemplateResponse("balances.html", {
        "request": request,
        "balances": balances,
        "wallet_balance": round(wallet_balance, 2)
    })

@router.get("/settlement", response_class=HTMLResponse)
async def show_settlement(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    balances, net_map = calculate_balances(db, active_trip.id)
    transfers = compute_settlement(net_map)
    
    member_map = {m.code: m for m in db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).all()}
    
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
