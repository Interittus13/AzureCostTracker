from collections import defaultdict

from src.config import BASE_URL, MANAGEMENT_GROUP_ID, MOCK_AZURE
from src.services.azure_cost import _mock_daily_rows, _throttled_cost_api_call
from src.services.cost_aggregator import derive_forecast_metrics, derive_metrics_from_daily_rows
from src.services.azure_cost import get_subscription_name
from src.utils.utils import get_currency_symbol, get_forecast_month_date


def _group_rows_by_subscription(cost_data):
    rows = cost_data.get("properties", {}).get("rows", [])
    columns = [col.get("name") for col in cost_data.get("properties", {}).get("columns", [])]

    grouped = defaultdict(list)
    for row in rows:
        row_map = dict(zip(columns, row)) if columns else {}
        subscription_id = row_map.get("SubscriptionId") or row_map.get("SubscriptionName")
        if not subscription_id:
            continue

        grouped[str(subscription_id).lower()].append([
            row_map.get("Cost", row[0] if row else 0),
            row_map.get("UsageDate", row[1] if len(row) > 1 else None),
            row_map.get("ServiceName", row[2] if len(row) > 2 else "Unknown"),
            row_map.get("Currency", row[3] if len(row) > 3 else "USD"),
        ])
    return grouped


async def _fetch_scope_cost_data(
    access_token,
    start_date,
    end_date,
    query="query",
    granularity="Daily",
):
    if MOCK_AZURE:
        from src.config import SUBSCRIPTIONS

        scale = 1.0
        is_forecast = query == "forecast"
        rows = _mock_daily_rows(start_date, end_date, scale, is_forecast=is_forecast)
        enriched_rows = []
        for index, row in enumerate(rows):
            subscription_id = SUBSCRIPTIONS[index % len(SUBSCRIPTIONS)]
            enriched_rows.append([row[0], row[1], subscription_id, row[2], row[3]])
        return {
            "properties": {
                "columns": [
                    {"name": "Cost", "type": "Number"},
                    {"name": "UsageDate", "type": "String"},
                    {"name": "SubscriptionId", "type": "String"},
                    {"name": "ServiceName", "type": "String"},
                    {"name": "Currency", "type": "String"},
                ],
                "rows": enriched_rows,
            }
        }

    url = f"{BASE_URL}/providers/Microsoft.CostManagement/{query}?api-version=2021-10-01"
    payload = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start_date, "to": end_date},
        "dataset": {
            "granularity": granularity,
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [
                {"type": "Dimension", "name": "SubscriptionId"},
                {"type": "Dimension", "name": "ServiceName"},
            ],
            "sorting": [{"direction": "ascending", "name": "UsageDate"}],
        },
        "scope": f"/providers/Microsoft.Management/managementGroups/{MANAGEMENT_GROUP_ID}",
    }

    if query == "forecast":
        payload["includeActualCost"] = True
        payload["includeFreshPartialCost"] = True

    return await _throttled_cost_api_call(
        url,
        access_token,
        payload,
        MANAGEMENT_GROUP_ID,
        query,
    )


async def get_management_group_report_entries(token, subscription_ids):
    """Fetch all configured subscriptions in two management-group scoped queries."""
    if not MANAGEMENT_GROUP_ID:
        raise ValueError("MANAGEMENT_GROUP_ID is required when COST_SCOPE=managementGroup")

    dates = await get_forecast_month_date(subscription_ids[0], token)

    actual_data = await _fetch_scope_cost_data(
        token, dates["year_starts_on"], dates["today"], query="query", granularity="Daily"
    )
    forecast_data = await _fetch_scope_cost_data(
        token,
        dates["year_starts_on"],
        dates["year_ends_on"],
        query="forecast",
        granularity="Daily",
    )

    actual_by_sub = _group_rows_by_subscription(actual_data)
    forecast_by_sub = _group_rows_by_subscription(forecast_data)

    entries = []
    for subscription_id in subscription_ids:
        sub_key = subscription_id.strip().lower()
        subscription_name = await get_subscription_name(subscription_id, token)
        actual_rows = actual_by_sub.get(sub_key, [])
        forecast_rows = forecast_by_sub.get(sub_key, [])

        metrics = derive_metrics_from_daily_rows(actual_rows, dates)
        forecast_metrics = derive_forecast_metrics(forecast_rows, dates)
        currency_symbol = get_currency_symbol(metrics["currency_code"])

        entries.append(
            {
                "subscription_name": subscription_name,
                "daily_cost": metrics["daily_cost"],
                "month_to_day": metrics["month_to_day"],
                "month_forecast": forecast_metrics["month_forecast"],
                "year_to_day": metrics["year_to_day"],
                "year_forecast": forecast_metrics["year_forecast"],
                "service_breakdown": metrics["service_breakdown"],
                "dates": dates,
                "currency_code": metrics["currency_code"],
                "currency_symbol": currency_symbol,
            }
        )

    return entries, dates
