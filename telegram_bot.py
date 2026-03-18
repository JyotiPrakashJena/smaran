import requests
from database import get_telegram_groups, get_bot_token, mark_reviews_notified, today_ist, get_logs_due_summary
from logger import get_logger

log = get_logger("telegram")


def _escape(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def _send(group_id: str, text: str, token: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": group_id, "text": text, "parse_mode": "MarkdownV2"}, timeout=5)
        if not resp.ok:
            log.warning("Telegram send failed for group %s: %s", group_id, resp.text)
        else:
            log.info("Telegram message sent to group %s", group_id)
    except Exception as e:
        log.exception("Telegram request error for group %s: %s", group_id, e)


def send_daily_reminder(user_id: int, username: str, pending_reviews: list):
    bt = get_bot_token(user_id)
    if not bt["active"] or not bt["token"]:
        return

    from datetime import date
    today = str(today_ist())
    token = bt["token"]
    total = len(pending_reviews)
    overdue = [r for r in pending_reviews if r["due_date"] < today]

    # Group by subject
    grouped = {}
    for r in pending_reviews:
        grouped.setdefault(r["subject_name"], []).append(r["topic_name"])

    lines = [
        f"📚 *Smaran — UPSC Revision Reminder*",
        f"📅 {_escape(today)}  \\|  👤 {_escape(username)}",
        f"━━━━━━━━━━━━━━━━━━",
        f"📋 *Total Reviews:* {total}",
        f"⏰ *Pending from past:* {len(overdue)}",
        f"━━━━━━━━━━━━━━━━━━",
    ]

    for subject, topics in grouped.items():
        lines.append(f"\n📖 *{_escape(subject)}*")
        for topic in topics:
            lines.append(f"    ▪️ {_escape(topic)}")

    lines.append(f"\n━━━━━━━━━━━━━━━━━━\n⚡ _Smaran_")

    # Append Important Facts due
    facts_summary = get_logs_due_summary(user_id)
    if facts_summary:
        total_facts = sum(sum(t.values()) for t in facts_summary.values())
        lines.append(f"\n━━━━━━━━━━━━━━━━━━")
        lines.append(f"📝 *Important Facts Due:* {total_facts}")
        for subject, topics_dict in facts_summary.items():
            lines.append(f"\n📖 *{_escape(subject)}*")
            for topic_name, cnt in topics_dict.items():
                lines.append(f"    ▪️ {_escape(topic_name)}: {cnt}")
        lines.append(f"\n━━━━━━━━━━━━━━━━━━\n⚡ _Smaran_")
    else:
        pass  # footer already added above

    text = "\n".join(lines)
    groups = get_telegram_groups(user_id)
    sent = False
    for g in groups:
        if g["active"]:
            _send(g["group_id"], text, token)
            sent = True
    if sent:
        mark_reviews_notified(user_id)
