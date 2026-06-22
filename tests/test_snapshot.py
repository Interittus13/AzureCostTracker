import os
from decimal import Decimal

import pytest

from src.services.snapshot import CostSnapshot, DiffEngine, SnapshotStore


def _report(subscriptions, report_for="2026-06-18", report_generated_on="2026-06-20"):
    return {
        "subscriptions": subscriptions,
        "report_for": report_for,
        "report_generated_on": report_generated_on,
        "currency_code": "USD",
        "currency_symbol": "$",
    }


def _sub(name, mtd, ytd=0, services=None):
    return {
        "subscription_name": name,
        "month_to_day": Decimal(str(mtd)),
        "year_to_day": Decimal(str(ytd)),
        "service_breakdown": services or [],
    }


class TestSnapshotStore:
    def test_save_and_load_round_trip(self, tmp_path):
        db_path = str(tmp_path / "snapshots.db")
        store = SnapshotStore(db_path=db_path)

        data = _report([_sub("Prod", 100.0, 500.0)])
        saved = store.save(data)

        assert saved is not None
        assert saved.id == 1

        loaded = store.get_latest()
        assert loaded.report_for == "2026-06-18"
        assert loaded.payload["subscriptions"][0]["subscription_name"] == "Prod"

    def test_get_previous_excludes_latest(self, tmp_path):
        db_path = str(tmp_path / "snapshots.db")
        store = SnapshotStore(db_path=db_path)

        store.save(_report([_sub("Prod", 100.0)], report_generated_on="2026-06-19"))
        second = store.save(_report([_sub("Prod", 120.0)], report_generated_on="2026-06-20"))

        previous = store.get_previous(exclude_id=second.id)
        assert previous.payload["subscriptions"][0]["month_to_day"] == 100.0

    def test_disabled_store_returns_none(self, tmp_path):
        store = SnapshotStore(db_path=str(tmp_path / "snapshots.db"))
        store.enabled = False
        assert store.save(_report([_sub("Prod", 1.0)])) is None
        assert store.get_latest() is None


class TestDiffEngine:
    def test_no_previous_returns_has_previous_false(self):
        current = _report([_sub("Prod", 100.0)])
        diff = DiffEngine.compute(current, None)
        assert diff["has_previous"] is False

    def test_mtd_delta_and_narrative(self):
        previous = _report([
            _sub("Prod", 1000.0, 5000.0, [
                {"service": "Virtual Machines", "raw_cost": 800.0},
            ]),
        ])
        current = _report([
            _sub("Prod", 1420.0, 5200.0, [
                {"service": "Virtual Machines", "raw_cost": 1110.0},
                {"service": "Storage Accounts", "raw_cost": 310.0},
            ]),
        ])

        diff = DiffEngine.compute(current, previous)

        assert diff["has_previous"] is True
        assert diff["mtd_delta"] == 420.0
        assert diff["mtd_delta_pct"] == 42.0
        assert diff["ytd_delta"] == 200.0
        assert "Since last report:" in diff["narrative"]
        assert "+$420.00" in diff["narrative"]
        assert len(diff["top_movers"]) >= 1
        vm_mover = next(m for m in diff["top_movers"] if m["service"] == "Virtual Machines")
        assert vm_mover["delta"] == 310.0

    def test_cost_snapshot_strips_diff_key(self):
        data = _report([_sub("Prod", 50.0)])
        data["diff"] = {"has_previous": False}
        snapshot = CostSnapshot.from_report_data(data)
        assert "diff" not in snapshot.payload
