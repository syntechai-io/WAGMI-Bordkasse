from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    admin = "admin"
    crew = "crew"

class TripStatus(str, enum.Enum):
    active = "active"
    archived = "archived"

class Currency(str, enum.Enum):
    EUR = "EUR"
    DKK = "DKK"
    SEK = "SEK"
    GBP = "GBP"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(SQLEnum(TripStatus), nullable=False, default=TripStatus.active)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    crew_members = relationship("CrewMember", back_populates="trip", cascade="all, delete-orphan")
    deposits = relationship("Deposit", back_populates="trip", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="trip", cascade="all, delete-orphan")

class CrewMember(Base):
    __tablename__ = "crew_members"
    __table_args__ = (
        UniqueConstraint('trip_id', 'code', name='uq_crew_trip_code'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    iban_or_handle = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trip = relationship("Trip", back_populates="crew_members")
    deposits = relationship("Deposit", back_populates="member", cascade="all, delete-orphan")
    paid_expenses = relationship("Expense", foreign_keys="Expense.payer_id", back_populates="payer")
    expense_participations = relationship("ExpenseParticipant", back_populates="member", cascade="all, delete-orphan")

class Deposit(Base):
    __tablename__ = "deposits"
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_deposit_amount_positive'),
        CheckConstraint('amount_eur > 0', name='check_deposit_amount_eur_positive'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(SQLEnum(Currency), nullable=False, default=Currency.EUR)
    amount_eur = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trip = relationship("Trip", back_populates="deposits")
    member = relationship("CrewMember", back_populates="deposits")

class PaidFromEnum(str, enum.Enum):
    wallet = "wallet"
    private = "private"

class SplitModeEnum(str, enum.Enum):
    equal = "equal"
    participants = "participants"

class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_expense_amount_positive'),
        CheckConstraint('amount_eur > 0', name='check_expense_amount_eur_positive'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    payer_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False)
    date = Column(Date, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(SQLEnum(Currency), nullable=False, default=Currency.EUR)
    amount_eur = Column(Float, nullable=False)
    paid_from = Column(SQLEnum(PaidFromEnum), nullable=False)
    split_mode = Column(SQLEnum(SplitModeEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trip = relationship("Trip", back_populates="expenses")
    payer = relationship("CrewMember", foreign_keys=[payer_id], back_populates="paid_expenses")
    participants = relationship("ExpenseParticipant", back_populates="expense", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="expense", cascade="all, delete-orphan")

class ExpenseParticipant(Base):
    __tablename__ = "expense_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False)
    
    expense = relationship("Expense", back_populates="participants")
    member = relationship("CrewMember", back_populates="expense_participations")

class Receipt(Base):
    __tablename__ = "receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    stored_filename = Column(String(100), nullable=False)
    original_name = Column(String(200), nullable=False)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    expense = relationship("Expense", back_populates="receipts")
