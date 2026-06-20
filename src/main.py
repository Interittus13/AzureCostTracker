import argparse
import asyncio
import os
import sys
from src.config import NOTIFY_METHOD, SUBSCRIPTIONS
from src.services.webhook_service import send_webhook_notification
from src.services.email_service import send_email_notification
from src.utils.utils import (calculate_cost, get_forecast_month_date, get_cost_breakdown, get_currency_symbol)
from src.services.azure_auth import get_access_token
from src.services.azure_cost import get_subscription_name, get_cost_data
from src.services.report import PdfExporter, ReportMode, ReportRenderer
from src.services.html_renderer import preview_email
from src.utils.logger import logger

_renderer = ReportRenderer()
_pdf_exporter = PdfExporter()


async def process_subscription(subscription_id, token):
    """Process cost calculations and returns data for reporting."""
    try:
        subscription_name = await get_subscription_name(subscription_id, token)

        dates = await get_forecast_month_date(subscription_id)

        # Fetch all cost data concurrently
        daily_cost_data, mtd_data, ytd_data, month_forecast_data, year_forecast_data = await asyncio.gather(
            get_cost_data(token, dates["yesterday"], dates["yesterday"], subscription_id),
            get_cost_data(token, dates["month_starts_on"], dates["today"], subscription_id),
            get_cost_data(token, dates["year_starts_on"], dates["today"], subscription_id),
            get_cost_data(token, dates["month_starts_on"], dates["month_ends_on"], subscription_id, "forecast"),
            get_cost_data(token, dates["year_starts_on"], dates["year_ends_on"], subscription_id, "forecast")
        )

        service_breakdown, _ = get_cost_breakdown(mtd_data)

        # Retrieve currency details
        rows = mtd_data.get("properties", {}).get("rows", [])
        currency_code = "USD"
        if rows and len(rows[0]) >= 4:
            currency_code = rows[0][3] or "USD"
        currency_symbol = get_currency_symbol(currency_code)

        return {
                "subscription_name": subscription_name,
                "daily_cost": calculate_cost(daily_cost_data),
                "month_to_day": calculate_cost(mtd_data),
                "month_forecast": calculate_cost(month_forecast_data),
                "year_to_day": calculate_cost(ytd_data),
                "year_forecast": calculate_cost(year_forecast_data),
                "service_breakdown": service_breakdown,
                "dates": dates,
                "currency_code": currency_code,
                "currency_symbol": currency_symbol
        }

    except Exception as e:
        logger.exception(f"Error processing subscription {subscription_id}: {str(e)}")


async def get_report_data():
    """Fetches all subscription cost reports concurrently and aggregates them."""
    token = get_access_token()
    tasks = [process_subscription(sub_id.strip(), token) for sub_id in SUBSCRIPTIONS]
    subscription_data = [res for res in await asyncio.gather(*tasks) if res]
    subscription_data.sort(key=lambda entry: entry.get("subscription_name", ""))

    if not subscription_data:
        raise ValueError("No data available to generate the report.")

    final_data = {
        "subscriptions": subscription_data,
        "report_for": subscription_data[0].get('dates', {}).get('yesterday'),
        "report_generated_on": subscription_data[0].get('dates', {}).get('today'),
        "currency_code": subscription_data[0].get('currency_code', 'USD'),
        "currency_symbol": subscription_data[0].get('currency_symbol', '$')
    }
    return final_data


async def main(preview=False):
    pdf_path = None
    try:
        final_data = await get_report_data()
        report_html = _renderer.render(final_data, mode=ReportMode.STATIC)

        if preview:
            preview_email(report_html)

        if NOTIFY_METHOD in ["email", "both"]:
            pdf_path = _pdf_exporter.create_temp_path()
            try:
                logger.info(f"Generating PDF report at {pdf_path}...")
                _pdf_exporter.export(report_html, pdf_path)
                send_email_notification("Azure Cost Report", report_html, attachments=[pdf_path])
            except Exception as pdf_err:
                logger.error(f"Failed to generate PDF report: {pdf_err}")
                raise RuntimeError(f"PDF generation failed: {pdf_err}") from pdf_err

        if NOTIFY_METHOD in ["webhook", "both"]:
            send_webhook_notification(final_data)

    except Exception as e:
        logger.exception(f"Error in main execution: {e}")
        sys.exit(1)
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError as cleanup_err:
                logger.warning(f"Failed to remove temp PDF {pdf_path}: {cleanup_err}")


def run():
    parser = argparse.ArgumentParser(description="Azure Cost Tracker Utility")
    parser.add_argument("--server", action="store_true", help="Start the FastAPI interactive dashboard server")
    parser.add_argument("--preview", action="store_true", help="Generate report, write locally, and open in browser")
    args = parser.parse_args()

    if args.server:
        import uvicorn
        logger.info("Starting FastAPI interactive dashboard server...")
        uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
    else:
        asyncio.run(main(preview=args.preview))


if __name__ == "__main__":
    run()
