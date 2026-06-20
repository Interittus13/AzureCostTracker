import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from src.main import get_report_data
from src.services.html_renderer import render_html_report, export_html_to_pdf
from src.services.email_service import send_email_notification
from src.services.webhook_service import send_webhook_notification
from src.utils.logger import logger

app = FastAPI(title="Azure Cost Tracker Dashboard")

# Thread-safe in-memory cache to avoid slamming APIs
_cached_data = None
_cache_lock = asyncio.Lock()

def send_email_with_pdf_task(subject, data, pdf_path):
    """Background task to compile HTML to PDF and send it as an email attachment."""
    try:
        logger.info(f"Generating PDF attachment in background at {pdf_path}...")
        email_html = render_html_report(data, is_server_mode=False, is_pdf_mode=False)
        pdf_html = render_html_report(data, is_server_mode=False, is_pdf_mode=True)
        export_html_to_pdf(pdf_html, pdf_path)
        send_email_notification(subject, email_html, attachments=[pdf_path])
    except Exception as err:
        logger.error(f"Failed to generate/attach PDF in background task: {err}")
        email_html = render_html_report(data, is_server_mode=False, is_pdf_mode=False)
        send_email_notification(subject, email_html)

async def get_cached_report_data(force_refresh=False):
    global _cached_data
    async with _cache_lock:
        if _cached_data is None or force_refresh:
            logger.info("Fetching fresh report data...")
            _cached_data = await get_report_data()
        return _cached_data

@app.get("/", response_class=HTMLResponse)
async def read_dashboard():
    try:
        data = await get_cached_report_data()
        # Render HTML report passing is_server_mode=True
        html_content = render_html_report(data, is_server_mode=True)
        return html_content
    except Exception as e:
        logger.exception(f"Error rendering dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to render dashboard: {str(e)}")

@app.get("/api/costs")
async def get_costs():
    try:
        data = await get_cached_report_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
async def refresh_costs():
    try:
        data = await get_cached_report_data(force_refresh=True)
        return {"status": "success", "message": "Cost data refreshed successfully", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notify/email")
async def trigger_email(background_tasks: BackgroundTasks):
    try:
        data = await get_cached_report_data()
        pdf_path = "output/azure_cost_report.pdf"
        background_tasks.add_task(send_email_with_pdf_task, "Azure Cost Report", data, pdf_path)
        return {"status": "success", "message": "Email notification with PDF attachment triggered in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notify/webhook")
async def trigger_webhook(background_tasks: BackgroundTasks):
    try:
        data = await get_cached_report_data()
        background_tasks.add_task(send_webhook_notification, data)
        return {"status": "success", "message": "Webhook notification triggered in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
