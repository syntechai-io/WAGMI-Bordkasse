from fastapi import APIRouter, Request, Depends
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import get_db
from models import CrewMember, Deposit, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum, CrewGroup, CrewGroupMember
from services.trip import TripService
from services.group import GroupService
from settlement import compute_settlement

router = APIRouter(tags=["balances"])
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

def calculate_balances(db: Session, trip_id: int):
    # Get ALL crew members for the trip (including departed) for settlement calculations
    # This ensures we account for all financial activity during the trip
    crew_members = db.query(CrewMember).filter(
        CrewMember.trip_id == trip_id
    ).all()
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
    # Note: External charges (payer_id == NULL) won't appear in this sum
    private_expenses_by_member = {}
    private_sums = db.query(
        Expense.payer_id,
        func.sum(Expense.amount_eur).label('total')
    ).filter(
        Expense.trip_id == trip_id,
        Expense.paid_from == PaidFromEnum.private,
        Expense.payer_id.isnot(None)
    ).group_by(Expense.payer_id).all()
    for payer_id, total in private_sums:
        private_expenses_by_member[payer_id] = total or 0.0
    
    # Get all expenses for this trip
    all_expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
    
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
        
        # Calculate share from expenses with specific participants (percentage or participants mode)
        for participation, expense in participations_by_member.get(member.id, []):
            # Skip equal mode expenses to prevent double-counting (they're handled below)
            if expense.split_mode == SplitModeEnum.equal:
                continue
            
            # For percentage mode, use the actual percentage stored in the participation record
            if expense.split_mode == SplitModeEnum.percentage:
                if participation.percentage is not None:
                    share_owed += expense.amount_eur * (participation.percentage / 100.0)
            # For participants mode, divide equally among selected participants
            elif expense.split_mode == SplitModeEnum.participants:
                total_participants = participant_counts.get(expense.id, 0)
                if total_participants > 0:
                    share_owed += expense.amount_eur / total_participants
        
        # Calculate share from "equal" split mode expenses (dynamic calculation)
        for expense in all_expenses:
            if expense.split_mode == SplitModeEnum.equal:
                # Count crew members who were active at the time of this expense
                # All crew members are assumed active from trip start unless they departed
                # A member was active if they had not departed yet OR the expense occurred before their departure
                # This allows crew to be added to the list retroactively while maintaining correct splits
                expense_timestamp = expense.occurred_at
                active_at_expense = [
                    m for m in crew_members 
                    if m.departed_at is None or expense_timestamp < m.departed_at
                ]
                expense_crew_count = len(active_at_expense)
                
                # Only include this member in the split if they were active at the time
                member_was_active = (
                    member.departed_at is None or 
                    expense_timestamp < member.departed_at
                )
                
                if expense_crew_count > 0 and member_was_active:
                    share_owed += expense.amount_eur / expense_crew_count
        
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
    
    # Group aggregation for settlement calculations
    # Get all groups for this trip
    groups = GroupService.get_groups_for_trip(db, trip_id)
    
    # Create mappings for group members
    member_to_group = {}  # member_id -> (group, is_representative)
    for group in groups:
        for group_member in group.members:
            is_rep = (group_member.member_id == group.representative_member_id)
            member_to_group[group_member.member_id] = (group, is_rep)
    
    # Mark grouped members in balances list
    for balance in balances:
        member = balance["member"]
        if member.id in member_to_group:
            group, is_rep = member_to_group[member.id]
            balance["grouped"] = True
            balance["is_representative"] = is_rep
            balance["group_name"] = group.name
            if not is_rep:
                # Non-representative members show the representative's code
                balance["representative_code"] = group.representative.code
        else:
            balance["grouped"] = False
            balance["is_representative"] = False
    
    # Create settlement_net_map (only representatives and solo members)
    settlement_net_map = {}
    
    # Calculate aggregated net for each group
    group_aggregates = {}  # group_id -> total_net
    for group in groups:
        total_net = 0.0
        for group_member in group.members:
            # Find the member's code
            member_code = None
            for member in crew_members:
                if member.id == group_member.member_id:
                    member_code = member.code
                    break
            if member_code and member_code in net_map:
                total_net += net_map[member_code]
        group_aggregates[group.id] = round(total_net, 2)
    
    # Build settlement_net_map
    for member in crew_members:
        if member.id in member_to_group:
            group, is_rep = member_to_group[member.id]
            if is_rep:
                # Representative gets the aggregated group net
                settlement_net_map[member.code] = group_aggregates[group.id]
            # Non-representatives are excluded from settlement
        else:
            # Solo member - use individual net
            settlement_net_map[member.code] = net_map[member.code]
    
    return balances, settlement_net_map

@router.get("/balances", response_class=HTMLResponse)
async def show_balances(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    balances, settlement_net_map = calculate_balances(db, active_trip.id)
    
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
        "settlement_net_map": settlement_net_map,
        "wallet_balance": round(wallet_balance, 2)
    })

@router.get("/settlement", response_class=HTMLResponse)
async def show_settlement(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    balances, settlement_net_map = calculate_balances(db, active_trip.id)
    transfers = compute_settlement(settlement_net_map)
    
    # Include ALL crew members (even departed) for settlement display
    # since they may have financial balances to settle
    member_map = {m.code: m for m in db.query(CrewMember).filter(
        CrewMember.trip_id == active_trip.id
    ).all()}
    
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
