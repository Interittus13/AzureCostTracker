import os
import json
import math
import requests
import smtplib
import argparse
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
def load_env_vars():
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)

    return {
        'tenant_id': os.environ.get('TENANT_ID'),
        'client_id': os.environ.get('CLIENT_ID'),
        'client_secret': os.environ.get('CLIENT_SECRET'),
        'subscription_ids': {
            os.environ.get('SUBSCRIPTION_ID1'): 1,  # User-defined start date per subscription
            os.environ.get('SUBSCRIPTION_ID2'): 14  # User-defined start date per subscription
        },
        'smtp_server': os.environ.get('SMTP_SERVER'),
        'smtp_port': os.environ.get('SMTP_PORT'),
        'smtp_user': os.environ.get('SMTP_USER'),
        'smtp_pass': os.environ.get('SMTP_PASS'),
        'email_from': os.environ.get('EMAIL_FROM'),
        'email_to': os.environ.get('EMAIL_TO'),
        'cc_to': os.environ.get('CC_TO')
    }

# Function to fetch Azure authentication token
def get_azure_token(tenant_id, client_id, client_secret):
    """Fetch Azure authentication token using service principal credentials"""
    body = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': 'https://management.azure.com'
    }

    try:
        token_response = requests.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/token",
            data=body
        )
        token_response.raise_for_status()
        return token_response.json()['access_token']
    except Exception as e:
        print(f"Error fetching Azure token: {e}")
        exit(1)

# Function to fetch cost data with retry logic
def get_costing(sub_id, az_token, start_date, end_date, query_type, query):
    """Fetch cost data for a specific subscription and date range with retry logic for rate limiting"""
    request_body = {
        "type": query_type,
        "timeframe": "Custom",
        "timePeriod": {
            "from": start_date,
            "to": end_date
        },
        "dataset": {
            "granularity": "Daily",
            "aggregation": {
                "totalCost": {
                    "name": "PreTaxCost",
                    "function": "Sum"
                }
            }
        }
    }

    # Retry configuration
    max_retries = 5
    base_delay = 2  # Starting delay in seconds

    for retry in range(max_retries):
        try:
            cost_response = requests.post(
                f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.CostManagement/{query}?api-version=2021-10-01",
                headers={"Authorization": f"Bearer {az_token}", "Content-Type": "application/json"},
                json=request_body
            )

            # If rate limited, retry with exponential backoff
            if cost_response.status_code == 429:
                # Get retry-after header or use exponential backoff
                retry_after = int(cost_response.headers.get('Retry-After', 0)) or (base_delay * (2 ** retry) + random.random())
                print(f"Rate limited. Retrying after {retry_after:.2f} seconds... (Attempt {retry+1}/{max_retries})")
                time.sleep(retry_after)
                continue

            cost_response.raise_for_status()

            data = cost_response.json()
            if 'properties' in data and 'rows' in data['properties'] and data['properties']['rows']:
                cost_sum = sum([row[0] for row in data['properties']['rows']])
                return round(cost_sum, 2)
            else:
                print(f"No cost data found for Subscription {sub_id} between {start_date} and {end_date}")
                return 0

        except requests.exceptions.HTTPError as e:
            if retry < max_retries - 1:
                delay = base_delay * (2 ** retry) + random.random()
                print(f"HTTP Error: {e}. Retrying after {delay:.2f} seconds... (Attempt {retry+1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"Error fetching cost data for Subscription {sub_id} after {max_retries} attempts: {e}")
                return 0
        except Exception as e:
            print(f"Error fetching cost data for Subscription {sub_id}: {e}")
            return 0

    print(f"Failed to get cost data after {max_retries} attempts")
    return 0

# Function to fetch Azure Reservations
def get_azure_reservations(az_token):
    """Fetch Azure Reservation data"""
    try:
        response = requests.get(
            "https://management.azure.com/providers/Microsoft.Capacity/reservationOrders?api-version=2022-11-01",
            headers={"Authorization": f"Bearer {az_token}"}
        )
        response.raise_for_status()

        data = response.json()
        if not data.get('value'):
            print("No reservations found.")
            return 0

        return data['value']
    except Exception as e:
        print(f"Error fetching reservation data: {e}")
        return 0

# Function to get subscription name
def get_subscription_name(sub_id, az_token):
    """Get subscription name from subscription ID"""
    try:
        response = requests.get(
            f"https://management.azure.com/subscriptions/{sub_id}?api-version=2020-01-01",
            headers={"Authorization": f"Bearer {az_token}"}
        )
        response.raise_for_status()

        data = response.json()
        return data.get('displayName', sub_id)
    except Exception as e:
        print(f"Error fetching subscription name for {sub_id}: {e}")
        return sub_id

# Function to generate HTML report
def generate_html(report_data, daily_date, reservation_cost=3837.00):
    """Generate HTML report content"""
    # Check if report data is empty
    if not report_data:
        print("No report data available. Generating minimal report.")
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Azure Cost Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f9f9f9;
                    color: #333;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: white;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #0078D4;
                    color: white;
                    padding: 20px;
                    border-radius: 5px 5px 0 0;
                    margin-bottom: 20px;
                }}
                .header h1 {{
                    margin: 0;
                    font-weight: 400;
                }}
                .error-card {{
                    background-color: #f8d7da;
                    padding: 30px;
                    border-radius: 5px;
                    margin: 40px 0;
                    border-left: 5px solid #d9534f;
                    text-align: center;
                }}
                .error-card h2 {{
                    color: #721c24;
                    margin-top: 0;
                }}
                .error-card p {{
                    font-size: 16px;
                    line-height: 1.6;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eaeaea;
                    color: #666;
                    font-size: 14px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>BFX Azure Cost Report</h1>
                    <p>Reporting period: {daily_date}</p>
                </div>

                <div class="error-card">
                    <h2>No Data Available</h2>
                    <p>No cost data is available for this reporting period. This may be due to API rate limiting or insufficient permissions.</p>
                    <p>Please try again later or contact your Azure administrator.</p>
                </div>

                <div class="footer">
                    <p>Report Generated on {datetime.now().strftime('%d-%b-%Y %H:%M')} | BFX Azure Cost Management</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content

    # Calculate total costs
    total_daily = sum(entry.get('dailyCost', 0) for entry in report_data)
    total_monthly = sum(entry.get('monthForecast', 0) for entry in report_data)
    total_mtd = sum(entry.get('mtdCost', 0) for entry in report_data)
    total_ytd = sum(entry.get('ytdCost', 0) for entry in report_data)

    # Calculate percentages for visualizations
    mtd_percentages = {}
    ytd_percentages = {}
    month_forecast_percentages = {}
    year_forecast_percentages = {}

    # Calculate total values for percentages
    total_mtd = sum(entry.get('mtdCost', 0) for entry in report_data)
    total_ytd = sum(entry.get('ytdCost', 0) for entry in report_data)
    total_month_forecast = sum(entry.get('monthForecast', 0) for entry in report_data)
    total_year_forecast = sum(entry.get('yearForecast', 0) for entry in report_data)

    # Calculate percentage for each subscription
    for entry in report_data:
        sub_name = entry.get('subName', 'Unknown')
        mtd_percentages[sub_name] = (entry.get('mtdCost', 0) / total_mtd * 100) if total_mtd > 0 else 0
        ytd_percentages[sub_name] = (entry.get('ytdCost', 0) / total_ytd * 100) if total_ytd > 0 else 0
        month_forecast_percentages[sub_name] = (entry.get('monthForecast', 0) / total_month_forecast * 100) if total_month_forecast > 0 else 0
        year_forecast_percentages[sub_name] = (entry.get('yearForecast', 0) / total_year_forecast * 100) if total_year_forecast > 0 else 0

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Azure Cost Report</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f9f9f9;
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: white;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background-color: #0078D4;
                color: white;
                padding: 20px;
                border-radius: 5px 5px 0 0;
                margin-bottom: 20px;
            }}
            .header h1 {{
                margin: 0;
                font-weight: 400;
            }}
            .summary-cards {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .card {{
                flex: 1;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                min-width: 200px;
                transition: transform 0.2s;
            }}
            .card:hover {{
                transform: translateY(-5px);
            }}
            .card-title {{
                font-size: 14px;
                color: #666;
                margin-bottom: 5px;
            }}
            .card-value {{
                font-size: 32px;
                font-weight: 600;
                margin: 0;
                color: #0078D4;
            }}
            .section {{
                margin-bottom: 40px;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            }}
            .section h2 {{
                color: #0078D4;
                border-bottom: 2px solid #eaeaea;
                padding-bottom: 10px;
                font-weight: 500;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                margin-bottom: 10px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f2f8fd;
                color: #0078D4;
                font-weight: 500;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .total-row {{
                font-weight: bold;
                background-color: #e6f2ff;
            }}
            .error-message {{
                color: #721c24;
                background-color: #f8d7da;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border-left: 4px solid #f5c6cb;
            }}
            .bar-chart {{
                height: 20px;
                background-color: #e6f2ff;
                position: relative;
                border-radius: 3px;
                overflow: hidden;
                margin-top: 5px;
            }}
            .bar {{
                height: 100%;
                background-color: #0078D4;
                position: absolute;
                left: 0;
                top: 0;
                border-radius: 3px;
            }}
            .bar-label {{
                position: relative;
                z-index: 1;
                padding: 0 10px;
                font-size: 12px;
                line-height: 20px;
                color: #333;
                text-shadow: 0 0 2px white;
            }}
            .visualization {{
                display: flex;
                flex-wrap: wrap;
                gap: 30px;
                margin-top: 30px;
            }}
            .chart {{
                flex: 1;
                min-width: 300px;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            }}
            .chart-title {{
                font-size: 16px;
                font-weight: 500;
                color: #0078D4;
                margin-bottom: 15px;
                text-align: center;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #eaeaea;
                color: #666;
                font-size: 14px;
                text-align: center;
            }}
            @media (max-width: 768px) {{
                .summary-cards {{ flex-direction: column; }}
                .card {{ min-width: 100%; }}
                .visualization {{ flex-direction: column; }}
                .chart {{ min-width: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>BFX Azure Cost Report</h1>
                <p>Reporting period: {daily_date}</p>
            </div>

            {'''<div class="error-message">
                <strong>Note:</strong> Some data may be incomplete due to API rate limiting.
                Values of 0 may indicate that the data is not yet available.
            </div>''' if any(entry.get('dailyCost', 0) == 0 for entry in report_data) else ''}

            <div class="summary-cards">
                <div class="card">
                    <div class="card-title">TOTAL DAILY COST</div>
                    <div class="card-value">${total_daily:.2f}</div>
                    <div class="card-title">CAD</div>
                </div>
                <div class="card">
                    <div class="card-title">TOTAL MONTH-TO-DATE COST</div>
                    <div class="card-value">${total_mtd:.2f}</div>
                    <div class="card-title">CAD</div>
                </div>
                <div class="card">
                    <div class="card-title">TOTAL MONTHLY FORECAST</div>
                    <div class="card-value">${total_monthly:.2f}</div>
                    <div class="card-title">CAD</div>
                </div>
                <div class="card">
                    <div class="card-title">TOTAL YEAR-TO-DATE COST</div>
                    <div class="card-value">${total_ytd:.2f}</div>
                    <div class="card-title">CAD</div>
                </div>
            </div>

            <div class="section">
                <h2>Daily Cost Report</h2>
                <table>
                    <tr>
                        <th>Subscription</th>
                        <th>Daily Cost (CAD)</th>
                        <th>MTD Cost (CAD)</th>
                        <th>Monthly Forecast (CAD)</th>
                    </tr>
    """

    for entry in report_data:
        html_content += f"""
        <tr>
            <td>{entry.get('subName', 'Unknown')}</td>
            <td>${entry.get('dailyCost', 0):.2f}</td>
            <td>${entry.get('mtdCost', 0):.2f}</td>
            <td>${entry.get('monthForecast', 0):.2f}</td>
        </tr>
        """

    html_content += f"""
        <tr class="total-row">
            <td>Total</td>
            <td>${total_daily:.2f}</td>
            <td>${total_mtd:.2f}</td>
            <td>${total_monthly:.2f}</td>
        </tr>
        </table>

        <div class="visualization">
            <div class="chart">
                <div class="chart-title">Month-to-Date Cost Distribution</div>
                {'''
                '''.join([f'''
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>{sub}</div>
                        <div>${entry.get('mtdCost', 0):.2f} ({mtd_percentages.get(sub, 0):.1f}%)</div>
                    </div>
                    <div class="bar-chart">
                        <div class="bar" style="width: {mtd_percentages.get(sub, 0)}%;"></div>
                        <div class="bar-label">{mtd_percentages.get(sub, 0):.1f}%</div>
                    </div>
                </div>
                ''' for sub, entry in [(entry.get('subName', 'Unknown'), entry) for entry in report_data]])}
            </div>

            <div class="chart">
                <div class="chart-title">Monthly Forecast Distribution</div>
                {'''
                '''.join([f'''
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>{sub}</div>
                        <div>${entry.get('monthForecast', 0):.2f} ({month_forecast_percentages.get(sub, 0):.1f}%)</div>
                    </div>
                    <div class="bar-chart">
                        <div class="bar" style="width: {month_forecast_percentages.get(sub, 0)}%;"></div>
                        <div class="bar-label">{month_forecast_percentages.get(sub, 0):.1f}%</div>
                    </div>
                </div>
                ''' for sub, entry in [(entry.get('subName', 'Unknown'), entry) for entry in report_data]])}
            </div>
        </div>
        </div>

        <div class="section">
            <h2>YEAR-TO-DATE and Annual Forecast</h2>
            <table>
                <tr>
                    <th>Subscription</th>
                    <th>YEAR-TO-DATE Cost (CAD)</th>
                    <th>Annual Forecast (CAD)</th>
                </tr>
    """

    for entry in report_data:
        html_content += f"""
        <tr>
            <td>{entry.get('subName', 'Unknown')}</td>
            <td>${entry.get('ytdCost', 0):.2f}</td>
            <td>${entry.get('yearForecast', 0):.2f}</td>
        </tr>
        """

    html_content += f"""
        <tr class="total-row">
            <td>Total</td>
            <td>${total_ytd:.2f}</td>
            <td>${sum(entry.get('yearForecast', 0) for entry in report_data):.2f}</td>
        </tr>
        </table>

        <div class="visualization">
            <div class="chart">
                <div class="chart-title">YEAR-TO-DATE Cost Distribution</div>
                {'''
                '''.join([f'''
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>{sub}</div>
                        <div>${entry.get('ytdCost', 0):.2f} ({ytd_percentages.get(sub, 0):.1f}%)</div>
                    </div>
                    <div class="bar-chart">
                        <div class="bar" style="width: {ytd_percentages.get(sub, 0)}%;"></div>
                        <div class="bar-label">{ytd_percentages.get(sub, 0):.1f}%</div>
                    </div>
                </div>
                ''' for sub, entry in [(entry.get('subName', 'Unknown'), entry) for entry in report_data]])}
            </div>

            <div class="chart">
                <div class="chart-title">Annual Forecast Distribution</div>
                {'''
                '''.join([f'''
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>{sub}</div>
                        <div>${entry.get('yearForecast', 0):.2f} ({year_forecast_percentages.get(sub, 0):.1f}%)</div>
                    </div>
                    <div class="bar-chart">
                        <div class="bar" style="width: {year_forecast_percentages.get(sub, 0)}%;"></div>
                        <div class="bar-label">{year_forecast_percentages.get(sub, 0):.1f}%</div>
                    </div>
                </div>
                ''' for sub, entry in [(entry.get('subName', 'Unknown'), entry) for entry in report_data]])}
            </div>
        </div>
        </div>

        <div class="section">
            <h2>Azure Reservations</h2>
            <table>
                <tr>
                    <th>Type</th>
                    <th>Cost (CAD)</th>
                </tr>
                <tr>
                    <td>Azure Reservations</td>
                    <td>${reservation_cost:.2f}</td>
                </tr>
            </table>
        </div>

        <div class="footer">
            <p>Report Generated on {datetime.now().strftime('%d-%b-%Y %H:%M')} | BFX Azure Cost Management</p>
        </div>
        </div>
    </body>
    </html>
    """

    # Save report to file
    download_path = os.path.expanduser('~/Downloads')
    html_file_path = os.path.join(download_path, 'Azure-cost-report.html')
    os.makedirs(download_path, exist_ok=True)

    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML Report saved: {html_file_path}")

    return html_content

# Function to send email with HTML report
def send_email(html_content, env_vars):
    """Send email with the HTML report"""
    # Check if email configuration is complete
    if not all([env_vars.get('smtp_server'), env_vars.get('smtp_port'),
                env_vars.get('smtp_user'), env_vars.get('smtp_pass'),
                env_vars.get('email_from'), env_vars.get('email_to')]):
        print("Email configuration incomplete. Please check your .env file.")
        return

    # Parse email addresses
    to_addresses = [email.strip() for email in env_vars['email_to'].split(',') if email.strip()]
    if not to_addresses:
        print("No valid 'to' email addresses found")
        return

    cc_addresses = []
    if env_vars.get('cc_to'):
        cc_addresses = [email.strip() for email in env_vars['cc_to'].split(',') if email.strip()]

    # Create message
    msg = MIMEMultipart()
    msg['From'] = env_vars['email_from']
    msg['To'] = ', '.join(to_addresses)
    if cc_addresses:
        msg['Cc'] = ', '.join(cc_addresses)

    msg['Subject'] = "Azure Cost Report"

    # Create email body
    body = """
    <p>Hi</p>
    <p>Please find the Azure Cost Report.</p>
    """

    # Only attach HTML content if it exists and is not empty
    if html_content and isinstance(html_content, str):
        body += html_content
    else:
        body += "<p>No cost data available for this report period.</p>"

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(env_vars['smtp_server'], int(env_vars['smtp_port']))
        server.starttls()
        server.login(env_vars['smtp_user'], env_vars['smtp_pass'])

        # Get all recipients
        all_recipients = to_addresses + cc_addresses

        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

def main():
    """Main function to process all subscriptions and generate report"""
    parser = argparse.ArgumentParser(description='Azure Cost Report Generator')
    parser.add_argument('--run-now', action='store_true', help='Run the report immediately')
    parser.add_argument('--delay', type=int, default=5, help='Delay in seconds between API calls to avoid rate limiting')
    args = parser.parse_args()

    # Load environment variables
    env_vars = load_env_vars()

    # Validate required environment variables
    if not all([env_vars.get('tenant_id'), env_vars.get('client_id'), env_vars.get('client_secret')]):
        print("Error: Missing required Azure credentials in .env file")
        print("Please configure TENANT_ID, CLIENT_ID, and CLIENT_SECRET")
        return

    if not env_vars.get('subscription_ids'):
        print("Error: No subscription IDs found in .env file")
        print("Please configure at least one SUBSCRIPTION_ID")
        return

    # Calculate dates
    today = datetime.now()
    yesterday = (today - timedelta(days=2)).strftime('%Y-%m-%d')  # 2 days ago for reporting
    current_year = today.year
    current_month = today.month

    # Calculate year start date
    year_start = datetime(current_year, 1, 1).strftime('%Y-%m-%d')
    year_end = datetime(current_year, 12, 31).strftime('%Y-%m-%d')

    try:
        # Get Azure Access Token
        print("Authenticating with Azure...")
        az_token = get_azure_token(env_vars['tenant_id'], env_vars['client_id'], env_vars['client_secret'])
        print("Authentication successful!")

        # Initialize report data
        report_data = []

        # Process each subscription
        for sub_id, start_day in env_vars['subscription_ids'].items():
            if not sub_id:
                continue

            print(f"🔄 Processing subscription: {sub_id}")

            try:
                # Get subscription name
                sub_name = get_subscription_name(sub_id, az_token)

                # Calculate month dates (handling potential day-of-month issues)
                try:
                    month_starts_on = datetime(current_year, current_month, int(start_day))
                except ValueError:
                    # Handle case where start_day is invalid for the current month (e.g., Feb 30)
                    # Use last day of month instead
                    last_day = (datetime(current_year, current_month % 12 + 1, 1) - timedelta(days=1)).day
                    month_starts_on = datetime(current_year, current_month, min(int(start_day), last_day))
                    print(f"Adjusted billing start day to {month_starts_on.day} for this month")

                month_ends_on = (month_starts_on.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

                # Format dates for API
                month_start_str = month_starts_on.strftime('%Y-%m-%d')
                month_end_str = month_ends_on.strftime('%Y-%m-%d')
                month_today_str = today.strftime('%Y-%m-%d')

                # Add delay between API calls to prevent rate limiting
                print(f"Fetching daily cost data...")
                # Fetch daily cost
                daily_cost = get_costing(
                    sub_id,
                    az_token,
                    yesterday,
                    yesterday,
                    "ActualCost",
                    "query"
                )
                time.sleep(args.delay)  # Add delay between API calls

                print(f"Fetching MTD cost data...")
                # Fetch MTD (month-to-date) cost
                mtd_cost = get_costing(
                    sub_id,
                    az_token,
                    month_start_str,
                    month_today_str,
                    "ActualCost",
                    "query"
                )
                time.sleep(args.delay)  # Add delay between API calls

                print(f"Fetching YTD cost data...")
                # Fetch YTD (year-to-date) cost
                ytd_cost = get_costing(
                    sub_id,
                    az_token,
                    year_start,
                    month_today_str,
                    "ActualCost",
                    "query"
                )
                time.sleep(args.delay)  # Add delay between API calls

                print(f"Fetching monthly actual cost data...")
                # Fetch monthly forecasts
                month_actual_cost = get_costing(
                    sub_id,
                    az_token,
                    month_start_str,
                    month_end_str,
                    "ActualCost",
                    "query"
                )
                time.sleep(args.delay)  # Add delay between API calls

                print(f"Fetching monthly forecast data...")
                month_forecast_cost = get_costing(
                    sub_id,
                    az_token,
                    month_start_str,
                    month_end_str,
                    "Usage",
                    "forecast"
                )

                # Calculate year forecast based on YTD + remaining months
                remaining_months = 12 - today.month # 9
                monthly_avg = ytd_cost / today.month if today.month > 0 else 0
                year_forecast = ytd_cost + (monthly_avg * remaining_months)

                # Calculate total monthly forecast
                month_forecast = month_actual_cost + month_forecast_cost

                report_data.append({
                    'subName': sub_name,
                    'dailyCost': daily_cost,
                    'mtdCost': mtd_cost,
                    'ytdCost': ytd_cost,
                    'monthForecast': month_forecast,
                    'yearForecast': round(year_forecast, 2)
                })

                # Print summary of data collected
                print(f"✅ Subscription: {sub_name}")
                print(f"   Daily Cost: {daily_cost} CAD")
                print(f"   MONTH-TO-DATE Cost: {mtd_cost} CAD")
                print(f"   YEAR-TO-DATE Cost: {ytd_cost} CAD")
                print(f"   Monthly Forecast: {month_forecast} CAD")

            except Exception as e:
                print(f"Error processing subscription {sub_id}: {e}")
                # Still add the subscription to the report with zeros to indicate an error
                report_data.append({
                    'subName': sub_id,  # Use ID if name can't be fetched
                    'dailyCost': 0,
                    'mtdCost': 0,
                    'ytdCost': 0,
                    'monthForecast': 0,
                    'yearForecast': 0
                })

        # Generate report
        html_content = generate_html(report_data, (today - timedelta(days=2)).strftime('%d-%b-%Y'))

        # Send email
        if env_vars.get('smtp_server') and env_vars.get('email_to'):
            send_email(html_content, env_vars)
        else:
            print("Email sending skipped: SMTP configuration missing from .env file")

    except Exception as e:
        print(f"Error running Azure Cost Report: {e}")
        # Generate a minimal error report
        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Azure Cost Report - Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #d9534f; }}
                .error {{ color: #721c24; background-color: #f8d7da; padding: 15px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>Azure Cost Report - Error</h1>
            <div class="error">
                <p>An error occurred while generating the Azure Cost Report:</p>
                <p>{str(e)}</p>
            </div>
            <p>Please check the script logs for more details.</p>
            <footer>
                <p>Report Generated on {datetime.now().strftime('%d-%b-%Y')}</p>
            </footer>
        </body>
        </html>
        """

        # Try to send error email if email config exists
        if env_vars.get('smtp_server') and env_vars.get('email_to'):
            send_email(error_html, env_vars)

if __name__ == "__main__":
    main()
