import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
from src.config import SMTP_SERVER, SMTP_PORT, SMTP_PASS, EMAIL_FROM, EMAIL_TO
from src.utils.logger import logger

def send_email_notification(subject, html_content, attachments=None):
    """Send email with cost report and optional attachments."""
    if not EMAIL_TO or not EMAIL_FROM:
        logger.warning("Email notification skipped: EMAIL_TO or EMAIL_FROM is not set.")
        return
    recipients = [email.strip() for email in EMAIL_TO.split(",") if email.strip()]
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html"))

    # Process and attach files
    for attachment_path in (attachments or []):
        if os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            try:
                with open(attachment_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)
                logger.info(f"Attached file: {filename}")
            except Exception as attachment_err:
                logger.error(f"Failed to attach file {attachment_path}: {attachment_err}")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, SMTP_PASS)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send email. Error: {e}")
