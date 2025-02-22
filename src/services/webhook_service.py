import requests
from src.config import WEBHOOK_URL
from src.utils.logger import logger

def send_webhook_notification(message):
    """Send notification via webhook."""
    if not WEBHOOK_URL:
        return

    payload = {"text": message}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
        response.raise_for_status()
        logger.info("Webhook notification sent successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send webhook: {e}")
