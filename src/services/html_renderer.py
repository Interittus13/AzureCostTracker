import os
from jinja2 import Environment, FileSystemLoader
from time import strftime
from src.services.utils import format_date, print_cost_breakdown

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
template = env.get_template("email-template.html")

def render_html_report(daily_date, daily_cost_data, first_day_of_month, last_day_of_month, monthly_forecast, subscription_name):
    # today = datetime.now(timezone.utc)
    daily_table, daily_total = print_cost_breakdown(daily_cost_data)

    return template.render(
        daily_date=format_date(daily_date),
        daily_table=daily_table,
        daily_total=f"{daily_total:.2f}",
        first_day_of_month={"month": first_day_of_month.strftime('%B'), "day": first_day_of_month.day},
        last_day_of_month={"month": last_day_of_month.strftime('%B'), "day": last_day_of_month.day},
        monthly_forecast=f"{monthly_forecast:.2f}",
        subscription_name=subscription_name,
    )
