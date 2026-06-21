from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from src.utils.utils import format_currency, get_cost_breakdown, get_currency_symbol


def _normalize_usage_date(value) -> datetime | None:
    """Parse Azure UsageDate values (YYYYMMDD int/str, YYYY-MM-DD, or YYYYMM)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d")
    if len(text) == 6 and text.isdigit():
        return datetime.strptime(text + "01", "%Y%m%d")
    if len(text) >= 10 and text[4] == "-":
        return datetime.strptime(text[:10], "%Y-%m-%d")
    return None


def _parse_row(row):
    if len(row) < 4:
        return None
    cost, usage_date, service_name, currency = row[0], row[1], row[2], row[3]
    if not isinstance(cost, (int, float)):
        return None
    parsed_date = _normalize_usage_date(usage_date)
    if parsed_date is None:
        return None
    return float(cost), parsed_date, service_name or "Unknown", currency or "USD"


def _in_range(parsed_date: datetime, start: datetime, end: datetime) -> bool:
    return start.date() <= parsed_date.date() <= end.date()


def _rows_to_cost_data(rows):
    return {"properties": {"rows": rows}}


def derive_metrics_from_daily_rows(rows, dates: dict) -> dict:
    """
    Derive daily, MTD, YTD totals and MTD service breakdown from Daily-granularity rows.
    Row shape: [cost, usageDate, serviceName, currency]
    """
    yesterday = datetime.strptime(dates["yesterday"], "%Y-%m-%d")
    month_start = datetime.strptime(dates["month_starts_on"], "%Y-%m-%d")
    today = datetime.strptime(dates["today"], "%Y-%m-%d")
    year_start = datetime.strptime(dates["year_starts_on"], "%Y-%m-%d")

    daily_total = Decimal("0")
    mtd_total = Decimal("0")
    ytd_total = Decimal("0")
    mtd_by_service: dict[str, float] = defaultdict(float)
    currency_code = "USD"

    for row in rows:
        parsed = _parse_row(row)
        if not parsed:
            continue
        cost, parsed_date, service_name, currency = parsed
        currency_code = currency
        cost_dec = Decimal(str(cost))

        if parsed_date.date() == yesterday.date():
            daily_total += cost_dec

        if _in_range(parsed_date, month_start, today):
            mtd_total += cost_dec
            mtd_by_service[service_name] += cost
            currency_code = currency

        if _in_range(parsed_date, year_start, today):
            ytd_total += cost_dec

    quantize = lambda value: value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    mtd_rows = [
        [cost, dates["month_starts_on"], service, currency_code]
        for service, cost in mtd_by_service.items()
    ]
    service_breakdown, _ = get_cost_breakdown(_rows_to_cost_data(mtd_rows))

    return {
        "daily_cost": quantize(daily_total),
        "month_to_day": quantize(mtd_total),
        "year_to_day": quantize(ytd_total),
        "service_breakdown": service_breakdown,
        "currency_code": currency_code,
    }


def derive_forecast_metrics(rows, dates: dict) -> dict:
    """
    Derive month and year forecast totals from a single forecast query (year range).
    Supports Daily or Monthly granularity rows.
    """
    month_start = datetime.strptime(dates["month_starts_on"], "%Y-%m-%d")
    month_end = datetime.strptime(dates["month_ends_on"], "%Y-%m-%d")
    year_start = datetime.strptime(dates["year_starts_on"], "%Y-%m-%d")
    year_end = datetime.strptime(dates["year_ends_on"], "%Y-%m-%d")

    month_total = Decimal("0")
    year_total = Decimal("0")

    for row in rows:
        parsed = _parse_row(row)
        if not parsed:
            continue
        cost, parsed_date, _, _ = parsed
        cost_dec = Decimal(str(cost))

        if _in_range(parsed_date, year_start, year_end):
            year_total += cost_dec
        if _in_range(parsed_date, month_start, month_end):
            month_total += cost_dec

    quantize = lambda value: value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "month_forecast": quantize(month_total),
        "year_forecast": quantize(year_total),
    }
