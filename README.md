# movie-alert

A small Python watcher for a movie schedule.

It checks the District API for a movie and cinema, stores the last known session IDs in `state.json`, and sends a Telegram message when a new show is added.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `config.ini` file in the project root and update the values:
   ```ini
   [movie]
   name = odyssey
   cinema_name = PVR Priya IMAX
   show_date = 2026-07-17
   cinema_id = 1022246

   [telegram]
   bot_token = your_bot_token
   chat_id = your_chat_id

   [district]
   guest_token = your_guest_token
   ```
3. Run the watcher:
   ```bash
   python movie_alert.py
   ```

## Notes

- This project is intentionally lightweight and not production-ready.
- `state.json` is created automatically and stores the last seen session IDs.
- If the movie is not listed yet, the watcher saves an empty baseline without raising an error. When sessions appear later, they are treated as new and trigger notifications.
- `alerts.json` is kept for the optional simple alert list helper in `storage.py`.
