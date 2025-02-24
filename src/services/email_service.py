from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import os
import webbrowser
from src.config import SMTP_SERVER, SMTP_PORT, SMTP_PASS, EMAIL_FROM, EMAIL_TO
from src.utils.logger import logger

def preview_email(html, filename="preview.html"):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    temp_file = os.path.join(output_dir, filename)

    with open(temp_file, "w", encoding="utf-8") as file:
        file.write(html)

    webbrowser.open(temp_file)

def send_email_notification(subject, html_content):
    """Send email with cost report."""
    recipients = [email.strip() for email in EMAIL_TO.split(",") if email.strip()]
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, SMTP_PASS)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send email. Error: {e}")
