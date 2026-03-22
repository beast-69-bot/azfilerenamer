"""
Telegram File Manager Bot - Configuration
"""

import os
import tempfile
from pathlib import Path


def _load_dotenv_file() -> None:
    """Load values from a local .env file when they are not already set."""
    if os.environ.get("BOT_TOKEN"):
        return

    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv_file()

# Bot Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Storage Configuration
TEMP_DIR = os.environ.get(
    "TEMP_DIR",
    os.path.join(tempfile.gettempdir(), "telegram_bot"),
)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit
FILES_PER_PAGE = 20  # Pagination for file list

# Upload Configuration
UPLOAD_DELAY = 1  # Seconds between uploads to avoid rate limits

# Messages
WELCOME_MESSAGE = """
Welcome to File Manager Bot.

I can help you manage ZIP and RAR files:
- Extract and view file contents
- Upload files individually or all at once
- Rename files before downloading
- Get a new ZIP with renamed files

How to use:
1. Send me a ZIP or RAR file
2. I'll show you the contents
3. Use buttons to upload or rename
"""

HELP_MESSAGE = """
Help - File Manager Bot

Commands:
/start - Start the bot
/help - Show this help message
/cancel - Cancel current operation

Features:
- Send any ZIP or RAR file
- View the file list with upload buttons
- Upload all files at once
- Rename files before downloading a new ZIP

Note: Max file size is 50MB.
"""
