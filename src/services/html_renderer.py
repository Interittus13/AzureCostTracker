import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def render_html_report(subscription_data):
    """
    Renders the HTML report using Jinja2.

    :param subscription_data: List of subscription cost data
    :return: Rendered HTML report as a string
    """
    template = env.get_template("email-template.html")
    for sub in subscription_data:
        sub["daily_table"] = "".join(
            f"<tr><td>{item['service']}</td><td>{item['cost']} {item['currency']}</td></tr>"
            for item in sub["daily_table"]
        )

    context = {
        "subscriptions": subscription_data,
        "report_generated_on": datetime.now().strftime("%B %d, %Y")
    }

    return template.render(**context)

def render_html_summary(subscription_data):
    """
    Renders the HTML summary using Jinja2.
    """
    template = env.get_template("cost-summary.html")

    return template.render(subscriptions=subscription_data)
