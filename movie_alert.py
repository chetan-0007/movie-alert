import requests
import json
from pathlib import Path
from datetime import datetime
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
DISTRICT_GUEST_TOKEN = os.environ["DISTRICT_GUEST_TOKEN"]

url = "https://www.district.in/gw/consumer/movies/v3/cinema"

movie_name = "odyssey"
state_file = "state.json"


def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

send_telegram("GitHub Action works!")

params = {
    "meta": 1,
    "reqData": 1,
    "version": 3,
    "site_id": 1,
    "channel": "mweb",
    "child_site_id": 1,
    "platform": "district",
    "cinemaId": "1022246",
    "date": "2026-07-17"
}

headers = {
    "api_source": "district",
    "x-app-type": "ed_mweb",
    "x-guest-token": DISTRICT_GUEST_TOKEN,
    "user-agent": "Mozilla/5.0"
}

r = requests.get(url, params=params, headers=headers)
data = r.json()

# Find movie
movie = next(
    (
        m for m in data["meta"]["movies"]
        if movie_name.lower() in m["name"].lower()
    ),
    None
)

if not movie:
    print("Movie not found")
    exit()

# Get sessions for this movie
sessions = [
    s for s in data["pageData"]["sessions"]
    if s["mid"] == movie["id"]
]

current_ids = {s["sid"] for s in sessions}

# First run
if not Path(state_file).exists():
    with open(state_file, "w") as f:
        json.dump(list(current_ids), f)

    print("Baseline saved")
    exit()

# Load previous state
with open(state_file) as f:
    previous_ids = set(json.load(f))

new_ids = current_ids - previous_ids

if new_ids:
    print("🚨 New show(s) added!")

    for s in sessions:
        if s["sid"] in new_ids:
            show_time = datetime.fromisoformat(s["showTime"])

            send_telegram(
                f"🎬 New Odyssey Show!\n\n"
                f"📍 PVR Priya IMAX\n"
                f"🕒 {show_time.strftime('%I:%M %p')}"
            )

# Save latest state
with open(state_file, "w") as f:
    json.dump(list(current_ids), f)
