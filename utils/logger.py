import logging
import os
from datetime import datetime, timezone

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(APP_ROOT, "activity.log")

_logger = logging.getLogger("quizzin_activity")
_logger.setLevel(logging.INFO)

_fh = logging.FileHandler(LOG_FILE)
_fh.setLevel(logging.INFO)

_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_fh.setFormatter(_formatter)
_logger.addHandler(_fh)


def log_action(user_id, action: str, endpoint: str = "", detail: str = "", ip: str = ""):
    ts = datetime.now(timezone.utc).isoformat()
    parts = [
        f"user_id={user_id}",
        f"action={action}",
    ]
    if endpoint:
        parts.append(f"endpoint={endpoint}")
    if ip:
        parts.append(f"ip={ip}")
    if detail:
        parts.append(f"detail={detail}")
    _logger.info(" | ".join(parts))
