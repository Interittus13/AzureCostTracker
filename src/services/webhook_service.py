import requests
from src.config import WEBHOOK_URL
from src.utils.logger import logger


def render_markdown_summary(final_data):
    """Compile a clean, human-readable Markdown summary of subscription costs."""
    report_for = final_data.get("report_for", "N/A")
    generated_on = final_data.get("report_generated_on", "N/A")
    
    markdown_lines = [
        "### 📊 Azure Cost Tracker Report",
        f"**Report Period:** {report_for}  |  **Generated On:** {generated_on}",
        "",
        "| Subscription | Yesterday | Month-to-Date | Month Forecast |",
        "| :--- | :---: | :---: | :---: |"
    ]
    
    currency_symbol = final_data.get("currency_symbol", "$")

    for sub in final_data.get("subscriptions", []):
        sub_name = sub.get("subscription_name", "Unknown")
        daily = f"{currency_symbol}{sub.get('daily_cost', 0.0):,.2f}"
        mtd = f"{currency_symbol}{sub.get('month_to_day', 0.0):,.2f}"
        forecast = f"{currency_symbol}{sub.get('month_forecast', 0.0):,.2f}"
        markdown_lines.append(f"| **{sub_name}** | {daily} | {mtd} | {forecast} |")
        
    markdown_lines.extend(["", "---", "", "#### 🔍 Service Cost Breakdown (MTD)"])
    
    for sub in final_data.get("subscriptions", []):
        sub_name = sub.get("subscription_name", "Unknown")
        markdown_lines.append(f"\n**{sub_name}:**")
        breakdown = sub.get("service_breakdown", [])
        if not breakdown:
            markdown_lines.append("- No service breakdown data available.")
        else:
            for item in breakdown[:5]:  # Top 5 services
                markdown_lines.append(f"- {item['service']}: {item['cost']}")
            if len(breakdown) > 5:
                markdown_lines.append(f"- *And {len(breakdown) - 5} other services...*")
                
    return "\n".join(markdown_lines)


def send_webhook_notification(final_data):
    """Send notification via webhook."""
    if not WEBHOOK_URL:
        logger.warning("Webhook notification skipped: WEBHOOK_URL is not set.")
        return

    message = render_markdown_summary(final_data)
    payload = {"text": message}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
        response.raise_for_status()
        logger.info("Webhook notification sent successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send webhook: {e}")

