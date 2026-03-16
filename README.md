# Smaran — UPSC Spaced Revision Tracker

> *Smaran* (Sanskrit: स्मरण) means **remembrance**.

A personal spaced-repetition tracker built for UPSC preparation. Log what you read, get reminded when to revise, and never let a topic slip through the cracks.

---

## Features

- **Spaced Revision** — Intervals of 1 → 3 → 7 → 15 → 30 days. Each reading entry auto-creates 5 review tasks
- **Multi-user** — Independent data per account, fully isolated by `user_id`
- **Dashboard** — Review stats + GitHub-style monthly activity heatmap
- **Subject & Topic Manager** — Organise notes with file attachments
- **Exams Countdown** — Color-coded badges (green / purple / amber / red / grey) by days remaining
- **Telegram Notifications** — Daily 08:00 IST reminders grouped by subject → topics, with dedup so restarts don't re-notify
- **Session Persistence** — Token-based sessions survive Streamlit Cloud restarts

---

## Tech Stack

| Layer | Choice |
|---|---|
| UI | Streamlit |
| Database | SQLite (`data/smaran.db`) |
| Scheduler | APScheduler (CronTrigger) |
| Notifications | Telegram Bot API |
| Timezone | IST (UTC+5:30) throughout |

---

## Project Structure

```
smaran/
├── app.py              # Main Streamlit app (5 tabs)
├── database.py         # All DB logic, IST helpers, spaced revision functions
├── scheduler.py        # APScheduler — daily 08:00 IST job
├── telegram_bot.py     # Telegram notification sender
├── styling.py          # Purple theme + custom CSS
├── logger.py           # Rotating file logger
├── requirements.txt
├── data/
│   └── smaran.db       # SQLite DB (tracked in git for Streamlit Cloud)
├── logs/
│   └── smaran.log      # App logs (tracked in git for Streamlit Cloud)
└── .streamlit/
    └── config.toml     # Theme config
```

---

## Local Setup

```bash
git clone <repo-url>
cd smaran
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

---

## Streamlit Cloud Deployment

1. Push this repo to GitHub
2. Connect it on [share.streamlit.io](https://share.streamlit.io)
3. Add secrets under **App Settings → Secrets**:

```toml
[telegram]
bot_token = "<your-bot-token>"
```

> `data/smaran.db` and `logs/smaran.log` are intentionally tracked in git so Streamlit Cloud's free tier (no persistent disk) has them on cold start.

---

## Spaced Revision Logic

Each time you log a reading entry, 5 review tasks are created automatically:

| Review | Due after |
|---|---|
| R1 | 1 day |
| R2 | 3 days |
| R3 | 7 days |
| R4 | 15 days |
| R5 | 30 days |

Overdue items stack and remain visible until marked done.

---

## Telegram Notification Format

```
📚 Smaran — Daily Revision Reminder
📅 15 Jan 2025 | 👤 username

📊 Total Reviews Today: 8
⏰ Pending from Past: 3

History
  • Medieval India (R2)
  • Modern India (R3)

Polity
  • Fundamental Rights (R1)
```

Notifications are deduplicated via a `notified_date` stamp — restarting the app won't re-send.
