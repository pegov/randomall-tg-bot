import json
import logging
from datetime import datetime, timezone

from randomall_tg_bot.config import DEBUG, LOG_PATH


class LevelFilter:
    def __init__(self, level):
        self._level = level

    def filter(self, log_record):
        return log_record.levelno == self._level


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if DEBUG:
    # handler = logging.StreamHandler()
    handler = logging.FileHandler(f"{LOG_PATH}/actions.log")
else:
    handler = logging.FileHandler(f"{LOG_PATH}/actions.log")

formatter = logging.Formatter("%(asctime)s %(message)s")
formatter.formatTime = (  # type: ignore
    lambda record, datefmt=None: datetime.fromtimestamp(record.created, timezone.utc)
    .astimezone()
    .isoformat(sep="T", timespec="milliseconds")
)

handler.setFormatter(formatter)

logger.addFilter(LevelFilter(level=logging.INFO))  # type: ignore
logger.addHandler(handler)


class Action:
    HELP = "help"
    GENERAL_INFO = "general_info"
    GENERAL_RESULT = "general_result"
    CUSTOM_INFO = "custom_info"
    CUSTOM_RESULT = "custom_result"


class Event:
    def __init__(self, action: str, user_id: int, payload: dict | None = None):
        self.action = action
        self.user_id = user_id
        self.payload = payload

    def to_json(self) -> str:
        if self.payload is None:
            return json.dumps(
                {
                    "action": self.action,
                    "user_id": self.user_id,
                }
            )
        else:
            return json.dumps(
                {
                    "action": self.action,
                    "user_id": self.user_id,
                    "payload": self.payload,
                }
            )


def log_event(event: Event):
    logger.info(event.to_json())
