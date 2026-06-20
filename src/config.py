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

# Check if credentials are placeholders or missing
def is_placeholder(val):
    return not val or any(placeholder in str(val).lower() for placeholder in ["your-", "placeholder", "subscription-id", "client-secret"])

MOCK_AZURE = str_to_bool(os.getenv("MOCK_AZURE", "false")) or is_placeholder(TENANT_ID) or is_placeholder(CLIENT_SECRET)

raw_subs = os.getenv("SUBSCRIPTION_IDS", "mock-sub-1,mock-sub-2")
if is_placeholder(raw_subs) or not raw_subs.strip():
    raw_subs = "mock-subscription-development,mock-subscription-production"

SUBSCRIPTIONS = [sub.strip() for sub in raw_subs.split(",") if sub.strip()]

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
