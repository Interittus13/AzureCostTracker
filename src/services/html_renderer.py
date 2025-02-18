import os
from jinja2 import Environment, FileSystemLoader
from time import strftime
from src.utils.utils import format_date, get_cost_breakdown

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
template = env.get_template("email-template.html")

def render_html_report(daily_date, daily_cost_data, first_day_of_month, last_day_of_month, monthly_forecast, subscription_name):
    """
    Renders the HTML report using Jinja2.

    :param daily_date: Date for the daily cost report
    :param daily_cost_data: List of cost breakdown data
    :param monthly_forecast: Monthly cost forecast
    :param first_day: First day of the billing period (datetime object)
    :param last_day: Last day of the billing period (datetime object)
    :param subscription_name: Name of the Azure subscription
    :return: Rendered HTML report as a string
    """
    daily_table, daily_total = get_cost_breakdown(daily_cost_data)

    cost_rows = "".join(
        f"<tr><td>{item['service']}</td><td>{item['cost']} {item['currency']}</td></tr>"
        for item in daily_table
    )

    return template.render(
        daily_date=format_date(daily_date),
        daily_table=cost_rows,
        daily_total=f"{daily_total}",
        first_day_of_month={"month": first_day_of_month.strftime('%B'), "day": first_day_of_month.day},
        last_day_of_month={"month": last_day_of_month.strftime('%B'), "day": last_day_of_month.day},
        monthly_forecast=f"{monthly_forecast}",
        subscription_name=subscription_name,
    )
