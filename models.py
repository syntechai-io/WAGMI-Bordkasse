from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, CheckConstraint, Text, Boolean, Index, Double
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

class SeaStateEnum(str, enum.Enum):
    calm = "calm"
    slight = "slight"
    moderate = "moderate"
    rough = "rough"
    very_rough = "very_rough"
    high = "high"

class PlanEnum(str, enum.Enum):
    FREE = "FREE"
    SKIPPER_PLUS = "SKIPPER_PLUS"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"

class TripRole(str, enum.Enum):
    skipper = "skipper"
    crew = "crew"

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
        return check_password_hash(str(self.password_hash), password)

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(SQLEnum(TripStatus), nullable=False, default=TripStatus.active)
    is_closed = Column(Integer, nullable=False, default=0)  # 0 = open, 1 = closed (admin only can edit)
    trip_admin_password_hash = Column(String(200), nullable=True)  # Password for trip admins
    crew_password_hash = Column(String(200), nullable=True)  # Password for regular crew members
    skipper_name = Column(String(100), nullable=True)  # Skipper name for logbook PDFs
    skipper_code = Column(String(20), nullable=True)  # Skipper code for logbook PDFs
    home_port = Column(String(100), nullable=True)  # Vessel home port for logbook PDFs
    call_sign = Column(String(50), nullable=True)  # Vessel call sign for logbook PDFs
    imo_mmsi = Column(String(50), nullable=True)  # Vessel IMO/MMSI number for logbook PDFs
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account", backref="trips")
    crew_members = relationship("CrewMember", back_populates="trip", cascade="all, delete-orphan")
    deposits = relationship("Deposit", back_populates="trip", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="trip", cascade="all, delete-orphan")
    logbook_entries = relationship("LogbookEntry", back_populates="trip", cascade="all, delete-orphan")
    trip_members = relationship("TripMember", backref="trip", cascade="all, delete-orphan")
    
    def set_trip_admin_password(self, password: str):
        """Hash and set trip admin password"""
        if password:
            self.trip_admin_password_hash = generate_password_hash(password)
        else:
            self.trip_admin_password_hash = None
    
    def check_trip_admin_password(self, password: str) -> bool:
        """Verify trip admin password against hash"""
        if self.trip_admin_password_hash is None or not password:
            return False
        return check_password_hash(str(self.trip_admin_password_hash), password)
    
    def set_crew_password(self, password: str):
        """Hash and set crew password"""
        if password:
            self.crew_password_hash = generate_password_hash(password)
        else:
            self.crew_password_hash = None
    
    def check_crew_password(self, password: str) -> bool:
        """Verify crew password against hash"""
        if self.crew_password_hash is None or not password:
            return False
        return check_password_hash(str(self.crew_password_hash), password)

class CrewMember(Base):
    __tablename__ = "crew_members"
    __table_args__ = (
        UniqueConstraint('trip_id', 'code', name='uq_crew_trip_code'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    iban_or_handle = Column(String(100), nullable=True)
    paypal_me = Column(String(100), nullable=True)
    is_trip_admin = Column(Integer, nullable=False, default=0)  # 0 = regular crew, 1 = trip admin
    departed_at = Column(DateTime, nullable=True)  # Timestamp when crew member departed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trip = relationship("Trip", back_populates="crew_members")
    deposits = relationship("Deposit", back_populates="member", cascade="all, delete-orphan")
    paid_expenses = relationship("Expense", foreign_keys="Expense.payer_id", back_populates="payer")
    expense_participations = relationship("ExpenseParticipant", back_populates="member", cascade="all, delete-orphan")
    group_memberships = relationship("CrewGroupMember", back_populates="member", cascade="all, delete-orphan")
    representing_groups = relationship("CrewGroup", foreign_keys="CrewGroup.representative_member_id", back_populates="representative")

class CrewGroup(Base):
    __tablename__ = "crew_groups"
    __table_args__ = (
        UniqueConstraint('trip_id', 'name', name='uq_crew_groups_trip_name'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    representative_member_id = Column(Integer, ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trip = relationship("Trip")
    representative = relationship("CrewMember", foreign_keys=[representative_member_id], back_populates="representing_groups")
    members = relationship("CrewGroupMember", back_populates="group", cascade="all, delete-orphan")

class CrewGroupMember(Base):
    __tablename__ = "crew_group_members"
    __table_args__ = (
        UniqueConstraint('group_id', 'member_id', name='uq_crew_group_members_group_member'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("crew_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("CrewGroup", back_populates="members")
    member = relationship("CrewMember", back_populates="group_memberships")

class Deposit(Base):
    __tablename__ = "deposits"
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_deposit_amount_positive'),
        CheckConstraint('amount_eur > 0', name='check_deposit_amount_eur_positive'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    client_temp_id = Column(String(100), nullable=True, index=True, unique=True)
    member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False, index=True)
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
    percentage = "percentage"

class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_expense_amount_positive'),
        CheckConstraint('amount_eur > 0', name='check_expense_amount_eur_positive'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    client_temp_id = Column(String(100), nullable=True, index=True, unique=True)
    payer_id = Column(Integer, ForeignKey("crew_members.id"), nullable=True, index=True)
    date = Column(Date, nullable=False)
    occurred_at = Column(DateTime, nullable=False, index=True)  # When expense actually occurred (with time)
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
    __table_args__ = (
        CheckConstraint('percentage > 0 AND percentage <= 100', name='check_percentage_valid'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False, index=True)
    percentage = Column(Float, nullable=True)
    
    expense = relationship("Expense", back_populates="participants")
    member = relationship("CrewMember", back_populates="expense_participations")

class Receipt(Base):
    __tablename__ = "receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False, index=True)
    stored_filename = Column(String(100), nullable=False)
    original_name = Column(String(200), nullable=False)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    expense = relationship("Expense", back_populates="receipts")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    trip = relationship("Trip")

class LogbookEntry(Base):
    __tablename__ = "logbook_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, index=True)
    client_temp_id = Column(String(100), nullable=True, index=True, unique=True)
    watch_leader_id = Column(Integer, ForeignKey("crew_members.id"), nullable=True, index=True)
    entry_date = Column(DateTime, nullable=False, index=True)
    entry_date_utc = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    wind_direction = Column(String(20), nullable=True)
    wind_strength = Column(String(50), nullable=True)
    sea_state = Column(SQLEnum(SeaStateEnum), nullable=True)
    visibility = Column(String(50), nullable=True)
    temperature = Column(Float, nullable=True)
    sail_plan = Column(String(200), nullable=True)
    engine_hours = Column(Float, nullable=True)
    departure = Column(String(100), nullable=True)
    destination = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    safety_checks_completed = Column(String(500), nullable=True)
    
    # Navigation data (Phase A enhancement)
    cog_deg = Column(Integer, nullable=True)
    sog_kn = Column(Float, nullable=True)
    log_kn = Column(Float, nullable=True)
    dist_day_nm = Column(Float, nullable=True)
    
    # Weather data (Phase A enhancement)
    pressure_hpa = Column(Integer, nullable=True)
    pressure_trend = Column(String(20), nullable=True)
    weather_source = Column(String(100), nullable=True)
    
    # Engine tracking (Phase A enhancement)
    engine_on = Column(Boolean, nullable=True)
    engine_on_time = Column(DateTime, nullable=True)
    engine_off_time = Column(DateTime, nullable=True)
    eng_hours_total = Column(Float, nullable=True)
    fuel_level_l = Column(Float, nullable=True)
    
    # Sails - In-mast furling (Phase A enhancement)
    main_furl_pct = Column(Integer, nullable=True)
    headsail = Column(String(100), nullable=True)
    sail_action = Column(String(200), nullable=True)
    
    # Sail Change structured state
    main_reef_level = Column(Integer, nullable=True)
    headsail_type = Column(String(10), nullable=True)
    headsail_furl_percent = Column(Integer, nullable=True)
    extra_sail = Column(String(10), nullable=True)

    # Events (Phase A enhancement)
    event_category = Column(String(100), nullable=True)
    event_details = Column(Text, nullable=True)
    
    # Quick entry mode (Phase B enhancement)
    maneuver_type = Column(String(50), nullable=True)
    
    # Append-only compliance (Phase A enhancement)
    parent_id = Column(Integer, ForeignKey("logbook_entries.id"), nullable=True, index=True)
    is_superseded = Column(Boolean, default=False, nullable=False)
    change_note = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    trip = relationship("Trip", back_populates="logbook_entries")
    photos = relationship("LogbookPhoto", back_populates="entry", cascade="all, delete-orphan")
    crew_on_watch = relationship("CrewOnWatch", back_populates="entry", cascade="all, delete-orphan")
    watch_leader = relationship("CrewMember", foreign_keys=[watch_leader_id])
    
    # Self-referential relationship for addendums
    parent = relationship("LogbookEntry", remote_side=[id], foreign_keys=[parent_id], backref="addendums")

class LogbookPhoto(Base):
    __tablename__ = "logbook_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("logbook_entries.id"), nullable=False, index=True)
    stored_filename = Column(String(100), nullable=False)
    original_name = Column(String(200), nullable=False)
    caption = Column(String(500), nullable=True)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    entry = relationship("LogbookEntry", back_populates="photos")

class CrewOnWatch(Base):
    __tablename__ = "crew_on_watch"
    
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("logbook_entries.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("crew_members.id"), nullable=False, index=True)
    
    entry = relationship("LogbookEntry", back_populates="crew_on_watch")
    member = relationship("CrewMember")

class ExpenseTemplate(Base):
    __tablename__ = "expense_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    default_amount = Column(Float, nullable=True)
    currency = Column(SQLEnum(Currency), nullable=False, default=Currency.EUR)
    paid_from = Column(SQLEnum(PaidFromEnum), nullable=False, default=PaidFromEnum.wallet)
    split_mode = Column(SQLEnum(SplitModeEnum), nullable=False, default=SplitModeEnum.equal)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    skipper_name = Column(String(100), nullable=True)
    skipper_code = Column(String(20), nullable=True)
    boat_name = Column(String(100), nullable=True)
    home_port = Column(String(100), nullable=True)
    home_lat = Column(Float, nullable=True)
    home_lon = Column(Float, nullable=True)
    default_currency = Column(SQLEnum(Currency), nullable=False, default=Currency.EUR)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    subscriptions = relationship("Subscription", back_populates="account", cascade="all, delete-orphan")
    saas_users = relationship("SaaSUser", back_populates="account", cascade="all, delete-orphan")
    boat_profile = relationship("BoatProfile", back_populates="account", uselist=False, cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True, nullable=True, unique=True)
    plan = Column(SQLEnum(PlanEnum, name="planenum", create_type=False), nullable=False, default=PlanEnum.FREE)
    status = Column(SQLEnum(SubscriptionStatus, name="subscriptionstatus", create_type=False), nullable=False, default=SubscriptionStatus.CANCELED)
    current_period_end = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    webhook_received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="subscriptions")


class SaaSUser(Base):
    __tablename__ = "new_users"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True, nullable=False)
    email = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_owner = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="saas_users")
    trip_memberships = relationship("TripMember", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_new_users_email", "email"),
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(str(self.password_hash), password)


class TripMember(Base):
    __tablename__ = "trip_members"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("new_users.id"), index=True, nullable=False)
    role = Column(SQLEnum(TripRole, name="triprole", create_type=False), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("SaaSUser", back_populates="trip_memberships")

    __table_args__ = (
        UniqueConstraint("trip_id", "user_id", name="uq_trip_members_trip_user"),
        Index("ix_trip_members_trip_user", "trip_id", "user_id"),
    )


class InviteToken(Base):
    __tablename__ = "invite_tokens"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True, nullable=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), index=True, nullable=False)
    role = Column(SQLEnum(TripRole, name="triprole", create_type=False), nullable=False)
    email = Column(String, nullable=False)
    token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_invite_tokens_token", "token"),
        Index("ix_invite_tokens_email", "email"),
    )


class BoatProfile(Base):
    __tablename__ = "boat_profiles"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), unique=True, nullable=False, index=True)
    boat_name = Column(String(100), nullable=False, default="My Boat")
    boat_name_is_default = Column(Boolean, nullable=False, default=True)
    home_port_name = Column(String(100), nullable=True)
    home_port_lat = Column(Float, nullable=True)
    home_port_lon = Column(Float, nullable=True)
    boat_make = Column(String(100), nullable=True)
    boat_model = Column(String(100), nullable=True)
    boat_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("Account", back_populates="boat_profile")
    sail_profile = relationship("SailProfile", back_populates="boat_profile", uselist=False, cascade="all, delete-orphan")


class SailProfile(Base):
    __tablename__ = "sail_profiles"

    id = Column(Integer, primary_key=True, index=True)
    boat_profile_id = Column(Integer, ForeignKey("boat_profiles.id"), unique=True, nullable=False, index=True)
    main_type = Column(String(20), nullable=False, default="FURLING")
    main_reef_levels = Column(Integer, nullable=False, default=2)
    headsail_genoa = Column(Boolean, nullable=False, default=True)
    headsail_jib = Column(Boolean, nullable=False, default=False)
    headsail_furling = Column(Boolean, nullable=False, default=True)
    has_code0 = Column(Boolean, nullable=False, default=False)
    has_gennaker = Column(Boolean, nullable=False, default=False)
    has_spinnaker = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    boat_profile = relationship("BoatProfile", back_populates="sail_profile")

    @property
    def reef_count(self):
        return self.main_reef_levels or 2

    @property
    def headsail_names(self):
        names = []
        if self.headsail_genoa:
            names.append("Genoa")
        if self.headsail_jib:
            names.append("Jib")
        return names if names else None

    @property
    def extra_sail_names(self):
        names = []
        if self.has_code0:
            names.append("Code 0")
        if self.has_gennaker:
            names.append("Gennaker")
        if self.has_spinnaker:
            names.append("Spinnaker")
        return names if names else None
