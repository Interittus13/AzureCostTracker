import time
import requests
from datetime import datetime

from src.config import BASE_URL, BILLING_START_DAY, MOCK_AZURE
from src.utils.logger import logger

_billing_period_cache = {}
_BILLING_CACHE_TTL_SEC = 24 * 60 * 60


def get_billing_period(subscription_id, access_token=None):
    """Fetch billing period start/end for a subscription, with in-memory cache."""
    if BILLING_START_DAY is not None:
        today = datetime.now()
        start_date = today.replace(day=BILLING_START_DAY).strftime("%Y-%m-%d")
        end_date = (today.replace(day=28) + __import__("datetime").timedelta(days=4)).replace(day=1)
        end_date = (end_date - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d")
        return start_date, end_date

    if MOCK_AZURE:
        today = datetime.now()
        start_date = f"{today.year}-{today.month:02d}-01"
        end_date = f"{today.year}-{today.month:02d}-28"
        return start_date, end_date

    cached = _billing_period_cache.get(subscription_id)
    if cached and (time.time() - cached["fetched_at"]) < _BILLING_CACHE_TTL_SEC:
        return cached["start_date"], cached["end_date"]

    if not access_token:
        from src.services.azure_auth import get_access_token
        access_token = get_access_token()

    url = (
        f"{BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.Billing/"
        f"billingPeriods?api-version=2018-03-01-preview"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        periods = response.json().get("value", [])
        if periods:
            latest = periods[0]
            start_date = latest["properties"]["billingPeriodStartDate"]
            end_date = latest["properties"]["billingPeriodEndDate"]
            _billing_period_cache[subscription_id] = {
                "start_date": start_date,
                "end_date": end_date,
                "fetched_at": time.time(),
            }
            return start_date, end_date
        logger.info(
            f"No billing periods returned for subscription {subscription_id}; using calendar month."
        )
    else:
        logger.warning(
            f"Billing period request failed for subscription {subscription_id}: "
            f"{response.status_code}, {response.text}"
        )

    return None, None
