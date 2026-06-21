from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.services.report.constants import CHART_COLORS, TEMPLATE_DIR
from src.services.report.modes import ReportMode
from src.services.report.pdf_exporter import PdfExporter


class ReportRenderer:
    """Renders Azure cost reports from Jinja2 templates."""

    def __init__(self, template_dir: str = TEMPLATE_DIR):
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._env.globals["chart_colors"] = CHART_COLORS
        self._pdf_exporter = PdfExporter()

    def render(self, data: dict, mode: ReportMode = ReportMode.STATIC) -> str:
        template = self._env.get_template("report_template.html")
        context = {
            **data,
            "mode": mode,
            "is_interactive": mode == ReportMode.INTERACTIVE,
            "chart_colors": CHART_COLORS,
        }
        return template.render(context)

    def render_pdf(self, data: dict, output_path: str, mode: ReportMode = ReportMode.STATIC) -> str:
        html = self.render(data, mode=mode)
        return self._pdf_exporter.export(html, output_path)
