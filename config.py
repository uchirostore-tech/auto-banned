import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN is missing! Please provide it in environment variables or .env file.")

ADMIN_IDS_RAW = os.getenv("ADMIN_ID", "").strip()
ADMIN_IDS = []
if ADMIN_IDS_RAW:
    for aid in ADMIN_IDS_RAW.split(","):
        aid = aid.strip()
        if aid.lstrip("-").isdigit():
            ADMIN_IDS.append(int(aid))

# Database configuration
DB_PATH = os.getenv("DB_PATH", "data/bot.db").strip()
db_dir = Path(DB_PATH).parent
if db_dir and not db_dir.exists():
    db_dir.mkdir(parents=True, exist_ok=True)

# Optional log channel/group ID where ban alerts are also sent
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "").strip()
LOG_CHANNEL_ID = int(LOG_CHANNEL_ID) if LOG_CHANNEL_ID.lstrip("-").isdigit() else None
