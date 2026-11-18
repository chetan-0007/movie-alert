import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from config import (
    BOT_TOKEN,
    CHAT_ID,
    CINEMA_ID,
    CINEMA_NAME,
    DISTRICT_GUEST_TOKEN,
    MOVIE_NAME,
    SHOW_DATES,
    STATE_FILE,
)

IST = timezone(timedelta(hours=5, minutes=30))  # no DST, works on Windows too
API_URL = "https://www.district.in/gw/consumer/movies/v1/cinema/sessions"
FAILURES_BEFORE_ALERT = 3  # only ping Telegram after N consecutive failed runs
FETCH_RETRIES = 3

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "api_source": "district",
    "referer": "https://www.district.in/movies/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "x-app-type": "ed_web",
    "x-guest-token": DISTRICT_GUEST_TOKEN,
}


# ---------- Telegram ----------

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram config missing. Skipping notification.")
        return

    # Telegram caps messages at 4096 chars; split on line boundaries.
    chunks, current = [], ""
    for line in message.split("\n"):
        if len(current) + len(line) + 1 > 3900:
            chunks.append(current)
            current = ""
        current += line + "\n"
    chunks.append(current)

    for chunk in chunks:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": chunk.strip()},
                timeout=10,
            )
            print(f"Telegram status: {response.status_code}")
        except requests.RequestException as exc:
            print(f"Telegram failed: {exc}")


# ---------- District API ----------

def fetch_day(http, date):
    params = {
        "meta": 1,
        "reqData": 1,
        "version": 3,
        "site_id": 1,
        "channel": "web",
        "child_site_id": 1,
        "platform": "district",
        "cinemaId": CINEMA_ID,
        "date": date,
    }
    last_error = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            response = http.get(API_URL, params=params, headers=HEADERS, timeout=30)
            print(f"[{date}] District status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            last_error = f"HTTP {response.status_code}: {response.text[:200]!r}"
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)
        time.sleep(2 * attempt)
    raise RuntimeError(f"{date}: {last_error}")


def normalize(title):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def matching_sessions(data):
    """All sessions of every listing of the movie (language/format variants)."""
    wanted = normalize(MOVIE_NAME)
    movie_ids = {
        m["id"]
        for m in data.get("meta", {}).get("movies", [])
        if wanted in normalize(m.get("name", ""))
    }
    return [
        s for s in data.get("pageData", {}).get("sessions", [])
        if s.get("mid") in movie_ids
    ]


def collect_sessions(http):
    """Returns (sessions_by_date, failed_dates)."""
    today = datetime.now(IST).strftime("%Y-%m-%d")
    by_date, failed = {}, []

    if SHOW_DATES == ["auto"]:
        first = fetch_day(http, today)  # a failure here is fatal
        dates = first.get("data", {}).get("sessionDates") or [today]
        cache = {today: first}
    else:
        dates, cache = SHOW_DATES, {}

    for date in dates:
        try:
            data = cache.get(date) or fetch_day(http, date)
            by_date[date] = matching_sessions(data)
        except RuntimeError as exc:
            print(f"Fetch failed: {exc}")
            failed.append(date)
    return by_date, failed


# ---------- State ----------

def load_state():
    if not STATE_FILE.exists():
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, list):  # old format: just a list of session ids
        return {"sessions": {str(sid): "" for sid in data}, "failures": 0}
    return {
        "sessions": data.get("sessions", {}),
        "failures": data.get("failures", 0),
    }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)


# ---------- Formatting ----------

def show_time_ist(session):
    """District sends showTime as UTC with no marker; the site displays IST."""
    naive = datetime.fromisoformat(session["showTime"])
    return naive.replace(tzinfo=timezone.utc).astimezone(IST)


def format_alert(new_sessions):
    new_sessions = sorted(new_sessions, key=show_time_ist)
    lines = [
        f"🎬 {len(new_sessions)} new show(s)!",
        f"Movie: {MOVIE_NAME.title()}",
        f"Cinema: {CINEMA_NAME}",
    ]
    current_date = None
    for s in new_sessions:
        t = show_time_ist(s)
        if t.date() != current_date:
            current_date = t.date()
            lines += ["", f"📅 {t.strftime('%a, %d %b %Y')}"]
        lines.append(
            f"• {t.strftime('%I:%M %p')} | {s.get('lang', '?')} | "
            f"{s.get('scrnFmt', '?')} | {s.get('audi', '?')}"
        )
    return "\n".join(lines)


# ---------- Main ----------

def main():
    if not DISTRICT_GUEST_TOKEN:
        raise RuntimeError("DISTRICT_GUEST_TOKEN is not set.")

    state = load_state()
    http = requests.Session()

    try:
        by_date, failed = collect_sessions(http)
    except RuntimeError as exc:
        failures = (state or {"failures": 0})["failures"] + 1
        print(f"Run failed ({failures} in a row): {exc}")
        if state is not None:
            state["failures"] = failures
            save_state(state)
        if failures == FAILURES_BEFORE_ALERT:
            send_telegram(f"⚠️ Movie Alert failing for {failures} runs in a row.\n{exc}")
        sys.exit(1)

    current = {
        str(s["sid"]): s for sessions in by_date.values() for s in sessions
    }
    date_of = {
        str(s["sid"]): d for d, sessions in by_date.items() for s in sessions
    }
    print(f"Dates checked: {sorted(by_date)} | failed: {failed}")
    print(f"Current sessions: {len(current)}")

    if state is None:  # first ever run: silent baseline (may be empty)
        save_state(
            {
                "sessions": date_of,
                "failures": 0,
            }
        )
        send_telegram(
            f"✅ Movie Alert started. Tracking {len(current)} existing show(s) "
            f"for {MOVIE_NAME.title()} at {CINEMA_NAME}."
        )
        return

    previous = state["sessions"]
    new_ids = set(current) - set(previous)
    print(f"New sessions: {sorted(new_ids)}")

    if new_ids:
        send_telegram(format_alert([current[sid] for sid in new_ids]))

    # Keep remembered sessions for dates we couldn't fetch this run, so a
    # transient failure doesn't make them look "new" next time.
    kept = {sid: d for sid, d in previous.items() if d in failed}
    kept.update(date_of)

    state["sessions"] = kept
    state["failures"] = 0 if not failed else state["failures"] + 1
    save_state(state)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
