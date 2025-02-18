import logging
from logging.handlers import RotatingFileHandler
import os

# Log file path
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configure rotating log handler
FILE_HANDLER = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 5MB per file, keep last 5 logs
)
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        FILE_HANDLER,
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ACT")
