from calendar import monthrange
from datetime import datetime, timedelta, timezone
from src.services.azure_billing import get_billing_period


# Returns YYYY-MM-DD
def format_date(date):
    return date.strftime("%Y-%m-%d")


def format_currency(value, currency_symbol="$"):
    """
    Format a number into a currency format with commas and two decimal places.

    Example:
    - 1425.20 -> "1,425.20"
    - 9876543.5 -> "9,876,543.50"
    """
    try:
        value = float(value)
        formatted_value = f"{value:,.2f}"
        return f"{currency_symbol}{formatted_value}"
    except ValueError:
        return value


async def get_forecast_month_date(subscription_id: str):
    """
    Fetch the billing start day and adjust it for the current month.

    :param subscription_id: Azure Subscription ID
    :return: Tuple containing first_day and last_day
    """
    last_billing_start_day, _ = get_billing_period(subscription_id)

    start_date = datetime.strptime(last_billing_start_day, "%Y-%m-%d")
    today = datetime.now(timezone.utc)

    if today.day >= start_date.day:
        first_day = today.replace(day=start_date.day)
        last_day = (first_day + timedelta(days=32)).replace(day=start_date.day) - timedelta(days=1)
    else:
        first_day = (today.replace(day=start_date.day) - timedelta(days=32)).replace(day=start_date.day)
        last_day = today.replace(day=start_date.day) - timedelta(days=1)

    return first_day, last_day


def calculate_cost(cost_data):
    total_cost = sum(
        item[0]
        for item in cost_data.get("properties", {}).get("rows", [])
        if isinstance(item[0], (int, float))
    )
    return total_cost


def get_cost_breakdown(cost_data):
    breakdown = []
    total_cost = 0.0

    rows = cost_data.get("properties", {}).get("rows", [])
    sorted_rows = sorted(rows, key=lambda x: float(x[0]), reverse=True)

    for item in sorted_rows:
        # Ensure proper unpacking and handle missing service names
        if len(item) < 4:
            continue

        cost, _, service_name, currency = item[:4]
        total_cost += cost if isinstance(cost, (int, float)) else 0

        breakdown.append({"service": service_name, "cost": format_currency(cost), "currency": currency})

    return breakdown, format_currency(total_cost)
