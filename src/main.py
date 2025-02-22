import asyncio
from datetime import datetime, timezone, timedelta
from src.config import NOTIFY_METHOD, SUBSCRIPTIONS
from src.services.webhook_service import send_webhook_notification
from src.services.email_service import send_email_notification, preview_email
from src.utils.utils import format_currency, calculate_cost, get_cost_breakdown, get_forecast_month_date
from src.services.azure_auth import get_access_token
from src.services.azure_cost import get_subscription_name, get_cost_data
from src.services.html_renderer import render_html_report, render_html_summary
from src.utils.logger import logger


async def process_subscription(subscription_id, token, today):
    """Process cost calculations and returns data for reporting."""
    try:
        subscription_name = get_subscription_name(subscription_id, token)

        # Fetch Daily cost (Today - 2)
        daily_date = today - timedelta(days=2)
        # Fetch Forecasting Period
        first_day, last_day = await get_forecast_month_date(subscription_id)
        
        # Fetch Daily costing and Monthly Forecast
        daily_cost_data = get_cost_data(token, daily_date, daily_date, subscription_id)
        monthly_forecast_data = get_cost_data(token, first_day, last_day, subscription_id, "forecast")

        daily_table, daily_total = get_cost_breakdown(daily_cost_data)
        monthly_forecast = format_currency(calculate_cost(monthly_forecast_data))

        print(f"✅ Daily Cost for {subscription_name}: {calculate_cost(daily_cost_data)}")
        print(f"✅ Forecasted Cost for {subscription_name}: {monthly_forecast}")


        return {
            "subscription_name": subscription_name,
            "daily_date": daily_date.strftime("%B %d %Y"),
            "first_day_of_month": first_day.strftime("%B %d %Y"),
            "last_day_of_month": last_day.strftime("%B %d %Y"),
            "daily_table": daily_table,
            "daily_total": daily_total,
            "monthly_forecast": monthly_forecast,
        }
    except Exception as e:
        logger.exception(f"Error processing subscription {subscription_id}: {str(e)}")

async def main():
    try:
        token = get_access_token()
        today = datetime.now(timezone.utc)
        subscription_data = []

        # Process all subscriptions asynchronously
        tasks = [process_subscription(subscription_id.strip(), token, today) for subscription_id in SUBSCRIPTIONS]
        results = await asyncio.gather(*tasks)

        # Collect only successful results
        subscription_data = [res for res in results if res]

        if subscription_data:
            # Generate Email content
            email_html = render_html_report(subscription_data)
            summary = render_html_summary(subscription_data)

            if NOTIFY_METHOD in ["email", "both"]:
                send_email_notification("Azure Cost Report", summary, email_html)
            
            if NOTIFY_METHOD in ["webhook", "both"]:
                send_webhook_notification(email_html)

            preview_email(email_html)
        else:
            logger.warning("No data available to generate the report.")
    except Exception as e:
        logger.exception(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
