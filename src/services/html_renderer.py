import os
import webbrowser
from jinja2 import Environment, FileSystemLoader

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

    :param subscription_data: List of subscription cost data
    :param is_server_mode: Boolean indicating if page is rendered inside local dashboard
    :param is_pdf_mode: Boolean indicating if page is rendered for PDF export
    :return: Rendered HTML report as a string
    """
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates")
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    template = env.get_template("report_template.html")

    context = {
        **subscription_data,
        "is_server_mode": is_server_mode,
        "is_pdf_mode": is_pdf_mode
    }
    return template.render(context)

def export_html_to_pdf(html_content, output_path):
    """
    Compiles the HTML content into a PDF using WeasyPrint.

    :param html_content: Rendered HTML report as a string
    :param output_path: Destination path for the PDF file
    """
    from weasyprint import HTML
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    HTML(string=html_content).write_pdf(output_path)

