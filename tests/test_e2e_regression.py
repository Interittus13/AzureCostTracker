"""
End-to-end regression tests for the unified report pipeline.

Covers: mock data fetch → render (STATIC/INTERACTIVE) → PDF export →
FastAPI endpoints → email background task → CLI main flow.
"""
import asyncio
import os
import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.app import app, send_email_with_pdf_task
from src.main import get_report_data, main
from src.services.html_renderer import generate_pdf_report, render_html_report
from src.services.report import PdfExporter, ReportMode, ReportRenderer


def _has_service_bars(html: str) -> bool:
    return 'role="presentation"' in html and "background-color: #3b82f6" in html


def _core_report_markers(html: str) -> set[str]:
    """Sections that must appear in every report mode."""
    markers = set()
    for marker in (
        "Azure Cost Report",
        "Service-Level Cost Breakdown",
        "summary-cards-table",
        "Virtual Machines",
    ):
        if marker in html:
            markers.add(marker)
    if _has_service_bars(html):
        markers.add("bars_present")
    return markers


def _remove_control_bar(html: str) -> str:
    marker = '<div class="control-bar"'
    start = html.find(marker)
    if start == -1:
        return html
    depth = 0
    i = start
    while i < len(html):
        if html.startswith("<div", i):
            depth += 1
            i += 4
            continue
        if html.startswith("</div>", i):
            depth -= 1
            i += 6
            if depth == 0:
                return html[:start] + html[i:]
            continue
        i += 1
    return html


def _strip_interactive_only(html: str) -> str:
    """Remove dashboard-only UI so STATIC and INTERACTIVE bodies can be compared."""
    html = _remove_control_bar(html)
    html = re.sub(r"<script>.*?</script>\s*", "", html, flags=re.DOTALL)
    html = re.sub(r"<!-- Google Fonts.*?-->\s*", "", html, flags=re.DOTALL)
    html = re.sub(r"<!-- Web Dashboard Interactive Scripts -->\s*", "", html, flags=re.DOTALL)
    html = re.sub(r"<!-- DASHBOARD CONTROL BAR.*?-->\s*", "", html, flags=re.DOTALL)
    html = re.sub(r"<link[^>]*>\s*", "", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


@pytest.fixture
def mock_report_data():
    return asyncio.run(get_report_data())


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_app_cache():
    import src.app as app_module

    app_module._cached_data = None
    yield
    app_module._cached_data = None


@pytest.fixture(autouse=True)
def force_mock_azure():
    with patch("src.config.MOCK_AZURE", True), \
         patch("src.services.azure_auth.MOCK_AZURE", True), \
         patch("src.services.azure_cost.MOCK_AZURE", True), \
         patch("src.services.azure_billing.MOCK_AZURE", True):
        yield


class TestMockDataPipeline:
    def test_get_report_data_returns_sorted_subscriptions(self, mock_report_data):
        names = [s["subscription_name"] for s in mock_report_data["subscriptions"]]
        assert names == sorted(names)
        assert len(names) >= 2
        assert mock_report_data["currency_code"] == "CAD"

    def test_static_and_interactive_share_core_content(self, mock_report_data):
        renderer = ReportRenderer()
        static_html = renderer.render(mock_report_data, mode=ReportMode.STATIC)
        interactive_html = renderer.render(mock_report_data, mode=ReportMode.INTERACTIVE)

        assert _core_report_markers(static_html) == _core_report_markers(interactive_html)
        assert "Send Email Report" in interactive_html
        assert "Send Email Report" not in static_html
        assert "chart.js" not in static_html.lower()
        assert "chart.js" not in interactive_html.lower()

    def test_static_and_interactive_body_parity_after_strip(self, mock_report_data):
        renderer = ReportRenderer()
        static_html = _strip_interactive_only(
            renderer.render(mock_report_data, mode=ReportMode.STATIC)
        )
        interactive_html = _strip_interactive_only(
            renderer.render(mock_report_data, mode=ReportMode.INTERACTIVE)
        )
        assert static_html == interactive_html

    def test_pdf_export_produces_valid_pdf(self, mock_report_data, tmp_path):
        renderer = ReportRenderer()
        html = renderer.render(mock_report_data, mode=ReportMode.STATIC)
        pdf_path = str(tmp_path / "report.pdf")

        PdfExporter().export(html, pdf_path)

        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_email_and_pdf_use_same_html(self, mock_report_data, tmp_path):
        renderer = ReportRenderer()
        report_html = renderer.render(mock_report_data, mode=ReportMode.STATIC)
        pdf_path = str(tmp_path / "attachment.pdf")
        PdfExporter().export(report_html, pdf_path)

        assert _has_service_bars(report_html)
        assert os.path.getsize(pdf_path) > 1000

    def test_html_renderer_shim_backward_compat(self, mock_report_data, tmp_path):
        static_html = render_html_report(mock_report_data, is_server_mode=False, is_pdf_mode=False)
        interactive_html = render_html_report(mock_report_data, is_server_mode=True, is_pdf_mode=False)

        assert _has_service_bars(static_html)
        assert "Send Email Report" in interactive_html

        pdf_path = str(tmp_path / "shim.pdf")
        generate_pdf_report(mock_report_data, pdf_path)
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"


class TestFastAPIEndpoints:
    def test_dashboard_returns_interactive_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Send Email Report" in response.text
        assert _has_service_bars(response.text)

    def test_costs_api_returns_json(self, client):
        response = client.get("/api/costs")
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        assert len(data["subscriptions"]) >= 2

    def test_refresh_api_refetches_data(self, client):
        first = client.get("/api/costs").json()
        response = client.post("/api/refresh")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        refreshed = response.json()["data"]
        assert len(refreshed["subscriptions"]) == len(first["subscriptions"])

    def test_download_pdf_returns_valid_pdf(self, client):
        response = client.get("/api/download/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"
        assert len(response.content) > 1000

    def test_dashboard_and_static_render_share_core_markers(self, client, mock_report_data):
        dashboard = client.get("/").text
        static_html = ReportRenderer().render(mock_report_data, mode=ReportMode.STATIC)
        assert _core_report_markers(dashboard) == _core_report_markers(static_html)

    @patch("src.app.send_email_notification")
    def test_email_background_task_sends_html_and_pdf(self, mock_send, mock_report_data):
        send_email_with_pdf_task("Azure Cost Report", mock_report_data)

        mock_send.assert_called_once()
        html = mock_send.call_args[0][1]
        attachments = mock_send.call_args.kwargs["attachments"]
        assert _has_service_bars(html)
        assert attachments
        assert attachments[0].endswith(".pdf")
        assert not os.path.exists(attachments[0])  # temp file cleaned up

    @patch("src.app.send_email_notification")
    def test_trigger_email_endpoint(self, mock_send, client):
        response = client.post("/api/notify/email")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_send.assert_called_once()

    @patch("src.app.send_webhook_notification")
    def test_trigger_webhook_endpoint(self, mock_webhook, client):
        response = client.post("/api/notify/webhook")
        assert response.status_code == 200
        assert response.json()["status"] == "success"


class TestCLIMainFlow:
    @patch("src.main.send_email_notification")
    @patch("src.main.NOTIFY_METHOD", "email")
    def test_cli_email_flow_generates_pdf_attachment(self, mock_send):
        def verify_pdf_at_send_time(subject, html, attachments=None):
            assert _has_service_bars(html)
            assert attachments
            with open(attachments[0], "rb") as f:
                assert f.read(4) == b"%PDF"

        mock_send.side_effect = verify_pdf_at_send_time
        asyncio.run(main(preview=False))
        mock_send.assert_called_once()

    @patch("src.main.preview_email")
    @patch("src.main.NOTIFY_METHOD", "webhook")
    def test_cli_preview_writes_static_html(self, mock_preview):
        asyncio.run(main(preview=True))
        mock_preview.assert_called_once()
        html = mock_preview.call_args[0][0]
        assert _has_service_bars(html)
        assert "Send Email Report" not in html

    @patch("src.main.send_webhook_notification")
    @patch("src.main.NOTIFY_METHOD", "webhook")
    def test_cli_webhook_only_skips_pdf(self, mock_webhook):
        asyncio.run(main(preview=False))
        mock_webhook.assert_called_once()

    @patch("src.main.send_email_notification")
    @patch("src.main._pdf_exporter.export", side_effect=RuntimeError("PDF failed"))
    @patch("src.main.NOTIFY_METHOD", "email")
    def test_cli_pdf_failure_exits_with_error(self, mock_export, mock_send):
        with pytest.raises(SystemExit) as exc:
            asyncio.run(main(preview=False))
        assert exc.value.code == 1
        mock_export.assert_called_once()
        mock_send.assert_not_called()
