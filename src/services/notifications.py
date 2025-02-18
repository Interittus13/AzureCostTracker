from email.mime.text import MIMEText
import smtplib
import requests
from src.config import NOTIFY_METHOD, WEBHOOK_URL, SMTP_SERVER, SMTP_PORT, SMTP_PASS, EMAIL_FROM, EMAIL_TO
from src.utils.logger import logger


def send_webhook_notification(message):
    if not WEBHOOK_URL:
        return

    payload = {"text": message}
    response = requests.post(WEBHOOK_URL, json=payload)

    if response.status_code == 200:
        logger.info("Weebhook sent successfully")
    else:
        logger.error(f"Failed to send weebhook. Status code: ${response.status_code}")


def send_email_notification(subject, html_content):
    recipients = [email.strip() for email in EMAIL_TO.split(",") if email.strip()]
    msg = MIMEText(html_content, "html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, SMTP_PASS)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send email. Error: {e}")

def send_notification(subject, html_report):
    match NOTIFY_METHOD:
        case "email":
            send_email_notification(subject, html_report)
        case "webhook":
            send_webhook_notification(html_report)
        case "both":
            send_email_notification(subject, html_report)
            send_webhook_notification(html_report)
        case _:
            logger.error("Invalid Notify method")

