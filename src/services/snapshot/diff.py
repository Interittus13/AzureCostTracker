from decimal import Decimal, ROUND_HALF_UP

from src.utils.utils import format_currency


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _sum_metric(subscriptions: list, key: str) -> Decimal:
    return _quantize(sum((_to_decimal(sub.get(key, 0)) for sub in subscriptions), Decimal("0")))


def _service_totals(subscriptions: list) -> dict[tuple[str, str], Decimal]:
    totals: dict[tuple[str, str], Decimal] = {}
    for sub in subscriptions:
        sub_name = sub.get("subscription_name", "Unknown")
        for item in sub.get("service_breakdown", []):
            service = item.get("service", "Unknown")
            raw = _to_decimal(item.get("raw_cost", 0))
            totals[(sub_name, service)] = totals.get((sub_name, service), Decimal("0")) + raw
    return totals


def _format_delta_plain(value: Decimal, symbol: str) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{format_currency(abs(value), symbol)}"


class DiffEngine:
    """Compare two report payloads and produce period-over-period diff."""

    @staticmethod
    def compute(current: dict, previous: dict | None) -> dict:
        symbol = current.get("currency_symbol", "$")

        if not previous:
            return {"has_previous": False}

        current_subs = current.get("subscriptions", [])
        previous_subs = previous.get("subscriptions", [])

        current_mtd = _sum_metric(current_subs, "month_to_day")
        previous_mtd = _sum_metric(previous_subs, "month_to_day")
        mtd_delta = _quantize(current_mtd - previous_mtd)

        current_ytd = _sum_metric(current_subs, "year_to_day")
        previous_ytd = _sum_metric(previous_subs, "year_to_day")
        ytd_delta = _quantize(current_ytd - previous_ytd)

        mtd_delta_pct = None
        if previous_mtd > 0:
            mtd_delta_pct = float(_quantize((mtd_delta / previous_mtd) * 100))

        current_services = _service_totals(current_subs)
        previous_services = _service_totals(previous_subs)
        all_keys = set(current_services) | set(previous_services)

        movers = []
        for key in all_keys:
            delta = _quantize(current_services.get(key, Decimal("0")) - previous_services.get(key, Decimal("0")))
            if delta == 0:
                continue
            sub_name, service = key
            prev_val = previous_services.get(key, Decimal("0"))
            delta_pct = float(_quantize((delta / prev_val) * 100)) if prev_val > 0 else None
            movers.append(
                {
                    "subscription": sub_name,
                    "service": service,
                    "delta": float(delta),
                    "delta_pct": delta_pct,
                }
            )

        movers.sort(key=lambda item: abs(item["delta"]), reverse=True)
        top_movers = movers[:3]

        narrative = DiffEngine._build_narrative(mtd_delta, mtd_delta_pct, top_movers, symbol)

        return {
            "has_previous": True,
            "mtd_delta": float(mtd_delta),
            "mtd_delta_pct": mtd_delta_pct,
            "ytd_delta": float(ytd_delta),
            "top_movers": top_movers,
            "narrative": narrative,
        }

    @staticmethod
    def _build_narrative(mtd_delta: Decimal, mtd_delta_pct, top_movers: list, symbol: str) -> str:
        mtd_str = _format_delta_plain(mtd_delta, symbol)
        pct_str = f" ({mtd_delta_pct:+.1f}%)" if mtd_delta_pct is not None else ""

        if top_movers:
            top = top_movers[0]
            driver_delta = _format_delta_plain(_to_decimal(top["delta"]), symbol)
            driver = f", driven by {top['service']} ({driver_delta})"
        else:
            driver = ""

        return f"Since last report: {mtd_str} MTD{pct_str}{driver}."
