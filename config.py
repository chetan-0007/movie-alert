import configparser
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.ini"

config = configparser.ConfigParser()
config.read(CONFIG_FILE)


def get_value(section, key, default=""):
    return config.get(section, key, fallback=default)


def env_or_ini(env_name, section, key, default=""):
    """Environment variable wins (GitHub Actions), config.ini is the local fallback."""
    return os.environ.get(env_name) or get_value(section, key, default)


MOVIE_NAME = env_or_ini("MOVIE_NAME", "movie", "name", "odyssey")
CINEMA_NAME = env_or_ini("CINEMA_NAME", "movie", "cinema_name", "PVR Priya IMAX")
CINEMA_ID = env_or_ini("CINEMA_ID", "movie", "cinema_id", "1022246")

# Comma-separated dates (2026-12-18,2026-12-19) or "auto" to watch every
# date District currently lists for the cinema.
_raw_dates = env_or_ini("SHOW_DATES", "movie", "show_dates", "") or get_value(
    "movie", "show_date", "auto"
)
SHOW_DATES = [d.strip() for d in _raw_dates.split(",") if d.strip()] or ["auto"]

BOT_TOKEN = env_or_ini("BOT_TOKEN", "telegram", "bot_token")
CHAT_ID = env_or_ini("CHAT_ID", "telegram", "chat_id")
DISTRICT_GUEST_TOKEN = env_or_ini("DISTRICT_GUEST_TOKEN", "district", "guest_token")

STATE_FILE = BASE_DIR / "state.json"