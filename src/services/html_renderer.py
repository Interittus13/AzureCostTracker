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

def render_html_report(subscription_data):
    """
    Renders the HTML report using Jinja2.

    :param subscription_data: List of subscription cost data
    :return: Rendered HTML report as a string
    """
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates")
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    template = env.get_template("report_template.html")

    return template.render(subscription_data)
