from asyncio.windows_events import NULL
from email import header
import os
import tempfile
import webbrowser
import requests
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure Creds
TENANT_ID             = os.getenv("TENANT_ID")
CLIENT_ID             = os.getenv("CLIENT_ID")
CLIENT_SECRET         = os.getenv("CLIENT_SECRET")

subscription_ids = {
    # os.getenv("SUBSCRIPTION_ID1") : {"billing_start": 1},
    os.getenv("SUBSCRIPTION_ID2") : {"billing_start": 15}
}

# Azure API Endpoints
AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/token"
BASE_URL = "https://management.azure.com"

def format_date(date):
    return date.strftime("%Y-%m-%d")

def get_access_token():
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "resource": f"{BASE_URL}/"
    }

    response= requests.post(AUTH_URL, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def fetch_azure_data(url, token, payload=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload) if payload else requests.get(url, headers=headers)

    if response.status_code >= 400:
        print(f"Error {response.status_code}: {response.json()}")

    response.raise_for_status()
    return response.json()

# Fetching Azure Subscription Name
def get_subscription_name(subscription_id, token):
    url = f"{BASE_URL}/subscriptions/{subscription_id}/?api-version=2020-01-01"
    return fetch_azure_data(url, token).get("displayName", "Unknown Subscription")

# Fetching Cost
def get_cost_data(access_token, start_date, end_date, subscription_id, query="query", query_type="ActualCost"):
    url = f"{BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/{query}?api-version=2021-10-01"

    payload = {
        "type": query_type,
        "timeframe": "Custom",
        "timePeriod": {"from": format_date(start_date), "to": format_date(end_date)},
        "dataset": {
            "granularity": "Daily",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ServiceName"}],
        },
    }
    return fetch_azure_data(url, access_token, payload)

def print_cost_breakdown(cost_data):
    # print(f"\n🔹 {date_label} Cost Report {subscription_name}🔹")
    # print("=" * 40)

    total_rows = ""
    total_cost = 0.0
    rows = cost_data.get("properties", {}).get("rows", [])
    sorted_rows = sorted(rows, key=lambda x: float(x[0]), reverse=True)
    
    for item in sorted_rows:
        # Ensure proper unpacking and handle missing service names
        if len(item) < 4:
            continue

        cost, _, service_name, currency = item[:4]
        total_cost += cost if isinstance(cost, (int, float)) else 0

        total_rows += f"<tr><td>{service_name}</td><td>${cost:.2f} {currency}</td></tr>"

    return total_rows, total_cost

def calculate_cost(cost_data):
    total_cost = sum(item[0] for item in cost_data.get("properties", {}).get("rows", []) if isinstance(item[0], (int, float)))
    return round(total_cost, 2)

def generate_html_report(daily_date, daily_cost_data, first_day_of_month, last_day_of_month, monthly_forecast, subscription_name):
    # today = datetime.now(timezone.utc)
    daily_table, daily_total = print_cost_breakdown(daily_cost_data)
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
        </style>
    </head>
    <body>
    <h2>🔹 {subscription_name} - Cost Report</h2>
    <h3>📅 Daily Cost Report ({format_date(daily_date)})</h3>
    <table>
        <tr>
            <th>Service Name</th>
            <th>Cost (CAD)</th>
        </tr>
        {daily_table}
    <tr><td><strong>Total Daily Cost</strong></td><td><strong>${daily_total:.2f}</strong></td></tr>
    </table>
    
    <h3>📊 Forecasted Monthly Cost</h3>
    <p><strong>Estimated Forecast for ({first_day_of_month.strftime('%B')} {first_day_of_month.day} to {last_day_of_month.strftime('%B')} {last_day_of_month.day}):</strong> ${monthly_forecast:.2f}</p>
    </body>
    </html>
    """
    return html

def preview_email(html):
    print("\n--- EMAIL PREVIEW ---\n")
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as temp_file:
        temp_file.write(html)
        temp_file_path = temp_file.name

    webbrowser.open(f"file://{temp_file_path}")

def get_forecast_date(start_date):
    today = datetime.now(timezone.utc)
    if today.day >= start_date:
        first_day = today.replace(day=start_date)
        last_day = (first_day + timedelta(days=32)).replace(day=start_date) - timedelta(days=1)
        return first_day, last_day
    else:
        first_day = (today.replace(day=start_date) - timedelta(days=32)).replace(day=start_date)
        last_day = today.replace(day=start_date) - timedelta(days=1)
        return first_day, last_day

def main():
    try:
        token = get_access_token()
        today = datetime.now(timezone.utc)

        for subscription_id, details in subscription_ids.items():
            subscription_name = get_subscription_name(subscription_id, token)

            daily_date = (today - timedelta(days=2))
            # Fetching Daily cost (Today - 2)
            daily_cost_data = get_cost_data(token, daily_date, daily_date, subscription_id)

            billing_from = details["billing_start"]
            first_day, last_day = get_forecast_date(billing_from)

            # Fetch Monthly Forecast
            forecast_month_data = get_cost_data(token, first_day, last_day, subscription_id, "forecast", "Usage")
            forecast_month_cost = calculate_cost(forecast_month_data)

            actual_month_data = get_cost_data(token, first_day, last_day, subscription_id)
            actual_month_cost = calculate_cost(actual_month_data)

            monthly_forecast = forecast_month_cost + actual_month_cost
            print(f"🔹 Forecasted Cost for {subscription_name} (Feb):")
            print(f"   ✅ Total Forecast for {first_day.strftime('%B')} {first_day.day} To {last_day.strftime('%B')} {last_day.day}: ${monthly_forecast:.2f}\n")

            # Generate Email content
            email_html = generate_html_report(daily_date, daily_cost_data, first_day, last_day, monthly_forecast, subscription_name)
            preview_email(email_html)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()