from datetime import datetime, timezone, timedelta
from src.services.notifications import send_notification
from src.config import SUBSCRIPTIONS
from src.utils.utils import format_currency, get_forecast_date, calculate_cost
from src.services.azure_auth import get_access_token
from src.services.azure_cost import get_subscription_name, get_cost_data
from src.services.html_renderer import render_html_report
from src.services.email_service import preview_email
from src.utils.logger import logger


def main():
    try:
        token = get_access_token()
        today = datetime.now(timezone.utc)

        for subscription_id, details in SUBSCRIPTIONS.items():
            subscription_name = get_subscription_name(subscription_id, token)

            daily_date = (today - timedelta(days=2))
            # Fetching Daily cost (Today - 2)
            daily_cost_data = get_cost_data(token, daily_date, daily_date, subscription_id)

            billing_from = details["billing_start"]
            first_day, last_day = get_forecast_date(billing_from)

            # Fetch Monthly Forecast
            forecast_month_data = get_cost_data(token, first_day, last_day, subscription_id, "forecast", "Usage")
            forecast_month_cost = calculate_cost(forecast_month_data)

            actual_month_data = get_cost_data(token, first_day, last_day, subscription_id)
            actual_month_cost = calculate_cost(actual_month_data)

            monthly_forecast = format_currency(forecast_month_cost + actual_month_cost)
            print(f"🔹 Forecasted Cost for {subscription_name} (Feb):")
            print(f"✅ Total Forecast for {first_day.strftime('%B')} {first_day.day} To {last_day.strftime('%B')} {last_day.day}: {monthly_forecast}\n")

            # Generate Email content
            email_html = render_html_report(daily_date, daily_cost_data, first_day, last_day, monthly_forecast, subscription_name)
            preview_email(email_html)

            send_notification("Cost Report", email_html)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
