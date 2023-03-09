import os

from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "1") == "1"

TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN", "")
TELEGRAM_WEBHOOK_HOST = os.getenv("TELEGRAM_WEBHOOK_HOST", "")
TELEGRAM_WEBHOOK_PORT = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "5001"))
TELEGRAM_WEBHOOK_PATH = os.getenv("TELEGRAM_WEBHOOK_PATH", "")
TELEGRAM_WEBHOOK_URL = f"{TELEGRAM_WEBHOOK_HOST}{TELEGRAM_WEBHOOK_PATH}"

MQ_URL = os.getenv("MQ_URL", "amqp://rmuser:rmpassword@127.0.0.1:5672/%2f")
