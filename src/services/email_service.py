from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import webbrowser
from src.config import SMTP_SERVER, SMTP_PORT, SMTP_PASS, EMAIL_FROM, EMAIL_TO
from src.utils.logger import logger

def preview_email(html):
    temp_file = "preview.html"
    with open(temp_file, "w", encoding="utf-8") as file:
        file.write(html)

    webbrowser.open(temp_file)

def send_email_notification(subject, summary, html_content):
    """Send email with cost report."""
    recipients = [email.strip() for email in EMAIL_TO.split(",") if email.strip()]
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(summary, "html"))

    attachment = MIMEText(html_content, "html")
    attachment.add_header("Content-Disposition", "attachment", filename="Azure_Cost_Report.html")
    msg.attach(attachment)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, SMTP_PASS)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send email. Error: {e}")
