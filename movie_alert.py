import requests
import json
from pathlib import Path
from datetime import datetime
import os

# =========================
# CONFIG
# =========================

MOVIE_NAME = "odyssey"
CINEMA_NAME = "PVR Priya IMAX"
SHOW_DATE = "2026-07-17"

STATE_FILE = "state.json"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
DISTRICT_GUEST_TOKEN = os.environ["DISTRICT_GUEST_TOKEN"]

# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

    print("Telegram:", response.status_code)


# =========================
# DISTRICT API
# =========================

url = "https://www.district.in/gw/consumer/movies/v3/cinema"

params = {
    "meta": 1,
    "reqData": 1,
    "version": 3,
    "site_id": 1,
    "channel": "mweb",
    "child_site_id": 1,
    "platform": "district",
    "cinemaId": "1022246",
    "date": SHOW_DATE
}

headers = {
    "api_source": "district",
    "x-app-type": "ed_mweb",
    "x-guest-token": DISTRICT_GUEST_TOKEN,
    "user-agent": "Mozilla/5.0"
}

print("Calling District API...")

r = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30
)

print("Status:", r.status_code)

if r.status_code != 200:
    send_telegram(
        f"⚠️ Movie Alert Bot Error\n"
        f"Status Code: {r.status_code}"
    )
    raise Exception(f"District API failed: {r.status_code}")

data = r.json()

# =========================
# FIND MOVIE
# =========================

movie = next(
    (
        m for m in data["meta"]["movies"]
        if MOVIE_NAME.lower() in m["name"].lower()
    ),
    None
)

if movie is None:
    send_telegram(
        f"⚠️ Movie not found: {MOVIE_NAME}"
    )
    raise Exception("Movie not found")

print("Movie Found:", movie["name"])

# =========================
# FIND SESSIONS
# =========================

sessions = [
    s for s in data["pageData"]["sessions"]
    if s["mid"] == movie["id"]
]

current_ids = {s["sid"] for s in sessions}

print("Current Sessions:", current_ids)

# =========================
# FIRST RUN
# =========================

if not Path(STATE_FILE).exists():

    with open(STATE_FILE, "w") as f:
        json.dump(list(current_ids), f)

    print("Baseline created")

    exit()

# =========================
# LOAD OLD STATE
# =========================

with open(STATE_FILE) as f:
    previous_ids = set(json.load(f))

# empty file
if len(previous_ids) == 0:

    with open(STATE_FILE, "w") as f:
        json.dump(list(current_ids), f)

    print("Baseline initialized")

    exit()

print("Previous Sessions:", previous_ids)

# =========================
# NEW SHOW DETECTION
# =========================

new_ids = current_ids - previous_ids

print("New Sessions:", new_ids)

if new_ids:

    for s in sessions:

        if s["sid"] in new_ids:

            show_time = datetime.fromisoformat(
                s["showTime"]
            )

            send_telegram(
                f"🎬 New Show Added!\n\n"
                f"Movie: {movie['name']}\n"
                f"Cinema: {CINEMA_NAME}\n"
                f"Date: {show_time.strftime('%d %b %Y')}\n"
                f"Time: {show_time.strftime('%I:%M %p')}"
            )

# =========================
# SAVE NEW STATE
# =========================

with open(STATE_FILE, "w") as f:
    json.dump(list(current_ids), f)