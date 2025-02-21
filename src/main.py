import asyncio
from datetime import datetime, timezone, timedelta
from src.services.notifications import send_notification
from src.config import SUBSCRIPTIONS
from src.utils.utils import format_currency, calculate_cost, get_forecast_month_date
from src.services.azure_auth import get_access_token, remove_token
from src.services.azure_cost import get_subscription_name, get_cost_data
from src.services.html_renderer import render_html_report
from src.services.email_service import preview_email
from src.utils.logger import logger


async def process_subscription(subscription_id, token, today):
    """Process cost calculations"""
    try:
        subscription_name = get_subscription_name(subscription_id, token)

        # Fetch Daily cost (Today - 2)
        daily_date = today - timedelta(days=2)
        daily_cost_data = get_cost_data(token, daily_date, daily_date, subscription_id)

        # Fetch Forecasting Period
        first_day, last_day = await get_forecast_month_date(subscription_id)

        # Fetch Forecast and Actual costs
        monthly_forecast_data = get_cost_data(token, first_day, last_day, subscription_id, "forecast")
        monthly_forecast = format_currency(calculate_cost(monthly_forecast_data))

        print(f"✅ Daily Cost for {subscription_name}: {calculate_cost(daily_cost_data)}")
        print(f"✅ Forecasted Cost for {subscription_name}: {monthly_forecast}")

        # Generate Email content
        email_html = render_html_report(daily_date, daily_cost_data, first_day, last_day, monthly_forecast, subscription_name)
        preview_email(email_html)
        send_notification("Cost Report", email_html)
    except Exception as e:
        logger.exception(f"Error processing subscription {subscription_id}: {str(e)}")

async def main():
    try:
        token = get_access_token()
        today = datetime.now(timezone.utc)

        for subscription_id in SUBSCRIPTIONS:
            await process_subscription(subscription_id.strip(), token, today)
    except Exception as e:
        logger.error(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
