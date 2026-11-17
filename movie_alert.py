import json
import re
from datetime import datetime

import requests

from config import (
    BOT_TOKEN,
    CHAT_ID,
    CINEMA_ID,
    CINEMA_NAME,
    DISTRICT_GUEST_TOKEN,
    MOVIE_NAME,
    SHOW_DATE,
    STATE_FILE,
)


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram config missing. Skipping notification.")
        return

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message},
        timeout=10,
    )
    print(f"Telegram status: {response.status_code}")


def fetch_movie_data():
    if not DISTRICT_GUEST_TOKEN:
        raise RuntimeError("Set district.guest_token in config.ini.")

    url = "https://www.district.in/gw/consumer/movies/v3/cinema"
    params = {
        "meta": 1,
        "reqData": 1,
        "version": 3,
        "site_id": 1,
        "channel": "mweb",
        "child_site_id": 1,
        "platform": "district",
        "cinemaId": CINEMA_ID,
        "date": SHOW_DATE,
    }
    headers = {
        "api_source": "district",
        "x-app-type": "ed_mweb",
        "x-guest-token": DISTRICT_GUEST_TOKEN,
        "user-agent": "Mozilla/5.0",
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    print(f"District status: {response.status_code}")

    if response.status_code != 200:
        send_telegram(f"⚠️ Movie Alert Error\nStatus Code: {response.status_code}")
        raise RuntimeError(f"District API failed: {response.status_code}")

    return response.json()


def get_movie(data):
    def normalize_title(title):
        return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())

    requested_title = normalize_title(MOVIE_NAME)
    available_movies = data.get("meta", {}).get("movies", [])
    movie = next(
        (
            item for item in available_movies
            if requested_title in normalize_title(item.get("name", ""))
        ),
        None,
    )

    if movie is None:
        return None

    return movie


def load_previous_ids():
    if not STATE_FILE.exists():
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return {str(item) for item in data}
    raise ValueError(f"Invalid state file format: {STATE_FILE}")


def save_current_ids(ids):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(sorted({str(item) for item in ids}), file)


def main():
    data = fetch_movie_data()
    movie = get_movie(data)

    if movie is None:
        save_current_ids(set())
        print(f"Movie not listed for {SHOW_DATE}; empty baseline saved.")
        return

    sessions = [
        session for session in data.get("pageData", {}).get("sessions", [])
        if session.get("mid") == movie.get("id")
    ]

    current_ids = {str(session.get("sid")) for session in sessions}
    previous_ids = load_previous_ids()

    print(f"Current Sessions: {current_ids}")
    print(f"Previous Sessions: {previous_ids}")

    if previous_ids is None:
        save_current_ids(current_ids)
        print("Baseline initialized")
        return

    new_ids = current_ids - previous_ids
    print(f"New Sessions: {new_ids}")

    if new_ids:
        for session in sessions:
            session_id = str(session.get("sid"))
            if session_id not in new_ids:
                continue

            show_time = datetime.fromisoformat(session["showTime"])
            send_telegram(
                "🎬 New Show Added!\n\n"
                f"Movie: {movie['name']}\n"
                f"Cinema: {CINEMA_NAME}\n"
                f"Date: {show_time.strftime('%d %b %Y')}\n"
                f"Time: {show_time.strftime('%I:%M %p')}"
            )

    save_current_ids(current_ids)


if __name__ == "__main__":
    main()