import os

from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "1") == "1"

TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN", "")

TELEGRAM_WEBAPP_HOST = os.getenv("TELEGRAM_WEBAPP_HOST", "")
TELEGRAM_WEBAPP_PORT = os.getenv("TELEGRAM_WEBAPP_PORT", "5001")

TELEGRAM_WEBHOOK_HOST = os.getenv("TELEGRAM_WEBHOOK_HOST", "")
TELEGRAM_WEBHOOK_PATH = os.getenv("TELEGRAM_WEBHOOK_PATH", "")
TELEGRAM_WEBHOOK_URL = f"{TELEGRAM_WEBHOOK_HOST}{TELEGRAM_WEBHOOK_PATH}"

MQ_URL = os.getenv("MQ_URL", "amqp://rmuser:rmpassword@127.0.0.1:5672/%2f")
