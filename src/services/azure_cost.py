import os
import random
import time
import asyncio
import requests
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.config import (
    BASE_URL,
    COST_API_MAX_CONCURRENT,
    COST_API_MIN_INTERVAL_SEC,
    MOCK_AZURE,
)

_cost_api_semaphore = asyncio.Semaphore(COST_API_MAX_CONCURRENT)
_last_cost_api_request_at = 0.0
_rate_limit_lock = asyncio.Lock()


def fetch_azure_data(
    url,
    token,
    payload=None,
    max_retries=8,
    backoff_factor=2,
    subscription_id=None,
    query_type="query",
):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    context = f"subscription={subscription_id or 'n/a'} query={query_type}"

    try:
        retry_count = 0
        while retry_count < max_retries:
            response = (
                requests.post(url, headers=headers, json=payload)
                if payload
                else requests.get(url, headers=headers)
            )

            if response.status_code < 400:
                return response.json()

            if response.status_code == 429:
                retry_after = int(
                    response.headers.get(
                        "x-ms-ratelimit-microsoft.costmanagement-entity-retry-after", 2
                    )
                )
                wait_time = max(retry_after, backoff_factor ** retry_count) + random.uniform(0, 3)
                logger.warning(
                    f"Rate limit exceeded (429) [{context}]. Retrying in {wait_time:.1f} seconds..."
                )
                time.sleep(wait_time)
                retry_count += 1
                continue

            logger.error(f"Error {response.status_code} [{context}]: {response.text}")
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed after {max_retries} attempts [{context}]: {e}")
        raise e


async def _throttled_cost_api_call(url, token, payload, subscription_id, query_type):
    global _last_cost_api_request_at

    async with _cost_api_semaphore:
        async with _rate_limit_lock:
            if COST_API_MIN_INTERVAL_SEC > 0:
                elapsed = time.monotonic() - _last_cost_api_request_at
                if elapsed < COST_API_MIN_INTERVAL_SEC:
                    await asyncio.sleep(COST_API_MIN_INTERVAL_SEC - elapsed)
            _last_cost_api_request_at = time.monotonic()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: fetch_azure_data(
                url,
                token,
                payload,
                subscription_id=subscription_id,
                query_type=query_type,
            ),
        )


def _mock_daily_rows(start_date, end_date, scale, is_forecast=False):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    services = [
        ("Virtual Machines", 95.40),
        ("Azure SQL Database", 32.10),
        ("Storage Accounts", 22.50),
        ("Key Vault", 3.15),
        ("Cognitive Services", 14.20),
        ("Bandwidth", 7.45),
    ]
    rows = []
    current = start
    forecast_multiplier = 1.2 if is_forecast else 1.0
    while current <= end:
        usage_date = current.strftime("%Y%m%d")
        for service_name, base_cost in services:
            rows.append([
                round(base_cost * scale * forecast_multiplier, 2),
                usage_date,
                service_name,
                "CAD",
            ])
        current += timedelta(days=1)
    return rows


# Fetching Azure Subscription Name
async def get_subscription_name(subscription_id, token):
    if MOCK_AZURE:
        sub_type = "Prod" if "prod" in subscription_id.lower() or "production" in subscription_id.lower() else "Dev"
        return f"{sub_type} Subscription ({subscription_id[-8:] if len(subscription_id) > 8 else subscription_id})"

    url = f"{BASE_URL}/subscriptions/{subscription_id}/?api-version=2020-01-01"
    try:
        data = await _throttled_cost_api_call(url, token, None, subscription_id, "metadata")
        return data.get("displayName", "Unknown Subscription")
    except Exception:
        return f"Subscription {subscription_id}"


# Fetching Cost
async def get_cost_data(
    access_token,
    start_date,
    end_date,
    subscription_id,
    query="query",
    granularity="Monthly",
):
    if MOCK_AZURE:
        scale = 1.8 if "prod" in subscription_id.lower() or "production" in subscription_id.lower() else 0.5
        is_forecast = query == "forecast"
        if granularity == "Daily":
            rows = _mock_daily_rows(start_date, end_date, scale, is_forecast=is_forecast)
        else:
            usage_month = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m")
            time_factor = 8.5 if "01-01" in start_date else 1.0
            multiplier = (1.2 if is_forecast else 1.0) * time_factor
            rows = [
                [2850.30 * scale * multiplier, usage_month, "Virtual Machines", "CAD"],
                [980.45 * scale * multiplier, usage_month, "Azure SQL Database", "CAD"],
                [640.20 * scale * multiplier, usage_month, "Storage Accounts", "CAD"],
                [95.40 * scale * multiplier, usage_month, "Key Vault", "CAD"],
                [380.50 * scale * multiplier, usage_month, "Cognitive Services", "CAD"],
                [185.30 * scale * multiplier, usage_month, "Bandwidth", "CAD"],
            ]

        return {
            "properties": {
                "columns": [
                    {"name": "Cost", "type": "Number"},
                    {"name": "UsageDate", "type": "String"},
                    {"name": "ServiceName", "type": "String"},
                    {"name": "Currency", "type": "String"},
                ],
                "rows": rows,
            }
        }

    url = f"{BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/{query}?api-version=2021-10-01"

    payload = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start_date, "to": end_date},
        "dataset": {
            "granularity": granularity,
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ServiceName"}],
            "sorting": [{"direction": "ascending", "name": "UsageDate"}],
        },
    }

    if query == "forecast":
        payload["includeActualCost"] = True
        payload["includeFreshPartialCost"] = True

    return await _throttled_cost_api_call(url, access_token, payload, subscription_id, query)
