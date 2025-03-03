from datetime import datetime, timedelta, timezone
from src.services.azure_billing import get_billing_period


# Returns YYYY-MM-DD
def format_date(date):
    return date.strftime("%Y-%m-%d")


def format_currency(value, currency_symbol="$"):
    """
    Format a number into a currency format with commas and two decimal places.

    Example:
    - 1425.20 -> "$1,425.20"
    - 98543.5 -> "$98,543.50"
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
    :return: Tuple containing (first_day, last_day)
    """
    today = datetime.now()
    yesterday = today - timedelta(days=2) # today - 2 for fetching daily cost

    last_billing_start_day, _ = get_billing_period(subscription_id)

    # If API returns None, assume billing starts on 1st of month
    start_day = datetime.strptime(last_billing_start_day, "%Y-%m-%d").day if last_billing_start_day else 1

    month_starts_on = today.replace(day=start_day) if today.day >= start_day else (today - timedelta(days=today.day)).replace(day=start_day)
    month_ends_on = (month_starts_on + timedelta(days=32)).replace(day=start_day) - timedelta(days=1)

    year_starts_on = datetime(today.year, 1, start_day) if today >= datetime(today.year, 1, start_day) else datetime(today.year - 1, 1, start_day)
    year_ends_on = datetime(year_starts_on.year + 1, 1, start_day) - timedelta(days=1)

    return {
        "today": today.strftime('%Y-%m-%d'),
        "yesterday": yesterday.strftime('%Y-%m-%d'),
        "month_starts_on": month_starts_on.strftime('%Y-%m-%d'),
        "month_ends_on": month_ends_on.strftime('%Y-%m-%d'),
        "year_starts_on": year_starts_on.strftime("%Y-%m-%d"),
        "year_ends_on": year_ends_on.strftime("%Y-%m-%d"),
    }


def calculate_cost(data):
    total_cost = sum(
        item[0]
        for item in data.get("properties", {}).get("rows", [])
        if isinstance(item[0], (int, float))
    )
    return round(total_cost, 2)


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

        breakdown.append(
            {
                "service": service_name,
                "cost": format_currency(cost),
                "currency": currency,
            }
        )

    return breakdown, format_currency(total_cost)
