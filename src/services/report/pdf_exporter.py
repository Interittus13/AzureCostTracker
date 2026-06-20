import os
import tempfile

from src.services.report.constants import PDF_OUTPUT_DIR


class PdfExporter:
    """Converts rendered HTML into a PDF file via WeasyPrint."""

    def export(self, html_content: str, output_path: str) -> str:
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise RuntimeError(
                "WeasyPrint is not installed. Install with: pip install weasyprint"
            ) from exc

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        try:
            HTML(string=html_content).write_pdf(output_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to generate PDF: {exc}") from exc

        return output_path

    @staticmethod
    def create_temp_path() -> str:
        os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
        fd, path = tempfile.mkstemp(suffix=".pdf", dir=PDF_OUTPUT_DIR)
        os.close(fd)
        return path
