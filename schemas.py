from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from models import PaidFromEnum, SplitModeEnum

class CrewMemberBase(BaseModel):
    code: str
    name: str
    iban_or_handle: Optional[str] = None

class CrewMemberCreate(CrewMemberBase):
    pass

class CrewMemberUpdate(CrewMemberBase):
    pass

class CrewMember(CrewMemberBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class DepositBase(BaseModel):
    member_id: int
    amount_eur: float
    date: date
    note: Optional[str] = None

class DepositCreate(DepositBase):
    pass

class Deposit(DepositBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ExpenseBase(BaseModel):
    payer_id: int
    date: date
    category: str
    description: str
    amount_eur: float
    currency: str = "EUR"
    paid_from: PaidFromEnum
    split_mode: SplitModeEnum

class ExpenseCreate(ExpenseBase):
    participant_ids: List[int] = []

class Expense(ExpenseBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReceiptBase(BaseModel):
    expense_id: int
    stored_filename: str
    original_name: str
    content_type: str
    size_bytes: int

class Receipt(ReceiptBase):
    id: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class BalanceInfo(BaseModel):
    member_code: str
    member_name: str
    paid_total: float
    share_owed: float
    net: float
    status: str

class SettlementTransfer(BaseModel):
    from_code: str
    from_name: str
    to_code: str
    to_name: str
    amount: float
