"""Trip-track aggregation: haversine leg distances, day totals, and map data."""
from __future__ import annotations

from collections import OrderedDict
from datetime import date
from math import asin, cos, radians, sin, sqrt
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from models import LogbookEntry, Trip


_EARTH_RADIUS_NM = 3440.065  # Earth radius in nautical miles


def haversine_nm(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float],
) -> Optional[float]:
    """Great-circle distance in nautical miles. None if any coord missing."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        rlat1, rlon1 = radians(float(lat1)), radians(float(lon1))
        rlat2, rlon2 = radians(float(lat2)), radians(float(lon2))
    except (TypeError, ValueError):
        return None
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_NM * asin(sqrt(a))


def query_track_entries(db: Session, trip_id: int) -> List[LogbookEntry]:
    """All non-superseded logbook entries for a trip, ordered by entry_date."""
    return (
        db.query(LogbookEntry)
        .filter(
            LogbookEntry.trip_id == trip_id,
            LogbookEntry.is_superseded.is_(False),
        )
        .order_by(LogbookEntry.entry_date.asc(), LogbookEntry.id.asc())
        .all()
    )


def compute_leg_distances(entries: Iterable[LogbookEntry]) -> List[Optional[float]]:
    """For each entry, distance from previous entry's position. First entry => None."""
    legs: List[Optional[float]] = []
    prev_lat: Optional[float] = None
    prev_lon: Optional[float] = None
    for e in entries:
        if prev_lat is None or prev_lon is None:
            legs.append(None)
        else:
            legs.append(haversine_nm(prev_lat, prev_lon, e.latitude, e.longitude))
        if e.latitude is not None and e.longitude is not None:
            prev_lat, prev_lon = e.latitude, e.longitude
    return legs


def compute_entry_legs(db: Session, trip_id: int) -> dict:
    """Return {entry_id: leg_nm_or_None} computed across the full non-superseded
    trip sequence. Use this so per-day views agree with the trip-wide totals."""
    entries = query_track_entries(db, trip_id)
    legs = compute_leg_distances(entries)
    return {e.id: leg for e, leg in zip(entries, legs)}


def compute_trip_totals(db: Session, trip_ids: list) -> dict:
    """Return {trip_id: total_nm} where total_nm prefers any manual
    `dist_day_nm` per day (max), falling back to summed haversine legs.
    Used by the trips list to show one number per row — no map data needed."""
    out = {}
    for tid in trip_ids:
        s = compute_track_summary(db, tid, include_map=False)
        out[tid] = s.get("total_nm")
    return out


def compute_track_summary(db: Session, trip_id: int, include_map: bool = True) -> dict:
    """Return per-day distances, total trip distance, and (unless include_map
    is False) route polyline coords for the Leaflet map.

    Day total prefers the manually-set `dist_day_nm` on any entry of that day
    (max value across the day's entries) when present; otherwise it falls back
    to the sum of haversine legs computed within the day. Trip total is the
    sum of all per-day day totals.

    Pass include_map=False when only the numeric totals are needed (e.g. a
    dashboard KPI or the trips-list total) to skip building the per-entry
    polyline/marker payload that only the track map page actually renders.
    """
    entries = query_track_entries(db, trip_id)
    legs = compute_leg_distances(entries)

    # Group by local entry_date.date()
    by_day: "OrderedDict[date, dict]" = OrderedDict()
    for entry, leg_nm in zip(entries, legs):
        d = entry.entry_date.date() if entry.entry_date else None
        if d is None:
            continue
        slot = by_day.setdefault(
            d,
            {
                "date": d,
                "entries": 0,
                "auto_nm": 0.0,
                "manual_nm": None,
                "route": None,
                "destination": None,
            },
        )
        slot["entries"] += 1
        if leg_nm is not None:
            slot["auto_nm"] += float(leg_nm)
        if entry.dist_day_nm is not None:
            manual = float(entry.dist_day_nm)
            if slot["manual_nm"] is None or manual > slot["manual_nm"]:
                slot["manual_nm"] = manual
        if include_map:
            if entry.departure and not slot["route"]:
                slot["route"] = entry.departure
            if entry.destination:
                slot["destination"] = entry.destination

    days = []
    for slot in by_day.values():
        manual = slot["manual_nm"]
        auto = round(slot["auto_nm"], 2) if slot["auto_nm"] else 0.0
        chosen = manual if manual is not None else auto
        day_entry = {
            "date": slot["date"].isoformat(),
            "entries": slot["entries"],
            "distance_nm": round(float(chosen), 2),
            "auto_nm": auto,
            "manual_nm": round(float(manual), 2) if manual is not None else None,
        }
        if include_map:
            route_str = None
            if slot["route"] and slot["destination"]:
                route_str = f"{slot['route']} → {slot['destination']}"
            elif slot["destination"]:
                route_str = slot["destination"]
            elif slot["route"]:
                route_str = slot["route"]
            day_entry["route"] = route_str
        days.append(day_entry)

    total_nm = round(sum(d["distance_nm"] for d in days), 2)

    result = {
        "total_nm": total_nm,
        "days": days,
        "entry_count": len(entries),
    }

    if not include_map:
        return result

    # Polyline = ordered positions (skip entries without GPS)
    polyline = [
        [float(e.latitude), float(e.longitude)]
        for e in entries
        if e.latitude is not None and e.longitude is not None
    ]

    markers = []
    for entry, leg_nm in zip(entries, legs):
        if entry.latitude is None or entry.longitude is None:
            continue
        markers.append(
            {
                "id": entry.id,
                "lat": float(entry.latitude),
                "lon": float(entry.longitude),
                "time": entry.entry_date.isoformat() if entry.entry_date else None,
                "maneuver": entry.maneuver_type,
                "leg_nm": round(float(leg_nm), 2) if leg_nm is not None else None,
                "cog": entry.cog_deg,
                "sog": entry.sog_kn,
            }
        )

    result["polyline"] = polyline
    result["markers"] = markers
    result["positioned_count"] = len(polyline)
    return result
