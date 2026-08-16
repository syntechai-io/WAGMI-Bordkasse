"""Trip leg (passage) management.

A TripLeg groups logbook entries into a named passage (e.g. the outbound and
return legs of a roundtrip). All lookups are trip-scoped so a leg from one
trip can never be read or mutated through another trip's session — mirrors
the ownership-check pattern in routers/groups.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from models import LogbookEntry, TripLeg
from services.track import haversine_nm


def list_legs_for_trip(db: Session, trip_id: int) -> List[TripLeg]:
    return (
        db.query(TripLeg)
        .filter(TripLeg.trip_id == trip_id)
        .order_by(TripLeg.sort_order.asc(), TripLeg.id.asc())
        .all()
    )


def get_leg_or_none(db: Session, trip_id: int, leg_id: int) -> Optional[TripLeg]:
    """Trip-scoped lookup — returns None if the leg doesn't exist or belongs
    to a different trip, so callers never act on a cross-trip id."""
    return (
        db.query(TripLeg)
        .filter(TripLeg.id == leg_id, TripLeg.trip_id == trip_id)
        .first()
    )


def create_leg(
    db: Session,
    trip_id: int,
    name: Optional[str] = None,
    departure_port: Optional[str] = None,
    destination_port: Optional[str] = None,
    planned_start=None,
    planned_end=None,
    distance_planned_nm: Optional[float] = None,
    notes: Optional[str] = None,
) -> TripLeg:
    next_sort_order = (
        db.query(TripLeg)
        .filter(TripLeg.trip_id == trip_id)
        .count()
    )
    leg = TripLeg(
        trip_id=trip_id,
        name=name or None,
        departure_port=departure_port or None,
        destination_port=destination_port or None,
        planned_start=planned_start,
        planned_end=planned_end,
        distance_planned_nm=distance_planned_nm,
        sort_order=next_sort_order,
        notes=notes or None,
    )
    db.add(leg)
    db.commit()
    db.refresh(leg)
    return leg


def update_leg(db: Session, trip_id: int, leg_id: int, **fields) -> Optional[TripLeg]:
    """Update the given fields on a trip-scoped leg. Returns None if the leg
    doesn't belong to this trip. Unknown/None-valued keys in `fields` are
    ignored so callers can pass a raw form dict without filtering it first."""
    leg = get_leg_or_none(db, trip_id, leg_id)
    if leg is None:
        return None
    allowed = {
        "name", "departure_port", "destination_port",
        "planned_start", "planned_end", "distance_planned_nm", "notes",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(leg, key, value)
    leg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(leg)
    return leg


def delete_leg(db: Session, trip_id: int, leg_id: int) -> None:
    """Raises ValueError if the leg doesn't belong to this trip, or if any
    logbook entries still reference it (unlink/reassign them first) —
    consistent with GroupService.can_delete_member's "block if referenced"
    behavior for crew members."""
    leg = get_leg_or_none(db, trip_id, leg_id)
    if leg is None:
        raise ValueError(f"Leg {leg_id} not found")

    entry_count = (
        db.query(LogbookEntry)
        .filter(LogbookEntry.leg_id == leg_id)
        .count()
    )
    if entry_count:
        raise ValueError(
            f"Leg has {entry_count} logbook entr{'y' if entry_count == 1 else 'ies'} "
            "linked to it. Reassign or unlink them first."
        )

    db.delete(leg)
    db.commit()


def recompute_leg_actuals(db: Session, leg_id: int) -> Optional[TripLeg]:
    """Derive actual_start/actual_end/distance_actual_nm from the entries
    currently linked to this leg. Call after (re)assigning entries to a leg."""
    leg = db.query(TripLeg).filter(TripLeg.id == leg_id).first()
    if leg is None:
        return None

    entries = (
        db.query(LogbookEntry)
        .filter(LogbookEntry.leg_id == leg_id)
        .order_by(LogbookEntry.entry_date.asc())
        .all()
    )
    if not entries:
        leg.actual_start = None
        leg.actual_end = None
        leg.distance_actual_nm = None
        db.commit()
        db.refresh(leg)
        return leg

    leg.actual_start = entries[0].entry_date
    leg.actual_end = entries[-1].entry_date

    total_nm = 0.0
    prev_lat, prev_lon = None, None
    for entry in entries:
        if prev_lat is not None and prev_lon is not None:
            leg_nm = haversine_nm(prev_lat, prev_lon, entry.latitude, entry.longitude)
            if leg_nm is not None:
                total_nm += leg_nm
        if entry.latitude is not None and entry.longitude is not None:
            prev_lat, prev_lon = entry.latitude, entry.longitude
    leg.distance_actual_nm = round(total_nm, 2) if total_nm else None

    db.commit()
    db.refresh(leg)
    return leg
