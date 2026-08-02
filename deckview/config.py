import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "deckview"
CACHE_DIR = Path(
    os.getenv("DECKVIEW_CACHE_DIR") or DEFAULT_CACHE_DIR
).expanduser()
CARDS_DIR = CACHE_DIR / "cards"

VK_TOKEN = os.getenv("VK_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

DISCORD_LOGIN_TIMEOUT = float(os.getenv("DISCORD_LOGIN_TIMEOUT", "30"))
DISCORD_MESSAGE_CONTENT_INTENT = os.getenv(
    "DISCORD_MESSAGE_CONTENT_INTENT", "false"
).lower() in {"1", "true", "yes", "on"}

CARD_COSTS = {
    1: 0,
    2: 40,
    3: 100,
    4: 400,
    5: 1600,
    None: 0,
}

BANNED_PEERS = set()
