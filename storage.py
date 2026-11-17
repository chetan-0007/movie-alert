import json

from config import ALERTS_FILE


def ensure_alert_file():
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ALERTS_FILE.exists():
        ALERTS_FILE.write_text("[]", encoding="utf-8")


def load_alerts():
    ensure_alert_file()
    with open(ALERTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_alerts(alerts):
    ensure_alert_file()
    with open(ALERTS_FILE, "w", encoding="utf-8") as file:
        json.dump(alerts, file, indent=4)


def add_alert(chat_id, movie_name, cinema_id, cinema_name, show_date):
    alerts = load_alerts()

    for alert in alerts:
        if (
            alert.get("chat_id") == chat_id
            and alert.get("movie_name", "").lower() == movie_name.lower()
            and alert.get("cinema_id") == cinema_id
            and alert.get("show_date") == show_date
        ):
            return None

    next_id = max((alert.get("id", 0) for alert in alerts), default=0) + 1
    alert = {
        "id": next_id,
        "chat_id": chat_id,
        "movie_name": movie_name,
        "cinema_id": cinema_id,
        "cinema_name": cinema_name,
        "show_date": show_date,
    }
    alerts.append(alert)
    save_alerts(alerts)
    return next_id
