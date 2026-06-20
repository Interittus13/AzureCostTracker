import os
import webbrowser

from src.services.report.modes import ReportMode
from src.services.report.pdf_exporter import PdfExporter
from src.services.report.renderer import ReportRenderer

_renderer = ReportRenderer()


def preview_email(html, filename="preview.html"):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    temp_file = os.path.join(output_dir, filename)

    with open(temp_file, "w", encoding="utf-8") as file:
        file.write(html)

    webbrowser.open(temp_file)


def render_html_report(subscription_data, is_server_mode=False, is_pdf_mode=False):
    """
    Renders the HTML report using Jinja2.

    Backward-compatible shim. Prefer ReportRenderer.render() with ReportMode.
    """
    if is_server_mode:
        mode = ReportMode.INTERACTIVE
    else:
        mode = ReportMode.STATIC
    return _renderer.render(subscription_data, mode=mode)


def export_html_to_pdf(html_content, output_path):
    """Compiles HTML content into a PDF using WeasyPrint."""
    PdfExporter().export(html_content, output_path)


def generate_pdf_report(data, pdf_path):
    """Renders a static report and exports it to PDF."""
    _renderer.render_pdf(data, pdf_path, mode=ReportMode.STATIC)
