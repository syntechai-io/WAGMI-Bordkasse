import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from datetime import datetime

from models import Trip, TripMember, TripRole, SaaSUser
from db import SessionLocal


def backfill_trip_members_for_owners(db: Session) -> dict:
    """
    For each trip, ensures the account owner is added as skipper in trip_members.
    Safe to run multiple times (idempotent).
    """
    report = {
        "trips_total": 0,
        "trips_skipped_no_account_id": 0,
        "owners_missing": 0,
        "inserted": 0,
        "already_present": 0,
    }

    trips = db.query(Trip).all()
    report["trips_total"] = len(trips)

    for trip in trips:
        if not trip.account_id:
            report["trips_skipped_no_account_id"] += 1
            continue

        owner = (
            db.query(SaaSUser)
            .filter(SaaSUser.account_id == trip.account_id, SaaSUser.is_owner.is_(True))
            .first()
        )

        if not owner:
            report["owners_missing"] += 1
            continue

        exists = (
            db.query(TripMember)
            .filter(TripMember.trip_id == trip.id, TripMember.user_id == owner.id)
            .first()
        )

        if exists:
            report["already_present"] += 1
            continue

        db.add(
            TripMember(
                trip_id=trip.id,
                user_id=owner.id,
                role=TripRole.skipper,
                created_at=datetime.utcnow(),
            )
        )
        report["inserted"] += 1

    db.commit()
    return report


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Backfilling trip_members for account owners...")
        report = backfill_trip_members_for_owners(db)
        print(f"\nResults:")
        for key, value in report.items():
            print(f"  {key}: {value}")
    finally:
        db.close()
