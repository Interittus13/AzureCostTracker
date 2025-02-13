import requests
from src.config import CLIENT_ID, CLIENT_SECRET, BASE_URL, AUTH_URL

def get_access_token():
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "resource": f"{BASE_URL}/"
    }

    response= requests.post(AUTH_URL, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]