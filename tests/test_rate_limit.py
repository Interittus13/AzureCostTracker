import asyncio
from unittest.mock import AsyncMock, patch

from src.main import process_subscription


MOCK_DATES = {
    "today": "2026-06-20",
    "yesterday": "2026-06-18",
    "month_starts_on": "2026-06-01",
    "month_ends_on": "2026-06-30",
    "year_starts_on": "2026-01-01",
    "year_ends_on": "2026-12-31",
}


def test_process_subscription_uses_two_consolidated_cost_calls():
    empty_response = {"properties": {"rows": []}}

    async def run():
        with patch("src.main.get_subscription_name", new=AsyncMock(return_value="Test Sub")), \
             patch("src.main.get_forecast_month_date", new=AsyncMock(return_value=MOCK_DATES)), \
             patch("src.main.get_cost_data", new=AsyncMock(return_value=empty_response)) as mock_cost:
            result = await process_subscription("sub-test", "token")

        assert mock_cost.await_count == 2
        actual_call, forecast_call = mock_cost.await_args_list

        assert actual_call.args[1] == MOCK_DATES["year_starts_on"]
        assert actual_call.args[2] == MOCK_DATES["today"]
        assert actual_call.kwargs["query"] == "query"
        assert actual_call.kwargs["granularity"] == "Daily"

        assert forecast_call.args[1] == MOCK_DATES["year_starts_on"]
        assert forecast_call.args[2] == MOCK_DATES["year_ends_on"]
        assert forecast_call.kwargs["query"] == "forecast"
        assert forecast_call.kwargs["granularity"] == "Daily"

        assert result["subscription_name"] == "Test Sub"
        assert "month_to_day" in result
        assert "service_breakdown" in result

    asyncio.run(run())


def test_get_report_data_processes_subscriptions_sequentially():
    from src.main import get_report_data

    call_order = []

    async def track_process(sub_id, token):
        call_order.append(sub_id)
        return {
            "subscription_name": sub_id,
            "dates": MOCK_DATES,
            "currency_code": "USD",
            "currency_symbol": "$",
            "daily_cost": 1,
            "month_to_day": 2,
            "month_forecast": 3,
            "year_to_day": 4,
            "year_forecast": 5,
            "service_breakdown": [],
        }

    with patch("src.main.get_access_token", return_value="token"), \
         patch("src.main.COST_SCOPE", "subscription"), \
         patch("src.main.SUBSCRIPTIONS", ["sub-a", "sub-b"]), \
         patch("src.main.process_subscription", side_effect=track_process):
        asyncio.run(get_report_data())

    assert call_order == ["sub-a", "sub-b"]
