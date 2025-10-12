from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from db import get_db
from models import User, Trip, TripStatus, CrewMember, Deposit, Currency, Expense, ExpenseParticipant, PaidFromEnum, SplitModeEnum
from services.trip import TripService
from services.currency import CurrencyService
from jwt_auth import create_token_pair, verify_token, get_current_user, get_admin_user
from sqlalchemy import func
from settlement import compute_settlement

router = APIRouter(prefix="/api/v1", tags=["API v1"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not user.check_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    tokens = create_token_pair(str(user.username), user.role.value)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user={"username": user.username, "role": user.role.value}
    )

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshRequest):
    try:
        payload = verify_token(refresh_request.refresh_token, "refresh")
        username = payload.get("sub")
        role = payload.get("role")
        
        if not username or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        tokens = create_token_pair(username, role)
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            user={"username": username, "role": role}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/auth/verify")
async def verify_auth(current_user: dict = Depends(get_current_user)):
    return {
        "authenticated": True,
        "user": current_user
    }

# Pydantic schemas for Trips
class TripCreate(BaseModel):
    name: str
    start_date: date
    end_date: Optional[date] = None

class TripResponse(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: Optional[date]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Trip endpoints
@router.get("/trips", response_model=List[TripResponse])
async def list_trips(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all trips, optionally filtered by status"""
    query = db.query(Trip)
    if status:
        query = query.filter(Trip.status == status)
    trips = query.order_by(Trip.created_at.desc()).all()
    return trips

@router.post("/trips", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_data: TripCreate,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new trip (admin only). Archives the current active trip if exists."""
    active_trip = TripService.get_active_trip(db)
    if active_trip:
        active_trip.status = TripStatus.archived
    
    new_trip = Trip(
        name=trip_data.name,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        status=TripStatus.active
    )
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
    return new_trip

@router.get("/trips/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific trip by ID"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.put("/trips/{trip_id}/archive", response_model=TripResponse)
async def archive_trip(
    trip_id: int,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Archive a trip (admin only)"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.status = TripStatus.archived
    db.commit()
    db.refresh(trip)
    return trip

@router.get("/trips/active/current", response_model=Optional[TripResponse])
async def get_active_trip(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the currently active trip"""
    active_trip = TripService.get_active_trip(db)
    return active_trip

# Crew Member schemas
class CrewMemberCreate(BaseModel):
    code: str
    name: str
    iban_or_handle: Optional[str] = None

class CrewMemberUpdate(BaseModel):
    name: Optional[str] = None
    iban_or_handle: Optional[str] = None

class CrewMemberResponse(BaseModel):
    id: int
    trip_id: int
    code: str
    name: str
    iban_or_handle: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Crew Member endpoints
@router.get("/trips/{trip_id}/crew", response_model=List[CrewMemberResponse])
async def list_crew_members(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all crew members for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == trip_id).order_by(CrewMember.code).all()
    return crew_members

@router.post("/trips/{trip_id}/crew", response_model=CrewMemberResponse, status_code=status.HTTP_201_CREATED)
async def create_crew_member(
    trip_id: int,
    crew_data: CrewMemberCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new crew member for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check for duplicate code in this trip
    existing = db.query(CrewMember).filter(
        CrewMember.trip_id == trip_id,
        CrewMember.code == crew_data.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Crew member with code '{crew_data.code}' already exists for this trip")
    
    crew_member = CrewMember(
        trip_id=trip_id,
        code=crew_data.code,
        name=crew_data.name,
        iban_or_handle=crew_data.iban_or_handle
    )
    db.add(crew_member)
    db.commit()
    db.refresh(crew_member)
    return crew_member

@router.put("/crew/{crew_id}", response_model=CrewMemberResponse)
async def update_crew_member(
    crew_id: int,
    crew_data: CrewMemberUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a crew member"""
    crew_member = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
    if not crew_member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    
    if crew_data.name is not None:
        crew_member.name = crew_data.name
    if crew_data.iban_or_handle is not None:
        crew_member.iban_or_handle = crew_data.iban_or_handle
    
    db.commit()
    db.refresh(crew_member)
    return crew_member

@router.delete("/crew/{crew_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crew_member(
    crew_id: int,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a crew member (admin only)"""
    crew_member = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
    if not crew_member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    
    db.delete(crew_member)
    db.commit()
    return None

# Deposit schemas
class DepositCreate(BaseModel):
    member_id: int
    amount: float
    currency: str = "EUR"
    date: date
    note: Optional[str] = None
    client_temp_id: Optional[str] = None

class DepositResponse(BaseModel):
    id: int
    trip_id: int
    member_id: int
    amount: float
    currency: str
    amount_eur: float
    date: date
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Deposit endpoints
@router.get("/trips/{trip_id}/deposits", response_model=List[DepositResponse])
async def list_deposits(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all deposits for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    deposits = db.query(Deposit).filter(Deposit.trip_id == trip_id).order_by(Deposit.date.desc(), Deposit.id.desc()).all()
    return deposits

@router.post("/trips/{trip_id}/deposits", response_model=DepositResponse, status_code=status.HTTP_201_CREATED)
async def create_deposit(
    trip_id: int,
    deposit_data: DepositCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new deposit for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Verify crew member exists and belongs to this trip
    crew_member = db.query(CrewMember).filter(
        CrewMember.id == deposit_data.member_id,
        CrewMember.trip_id == trip_id
    ).first()
    if not crew_member:
        raise HTTPException(status_code=404, detail="Crew member not found for this trip")
    
    # Validate currency
    try:
        currency_enum = Currency[deposit_data.currency]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid currency: {deposit_data.currency}")
    
    # Convert to EUR
    amount_eur = CurrencyService.convert_to_eur(deposit_data.amount, currency_enum)
    
    # Check for duplicate client_temp_id if provided
    if deposit_data.client_temp_id:
        existing = db.query(Deposit).filter(Deposit.client_temp_id == deposit_data.client_temp_id).first()
        if existing:
            return existing
    
    deposit = Deposit(
        trip_id=trip_id,
        member_id=deposit_data.member_id,
        amount=deposit_data.amount,
        currency=currency_enum,
        amount_eur=amount_eur,
        date=deposit_data.date,
        note=deposit_data.note,
        client_temp_id=deposit_data.client_temp_id
    )
    db.add(deposit)
    db.commit()
    db.refresh(deposit)
    return deposit

@router.delete("/deposits/{deposit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deposit(
    deposit_id: int,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a deposit (admin only)"""
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    db.delete(deposit)
    db.commit()
    return None

# Expense schemas
class ExpenseParticipantData(BaseModel):
    member_id: int
    percentage: Optional[float] = None

class ExpenseCreate(BaseModel):
    payer_id: int
    date: date
    category: str
    description: str
    amount: float
    currency: str = "EUR"
    paid_from: str
    split_mode: str
    participants: List[ExpenseParticipantData] = []
    client_temp_id: Optional[str] = None

class ExpenseUpdate(BaseModel):
    date: Optional[date] = None
    category: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    paid_from: Optional[str] = None
    split_mode: Optional[str] = None
    participants: Optional[List[ExpenseParticipantData]] = None

class ExpenseParticipantResponse(BaseModel):
    id: int
    member_id: int
    percentage: Optional[float]

    class Config:
        from_attributes = True

class ExpenseResponse(BaseModel):
    id: int
    trip_id: int
    payer_id: int
    date: date
    category: str
    description: str
    amount: float
    currency: str
    amount_eur: float
    paid_from: str
    split_mode: str
    created_at: datetime
    participants: List[ExpenseParticipantResponse] = []

    class Config:
        from_attributes = True

# Expense endpoints
@router.get("/trips/{trip_id}/expenses", response_model=List[ExpenseResponse])
async def list_expenses(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all expenses for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    expenses = db.query(Expense).filter(Expense.trip_id == trip_id).order_by(Expense.date.desc(), Expense.id.desc()).all()
    return expenses

@router.post("/trips/{trip_id}/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    trip_id: int,
    expense_data: ExpenseCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new expense for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Verify payer exists and belongs to this trip
    payer = db.query(CrewMember).filter(
        CrewMember.id == expense_data.payer_id,
        CrewMember.trip_id == trip_id
    ).first()
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found for this trip")
    
    # Validate enums
    try:
        currency_enum = Currency[expense_data.currency]
        paid_from_enum = PaidFromEnum[expense_data.paid_from]
        split_mode_enum = SplitModeEnum[expense_data.split_mode]
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    
    # Convert to EUR
    amount_eur = CurrencyService.convert_to_eur(expense_data.amount, currency_enum)
    
    # Check for duplicate client_temp_id if provided
    if expense_data.client_temp_id:
        existing = db.query(Expense).filter(Expense.client_temp_id == expense_data.client_temp_id).first()
        if existing:
            return existing
    
    # Create expense
    expense = Expense(
        trip_id=trip_id,
        payer_id=expense_data.payer_id,
        date=expense_data.date,
        category=expense_data.category,
        description=expense_data.description,
        amount=expense_data.amount,
        currency=currency_enum,
        amount_eur=amount_eur,
        paid_from=paid_from_enum,
        split_mode=split_mode_enum,
        client_temp_id=expense_data.client_temp_id
    )
    db.add(expense)
    db.flush()
    
    # Add participants
    for participant_data in expense_data.participants:
        # Verify participant exists and belongs to this trip
        member = db.query(CrewMember).filter(
            CrewMember.id == participant_data.member_id,
            CrewMember.trip_id == trip_id
        ).first()
        if not member:
            raise HTTPException(status_code=404, detail=f"Participant {participant_data.member_id} not found for this trip")
        
        participant = ExpenseParticipant(
            expense_id=expense.id,
            member_id=participant_data.member_id,
            percentage=participant_data.percentage
        )
        db.add(participant)
    
    db.commit()
    db.refresh(expense)
    return expense

@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an expense"""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Update basic fields
    if expense_data.date is not None:
        expense.date = expense_data.date
    if expense_data.category is not None:
        expense.category = expense_data.category
    if expense_data.description is not None:
        expense.description = expense_data.description
    
    # Validate and update currency if provided
    if expense_data.currency is not None:
        try:
            new_currency = Currency[expense_data.currency]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid currency: {expense_data.currency}")
    else:
        new_currency = None
    
    # Handle amount/currency update
    if expense_data.amount is not None or new_currency is not None:
        new_amount = expense_data.amount if expense_data.amount is not None else expense.amount
        final_currency = new_currency if new_currency is not None else expense.currency
        expense.amount = new_amount
        expense.currency = final_currency
        expense.amount_eur = CurrencyService.convert_to_eur(new_amount, final_currency)
    
    # Update enums
    if expense_data.paid_from is not None:
        try:
            expense.paid_from = PaidFromEnum[expense_data.paid_from]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid paid_from: {expense_data.paid_from}")
    
    if expense_data.split_mode is not None:
        try:
            expense.split_mode = SplitModeEnum[expense_data.split_mode]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid split_mode: {expense_data.split_mode}")
    
    # Update participants if provided
    if expense_data.participants is not None:
        # Remove existing participants
        db.query(ExpenseParticipant).filter(ExpenseParticipant.expense_id == expense_id).delete()
        
        # Add new participants
        for participant_data in expense_data.participants:
            member = db.query(CrewMember).filter(
                CrewMember.id == participant_data.member_id,
                CrewMember.trip_id == expense.trip_id
            ).first()
            if not member:
                raise HTTPException(status_code=404, detail=f"Participant {participant_data.member_id} not found")
            
            participant = ExpenseParticipant(
                expense_id=expense.id,
                member_id=participant_data.member_id,
                percentage=participant_data.percentage
            )
            db.add(participant)
    
    db.commit()
    db.refresh(expense)
    return expense

@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an expense (admin only)"""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    return None

# Settlement schemas
class BalanceResponse(BaseModel):
    member_id: int
    member_code: str
    member_name: str
    paid_total: float
    share_owed: float
    net: float
    status: str

class SettlementTransferResponse(BaseModel):
    from_member_id: int
    from_code: str
    from_name: str
    to_member_id: int
    to_code: str
    to_name: str
    amount: float

class WalletBalanceResponse(BaseModel):
    total_deposits: float
    wallet_expenses: float
    wallet_balance: float

# Settlement endpoints
@router.get("/trips/{trip_id}/balances", response_model=List[BalanceResponse])
async def get_trip_balances(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get balances for all crew members in a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == trip_id).all()
    member_ids = [m.id for m in crew_members]
    
    # Pre-calculate deposits per member
    deposits_by_member = {}
    deposit_sums = db.query(
        Deposit.member_id,
        func.sum(Deposit.amount_eur).label('total')
    ).filter(
        Deposit.trip_id == trip_id
    ).group_by(Deposit.member_id).all()
    for member_id, total in deposit_sums:
        deposits_by_member[member_id] = total or 0.0
    
    # Pre-calculate private expenses per member
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
    
    # Pre-calculate participant counts per expense
    participant_counts = {}
    count_query = db.query(
        ExpenseParticipant.expense_id,
        func.count(ExpenseParticipant.member_id).label('count')
    ).join(Expense).filter(
        Expense.trip_id == trip_id
    ).group_by(ExpenseParticipant.expense_id).all()
    for expense_id, count in count_query:
        participant_counts[expense_id] = count
    
    # Get all participations
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
            "member_id": member.id,
            "member_code": member.code,
            "member_name": member.name,
            "paid_total": round(paid_total, 2),
            "share_owed": round(share_owed, 2),
            "net": round(net, 2),
            "status": status
        })
    
    return balances

@router.get("/trips/{trip_id}/settlements", response_model=List[SettlementTransferResponse])
async def get_trip_settlements(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get optimized settlement transfers for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Calculate balances and net map
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == trip_id).all()
    member_ids = [m.id for m in crew_members]
    
    deposits_by_member = {}
    deposit_sums = db.query(
        Deposit.member_id,
        func.sum(Deposit.amount_eur).label('total')
    ).filter(
        Deposit.trip_id == trip_id
    ).group_by(Deposit.member_id).all()
    for member_id, total in deposit_sums:
        deposits_by_member[member_id] = total or 0.0
    
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
    
    participant_counts = {}
    count_query = db.query(
        ExpenseParticipant.expense_id,
        func.count(ExpenseParticipant.member_id).label('count')
    ).join(Expense).filter(
        Expense.trip_id == trip_id
    ).group_by(ExpenseParticipant.expense_id).all()
    for expense_id, count in count_query:
        participant_counts[expense_id] = count
    
    participations_by_member = {}
    participations = db.query(ExpenseParticipant, Expense).join(Expense).filter(
        Expense.trip_id == trip_id,
        ExpenseParticipant.member_id.in_(member_ids) if member_ids else False
    ).all()
    
    for participation, expense in participations:
        if participation.member_id not in participations_by_member:
            participations_by_member[participation.member_id] = []
        participations_by_member[participation.member_id].append((participation, expense))
    
    net_map = {}
    member_map = {}
    for member in crew_members:
        deposits_total = deposits_by_member.get(member.id, 0.0)
        private_paid = private_expenses_by_member.get(member.id, 0.0)
        
        share_owed = 0.0
        for participation, expense in participations_by_member.get(member.id, []):
            total_participants = participant_counts.get(expense.id, 0)
            if total_participants > 0:
                share_owed += expense.amount_eur / total_participants
        
        paid_total = deposits_total + private_paid
        net = round(paid_total - share_owed, 2)
        net_map[member.code] = net
        member_map[member.code] = member
    
    # Compute settlement transfers
    transfers = compute_settlement(net_map)
    
    settlement_data = []
    for from_code, to_code, amount in transfers:
        from_member = member_map[from_code]
        to_member = member_map[to_code]
        settlement_data.append({
            "from_member_id": from_member.id,
            "from_code": from_code,
            "from_name": from_member.name,
            "to_member_id": to_member.id,
            "to_code": to_code,
            "to_name": to_member.name,
            "amount": round(amount, 2)
        })
    
    return settlement_data

@router.get("/trips/{trip_id}/wallet", response_model=WalletBalanceResponse)
async def get_wallet_balance(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get wallet balance for a trip"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    total_deposits = db.query(func.sum(Deposit.amount_eur)).filter(
        Deposit.trip_id == trip_id
    ).scalar() or 0.0
    
    wallet_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.paid_from == PaidFromEnum.wallet,
        Expense.trip_id == trip_id
    ).scalar() or 0.0
    
    wallet_balance = total_deposits - wallet_expenses
    
    return {
        "total_deposits": round(total_deposits, 2),
        "wallet_expenses": round(wallet_expenses, 2),
        "wallet_balance": round(wallet_balance, 2)
    }
