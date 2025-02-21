import requests
from config import BASE_URL
from src.services.azure_auth import get_access_token
from src.utils.logger import logger


def get_billing_period(subscription_id):
    """Fetch the billing period from Azure API for a specific subscription."""
    access_token = get_access_token()

    url = f"{BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.Billing/billingPeriods?api-version=2018-03-01-preview"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200 and len(response.json()["value"]):
        data = response.json()
        latest_billing_period = data.get("value", [])[0]  # Get the most recent billing period
        start_date = latest_billing_period["properties"]["billingPeriodStartDate"]
        end_date = latest_billing_period["properties"]["billingPeriodEndDate"]
        return start_date, end_date
    
    logger.error(f"Error fetching billing period: {response.status_code}, {response.text}")
    return None, None