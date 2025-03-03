import asyncio
from tkinter import NO
from src.config import NOTIFY_METHOD, SHOW_DAILYCOST_BREAKDOWN, SUBSCRIPTIONS
from src.services.webhook_service import send_webhook_notification
from src.services.email_service import send_email_notification, preview_email
from src.utils.utils import (
    calculate_cost,
    format_currency,
    get_cost_breakdown,
    get_forecast_month_date,
)
from src.services.azure_auth import get_access_token
from src.services.azure_cost import get_subscription_name, get_cost_data
from src.services.html_renderer import render_html_report
from src.utils.logger import logger


async def process_subscription(subscription_id, token):
    """Process cost calculations and returns data for reporting."""
    try:
        subscription_name = get_subscription_name(subscription_id, token)

        dates = await get_forecast_month_date(subscription_id)

        # Fetch Daily costing and Monthly Forecast
        daily_cost_data = get_cost_data(token, dates["yesterday"], dates["yesterday"], subscription_id)
        month_to_date = get_cost_data(token, dates["month_starts_on"], dates["today"], subscription_id)
        year_to_date = get_cost_data(token, dates["year_starts_on"], dates["today"], subscription_id)
        month_forecast_data = get_cost_data(token, dates["month_starts_on"], dates["month_ends_on"], subscription_id, "forecast")
        year_forecast_data = get_cost_data(token, dates["year_starts_on"], dates["year_ends_on"], subscription_id, "forecast")

        daily_cost = calculate_cost(daily_cost_data)
        mtd_cost = calculate_cost(month_to_date)
        ytd_cost = calculate_cost(year_to_date)
        month_forecast = calculate_cost(month_forecast_data)
        year_forecast = calculate_cost(year_forecast_data)

        return {
                "subscription_name": subscription_name,
                "daily_cost": daily_cost,
                "month_to_day": mtd_cost,
                "month_forecast": month_forecast,
                "year_to_day": ytd_cost,
                "year_forecast": year_forecast,
        }

        # if SHOW_DAILYCOST_BREAKDOWN:
        #     result["daily_table"] = daily_table
    except Exception as e:
        logger.exception(f"Error processing subscription {subscription_id}: {str(e)}")


async def main():
    try:
        subscription_data = []
        token = get_access_token()
        # token = "223554444585954864864654687646468468"

        # Process all subscriptions asynchronously
        tasks = [process_subscription(sub_id.strip(), token) for sub_id in SUBSCRIPTIONS]
        subscription_data = [res for res in await asyncio.gather(*tasks) if res]

        # for sub_id in SUBSCRIPTIONS:
        #     result = {
        #         "total": [
        #             {"daily": "$550"},
        #             {"month_to_day": "$5459"},
        #             {"year_to_day": "$5555"},
        #         ],
        #         "subscriptions": [
        #             {
        #                 "subscription_name": "Production",
        #                 "daily_cost": 242,
        #                 "month_to_day": 1420
        #             },
        #             {
        #                 "subscription_name": "Non-Production",
        #                 "daily_cost": 100,
        #                 "month_to_day": 1000
        #             }
        #         ],
        #     }

        # if not subscription_data:
        #     logger.warning("No data available to generate the report.")
        #     return

        # total_daily_cost = sum(sub["daily_total"] for sub in subscription_list)
        # total_monthly_forecast = sum(sub["monthly_forecast"] for sub in subscription_list)

        # Generate Summary
        final_data = {
            "total": [
                {"daily": 550},
                {"month_to_day": 5420},
                {"year_to_day": 5420}
            ],
            "subscriptions": subscription_data,
            # "report_generated_on": datetime.now().strftime("%B %d, %Y")
        }
        # Generate Email content
        # print(final_data)
        email_html = render_html_report(final_data)
        preview_email(email_html)

        # if NOTIFY_METHOD in ["email", "both"]:
        #     send_email_notification("Azure Cost Report", email_html)

        # if NOTIFY_METHOD in ["webhook", "both"]:
        #     send_webhook_notification(email_html)

    except Exception as e:
        logger.exception(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
