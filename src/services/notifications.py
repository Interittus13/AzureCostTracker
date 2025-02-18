from email.mime.text import MIMEText
import smtplib
import requests
from src.config import NOTIFY_METHOD, WEBHOOK_URL, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO


def send_webhook_notification(message):
    if not WEBHOOK_URL:
        return

    payload = {"text": message}
    response = requests.post(WEBHOOK_URL, json=payload)

    if response.status_code == 200:
        print("Weebhook sent successfully")
    else:
        print(f"Failed to send weebhook. Status code: ${response.status_code}")


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
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")

def send_notification(subject, html_report):
    if NOTIFY_METHOD == "email":
        send_email_notification(subject, html_report)
    elif NOTIFY_METHOD == "webhook":
        send_webhook_notification(html_report)
    elif NOTIFY_METHOD == "both":
        send_email_notification(subject, html_report)
        send_webhook_notification(html_report)
    else:
        print("Invalid notification method")
