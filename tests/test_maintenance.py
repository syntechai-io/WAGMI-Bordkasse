"""Maintenance & warranty log: service-layer CRUD, account scoping, and
due-status derivation against boat stats."""
from datetime import date, timedelta

import pytest

from models import Account
from services import maintenance as MaintenanceService


@pytest.fixture
def test_account(db_session):
    account = Account(name="Test Account")
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def other_account(db_session):
    account = Account(name="Other Account")
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


class TestMaintenanceRecordLifecycle:
    def test_create_and_list_record(self, db_session, test_account):
        MaintenanceService.create_record(
            db_session, account_id=test_account.id,
            title="Ölwechsel", category="service", performed_at=date(2026, 3, 1),
            engine_hours_at=120.0,
        )
        records = MaintenanceService.list_records_for_account(db_session, test_account.id)
        assert len(records) == 1
        assert records[0].title == "Ölwechsel"
        assert records[0].category == "service"
        assert records[0].status == "resolved"  # default

    def test_list_orders_newest_first(self, db_session, test_account):
        MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Older",
            performed_at=date(2026, 1, 1),
        )
        MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Newer",
            performed_at=date(2026, 3, 1),
        )
        records = MaintenanceService.list_records_for_account(db_session, test_account.id)
        assert [r.title for r in records] == ["Newer", "Older"]

    def test_update_record(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Original",
            performed_at=date(2026, 3, 1),
        )
        updated = MaintenanceService.update_record(
            db_session, test_account.id, record.id,
            title="Renamed", status="open",
        )
        assert updated.title == "Renamed"
        assert updated.status == "open"

    def test_update_ignores_none_valued_fields(self, db_session, test_account):
        """Same contract as services.legs.update_leg: a None-valued key must
        be left untouched, not used to blank the column out."""
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Original",
            performed_at=date(2026, 3, 1), vendor="Bavaria Yacht Service",
        )
        updated = MaintenanceService.update_record(
            db_session, test_account.id, record.id,
            title="Renamed", vendor=None,
        )
        assert updated.title == "Renamed"
        assert updated.vendor == "Bavaria Yacht Service"

    def test_delete_record(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="To delete",
            performed_at=date(2026, 3, 1),
        )
        MaintenanceService.delete_record(db_session, test_account.id, record.id)
        assert MaintenanceService.get_record_or_none(db_session, test_account.id, record.id) is None

    def test_delete_missing_record_raises(self, db_session, test_account):
        with pytest.raises(ValueError):
            MaintenanceService.delete_record(db_session, test_account.id, 99999)


class TestAccountScoping:
    def test_get_record_or_none_blocks_cross_account(self, db_session, test_account, other_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Mine",
            performed_at=date(2026, 3, 1),
        )
        assert MaintenanceService.get_record_or_none(db_session, other_account.id, record.id) is None

    def test_update_blocks_cross_account(self, db_session, test_account, other_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Mine",
            performed_at=date(2026, 3, 1),
        )
        result = MaintenanceService.update_record(
            db_session, other_account.id, record.id, title="Hacked",
        )
        assert result is None
        db_session.refresh(record)
        assert record.title == "Mine"

    def test_delete_blocks_cross_account(self, db_session, test_account, other_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Mine",
            performed_at=date(2026, 3, 1),
        )
        with pytest.raises(ValueError):
            MaintenanceService.delete_record(db_session, other_account.id, record.id)
        assert MaintenanceService.get_record_or_none(db_session, test_account.id, record.id) is not None


class TestDueStatus:
    def _stats(self, total_nm=0.0, total_motor_h=0.0):
        return {"total_nm": total_nm, "total_motor_h": total_motor_h}

    def test_no_thresholds_set_returns_none(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="No thresholds",
            performed_at=date(2026, 3, 1),
        )
        assert MaintenanceService.due_status(record, self._stats()) is None

    def test_engine_hours_overdue(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Oil change",
            performed_at=date(2026, 3, 1), next_due_engine_hours=100.0,
        )
        assert MaintenanceService.due_status(record, self._stats(total_motor_h=101.0)) == "overdue"

    def test_engine_hours_due_soon(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Oil change",
            performed_at=date(2026, 3, 1), next_due_engine_hours=100.0,
        )
        assert MaintenanceService.due_status(record, self._stats(total_motor_h=85.0)) == "due_soon"

    def test_engine_hours_on_track(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Oil change",
            performed_at=date(2026, 3, 1), next_due_engine_hours=100.0,
        )
        assert MaintenanceService.due_status(record, self._stats(total_motor_h=10.0)) is None

    def test_nm_overdue(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Anode check",
            performed_at=date(2026, 3, 1), next_due_nm=500.0,
        )
        assert MaintenanceService.due_status(record, self._stats(total_nm=600.0)) == "overdue"

    def test_date_overdue(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Rig check",
            performed_at=date(2026, 3, 1),
            next_due_date=date.today() - timedelta(days=1),
        )
        assert MaintenanceService.due_status(record, self._stats()) == "overdue"

    def test_date_due_soon(self, db_session, test_account):
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Rig check",
            performed_at=date(2026, 3, 1),
            next_due_date=date.today() + timedelta(days=5),
        )
        assert MaintenanceService.due_status(record, self._stats()) == "due_soon"

    def test_overdue_wins_over_due_soon_across_criteria(self, db_session, test_account):
        """One overdue criterion outranks another criterion merely due soon."""
        record = MaintenanceService.create_record(
            db_session, account_id=test_account.id, title="Multi-criterion",
            performed_at=date(2026, 3, 1),
            next_due_engine_hours=100.0,  # due soon at 90
            next_due_nm=500.0,            # overdue at 600
        )
        stats = self._stats(total_nm=600.0, total_motor_h=90.0)
        assert MaintenanceService.due_status(record, stats) == "overdue"
