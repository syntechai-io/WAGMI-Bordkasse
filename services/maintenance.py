"""Maintenance & warranty log: service records for the boat, account-scoped
like Trip. Due-soon/overdue status is derived by comparing each record's
next_due_* thresholds against the boat's cumulative NM/engine-hours from
services.boat.compute_boat_stats — there is no separate "current reading"
to maintain, it always reflects the logbook."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from models import MaintenanceRecord

CATEGORIES = ("service", "repair", "inspection", "warranty_claim")
STATUSES = ("open", "in_progress", "resolved")

# "Due soon" windows — a record is flagged before it's actually overdue so
# there's time to act (e.g. book the yard) rather than finding out at the
# dock that the interval already passed.
DUE_SOON_ENGINE_HOURS = 20.0
DUE_SOON_NM = 50.0
DUE_SOON_DAYS = 14


def list_records_for_account(db: Session, account_id: int) -> List[MaintenanceRecord]:
    return (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.account_id == account_id)
        .order_by(MaintenanceRecord.performed_at.desc(), MaintenanceRecord.id.desc())
        .all()
    )


def get_record_or_none(db: Session, account_id: int, record_id: int) -> Optional[MaintenanceRecord]:
    """Account-scoped lookup — returns None if the record doesn't exist or
    belongs to a different account, mirroring services.legs.get_leg_or_none."""
    return (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.id == record_id, MaintenanceRecord.account_id == account_id)
        .first()
    )


def create_record(db: Session, account_id: int, **fields) -> MaintenanceRecord:
    record = MaintenanceRecord(
        account_id=account_id,
        title=fields.get("title"),
        category=fields.get("category") or "service",
        status=fields.get("status") or "resolved",
        performed_at=fields.get("performed_at") or date.today(),
        engine_hours_at=fields.get("engine_hours_at"),
        nm_at=fields.get("nm_at"),
        vendor=fields.get("vendor"),
        cost_amount=fields.get("cost_amount"),
        cost_currency=fields.get("cost_currency"),
        notes=fields.get("notes"),
        next_due_date=fields.get("next_due_date"),
        next_due_engine_hours=fields.get("next_due_engine_hours"),
        next_due_nm=fields.get("next_due_nm"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, account_id: int, record_id: int, **fields) -> Optional[MaintenanceRecord]:
    """Update the given fields on an account-scoped record. Returns None if
    the record doesn't belong to this account. None-valued keys are ignored
    so callers can pass a raw form dict without filtering it first."""
    record = get_record_or_none(db, account_id, record_id)
    if record is None:
        return None
    allowed = {
        "title", "category", "status", "performed_at",
        "engine_hours_at", "nm_at", "vendor", "cost_amount", "cost_currency",
        "notes", "next_due_date", "next_due_engine_hours", "next_due_nm",
    }
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(record, key, value)
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, account_id: int, record_id: int) -> None:
    """Raises ValueError if the record doesn't belong to this account. The
    caller is responsible for deleting attachment files from disk before
    calling this — see routers/maintenance.py."""
    record = get_record_or_none(db, account_id, record_id)
    if record is None:
        raise ValueError("Maintenance record not found for this account")
    db.delete(record)
    db.commit()


def due_status(record: MaintenanceRecord, boat_stats: dict) -> Optional[str]:
    """Return 'overdue', 'due_soon', or None (no threshold set, or on track).
    Checks all three threshold types set on the record and returns the most
    urgent result across them."""
    worst = None
    today = date.today()
    total_nm = boat_stats.get("total_nm") or 0.0
    total_motor_h = boat_stats.get("total_motor_h") or 0.0

    def _escalate(level):
        nonlocal worst
        if level == "overdue":
            worst = "overdue"
        elif level == "due_soon" and worst != "overdue":
            worst = "due_soon"

    if record.next_due_date is not None:
        days_left = (record.next_due_date - today).days
        if days_left < 0:
            _escalate("overdue")
        elif days_left <= DUE_SOON_DAYS:
            _escalate("due_soon")

    if record.next_due_engine_hours is not None:
        remaining = record.next_due_engine_hours - total_motor_h
        if remaining < 0:
            _escalate("overdue")
        elif remaining <= DUE_SOON_ENGINE_HOURS:
            _escalate("due_soon")

    if record.next_due_nm is not None:
        remaining = record.next_due_nm - total_nm
        if remaining < 0:
            _escalate("overdue")
        elif remaining <= DUE_SOON_NM:
            _escalate("due_soon")

    return worst
