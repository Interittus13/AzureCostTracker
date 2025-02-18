import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure Creds
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SUBSCRIPTIONS = {
    # os.getenv("SUBSCRIPTION_ID1") : {"billing_start": 1},
    os.getenv("SUBSCRIPTION_ID2"): {"billing_start": 15}
}

NOTIFY_METHOD = os.getenv("NOTIFY_METHOD", "email")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")

# Azure API Endpoints
AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/token"
BASE_URL = "https://management.azure.com"
