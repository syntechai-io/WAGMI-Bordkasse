"""compute_track_summary: total_nm must agree whether or not the caller asks
for map data, and include_map=False must skip the polyline/marker payload.
"""
from datetime import datetime

from models import LogbookEntry
from services.track import compute_track_summary


def _add_entry(db_session, trip_id, *, dt, lat, lon, departure=None, destination=None):
    entry = LogbookEntry(
        trip_id=trip_id,
        entry_date=dt,
        entry_date_utc=dt,
        latitude=lat,
        longitude=lon,
        departure=departure,
        destination=destination,
    )
    db_session.add(entry)
    db_session.commit()
    return entry


def test_include_map_false_omits_map_payload_but_keeps_totals(db_session, test_trip):
    _add_entry(db_session, test_trip.id, dt=datetime(2025, 11, 1, 8, 0), lat=54.32, lon=10.13,
               departure="Kiel")
    _add_entry(db_session, test_trip.id, dt=datetime(2025, 11, 1, 14, 0), lat=54.78, lon=11.93,
               destination="Fehmarn")

    light = compute_track_summary(db_session, test_trip.id, include_map=False)
    full = compute_track_summary(db_session, test_trip.id, include_map=True)

    assert "polyline" not in light
    assert "markers" not in light
    assert "positioned_count" not in light
    assert "route" not in light["days"][0]

    assert "polyline" in full
    assert "markers" in full
    assert full["days"][0]["route"] == "Kiel → Fehmarn"

    # The numbers a dashboard/trips-list actually reads must be identical
    # regardless of whether the map payload was built.
    assert light["total_nm"] == full["total_nm"]
    assert light["entry_count"] == full["entry_count"]
    assert len(light["days"]) == len(full["days"])


def test_include_map_defaults_to_true(db_session, test_trip):
    _add_entry(db_session, test_trip.id, dt=datetime(2025, 11, 1, 8, 0), lat=54.32, lon=10.13)

    summary = compute_track_summary(db_session, test_trip.id)

    assert "polyline" in summary
    assert "markers" in summary
