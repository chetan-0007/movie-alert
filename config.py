import configparser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.ini"

config = configparser.ConfigParser()
config.read(CONFIG_FILE)


def get_value(section, key, default=""):
    return config.get(section, key, fallback=default)


MOVIE_NAME = get_value("movie", "name", "odyssey")
CINEMA_NAME = get_value("movie", "cinema_name", "PVR Priya IMAX")
SHOW_DATE = get_value("movie", "show_date", "2026-07-17")
CINEMA_ID = get_value("movie", "cinema_id", "1022246")

BOT_TOKEN = get_value("telegram", "bot_token", "")
CHAT_ID = get_value("telegram", "chat_id", "")
DISTRICT_GUEST_TOKEN = get_value("district", "guest_token", "")

STATE_FILE = BASE_DIR / "state.json"
ALERTS_FILE = BASE_DIR / "alerts.json"
