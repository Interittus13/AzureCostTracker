import requests
from src.config import BASE_URL
from src.utils.utils import format_date

def fetch_azure_data(url, token, payload=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload) if payload else requests.get(url, headers=headers)

    if response.status_code >= 400:
        print(f"Error {response.status_code}: {response.json()}")

    response.raise_for_status()
    return response.json()

# Fetching Azure Subscription Name
def get_subscription_name(subscription_id, token):
    url = f"{BASE_URL}/subscriptions/{subscription_id}/?api-version=2020-01-01"
    return fetch_azure_data(url, token).get("displayName", "Unknown Subscription")

# Fetching Cost
def get_cost_data(access_token, start_date, end_date, subscription_id, query="query"):
    url = f"{BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/{query}?api-version=2021-10-01"

    payload = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": format_date(start_date), "to": format_date(end_date)},
        "dataset": {
            "granularity": "Daily",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ServiceName"}],
        },
    }

    if query == "forecast":
        payload["includeActualCost"] =  True
        payload["includeFreshPartialCost"] =  True
  
    return fetch_azure_data(url, access_token, payload)
