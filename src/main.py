import asyncio
from src.config import NOTIFY_METHOD, SUBSCRIPTIONS
from src.services.webhook_service import send_webhook_notification
from src.services.email_service import send_email_notification, preview_email
from src.utils.utils import (calculate_cost, get_forecast_month_date)
from src.services.azure_auth import get_access_token
from src.services.azure_cost import get_subscription_name, get_cost_data
from src.services.html_renderer import render_html_report
from src.utils.logger import logger


async def process_subscription(subscription_id, token):
    """Process cost calculations and returns data for reporting."""
    try:
        subscription_name = get_subscription_name(subscription_id, token)

        dates = await get_forecast_month_date(subscription_id)

        # Fetch all cost data concurrently
        daily_cost_data, mtd_data, ytd_data, month_forecast_data, year_forecast_data = await asyncio.gather(
            get_cost_data(token, dates["yesterday"], dates["yesterday"], subscription_id),
            get_cost_data(token, dates["month_starts_on"], dates["today"], subscription_id),
            get_cost_data(token, dates["year_starts_on"], dates["today"], subscription_id),
            get_cost_data(token, dates["month_starts_on"], dates["month_ends_on"], subscription_id, "forecast"),
            get_cost_data(token, dates["year_starts_on"], dates["year_ends_on"], subscription_id, "forecast")
        )

        return {
                "subscription_name": subscription_name,
                "daily_cost": calculate_cost(daily_cost_data),
                "month_to_day": calculate_cost(mtd_data),
                "month_forecast": calculate_cost(month_forecast_data),
                "year_to_day": calculate_cost(ytd_data),
                "year_forecast": calculate_cost(year_forecast_data),
                "dates": dates
        }

    except Exception as e:
        logger.exception(f"Error processing subscription {subscription_id}: {str(e)}")


async def main():
    try:
        subscription_data = []
        token = get_access_token()

        # Process all subscriptions asynchronously
        tasks = [process_subscription(sub_id.strip(), token) for sub_id in SUBSCRIPTIONS]
        subscription_data = [res for res in await asyncio.gather(*tasks) if res]

        # if not subscription_data:
        #     logger.warning("No data available to generate the report.")
        #     return

        # Generate Summary
        final_data = {
            "subscriptions": subscription_data,
            "report_for": subscription_data[0].get('dates', {}).get('yesterday'),
            "report_generated_on": subscription_data[0].get('dates', {}).get('today')
        }

        email_html = render_html_report(final_data)
        preview_email(email_html)

        if NOTIFY_METHOD in ["email", "both"]:
            send_email_notification("Azure Cost Report", email_html)

        if NOTIFY_METHOD in ["webhook", "both"]:
            send_webhook_notification(email_html)

    except Exception as e:
        logger.exception(f"Error in main execution: {e}")

def run():
    asyncio.run(main())

if __name__ == "__main__":
    run()
