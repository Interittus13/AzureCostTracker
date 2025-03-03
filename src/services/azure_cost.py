import requests
import time
from src.utils.logger import logger
from src.config import BASE_URL


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
        logger.error(f"Failed after {max_retries}")



# Fetching Azure Subscription Name
def get_subscription_name(subscription_id, token):
    url = f"{BASE_URL}/subscriptions/{subscription_id}/?api-version=2020-01-01"
    return fetch_azure_data(url, token).get("displayName", "Unknown Subscription")


# Fetching Cost
async def get_cost_data(access_token, start_date, end_date, subscription_id, query="query"):
    url = f"{BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/{query}?api-version=2021-10-01"

    payload = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start_date, "to": end_date},
        "dataset": {
            "granularity": "Monthly",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "sorting": [{"direction": "ascending", "name": "UsageDate"}],
        },
    }

    if query == "forecast":
        payload["includeActualCost"] = True
        payload["includeFreshPartialCost"] = True

    return fetch_azure_data(url, access_token, payload)
