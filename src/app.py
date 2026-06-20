import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from src.main import get_report_data
from src.services.report import PdfExporter, ReportMode, ReportRenderer
from src.services.email_service import send_email_notification
from src.services.webhook_service import send_webhook_notification
from src.utils.logger import logger

app = FastAPI(title="Azure Cost Tracker Dashboard")

_renderer = ReportRenderer()
_pdf_exporter = PdfExporter()

# Thread-safe in-memory cache to avoid slamming APIs
_cached_data = None
_cache_lock = asyncio.Lock()
_email_task_status = {"last_error": None, "last_success": None}


def send_email_with_pdf_task(subject, data):
    """Background task: render once, export PDF, and email both."""
    pdf_path = None
    try:
        report_html = _renderer.render(data, mode=ReportMode.STATIC)
        pdf_path = _pdf_exporter.create_temp_path()
        _pdf_exporter.export(report_html, pdf_path)
        send_email_notification(subject, report_html, attachments=[pdf_path])
        _email_task_status["last_error"] = None
        _email_task_status["last_success"] = "Email sent with PDF attachment"
        logger.info("Email with PDF attachment sent successfully")
    except Exception as err:
        _email_task_status["last_error"] = str(err)
        logger.exception(f"Failed to send email with PDF: {err}")
        raise
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError as cleanup_err:
                logger.warning(f"Failed to remove temp PDF {pdf_path}: {cleanup_err}")


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
        html_content = _renderer.render(data, mode=ReportMode.INTERACTIVE)
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
        data = await get_cached_report_data(force_refresh=True)
        background_tasks.add_task(send_email_with_pdf_task, "Azure Cost Report", data)
        return {"status": "success", "message": "Email notification with PDF attachment triggered in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notify/webhook")
async def trigger_webhook(background_tasks: BackgroundTasks):
    try:
        data = await get_cached_report_data(force_refresh=True)
        background_tasks.add_task(send_webhook_notification, data)
        return {"status": "success", "message": "Webhook notification triggered in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/pdf")
async def download_pdf():
    pdf_path = None
    try:
        data = await get_cached_report_data(force_refresh=True)
        report_html = _renderer.render(data, mode=ReportMode.STATIC)
        pdf_path = _pdf_exporter.create_temp_path()
        _pdf_exporter.export(report_html, pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="azure_cost_report.pdf",
            background=None,
        )
    except Exception as e:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass
        logger.exception(f"Error generating PDF for download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
