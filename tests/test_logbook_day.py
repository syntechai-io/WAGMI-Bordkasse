"""Tests for Day Logbook batch creation, multi-photo upload, and Trip Finalize summary."""
import pytest
from datetime import datetime, timedelta, date

from models import Trip, LogbookEntry, LogbookPhoto, SeaStateEnum
from routers.logbook import build_logbook_entry


class TestBuildLogbookEntryHelper:
    """build_logbook_entry is shared between /new and /day-new — must apply
    the same compliance/normalization."""

    def test_sets_entry_date_utc_equal_to_entry_date(self, db_session, test_trip):
        dt = datetime(2025, 11, 5, 10, 30)
        e = build_logbook_entry(trip_id=test_trip.id, entry_dt=dt, latitude=54.32, longitude=10.13)
        db_session.add(e); db_session.commit()
        assert e.entry_date == dt
        assert e.entry_date_utc == dt

    def test_string_sea_state_converts_to_enum(self, db_session, test_trip):
        dt = datetime(2025, 11, 5, 10, 30)
        e = build_logbook_entry(trip_id=test_trip.id, entry_dt=dt, sea_state="moderate")
        db_session.add(e); db_session.commit()
        assert e.sea_state == SeaStateEnum.moderate

    def test_invalid_sea_state_raises(self, db_session, test_trip):
        with pytest.raises(ValueError):
            build_logbook_entry(trip_id=test_trip.id, entry_dt=datetime.utcnow(), sea_state="hurricane")

    def test_default_maneuver_full(self, db_session, test_trip):
        e = build_logbook_entry(trip_id=test_trip.id, entry_dt=datetime.utcnow())
        assert e.maneuver_type == "full"


class TestDayBatchPersistence:
    """Simulate what /logbook/day-new commits: N entries in one transaction
    sharing the same date with monotonically-increasing times."""

    def test_five_entries_same_day(self, db_session, test_trip):
        base = datetime(2025, 11, 5)
        for i, hour in enumerate([8, 10, 12, 14, 16]):
            e = build_logbook_entry(
                trip_id=test_trip.id,
                entry_dt=base.replace(hour=hour),
                latitude=54.32, longitude=10.13,
                wind_direction="SW", wind_strength="4 Bft",
                maneuver_type="full",
            )
            db_session.add(e)
        db_session.commit()
        rows = db_session.query(LogbookEntry).filter(LogbookEntry.trip_id == test_trip.id).order_by(LogbookEntry.entry_date).all()
        assert len(rows) == 5
        # Times monotonic
        times = [r.entry_date for r in rows]
        assert times == sorted(times)
        # Carry-forward effect persisted
        for r in rows:
            assert r.latitude == pytest.approx(54.32)
            assert r.wind_direction == "SW"


class TestMultiPhotoBatch:
    """LogbookPhoto rows can be associated to one entry in a single user action."""

    def test_three_photos_attached_to_one_entry(self, db_session, test_trip):
        entry = build_logbook_entry(trip_id=test_trip.id, entry_dt=datetime(2025, 11, 5, 8, 0))
        db_session.add(entry); db_session.commit()
        for i in range(3):
            p = LogbookPhoto(
                entry_id=entry.id,
                stored_filename=f"uuid-{i}.jpg",
                original_name=f"photo_{i}.jpg",
                content_type="image/jpeg",
                size_bytes=1024,
            )
            db_session.add(p)
        db_session.commit()
        photos = db_session.query(LogbookPhoto).filter(LogbookPhoto.entry_id == entry.id).all()
        assert len(photos) == 3


class TestTripFinalizeSummary:
    """Replicates the /trips/{id}/finalize summary computation:
    entry count, motor hours, sail hours, photo count."""

    def _summary(self, db_session, trip_id):
        from sqlalchemy import func
        entries = db_session.query(LogbookEntry).filter(LogbookEntry.trip_id == trip_id).order_by(LogbookEntry.entry_date).all()
        eng_values = [e.eng_hours_total for e in entries if e.eng_hours_total is not None]
        motor_hours = (max(eng_values) - min(eng_values)) if len(eng_values) >= 2 else 0
        sail_hours = 0.0
        if len(entries) >= 2 and entries[0].entry_date and entries[-1].entry_date:
            total = (entries[-1].entry_date - entries[0].entry_date).total_seconds() / 3600.0
            sail_hours = max(total - float(motor_hours), 0.0)
        photos = db_session.query(func.count(LogbookPhoto.id)).join(
            LogbookEntry, LogbookEntry.id == LogbookPhoto.entry_id
        ).filter(LogbookEntry.trip_id == trip_id).scalar() or 0
        return {
            "entry_count": len(entries),
            "motor_hours": round(motor_hours, 1),
            "sail_hours": round(sail_hours, 1),
            "photo_count": photos,
        }

    def test_summary_metrics(self, db_session, test_trip):
        # Two entries, 6h apart, engine ran 2.0h
        e1 = build_logbook_entry(trip_id=test_trip.id, entry_dt=datetime(2025, 11, 5, 8, 0), eng_hours_total=100.0)
        e2 = build_logbook_entry(trip_id=test_trip.id, entry_dt=datetime(2025, 11, 5, 14, 0), eng_hours_total=102.0)
        db_session.add_all([e1, e2]); db_session.commit()
        # Add 1 photo
        db_session.add(LogbookPhoto(entry_id=e1.id, stored_filename="x.jpg", original_name="x.jpg", content_type="image/jpeg", size_bytes=10))
        db_session.commit()
        s = self._summary(db_session, test_trip.id)
        assert s["entry_count"] == 2
        assert s["motor_hours"] == 2.0
        assert s["sail_hours"] == 4.0  # 6h total - 2h motor
        assert s["photo_count"] == 1


class TestTripFinalizeLocking:
    """is_closed=True must prevent further crew edits via TripService gate."""

    def test_closed_trip_blocks_crew_edits(self, db_session, test_trip):
        from services.trip import TripService
        test_trip.is_closed = True
        db_session.commit()
        # Crew role should be blocked
        assert TripService.is_trip_editable(test_trip, "crew", request=None) is False
        # Admin role still allowed
        assert TripService.is_trip_editable(test_trip, "admin", request=None) is True
