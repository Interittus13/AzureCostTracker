import argparse
import asyncio
import os
import sys
from src.config import COST_SCOPE, MANAGEMENT_GROUP_ID, NOTIFY_METHOD, SUBSCRIPTIONS
from src.services.webhook_service import send_webhook_notification
from src.services.email_service import send_email_notification
from src.utils.utils import get_currency_symbol, get_forecast_month_date
from src.services.azure_auth import get_access_token
from src.services.azure_cost import get_subscription_name, get_cost_data
from src.services.cost_aggregator import derive_forecast_metrics, derive_metrics_from_daily_rows
from src.services.azure_cost_scope import get_management_group_report_entries
from src.services.report import PdfExporter, ReportMode, ReportRenderer
from src.services.html_renderer import preview_email
from src.utils.logger import logger

_renderer = ReportRenderer()
_pdf_exporter = PdfExporter()


async def process_subscription(subscription_id, token):
    """Process cost calculations and returns data for reporting."""
    try:
        subscription_name = await get_subscription_name(subscription_id, token)
        dates = await get_forecast_month_date(subscription_id, token)

        actual_data = await get_cost_data(
            token,
            dates["year_starts_on"],
            dates["today"],
            subscription_id,
            query="query",
            granularity="Daily",
        )
        forecast_data = await get_cost_data(
            token,
            dates["year_starts_on"],
            dates["year_ends_on"],
            subscription_id,
            query="forecast",
            granularity="Daily",
        )

        actual_rows = actual_data.get("properties", {}).get("rows", [])
        forecast_rows = forecast_data.get("properties", {}).get("rows", [])
        metrics = derive_metrics_from_daily_rows(actual_rows, dates)
        forecast_metrics = derive_forecast_metrics(forecast_rows, dates)
        currency_symbol = get_currency_symbol(metrics["currency_code"])

        return {
            "subscription_name": subscription_name,
            "daily_cost": metrics["daily_cost"],
            "month_to_day": metrics["month_to_day"],
            "month_forecast": forecast_metrics["month_forecast"],
            "year_to_day": metrics["year_to_day"],
            "year_forecast": forecast_metrics["year_forecast"],
            "service_breakdown": metrics["service_breakdown"],
            "dates": dates,
            "currency_code": metrics["currency_code"],
            "currency_symbol": currency_symbol,
        }

    except Exception as e:
        logger.exception(f"Error processing subscription {subscription_id}: {str(e)}")


async def get_report_data():
    """Fetches all subscription cost reports with consolidated queries and throttling."""
    token = get_access_token()

    if COST_SCOPE == "managementgroup":
        if not MANAGEMENT_GROUP_ID:
            raise ValueError("MANAGEMENT_GROUP_ID must be set when COST_SCOPE=managementGroup")
        subscription_data, dates = await get_management_group_report_entries(token, SUBSCRIPTIONS)
    else:
        subscription_data = []
        for sub_id in SUBSCRIPTIONS:
            result = await process_subscription(sub_id.strip(), token)
            if result:
                subscription_data.append(result)
        dates = subscription_data[0].get("dates") if subscription_data else {}

    subscription_data.sort(key=lambda entry: entry.get("subscription_name", ""))

    if not subscription_data:
        raise ValueError("No data available to generate the report.")

    final_data = {
        "subscriptions": subscription_data,
        "report_for": dates.get("yesterday"),
        "report_generated_on": dates.get("today"),
        "currency_code": subscription_data[0].get("currency_code", "USD"),
        "currency_symbol": subscription_data[0].get("currency_symbol", "$"),
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
