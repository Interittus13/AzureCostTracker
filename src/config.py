import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

def str_to_bool(value):
    return str(value).lower() in ("true", "1", "yes")

# Azure Creds
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SUBSCRIPTIONS = set(os.getenv("SUBSCRIPTION_IDS").split(","))

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
