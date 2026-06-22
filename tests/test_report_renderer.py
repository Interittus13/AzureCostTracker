from unittest.mock import MagicMock, patch
import os

import pytest

from src.services.report import PdfExporter, ReportMode, ReportRenderer


MOCK_REPORT_DATA = {
    "subscriptions": [
        {
            "subscription_name": "Dev Sub",
            "daily_cost": 10.0,
            "month_to_day": 100.0,
            "month_forecast": 150.0,
            "year_to_day": 500.0,
            "year_forecast": 1000.0,
            "service_breakdown": [
                {"service": "Virtual Machines", "cost": "$80.00", "raw_cost": 80.0},
                {"service": "Storage", "cost": "$20.00", "raw_cost": 20.0},
            ],
            "dates": {},
            "currency_code": "USD",
            "currency_symbol": "$",
        }
    ],
    "report_for": "2026-06-18",
    "report_generated_on": "2026-06-19",
    "currency_code": "USD",
    "currency_symbol": "$",
}


@pytest.fixture
def renderer():
    return ReportRenderer()


def test_static_render_includes_service_bars(renderer):
    html = renderer.render(MOCK_REPORT_DATA, mode=ReportMode.STATIC)

    assert 'role="presentation"' in html
    assert "background-color: #3b82f6" in html
    assert "Service-Level Cost Breakdown" in html
    assert "chart.js" not in html.lower()
    assert "Send Email Report" not in html
    assert "<circle" not in html
    assert "data:image/png" not in html


def test_interactive_render_includes_control_bar(renderer):
    html = renderer.render(MOCK_REPORT_DATA, mode=ReportMode.INTERACTIVE)

    assert "control-bar" in html
    assert 'role="presentation"' in html
    assert "chart.js" not in html.lower()
    assert "triggerEmail" in html


@patch("weasyprint.HTML")
def test_pdf_exporter_writes_pdf(mock_html_class, tmp_path):
    mock_html = MagicMock()
    mock_html_class.return_value = mock_html
    output_path = tmp_path / "report.pdf"

    PdfExporter().export("<html><body>test</body></html>", str(output_path))

    mock_html_class.assert_called_once()
    mock_html.write_pdf.assert_called_once_with(str(output_path))


@patch("weasyprint.HTML", side_effect=RuntimeError("render failed"))
def test_pdf_exporter_raises_clear_error(mock_html_class, tmp_path):
    output_path = tmp_path / "report.pdf"

    with pytest.raises(RuntimeError, match="Failed to generate PDF"):
        PdfExporter().export("<html><body>test</body></html>", str(output_path))


def test_pdf_exporter_create_temp_path():
    path = PdfExporter.create_temp_path()

    assert path.endswith(".pdf")
    assert os.path.dirname(path).endswith("output")


def test_get_report_data_sorts_subscriptions():
    import asyncio
    from src.main import get_report_data

    with patch("src.main.get_access_token", return_value="token"), \
         patch("src.main.process_subscription") as mock_process, \
         patch("src.main.SnapshotStore") as mock_store_cls:
        mock_store = mock_store_cls.return_value
        mock_store.get_latest.return_value = None
        mock_store.save.return_value = None
        mock_process.side_effect = [
            {"subscription_name": "Zeta", "dates": {}, "currency_code": "USD", "currency_symbol": "$"},
            {"subscription_name": "Alpha", "dates": {}, "currency_code": "USD", "currency_symbol": "$"},
        ]

        with patch("src.main.SUBSCRIPTIONS", ["sub-z", "sub-a"]):
            data = asyncio.run(get_report_data())

    names = [entry["subscription_name"] for entry in data["subscriptions"]]
    assert names == ["Alpha", "Zeta"]
