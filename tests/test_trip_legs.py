"""
Tests for TripLeg model and services.legs — trip-scoped leg management.
"""
import pytest
from datetime import date, datetime

from models import Trip, LogbookEntry, PaidFromEnum
from services import legs as LegService


@pytest.fixture
def other_trip(db_session):
    """A second, unrelated trip — used to verify trip-scoping/IDOR checks."""
    trip = Trip(
        name="Other Trip 2025",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 10),
        is_closed=False,
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)
    return trip


class TestTripLegModel:
    def test_create_leg(self, db_session, test_trip):
        leg = LegService.create_leg(
            db_session,
            trip_id=test_trip.id,
            name="Kiel → Aarhus",
            departure_port="Kiel",
            destination_port="Aarhus",
        )
        assert leg.id is not None
        assert leg.trip_id == test_trip.id
        assert leg.sort_order == 0
        assert leg.name == "Kiel → Aarhus"

    def test_sort_order_increments(self, db_session, test_trip):
        leg1 = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg 1")
        leg2 = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg 2")
        assert leg1.sort_order == 0
        assert leg2.sort_order == 1

    def test_display_name_falls_back_to_ports(self, db_session, test_trip):
        leg = LegService.create_leg(
            db_session, trip_id=test_trip.id,
            departure_port="Kiel", destination_port="Rønne",
        )
        assert leg.display_name == "Kiel → Rønne"

    def test_display_name_falls_back_to_id(self, db_session, test_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id)
        assert leg.display_name == f"Leg {leg.id}"

    def test_trip_legs_relationship(self, db_session, test_trip):
        LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg B")
        db_session.refresh(test_trip)
        assert len(test_trip.legs) == 2

    def test_entry_leg_relationship(self, db_session, test_trip, test_crew):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        entry = LogbookEntry(
            trip_id=test_trip.id,
            leg_id=leg.id,
            entry_date=datetime(2025, 11, 2, 10, 0),
            entry_date_utc=datetime(2025, 11, 2, 10, 0),
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(leg)
        assert entry.leg.id == leg.id
        assert len(leg.entries) == 1


class TestTripScoping:
    """Cross-trip IDOR checks — a leg from trip A must never be reachable
    through trip B's id, mirroring the pattern fixed in routers/groups.py."""

    def test_get_leg_or_none_blocks_cross_trip(self, db_session, test_trip, other_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        assert LegService.get_leg_or_none(db_session, test_trip.id, leg.id) is not None
        assert LegService.get_leg_or_none(db_session, other_trip.id, leg.id) is None

    def test_update_leg_blocks_cross_trip(self, db_session, test_trip, other_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Original")
        result = LegService.update_leg(db_session, other_trip.id, leg.id, name="Hacked")
        assert result is None
        db_session.refresh(leg)
        assert leg.name == "Original"

    def test_delete_leg_blocks_cross_trip(self, db_session, test_trip, other_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        with pytest.raises(ValueError):
            LegService.delete_leg(db_session, other_trip.id, leg.id)
        # Still present, scoped to its real trip
        assert LegService.get_leg_or_none(db_session, test_trip.id, leg.id) is not None


class TestLegLifecycle:
    def test_update_leg(self, db_session, test_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Original")
        updated = LegService.update_leg(
            db_session, test_trip.id, leg.id,
            name="Renamed", notes="Windy crossing",
        )
        assert updated.name == "Renamed"
        assert updated.notes == "Windy crossing"

    def test_update_leg_ignores_none_valued_fields(self, db_session, test_trip):
        """Per update_leg's own docstring: a None-valued key must be left
        untouched, not used to blank the column out."""
        leg = LegService.create_leg(
            db_session, trip_id=test_trip.id, name="Original", notes="Keep me",
        )
        updated = LegService.update_leg(
            db_session, test_trip.id, leg.id,
            name="Renamed", notes=None,
        )
        assert updated.name == "Renamed"
        assert updated.notes == "Keep me"

    def test_delete_leg_without_entries(self, db_session, test_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        LegService.delete_leg(db_session, test_trip.id, leg.id)
        assert LegService.get_leg_or_none(db_session, test_trip.id, leg.id) is None

    def test_delete_leg_blocked_when_entries_exist(self, db_session, test_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        entry = LogbookEntry(
            trip_id=test_trip.id,
            leg_id=leg.id,
            entry_date=datetime(2025, 11, 2, 10, 0),
            entry_date_utc=datetime(2025, 11, 2, 10, 0),
        )
        db_session.add(entry)
        db_session.commit()

        with pytest.raises(ValueError, match="linked"):
            LegService.delete_leg(db_session, test_trip.id, leg.id)
        # Leg must still exist
        assert LegService.get_leg_or_none(db_session, test_trip.id, leg.id) is not None

    def test_list_legs_ordered_by_sort_order(self, db_session, test_trip):
        LegService.create_leg(db_session, trip_id=test_trip.id, name="First")
        LegService.create_leg(db_session, trip_id=test_trip.id, name="Second")
        result = LegService.list_legs_for_trip(db_session, test_trip.id)
        assert [leg.name for leg in result] == ["First", "Second"]


class TestRecomputeLegActuals:
    def test_recompute_with_no_entries_clears_actuals(self, db_session, test_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        result = LegService.recompute_leg_actuals(db_session, leg.id)
        assert result.actual_start is None
        assert result.actual_end is None
        assert result.distance_actual_nm is None

    def test_recompute_derives_start_end_and_distance(self, db_session, test_trip):
        leg = LegService.create_leg(db_session, trip_id=test_trip.id, name="Leg A")
        e1 = LogbookEntry(
            trip_id=test_trip.id, leg_id=leg.id,
            entry_date=datetime(2025, 11, 2, 8, 0), entry_date_utc=datetime(2025, 11, 2, 8, 0),
            latitude=54.32, longitude=10.13,
        )
        e2 = LogbookEntry(
            trip_id=test_trip.id, leg_id=leg.id,
            entry_date=datetime(2025, 11, 2, 14, 0), entry_date_utc=datetime(2025, 11, 2, 14, 0),
            latitude=55.10, longitude=10.35,
        )
        db_session.add_all([e1, e2])
        db_session.commit()

        result = LegService.recompute_leg_actuals(db_session, leg.id)
        assert result.actual_start == datetime(2025, 11, 2, 8, 0)
        assert result.actual_end == datetime(2025, 11, 2, 14, 0)
        assert result.distance_actual_nm is not None
        assert result.distance_actual_nm > 0
