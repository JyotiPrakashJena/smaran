import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from database import get_all_users_with_pending_reviews, get_reviews_for_date, today_ist
from logger import get_logger

_scheduler = BackgroundScheduler(executors={"default": ThreadPoolExecutor(max_workers=1)})
_started = False
log = get_logger("scheduler")


def _send_daily_reminders():
    from telegram_bot import send_daily_reminder
    today = str(today_ist())
    users = get_all_users_with_pending_reviews()
    for u in users:
        try:
            pending = get_reviews_for_date(u["user_id"], today)
            if pending:
                send_daily_reminder(u["user_id"], u["username"], pending)
                log.info("Reminder sent to %s (%d pending)", u["username"], len(pending))
        except Exception as e:
            log.exception("Failed to send reminder for user %s: %s", u["username"], e)


def start_scheduler():
    global _started
    if not _started:
        _scheduler.add_job(
            _send_daily_reminders,
            trigger=CronTrigger(hour=8, minute=0),
            id="daily_reminder",
            replace_existing=True,
            max_instances=1,
        )
        _scheduler.start()
        _started = True
        log.info("Scheduler started — Smaran daily reminders at 08:00")
        # Run immediately on startup — safe because notified_date deduplication
        # prevents re-sending if already notified today
        import threading
        threading.Thread(target=_send_daily_reminders, daemon=True).start()
