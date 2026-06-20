import requests
import time
import asyncio
from src.utils.logger import logger
from src.config import BASE_URL, MOCK_AZURE


def fetch_azure_data(url, token, payload=None, max_retries=5, backoff_factor=2):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

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
                retry_after = int(response.headers.get("x-ms-ratelimit-microsoft.costmanagement-entity-retry-after", 2))
                wait_time = max(retry_after, backoff_factor ** retry_count)
                logger.warning(f"Rate limit exceeded (429). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retry_count += 1
                continue

            logger.error(f"Error {response.status_code}: {response.json()}")
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed after {max_retries} attempts: {e}")
        raise e


# Fetching Azure Subscription Name
async def get_subscription_name(subscription_id, token):
    if MOCK_AZURE:
        sub_type = "Prod" if "prod" in subscription_id.lower() or "production" in subscription_id.lower() else "Dev"
        return f"{sub_type} Subscription ({subscription_id[-8:] if len(subscription_id) > 8 else subscription_id})"

    url = f"{BASE_URL}/subscriptions/{subscription_id}/?api-version=2020-01-01"
    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(None, fetch_azure_data, url, token)
        return data.get("displayName", "Unknown Subscription")
    except Exception:
        return f"Subscription {subscription_id}"


# Fetching Cost
async def get_cost_data(access_token, start_date, end_date, subscription_id, query="query"):
    if MOCK_AZURE:
        # Simulate realistic response grouped by ServiceName
        # Format of row: [cost, usageDate, serviceName, currency]
        from datetime import datetime
        usage_month = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m")
        
        is_forecast = query == "forecast"
        # Determine scale of values based on subscription_id
        scale = 1.8 if "prod" in subscription_id.lower() or "production" in subscription_id.lower() else 0.5
        
        if is_forecast:
            # We return forecast data (usually higher or projected values)
            rows = [
                [3200.50 * scale, usage_month, "Virtual Machines", "CAD"],
                [1100.20 * scale, usage_month, "Azure SQL Database", "CAD"],
                [750.40 * scale, usage_month, "Storage Accounts", "CAD"],
                [120.60 * scale, usage_month, "Key Vault", "CAD"],
                [450.80 * scale, usage_month, "Cognitive Services", "CAD"],
                [230.15 * scale, usage_month, "Bandwidth", "CAD"]
            ]
        elif (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days <= 2:
            # Daily cost mock (1-2 days)
            rows = [
                [95.40 * scale, usage_month, "Virtual Machines", "CAD"],
                [32.10 * scale, usage_month, "Azure SQL Database", "CAD"],
                [22.50 * scale, usage_month, "Storage Accounts", "CAD"],
                [3.15 * scale, usage_month, "Key Vault", "CAD"],
                [14.20 * scale, usage_month, "Cognitive Services", "CAD"],
                [7.45 * scale, usage_month, "Bandwidth", "CAD"]
            ]
        else:
            # Monthly to Date or Year to Date mock
            # If YTD, scale it up
            time_factor = 8.5 if "01-01" in start_date else 1.0
            rows = [
                [2850.30 * scale * time_factor, usage_month, "Virtual Machines", "CAD"],
                [980.45 * scale * time_factor, usage_month, "Azure SQL Database", "CAD"],
                [640.20 * scale * time_factor, usage_month, "Storage Accounts", "CAD"],
                [95.40 * scale * time_factor, usage_month, "Key Vault", "CAD"],
                [380.50 * scale * time_factor, usage_month, "Cognitive Services", "CAD"],
                [185.30 * scale * time_factor, usage_month, "Bandwidth", "CAD"]
            ]

        return {
            "properties": {
                "columns": [
                    {"name": "Cost", "type": "Number"},
                    {"name": "UsageDate", "type": "String"},
                    {"name": "ServiceName", "type": "String"},
                    {"name": "Currency", "type": "String"}
                ],
                "rows": rows
            }
        }

    url = f"{BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/{query}?api-version=2021-10-01"

    payload = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start_date, "to": end_date},
        "dataset": {
            "granularity": "Monthly",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [
                {"type": "Dimension", "name": "ServiceName"}
            ],
            "sorting": [{"direction": "ascending", "name": "UsageDate"}],
        },
    }

    if query == "forecast":
        payload["includeActualCost"] = True
        payload["includeFreshPartialCost"] = True

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fetch_azure_data, url, access_token, payload)
