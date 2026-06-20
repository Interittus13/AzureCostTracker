from decimal import Decimal

from src.services.cost_aggregator import derive_forecast_metrics, derive_metrics_from_daily_rows


DATES = {
    "today": "2026-06-20",
    "yesterday": "2026-06-18",
    "month_starts_on": "2026-06-01",
    "month_ends_on": "2026-06-30",
    "year_starts_on": "2026-01-01",
    "year_ends_on": "2026-12-31",
}


def _row(cost, usage_date, service="Virtual Machines", currency="USD"):
    return [cost, usage_date, service, currency]


def test_derive_metrics_daily_mtd_ytd_and_breakdown():
    rows = [
        _row(10.0, "20260115", "Storage Accounts"),
        _row(5.0, "20260618", "Virtual Machines"),
        _row(7.5, "20260619", "Virtual Machines"),
        _row(2.5, "20260619", "Key Vault"),
    ]

    metrics = derive_metrics_from_daily_rows(rows, DATES)

    assert metrics["daily_cost"] == Decimal("5.00")
    assert metrics["month_to_day"] == Decimal("15.00")
    assert metrics["year_to_day"] == Decimal("25.00")
    assert metrics["currency_code"] == "USD"
    assert len(metrics["service_breakdown"]) == 2
    assert metrics["service_breakdown"][0]["service"] == "Virtual Machines"


def test_derive_forecast_metrics_from_daily_rows():
    rows = [
        _row(100.0, "20260610", "Virtual Machines"),
        _row(200.0, "20260710", "Virtual Machines"),
        _row(50.0, "20261201", "Storage Accounts"),
    ]

    forecast = derive_forecast_metrics(rows, DATES)

    assert forecast["month_forecast"] == Decimal("100.00")
    assert forecast["year_forecast"] == Decimal("350.00")


def test_derive_metrics_handles_yyyymmdd_int_dates():
    rows = [_row(12.0, 20260618, "Bandwidth", "CAD")]

    metrics = derive_metrics_from_daily_rows(rows, DATES)

    assert metrics["daily_cost"] == Decimal("12.00")
    assert metrics["currency_code"] == "CAD"
