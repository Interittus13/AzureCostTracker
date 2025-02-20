from datetime import datetime, timezone
import json
from src.utils.logger import logger
import requests, os
from cryptography.fernet import Fernet
from src.config import CLIENT_ID, CLIENT_SECRET, BASE_URL, AUTH_URL

TOKEN_FILE = "token.enc"
KEY_FILE = "secret.key"

def get_access_token():
    """Retrive Azure access token (Generate new if expired)."""
    token = decrypt_token()

    if token and not is_token_expired(token['expires_on']):
        logger.info("Using cached token.")
        return token["access_token"]

    logger.info("Fetching new Token.")
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "resource": f"{BASE_URL}/"
    }

    response= requests.post(AUTH_URL, data=payload)

    if response.status_code == 200:
        access_token = response.json()["access_token"]
        expires_on = response.json()["expires_on"]

        token_data = {
            "access_token": access_token,
            "expires_on": expires_on
        }

        print(token_data["expires_on"])
        encrypt_token(token_data)
        return access_token
    else:
        logger.error(f"Failed to get token: {response.text}")
        raise Exception("Unable to authenticate with Azure")

def generate_key():
    """Generate and store a key for encryption."""
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)


def load_key():
    """Load the encryption key."""
    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

def encrypt_token(token):
    """Encrypt the token and save it securely."""
    generate_key()
    key = load_key()
    cipher = Fernet(key)

    encrypted_token = cipher.encrypt(json.dumps(token).encode())

    with open(TOKEN_FILE, "wb") as file:
        file.write(encrypted_token)

def decrypt_token():
    """Decrypt the stored token and return it."""
    if not os.path.exists(TOKEN_FILE):
        return None
    
    key = load_key()
    cipher = Fernet(key)

    with open(TOKEN_FILE, "rb") as file:
        encrypted_token = file.read()

    token = json.loads(cipher.decrypt(encrypted_token).decode())
    return token


def is_token_expired(expires_on):
    """Check if the token has expired."""
    expires_on = datetime.fromtimestamp(int(expires_on), tz=timezone.utc)
    return datetime.now(timezone.utc) >= expires_on

def remove_token():
    """Remove the stored token and key."""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        logger.info("Access token deleted.")

    if os.path.exists(KEY_FILE):
        os.remove(KEY_FILE)
        logger.info("Encryption key deleted.")