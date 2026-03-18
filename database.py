import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, date, timezone, timedelta
from git_sync import push_db

DB_PATH = Path(__file__).parent / "data" / "smaran.db"
# Research-backed spaced repetition intervals (days) for long-term retention.
# Based on Ebbinghaus forgetting curve: review at 1d, 3d, 7d, 14d, 30d, 60d, 120d.
SPACED_INTERVALS = [1, 3, 7, 14, 30, 60, 120]
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    return datetime.now(IST)


def today_ist() -> date:
    return now_ist().date()


def fmt_ist(dt_str: str) -> str:
    """Parse a stored UTC-naive datetime string and display in IST 12hr format."""
    if not dt_str:
        return ""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone(IST)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return dt_str


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, name)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            source TEXT,
            tags TEXT,
            created_at TEXT NOT NULL,
            last_revised_at TEXT,
            UNIQUE(user_id, subject_id, name)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_data BLOB NOT NULL,
            uploaded_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            read_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            interval_index INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            notified_date TEXT
        )
    """)
    # migrate existing DB
    try:
        c.execute("ALTER TABLE reviews ADD COLUMN notified_date TEXT")
    except Exception:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (user_id, key)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS telegram_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            group_id TEXT NOT NULL,
            label TEXT,
            active INTEGER DEFAULT 1,
            UNIQUE(user_id, group_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER")
    except Exception:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            answer TEXT NOT NULL,
            tag TEXT,
            source TEXT,
            image_path TEXT,
            interval_index INTEGER NOT NULL DEFAULT 0,
            next_review_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ── Exams ────────────────────────────────────────────────────────────────────

def get_exams(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM exams WHERE user_id=? ORDER BY exam_date ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_exam(user_id: int, name: str, exam_date: str) -> tuple[bool, str]:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO exams (user_id, name, exam_date, created_at) VALUES (?,?,?,?)",
            (user_id, name.strip(), exam_date, now_ist().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        push_db()
        return True, "Exam added."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_exam(user_id: int, exam_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM exams WHERE user_id=? AND id=?", (user_id, exam_id))
    conn.commit()
    conn.close()
    push_db()


# ── Sessions ─────────────────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?,?,?)",
        (token, user_id, now_ist().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    push_db()
    return token


def get_session_user(token: str):
    if not token:
        return None
    conn = get_conn()
    row = conn.execute(
        "SELECT u.* FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token=?",
        (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(token: str):
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()
    push_db()


# ── Auth ──────────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, password: str) -> tuple[bool, str]:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)",
            (username.strip(), _hash(password), now_ist().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        push_db()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def login_user(username: str, password: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=?",
        (username.strip(), _hash(password))
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Subjects ──────────────────────────────────────────────────────────────────

def get_subjects(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM subjects WHERE user_id=? ORDER BY name", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_subject(user_id: int, name: str) -> tuple[bool, str]:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO subjects (user_id, name, created_at) VALUES (?,?,?)",
            (user_id, name.strip(), now_ist().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        push_db()
        return True, "Subject added."
    except sqlite3.IntegrityError:
        return False, "Subject already exists."
    finally:
        conn.close()


def delete_subject(user_id: int, subject_id: int):
    conn = get_conn()
    topic_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM topics WHERE user_id=? AND subject_id=?", (user_id, subject_id)
    ).fetchall()]
    for tid in topic_ids:
        entry_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM entries WHERE user_id=? AND topic_id=?", (user_id, tid)
        ).fetchall()]
        for eid in entry_ids:
            conn.execute("DELETE FROM reviews WHERE user_id=? AND entry_id=?", (user_id, eid))
        conn.execute("DELETE FROM entries WHERE user_id=? AND topic_id=?", (user_id, tid))
        conn.execute("DELETE FROM attachments WHERE user_id=? AND topic_id=?", (user_id, tid))
    conn.execute("DELETE FROM topics WHERE user_id=? AND subject_id=?", (user_id, subject_id))
    conn.execute("DELETE FROM subjects WHERE user_id=? AND id=?", (user_id, subject_id))
    conn.commit()
    conn.close()
    push_db()


# ── Topics ────────────────────────────────────────────────────────────────────

def get_topics(user_id: int, subject_id: int = None):
    conn = get_conn()
    if subject_id:
        rows = conn.execute(
            "SELECT t.*, s.name as subject_name FROM topics t JOIN subjects s ON t.subject_id=s.id "
            "WHERE t.user_id=? AND t.subject_id=? ORDER BY t.name",
            (user_id, subject_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT t.*, s.name as subject_name FROM topics t JOIN subjects s ON t.subject_id=s.id "
            "WHERE t.user_id=? ORDER BY s.name, t.name",
            (user_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_topic(user_id: int, subject_id: int, name: str, source: str = "", tags: str = "") -> tuple[bool, str, int]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO topics (user_id, subject_id, name, source, tags, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, subject_id, name.strip(), source.strip(), tags.strip(),
             now_ist().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        push_db()
        return True, "Topic added.", cur.lastrowid
    except sqlite3.IntegrityError:
        return False, "Topic already exists in this subject.", -1
    finally:
        conn.close()


def delete_topic(user_id: int, topic_id: int):
    conn = get_conn()
    entry_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM entries WHERE user_id=? AND topic_id=?", (user_id, topic_id)
    ).fetchall()]
    for eid in entry_ids:
        conn.execute("DELETE FROM reviews WHERE user_id=? AND entry_id=?", (user_id, eid))
    conn.execute("DELETE FROM entries WHERE user_id=? AND topic_id=?", (user_id, topic_id))
    conn.execute("DELETE FROM attachments WHERE user_id=? AND topic_id=?", (user_id, topic_id))
    conn.execute("DELETE FROM topics WHERE user_id=? AND id=?", (user_id, topic_id))
    conn.commit()
    conn.close()
    push_db()


# ── Attachments ───────────────────────────────────────────────────────────────

def add_attachment(user_id: int, topic_id: int, filename: str, file_data: bytes):
    conn = get_conn()
    conn.execute(
        "INSERT INTO attachments (topic_id, user_id, filename, file_data, uploaded_at) VALUES (?,?,?,?,?)",
        (topic_id, user_id, filename, file_data, now_ist().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    push_db()


def get_attachments(user_id: int, topic_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, filename, uploaded_at FROM attachments WHERE user_id=? AND topic_id=?",
        (user_id, topic_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attachment_data(user_id: int, attachment_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT filename, file_data FROM attachments WHERE user_id=? AND id=?",
        (user_id, attachment_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_attachment(user_id: int, attachment_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM attachments WHERE user_id=? AND id=?", (user_id, attachment_id))
    conn.commit()
    conn.close()
    push_db()


# ── Entries ───────────────────────────────────────────────────────────────────

def add_entry(user_id: int, topic_id: int, read_date: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO entries (user_id, topic_id, read_date, created_at) VALUES (?,?,?,?)",
        (user_id, topic_id, read_date, now_ist().strftime("%Y-%m-%d %H:%M:%S"))
    )
    entry_id = cur.lastrowid
    conn.execute(
        "UPDATE topics SET last_revised_at=? WHERE user_id=? AND id=?",
        (read_date, user_id, topic_id)
    )
    conn.commit()
    conn.close()
    _create_review_schedule(user_id, entry_id, topic_id, read_date)
    push_db()
    return entry_id


def _create_review_schedule(user_id: int, entry_id: int, topic_id: int, read_date: str):
    from datetime import timedelta
    conn = get_conn()
    base = datetime.strptime(read_date, "%Y-%m-%d").date()
    for idx, days in enumerate(SPACED_INTERVALS):
        due = base + timedelta(days=days)
        conn.execute(
            "INSERT INTO reviews (user_id, entry_id, topic_id, due_date, interval_index, status) VALUES (?,?,?,?,?,?)",
            (user_id, entry_id, topic_id, str(due), idx, "pending")
        )
    conn.commit()
    conn.close()


def get_entries(user_id: int, date_filter: str = None):
    conn = get_conn()
    query = """
        SELECT e.*, t.name as topic_name, s.name as subject_name
        FROM entries e
        JOIN topics t ON e.topic_id = t.id
        JOIN subjects s ON t.subject_id = s.id
        WHERE e.user_id=?
    """
    params = [user_id]
    if date_filter:
        query += " AND e.read_date=?"
        params.append(date_filter)
    query += " ORDER BY e.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Reviews ───────────────────────────────────────────────────────────────────

def get_reviews_for_date(user_id: int, for_date: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT r.*, t.name as topic_name, s.name as subject_name,
               e.read_date as original_read_date
        FROM reviews r
        JOIN topics t ON r.topic_id = t.id
        JOIN subjects s ON t.subject_id = s.id
        JOIN entries e ON r.entry_id = e.id
        WHERE r.user_id=? AND r.due_date<=? AND r.status='pending'
        ORDER BY r.due_date ASC
    """, (user_id, for_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_review(user_id: int, review_id: int):
    from datetime import timedelta
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM reviews WHERE user_id=? AND id=?", (user_id, review_id)
    ).fetchone()
    if not row:
        conn.close()
        return
    row = dict(row)
    now = now_ist().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE reviews SET status='completed', completed_at=? WHERE id=?",
        (now, review_id)
    )
    conn.execute(
        "UPDATE topics SET last_revised_at=? WHERE user_id=? AND id=?",
        (today_ist().strftime("%Y-%m-%d"), user_id, row["topic_id"])
    )
    conn.commit()
    conn.close()
    push_db()


def get_review_stats(user_id: int):
    conn = get_conn()
    today = today_ist().strftime("%Y-%m-%d")
    pending_today = conn.execute(
        "SELECT COUNT(*) as cnt FROM reviews WHERE user_id=? AND due_date<=? AND status='pending'",
        (user_id, today)
    ).fetchone()["cnt"]
    total_completed = conn.execute(
        "SELECT COUNT(*) as cnt FROM reviews WHERE user_id=? AND status='completed'",
        (user_id,)
    ).fetchone()["cnt"]
    total_subjects = conn.execute(
        "SELECT COUNT(*) as cnt FROM subjects WHERE user_id=?", (user_id,)
    ).fetchone()["cnt"]
    total_topics = conn.execute(
        "SELECT COUNT(*) as cnt FROM topics WHERE user_id=?", (user_id,)
    ).fetchone()["cnt"]
    conn.close()
    return {
        "pending_today": pending_today,
        "total_completed": total_completed,
        "total_subjects": total_subjects,
        "total_topics": total_topics,
    }


def get_monthly_activity(user_id: int, year: int, month: int) -> set:
    """Returns a set of days (1-31) where user had activity (entry logged or review completed)."""
    conn = get_conn()
    prefix = f"{year}-{month:02d}-"
    entry_days = {int(r["d"]) for r in conn.execute(
        "SELECT strftime('%d', read_date) as d FROM entries WHERE user_id=? AND read_date LIKE ?",
        (user_id, prefix + "%")
    ).fetchall()}
    review_days = {int(r["d"]) for r in conn.execute(
        "SELECT strftime('%d', completed_at) as d FROM reviews WHERE user_id=? AND completed_at LIKE ?",
        (user_id, prefix + "%")
    ).fetchall()}
    conn.close()
    return entry_days | review_days


# ── Telegram ──────────────────────────────────────────────────────────────────

def get_bot_token(user_id: int) -> dict:
    conn = get_conn()
    t = conn.execute("SELECT value FROM settings WHERE user_id=? AND key='bot_token'", (user_id,)).fetchone()
    a = conn.execute("SELECT value FROM settings WHERE user_id=? AND key='bot_token_active'", (user_id,)).fetchone()
    conn.close()
    return {"token": t["value"] if t else "", "active": (a["value"] == "1") if a else True}


def save_bot_token(user_id: int, token: str):
    conn = get_conn()
    conn.execute("INSERT INTO settings (user_id,key,value) VALUES (?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                 (user_id, "bot_token", token))
    conn.execute("INSERT INTO settings (user_id,key,value) VALUES (?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value='1'",
                 (user_id, "bot_token_active", "1"))
    conn.commit()
    conn.close()
    push_db()


def set_bot_token_active(user_id: int, active: bool):
    conn = get_conn()
    conn.execute("INSERT INTO settings (user_id,key,value) VALUES (?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                 (user_id, "bot_token_active", "1" if active else "0"))
    conn.commit()
    conn.close()
    push_db()


def delete_bot_token(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE settings SET value='' WHERE user_id=? AND key='bot_token'", (user_id,))
    conn.execute("UPDATE settings SET value='1' WHERE user_id=? AND key='bot_token_active'", (user_id,))
    conn.commit()
    conn.close()
    push_db()


def get_telegram_groups(user_id: int):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM telegram_groups WHERE user_id=? ORDER BY id", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_telegram_group(user_id: int, group_id: str, label: str):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO telegram_groups (user_id, group_id, label) VALUES (?,?,?)",
                 (user_id, group_id, label))
    conn.commit()
    conn.close()
    push_db()


def toggle_telegram_group(user_id: int, row_id: int, active: bool):
    conn = get_conn()
    conn.execute("UPDATE telegram_groups SET active=? WHERE user_id=? AND id=?",
                 (1 if active else 0, user_id, row_id))
    conn.commit()
    conn.close()
    push_db()


def delete_telegram_group(user_id: int, row_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM telegram_groups WHERE user_id=? AND id=?", (user_id, row_id))
    conn.commit()
    conn.close()
    push_db()


def get_all_users_with_pending_reviews():
    """Returns users who have pending reviews due today that have NOT been notified today."""
    conn = get_conn()
    today = today_ist().strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT DISTINCT u.id as user_id, u.username
        FROM users u
        JOIN reviews r ON r.user_id = u.id
        WHERE r.due_date<=? AND r.status='pending'
          AND (r.notified_date IS NULL OR r.notified_date != ?)
    """, (today, today)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_reviews_notified(user_id: int):
    """Stamp today's date on all pending due reviews for this user so they won't be re-notified."""
    conn = get_conn()
    today = today_ist().strftime("%Y-%m-%d")
    conn.execute("""
        UPDATE reviews SET notified_date=?
        WHERE user_id=? AND due_date<=? AND status='pending'
          AND (notified_date IS NULL OR notified_date != ?)
    """, (today, user_id, today, today))
    conn.commit()
    conn.close()
    push_db()


# ── Important Facts Logs ──────────────────────────────────────────────────────

LOG_INTERVALS = SPACED_INTERVALS  # shared — same science applies to both


def add_log(user_id: int, subject_id: int, topic_id: int, prompt: str, answer: str,
            tag: str = "", source: str = "", image_path: str = "", log_date: str = "") -> tuple[bool, str]:
    from datetime import timedelta
    conn = get_conn()
    try:
        base = datetime.strptime(log_date, "%Y-%m-%d").date() if log_date else today_ist()
        tomorrow = (base + timedelta(days=1)).strftime("%Y-%m-%d")
        conn.execute(
            """INSERT INTO logs (user_id, subject_id, topic_id, prompt, answer, tag, source,
               image_path, interval_index, next_review_date, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, subject_id, topic_id, prompt.strip(), answer.strip(),
             tag.strip(), source.strip(), image_path, 0, tomorrow,
             now_ist().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        push_db()
        return True, "Log added."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_logs(user_id: int, subject_id: int = None, topic_id: int = None):
    conn = get_conn()
    query = """
        SELECT l.*, s.name as subject_name, t.name as topic_name
        FROM logs l
        JOIN subjects s ON l.subject_id = s.id
        JOIN topics t ON l.topic_id = t.id
        WHERE l.user_id=?
    """
    params = [user_id]
    if subject_id:
        query += " AND l.subject_id=?"
        params.append(subject_id)
    if topic_id:
        query += " AND l.topic_id=?"
        params.append(topic_id)
    query += " ORDER BY l.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_logs_due_today(user_id: int):
    today = today_ist().strftime("%Y-%m-%d")
    conn = get_conn()
    rows = conn.execute("""
        SELECT l.*, s.name as subject_name, t.name as topic_name
        FROM logs l
        JOIN subjects s ON l.subject_id = s.id
        JOIN topics t ON l.topic_id = t.id
        WHERE l.user_id=? AND l.next_review_date<=?
        ORDER BY l.next_review_date ASC
    """, (user_id, today)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def review_log(user_id: int, log_id: int, remembered: bool):
    from datetime import timedelta
    conn = get_conn()
    row = conn.execute("SELECT * FROM logs WHERE user_id=? AND id=?", (user_id, log_id)).fetchone()
    if not row:
        conn.close()
        return
    row = dict(row)
    if remembered:
        next_idx = row["interval_index"] + 1
        new_idx = next_idx % len(LOG_INTERVALS)  # wrap around after 120d
        days = LOG_INTERVALS[new_idx]
    else:
        new_idx = 0
        days = LOG_INTERVALS[0]
    next_date = (today_ist() + timedelta(days=days)).strftime("%Y-%m-%d")
    conn.execute(
        "UPDATE logs SET interval_index=?, next_review_date=? WHERE user_id=? AND id=?",
        (new_idx, next_date, user_id, log_id)
    )
    conn.commit()
    conn.close()
    push_db()


def update_log(user_id: int, log_id: int, subject_id: int, topic_id: int,
               prompt: str, answer: str, tag: str, source: str, image_path: str = None):
    conn = get_conn()
    if image_path is not None:
        conn.execute(
            """UPDATE logs SET subject_id=?, topic_id=?, prompt=?, answer=?, tag=?, source=?,
               image_path=? WHERE user_id=? AND id=?""",
            (subject_id, topic_id, prompt.strip(), answer.strip(), tag.strip(), source.strip(),
             image_path, user_id, log_id)
        )
    else:
        conn.execute(
            """UPDATE logs SET subject_id=?, topic_id=?, prompt=?, answer=?, tag=?, source=?
               WHERE user_id=? AND id=?""",
            (subject_id, topic_id, prompt.strip(), answer.strip(), tag.strip(), source.strip(),
             user_id, log_id)
        )
    conn.commit()
    conn.close()
    push_db()


def delete_log(user_id: int, log_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM logs WHERE user_id=? AND id=?", (user_id, log_id))
    conn.commit()
    conn.close()
    push_db()


def reset_log_review(user_id: int, log_id: int):
    from datetime import timedelta
    tomorrow = (today_ist() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn = get_conn()
    conn.execute(
        "UPDATE logs SET interval_index=0, next_review_date=? WHERE user_id=? AND id=?",
        (tomorrow, user_id, log_id)
    )
    conn.commit()
    conn.close()
    push_db()


def get_logs_due_summary(user_id: int) -> dict:
    """Returns {subject_name: {topic_name: count}} for logs due today."""
    due = get_logs_due_today(user_id)
    summary = {}
    for log in due:
        s = log["subject_name"]
        t = log["topic_name"]
        summary.setdefault(s, {}).setdefault(t, 0)
        summary[s][t] += 1
    return summary
