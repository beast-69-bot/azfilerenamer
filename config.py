"""
Telegram File Manager Bot - Configuration
"""

import os
import tempfile
from pathlib import Path


def _load_dotenv_file() -> None:
    """Load values from a local .env file when they are not already set."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _parse_admin_ids(raw_value: str) -> set[int]:
    """Parse comma-separated admin IDs from the environment."""
    admin_ids: set[int] = set()
    for chunk in raw_value.split(","):
        value = chunk.strip()
        if not value:
            continue
        if value.lstrip("-").isdigit():
            admin_ids.add(int(value))
    return admin_ids


_load_dotenv_file()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = _parse_admin_ids(os.environ.get("ADMIN_IDS", ""))

TEMP_DIR = os.environ.get(
    "TEMP_DIR",
    os.path.join(tempfile.gettempdir(), "telegram_bot"),
)
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(DATA_DIR / "bot.db"))
MAX_FILE_SIZE = 50 * 1024 * 1024
FILES_PER_PAGE = 20

UPLOAD_DELAY = 1
FREE_UPLOAD_CONCURRENCY = 1
PREMIUM_UPLOAD_CONCURRENCY = 3
FREE_DOWNLOAD_CHUNK_SIZE = 64 * 1024
PREMIUM_DOWNLOAD_CHUNK_SIZE = 256 * 1024
PROGRESS_UPDATE_INTERVAL = 0.8

BOT_TITLE = "AZ File Renamer"
FREE_PLAN_NAME = "Free"
PREMIUM_PLAN_NAME = "Premium"
