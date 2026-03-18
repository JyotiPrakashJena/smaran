import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from datetime import date, datetime
from git_sync import pull_db
from database import (
    init_db,
    register_user, login_user,
    create_session, get_session_user, delete_session,
    get_subjects, add_subject, delete_subject,
    get_topics, add_topic, delete_topic,
    add_attachment, get_attachments, get_attachment_data, delete_attachment,
    add_entry, get_entries,
    get_reviews_for_date, complete_review, get_review_stats, get_monthly_activity,
    get_bot_token, save_bot_token, set_bot_token_active, delete_bot_token,
    get_telegram_groups, add_telegram_group, toggle_telegram_group, delete_telegram_group,
    get_exams, add_exam, delete_exam,
    add_log, get_logs, get_logs_due_today, review_log, update_log, delete_log,
    reset_log_review, get_logs_due_summary, LOG_INTERVALS,
    today_ist, fmt_ist,
    SPACED_INTERVALS,
)
from scheduler import start_scheduler
from styling import CUSTOM_CSS

st.set_page_config(page_title="Smaran", page_icon="📚", layout="wide", initial_sidebar_state="expanded")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if "db_pulled" not in st.session_state:
    pull_db()
    st.session_state["db_pulled"] = True
init_db()

if "scheduler_started" not in st.session_state:
    start_scheduler()
    st.session_state["scheduler_started"] = True

# ── Session restore from token ────────────────────────────────────────────────
if "user" not in st.session_state:
    token = st.query_params.get("token", "")
    if token:
        user_from_token = get_session_user(token)
        if user_from_token:
            st.session_state["user"] = user_from_token
            st.session_state["token"] = token

# ── Auth ──────────────────────────────────────────────────────────────────────

def show_auth():
    st.markdown("""
        <h1 style='text-align:center;font-size:2.8rem;margin-bottom:0;'>📚 Smaran</h1>
        <p style='text-align:center;font-size:1rem;color:#7c3aed;font-weight:600;margin-top:0;'>
            Spaced Revision for UPSC Preparation
        </p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        mode = st.radio("Auth mode", ["Sign In", "Sign Up"], horizontal=True, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)

        if mode == "Sign In":
            username = st.text_input("Username", placeholder="your_username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            if st.button("Sign In", use_container_width=True):
                if username and password:
                    user = login_user(username, password)
                    if user:
                        token = create_session(user["id"])
                        st.session_state["user"] = user
                        st.session_state["token"] = token
                        st.query_params["token"] = token
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please fill in all fields.")
        else:
            username = st.text_input("Username", placeholder="choose_a_username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            confirm = st.text_input("Confirm Password", type="password", placeholder="••••••••")
            if st.button("Create Account", use_container_width=True):
                if username and password and confirm:
                    if password != confirm:
                        st.error("Passwords do not match.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        ok, msg = register_user(username, password)
                        if ok:
                            st.success(msg + " Please sign in.")
                        else:
                            st.error(msg)
                else:
                    st.warning("Please fill in all fields.")


if "user" not in st.session_state:
    show_auth()
    st.stop()

user = st.session_state["user"]
user_id = user["id"]

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"### 👤 {user['username']}")
    stats = get_review_stats(user_id)
    st.markdown(f"""
        <div style='background:#ede9fe;border-radius:10px;padding:0.75rem;margin-bottom:0.5rem;'>
            <p style='margin:0;font-size:0.85rem;color:#4c1d95;font-weight:600;'>
                🔔 {stats['pending_today']} reviews pending today
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        token = st.session_state.get("token", "")
        if token:
            delete_session(token)
        del st.session_state["user"]
        st.session_state.pop("token", None)
        st.query_params.clear()
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
    <h1 style='text-align:center;font-size:2.5rem;margin-bottom:0;'>📚 Smaran</h1>
    <p style='text-align:center;font-size:1rem;color:#7c3aed;font-weight:600;margin-top:0;'>
        Spaced Revision Platform
    </p>
""", unsafe_allow_html=True)
st.markdown("---")

tab_dash, tab_manager, tab_review, tab_exams, tab_facts, tab_notif = st.tabs([
    "📊 Dashboard", "📂 Subject & Topic Manager", "🔁 Review", "🎯 Exams", "📝 Important Facts", "🔔 Notifications"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

with tab_dash:
    st.header("📊 Dashboard")

    stats = get_review_stats(user_id)
    _c1, _c2, _c3, _c4 = st.columns(4)
    for _col, _label, _val, _color, _icon in [
        (_c1, "Subjects",         stats["total_subjects"],   "#7c3aed", "📖"),
        (_c2, "Topics",           stats["total_topics"],     "#4f46e5", "📝"),
        (_c3, "Pending Reviews",  stats["pending_today"],    "#ef4444", "🔔"),
        (_c4, "Completed Reviews",stats["total_completed"],  "#10b981", "✅"),
    ]:
        with _col:
            st.markdown(f"""
                <div style='padding:1rem;background:linear-gradient(135deg,{_color}18,{_color}10);
                            border-radius:10px;border-left:4px solid {_color};text-align:center;'>
                    <p style='color:#718096;font-size:0.85rem;margin:0;'>{_icon} {_label}</p>
                    <p style='color:{_color};font-size:2rem;font-weight:700;margin:0;'>{_val}</p>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Monthly Activity Tracker ──────────────────────────────────────────────
    import calendar
    today = today_ist()

    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.subheader("📆 Monthly Activity")
    with col_m2:
        month_options = [(date(today.year, m, 1).strftime("%B %Y"), m) for m in range(1, 13)]
        selected_month_label = st.selectbox(
            "Month", [m[0] for m in month_options],
            index=today.month - 1,
            label_visibility="collapsed",
            key="activity_month"
        )
        selected_month = next(m[1] for m in month_options if m[0] == selected_month_label)

    active_days = get_monthly_activity(user_id, today.year, selected_month)
    days_in_month = calendar.monthrange(today.year, selected_month)[1]
    first_weekday = calendar.monthrange(today.year, selected_month)[0]  # 0=Mon
    month_name = date(today.year, selected_month, 1).strftime("%B %Y")

    # weekday headers
    week_labels = "<div style='display:flex;gap:6px;margin-bottom:4px;margin-left:2px;'>"
    for d in ["M", "T", "W", "T", "F", "S", "S"]:
        week_labels += f"<span style='width:28px;text-align:center;font-size:0.7rem;color:#94a3b8;font-weight:600;'>{d}</span>"
    week_labels += "</div>"

    # build dot grid
    dots_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;'>"
    # empty cells for offset
    for _ in range(first_weekday):
        dots_html += "<span style='width:28px;height:28px;'></span>"

    for day in range(1, days_in_month + 1):
        is_today = (selected_month == today.month and day == today.day)
        is_future = (selected_month == today.month and day > today.day)
        has_activity = day in active_days

        if is_future:
            bg = "#e2e8f0"
            border = "#cbd5e1"
            color = "#94a3b8"
        elif has_activity:
            bg = "#7c3aed"
            border = "#6d28d9"
            color = "#ffffff"
        else:
            bg = "#f1f5f9"
            border = "#e2e8f0"
            color = "#64748b"

        today_ring = f"box-shadow:0 0 0 2px #7c3aed,0 0 0 4px #ede9fe;" if is_today else ""
        dots_html += f"""
            <span title='{date(today.year, selected_month, day).strftime("%d %b %Y")}'
                  style='width:28px;height:28px;border-radius:6px;background:{bg};
                         border:1px solid {border};display:inline-flex;align-items:center;
                         justify-content:center;font-size:0.7rem;font-weight:600;
                         color:{color};{today_ring}'>
                {day}
            </span>"""
    dots_html += "</div>"

    total_active = len([d for d in active_days if d <= (today.day if selected_month == today.month else days_in_month)])
    st.markdown(f"""
        <div style='background:#faf5ff;border:1px solid #ede9fe;border-radius:12px;padding:1rem 1.25rem;'>
            <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;'>
                <span style='font-size:0.9rem;font-weight:700;color:#4c1d95;'>{month_name}</span>
                <span style='font-size:0.8rem;color:#7c3aed;font-weight:600;'>
                    🟣 {total_active} active day{'s' if total_active != 1 else ''}
                </span>
            </div>
            {week_labels}
            {dots_html}
            <div style='display:flex;gap:1rem;margin-top:0.75rem;'>
                <span style='font-size:0.72rem;color:#64748b;'>⬜ No activity</span>
                <span style='font-size:0.72rem;color:#7c3aed;font-weight:600;'>🟣 Active</span>
                <span style='font-size:0.72rem;color:#94a3b8;'>░ Future</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📅 Reading Entries")

    col_d1, col_d2 = st.columns([2, 3])
    with col_d1:
        date_mode = st.selectbox("View entries for", ["Today", "Pick a date", "All"])
    with col_d2:
        if date_mode == "Pick a date":
            picked_date = st.date_input("Select date", value=today_ist(), key="dash_date")
            date_filter = str(picked_date)
        elif date_mode == "Today":
            date_filter = str(today_ist())
        else:
            date_filter = None

    entries = get_entries(user_id, date_filter)
    if not entries:
        st.info("No entries found for the selected date.")
    else:
        for e in entries:
            st.markdown(f"""
                <div style='padding:0.75rem 1rem;margin-bottom:0.5rem;border-radius:10px;
                            background:#faf5ff;border-left:4px solid #7c3aed;border:1px solid #ede9fe;'>
                    <span style='font-weight:700;color:#4c1d95;'>{e['subject_name']}</span>
                    <span style='color:#6d28d9;'> › {e['topic_name']}</span>
                    <span style='float:right;font-size:0.8rem;color:#94a3b8;'>{e['read_date']}</span>
                </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SUBJECT & TOPIC MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

with tab_manager:
    st.header("📂 Subject & Topic Manager")

    # ── Add Entry (Log Reading) ───────────────────────────────────────────────
    st.subheader("📖 Log Today's Reading")

    subjects = get_subjects(user_id)
    subject_map = {s["name"]: s["id"] for s in subjects}

    col_e1, col_e2, col_e3 = st.columns([2, 2, 1])
    with col_e1:
        subject_options = [s["name"] for s in subjects]
        sel_subject = st.selectbox("Subject", subject_options if subject_options else ["— no subjects yet —"],
                                   key="entry_subject")
    with col_e2:
        topic_options = []
        if sel_subject and sel_subject in subject_map:
            topics_for_sub = get_topics(user_id, subject_map[sel_subject])
            topic_options = [t["name"] for t in topics_for_sub]
        sel_topic = st.selectbox("Topic", topic_options if topic_options else ["— no topics yet —"],
                                 key="entry_topic")
    with col_e3:
        entry_date = st.date_input("Date", value=today_ist(), key="entry_date")

    col_log1, col_log2 = st.columns([1, 4])
    with col_log1:
        if st.button("➕ Log Entry", use_container_width=True):
            if sel_subject in subject_map and sel_topic in [t["name"] for t in get_topics(user_id, subject_map[sel_subject])]:
                topic_id = next(t["id"] for t in get_topics(user_id, subject_map[sel_subject]) if t["name"] == sel_topic)
                add_entry(user_id, topic_id, str(entry_date))
                st.success(f"Entry logged! Revision schedule created: +{', +'.join(str(d) for d in SPACED_INTERVALS)} days")
                st.rerun()
            else:
                st.error("Please select a valid subject and topic.")

    st.markdown("---")

    # ── Subjects ──────────────────────────────────────────────────────────────
    col_s1, col_s2, col_s3 = st.columns([3, 1, 1])
    with col_s1:
        st.subheader("📖 Subjects & Topics")
    with col_s2:
        if st.button("➕ New Subject", use_container_width=True):
            st.session_state["show_add_subject"] = True
            st.session_state["show_add_topic_top"] = False
    with col_s3:
        if st.button("➕ New Topic", use_container_width=True):
            st.session_state["show_add_topic_top"] = True
            st.session_state["show_add_subject"] = False

    if st.session_state.get("show_add_subject"):
        with st.form("add_subject_form", clear_on_submit=True):
            new_sub = st.text_input("Subject Name")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("✅ Add", use_container_width=True):
                    if new_sub.strip():
                        ok, msg = add_subject(user_id, new_sub)
                        st.success(msg) if ok else st.error(msg)
                        st.session_state["show_add_subject"] = False
                        st.rerun()
            with c2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state["show_add_subject"] = False
                    st.rerun()

    if st.session_state.get("show_add_topic_top"):
        subjects_for_topic = get_subjects(user_id)
        if not subjects_for_topic:
            st.warning("Create a subject first before adding a topic.")
            st.session_state["show_add_topic_top"] = False
        else:
            with st.form("add_topic_top_form", clear_on_submit=True):
                sub_names = [s["name"] for s in subjects_for_topic]
                sel_sub_for_topic = st.selectbox("Subject", sub_names)
                tn = st.text_input("Topic Name *")
                ts = st.text_input("Source (optional)")
                tt = st.text_input("Tags (optional, comma separated)")
                fc1, fc2 = st.columns(2)
                with fc1:
                    if st.form_submit_button("✅ Add Topic", use_container_width=True):
                        if tn.strip():
                            sub_id = next(s["id"] for s in subjects_for_topic if s["name"] == sel_sub_for_topic)
                            ok, msg, _ = add_topic(user_id, sub_id, tn, ts, tt)
                            st.success(msg) if ok else st.error(msg)
                            st.session_state["show_add_topic_top"] = False
                            st.rerun()
                        else:
                            st.error("Topic name is required.")
                with fc2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.session_state["show_add_topic_top"] = False
                        st.rerun()

    subjects = get_subjects(user_id)
    if not subjects:
        st.info("No subjects yet. Add one above.")
    else:
        for sub in subjects:
            topic_count = len(get_topics(user_id, sub["id"]))
            with st.expander(f"📖 {sub['name']}  ({topic_count} topics)", expanded=False):
                col_sub1, col_sub2 = st.columns([5, 1])
                with col_sub2:
                    if st.button("🗑️ Delete Subject", key=f"del_sub_{sub['id']}"):
                        st.session_state[f"confirm_del_sub_{sub['id']}"] = True

                if st.session_state.get(f"confirm_del_sub_{sub['id']}"):
                    st.warning(f"⚠️ Delete **{sub['name']}** and all its topics? This cannot be undone.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ Yes, Delete", key=f"yes_del_sub_{sub['id']}", use_container_width=True):
                            delete_subject(user_id, sub["id"])
                            st.session_state.pop(f"confirm_del_sub_{sub['id']}", None)
                            st.rerun()
                    with cc2:
                        if st.button("❌ Cancel", key=f"no_del_sub_{sub['id']}", use_container_width=True):
                            st.session_state.pop(f"confirm_del_sub_{sub['id']}", None)
                            st.rerun()

                # Topics inside subject
                topics = get_topics(user_id, sub["id"])
                for t in topics:
                    tc1, tc2 = st.columns([5, 1])
                    with tc1:
                        tags_str = f" 🏷️ {t['tags']}" if t.get("tags") else ""
                        src_str = f" | 📌 {t['source']}" if t.get("source") else ""
                        revised_str = f" | Last revised: {t['last_revised_at']}" if t.get("last_revised_at") else ""
                        st.markdown(f"""
                            <div style='padding:0.5rem 0.75rem;margin-bottom:0.4rem;border-radius:8px;
                                        background:#f5f3ff;border-left:3px solid #7c3aed;'>
                                <span style='font-weight:600;color:#4c1d95;'>{t['name']}</span>
                                <span style='font-size:0.78rem;color:#6d28d9;'>{src_str}{tags_str}{revised_str}</span>
                            </div>
                        """, unsafe_allow_html=True)

                        # Existing attachments
                        attachments = get_attachments(user_id, t["id"])
                        for att in attachments:
                            a1, a2 = st.columns([4, 1])
                            with a1:
                                att_data = get_attachment_data(user_id, att["id"])
                                if att_data:
                                    st.download_button(
                                        f"📎 {att['filename']}",
                                        data=att_data["file_data"],
                                        file_name=att["filename"],
                                        key=f"dl_{att['id']}",
                                    )
                            with a2:
                                if st.button("🗑️", key=f"del_att_{att['id']}"):
                                    delete_attachment(user_id, att["id"])
                                    st.rerun()

                        # Upload — always visible, no nested expander
                        uploaded = st.file_uploader(
                            "📎 Attach file",
                            key=f"upload_{t['id']}",
                            type=["png", "jpg", "jpeg", "pdf", "gif", "webp"],
                            label_visibility="visible"
                        )
                        if uploaded:
                            if st.button("💾 Save Attachment", key=f"save_att_{t['id']}"):
                                add_attachment(user_id, t["id"], uploaded.name, uploaded.read())
                                st.success("Attachment saved!")
                                st.rerun()

                    with tc2:
                        if st.button("🗑️", key=f"del_topic_{t['id']}"):
                            delete_topic(user_id, t["id"])
                            st.rerun()

                # Add topic inside subject
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"➕ Add Topic to {sub['name']}", key=f"add_topic_btn_{sub['id']}"):
                    st.session_state[f"show_add_topic_{sub['id']}"] = True

                if st.session_state.get(f"show_add_topic_{sub['id']}"):
                    with st.form(f"add_topic_form_{sub['id']}", clear_on_submit=True):
                        tn = st.text_input("Topic Name *")
                        ts = st.text_input("Source (optional)")
                        tt = st.text_input("Tags (optional, comma separated)")
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            if st.form_submit_button("✅ Add Topic", use_container_width=True):
                                if tn.strip():
                                    ok, msg, _ = add_topic(user_id, sub["id"], tn, ts, tt)
                                    st.success(msg) if ok else st.error(msg)
                                    st.session_state.pop(f"show_add_topic_{sub['id']}", None)
                                    st.rerun()
                                else:
                                    st.error("Topic name is required.")
                        with fc2:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                st.session_state.pop(f"show_add_topic_{sub['id']}", None)
                                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — REVIEW
# ═══════════════════════════════════════════════════════════════════════════════

with tab_review:
    st.header("🔁 Spaced Revision Review")

    st.markdown(f"""
        <div style='background:#ede9fe;border-radius:10px;padding:0.75rem 1rem;margin-bottom:1rem;
                    border-left:4px solid #7c3aed;'>
            <span style='font-size:0.85rem;color:#4c1d95;font-weight:600;'>
                📐 Revision Schedule: +{' → +'.join(str(d) for d in SPACED_INTERVALS)} days after each reading
            </span>
        </div>
    """, unsafe_allow_html=True)

    col_r1, col_r2 = st.columns([2, 3])
    with col_r1:
        review_date_mode = st.selectbox("Show reviews for", ["Today", "Pick a date"], key="rev_date_mode")
    with col_r2:
        if review_date_mode == "Pick a date":
            rev_date = st.date_input("Select date", value=today_ist(), key="rev_date_pick")
            review_date_str = str(rev_date)
        else:
            review_date_str = str(today_ist())

    pending = get_reviews_for_date(user_id, review_date_str)

    if not pending:
        st.success("🎉 No pending reviews for this date! You're all caught up.")
    else:
        st.markdown(f"**{len(pending)} item(s) pending**")
        st.markdown("---")

        for r in pending:
            interval_label = f"Day +{SPACED_INTERVALS[r['interval_index']]}" if r['interval_index'] < len(SPACED_INTERVALS) else "Final"
            overdue = r["due_date"] < review_date_str
            border = "#ef4444" if overdue else "#7c3aed"
            bg = "rgba(239,68,68,0.05)" if overdue else "#faf5ff"
            overdue_badge = " 🔴 Overdue" if overdue else ""

            st.markdown(f"""
                <div class='flashcard' style='border-left-color:{border};background:{bg};'>
                    <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                        <div>
                            <p style='margin:0;font-size:1rem;font-weight:700;color:#4c1d95;'>
                                {r['subject_name']} › {r['topic_name']}
                            </p>
                            <p style='margin:0.25rem 0 0 0;font-size:0.82rem;color:#6d28d9;'>
                                📅 Originally read: {r['original_read_date']} &nbsp;|&nbsp;
                                Due: {r['due_date']} &nbsp;|&nbsp;
                                Revision: {interval_label}{overdue_badge}
                            </p>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if st.button(f"✅ Mark as Done", key=f"complete_{r['id']}"):
                complete_review(user_id, r["id"])
                st.success(f"Revised! Next revision scheduled automatically.")
                st.rerun()

            st.markdown("<div style='margin-bottom:0.25rem;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — EXAMS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_exams:
    st.header("🎯 Exams")

    # ── Add Exam ──────────────────────────────────────────────────────────────
    with st.form("add_exam_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            exam_name = st.text_input("Exam Name", placeholder="e.g. UPSC Prelims 2025")
        with col2:
            exam_date = st.date_input("Exam Date", min_value=today_ist())
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("➕ Add Exam", use_container_width=True)
        if submitted:
            if exam_name.strip():
                ok, msg = add_exam(user_id, exam_name, str(exam_date))
                st.success(msg) if ok else st.error(msg)
                st.rerun()
            else:
                st.error("Exam name is required.")

    st.markdown("---")

    # ── Exam List ─────────────────────────────────────────────────────────────
    exams = get_exams(user_id)
    if not exams:
        st.info("No exams added yet. Add one above.")
    else:
        today = today_ist()
        for ex in exams:
            exam_dt = date.fromisoformat(ex["exam_date"])
            days_left = (exam_dt - today).days

            if days_left < 0:
                label = f"🗓️ {abs(days_left)} days ago"
                border = "#94a3b8"
                bg = "#f8fafc"
                badge_bg = "#e2e8f0"
                badge_color = "#64748b"
            elif days_left == 0:
                label = "🔴 Today!"
                border = "#ef4444"
                bg = "rgba(239,68,68,0.05)"
                badge_bg = "#ef4444"
                badge_color = "#ffffff"
            elif days_left <= 30:
                label = f"🔥 {days_left} days left"
                border = "#f59e0b"
                bg = "rgba(245,158,11,0.05)"
                badge_bg = "#f59e0b"
                badge_color = "#ffffff"
            elif days_left <= 90:
                label = f"⏰ {days_left} days left"
                border = "#7c3aed"
                bg = "#faf5ff"
                badge_bg = "#7c3aed"
                badge_color = "#ffffff"
            else:
                label = f"📅 {days_left} days left"
                border = "#10b981"
                bg = "rgba(16,185,129,0.05)"
                badge_bg = "#10b981"
                badge_color = "#ffffff"

            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"""
                    <div style='padding:1rem 1.25rem;margin-bottom:0.75rem;border-radius:12px;
                                background:{bg};border:1px solid {border}22;
                                border-left:4px solid {border};'>
                        <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <div>
                                <p style='margin:0;font-size:1.05rem;font-weight:700;color:#1e293b;'>
                                    🎯 {ex['name']}
                                </p>
                                <p style='margin:0.2rem 0 0 0;font-size:0.82rem;color:#64748b;'>
                                    📅 {exam_dt.strftime('%d %B %Y')}
                                </p>
                            </div>
                            <span style='background:{badge_bg};color:{badge_color};
                                         padding:0.35rem 0.85rem;border-radius:20px;
                                         font-size:0.85rem;font-weight:700;white-space:nowrap;'>
                                {label}
                            </span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("🗑️", key=f"del_exam_{ex['id']}"):
                    delete_exam(user_id, ex["id"])
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — IMPORTANT FACTS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_facts:
    st.header("📝 Important Facts")

    facts_sub = st.tabs(["📊 Dashboard", "🔁 Today's Review", "➕ Add Log", "📋 Browse Logs"])

    # ── Facts Dashboard ───────────────────────────────────────────────────────
    with facts_sub[0]:
        all_logs = get_logs(user_id)
        due_logs = get_logs_due_today(user_id)
        subjects_list = get_subjects(user_id)
        topics_list = get_topics(user_id)

        fc1, fc2, fc3, fc4 = st.columns(4)
        for _col, _label, _val, _color, _icon in [
            (fc1, "Subjects",   len(subjects_list),  "#7c3aed", "📖"),
            (fc2, "Topics",     len(topics_list),    "#4f46e5", "📝"),
            (fc3, "Total Logs", len(all_logs),       "#0ea5e9", "🗂️"),
            (fc4, "Due Today",  len(due_logs),       "#ef4444", "🔔"),
        ]:
            with _col:
                st.markdown(f"""
                    <div style='padding:1rem;background:linear-gradient(135deg,{_color}18,{_color}10);
                                border-radius:10px;border-left:4px solid {_color};text-align:center;'>
                        <p style='color:#718096;font-size:0.85rem;margin:0;'>{_icon} {_label}</p>
                        <p style='color:{_color};font-size:2rem;font-weight:700;margin:0;'>{_val}</p>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        due_summary = get_logs_due_summary(user_id)
        if due_summary:
            st.subheader("📌 Pending by Subject")
            for subj, topics_dict in due_summary.items():
                total_subj = sum(topics_dict.values())
                st.markdown(f"**{subj}: {total_subj}**")
                for topic_name, cnt in topics_dict.items():
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {topic_name}: {cnt}")
            st.markdown("---")

        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            if st.button("▶️ Start Today's Review", use_container_width=True, key="facts_start_review"):
                st.session_state["facts_tab"] = 1
                st.rerun()
        with col_q2:
            if st.button("➕ Add New Log", use_container_width=True, key="facts_add_log"):
                st.session_state["facts_tab"] = 2
                st.rerun()
        with col_q3:
            if st.button("📋 Browse Logs", use_container_width=True, key="facts_browse"):
                st.session_state["facts_tab"] = 3
                st.rerun()

    # ── Today's Review ────────────────────────────────────────────────────────
    with facts_sub[1]:
        due_logs = get_logs_due_today(user_id)
        st.markdown(f"**Logs due today: {len(due_logs)}**")

        if not due_logs:
            st.success("No logs due today 🎉")
            if st.button("📚 Review all logs", key="review_all_logs"):
                st.session_state["facts_review_all"] = True
                st.rerun()
        else:
            review_queue = due_logs
            idx_key = "facts_review_idx"
            if idx_key not in st.session_state or st.session_state.get("facts_review_reset"):
                st.session_state[idx_key] = 0
                st.session_state["facts_review_reset"] = False
                st.session_state["facts_show_answer"] = False

            idx = st.session_state[idx_key]
            if idx >= len(review_queue):
                st.success("🎉 All done for today!")
                if st.button("🔄 Restart", key="facts_restart"):
                    st.session_state[idx_key] = 0
                    st.session_state["facts_show_answer"] = False
                    st.rerun()
            else:
                log = review_queue[idx]
                st.markdown(f"**Review {idx + 1} / {len(review_queue)}**")
                progress = (idx) / len(review_queue)
                st.progress(progress)

                st.markdown(f"""
                    <div style='padding:1.25rem;background:#faf5ff;border-radius:12px;
                                border-left:4px solid #7c3aed;margin-bottom:1rem;'>
                        <p style='margin:0;font-size:0.82rem;color:#6d28d9;font-weight:600;'>
                            📖 {log['subject_name']} &nbsp;›&nbsp; {log['topic_name']}
                        </p>
                        <p style='margin:0.75rem 0 0 0;font-size:1.1rem;font-weight:700;color:#1e293b;'>
                            {log['prompt']}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

                if log.get("image_path") and Path(log["image_path"]).exists():
                    st.image(log["image_path"], use_container_width=True)

                if not st.session_state.get("facts_show_answer"):
                    if st.button("👁️ Show Answer", key="facts_show_ans_btn", use_container_width=True):
                        st.session_state["facts_show_answer"] = True
                        st.rerun()
                else:
                    st.markdown(f"""
                        <div style='padding:1rem;background:#f0fdf4;border-radius:10px;
                                    border-left:4px solid #10b981;margin-bottom:1rem;'>
                            <p style='margin:0;font-size:1rem;color:#065f46;'>{log['answer']}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        if st.button("✅ Remembered", use_container_width=True, key=f"rem_{log['id']}"):
                            review_log(user_id, log["id"], remembered=True)
                            st.session_state[idx_key] += 1
                            st.session_state["facts_show_answer"] = False
                            st.rerun()
                    with col_r2:
                        if st.button("❌ Forgot", use_container_width=True, key=f"forg_{log['id']}"):
                            review_log(user_id, log["id"], remembered=False)
                            st.session_state[idx_key] += 1
                            st.session_state["facts_show_answer"] = False
                            st.rerun()

    # ── Add Log ───────────────────────────────────────────────────────────────
    with facts_sub[2]:
        subjects_for_log = get_subjects(user_id)
        if not subjects_for_log:
            st.warning("Create a subject first in Subject & Topic Manager.")
        else:
            sub_map = {s["name"]: s["id"] for s in subjects_for_log}

            col_s1, col_s2 = st.columns([4, 1])
            with col_s1:
                sel_sub = st.selectbox("Subject", list(sub_map.keys()), key="log_sub")
            with col_s2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕", key="log_add_sub", help="Add Subject"):
                    st.session_state["log_show_add_sub"] = True

            if st.session_state.get("log_show_add_sub"):
                with st.form("log_add_sub_form", clear_on_submit=True):
                    new_sub_name = st.text_input("Subject Name")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("✅ Add"):
                            if new_sub_name.strip():
                                ok, msg = add_subject(user_id, new_sub_name.strip())
                                st.success(msg) if ok else st.error(msg)
                                st.session_state["log_show_add_sub"] = False
                                st.rerun()
                    with c2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state["log_show_add_sub"] = False
                            st.rerun()

            topics_for_log = get_topics(user_id, sub_map.get(sel_sub)) if sel_sub in sub_map else []
            topic_map = {t["name"]: t["id"] for t in topics_for_log}

            col_t1, col_t2 = st.columns([4, 1])
            with col_t1:
                sel_topic = st.selectbox(
                    "Topic",
                    list(topic_map.keys()) if topic_map else ["— no topics yet —"],
                    key="log_topic"
                )
            with col_t2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕", key="log_add_topic", help="Add Topic"):
                    st.session_state["log_show_add_topic"] = True

            if st.session_state.get("log_show_add_topic"):
                with st.form("log_add_topic_form", clear_on_submit=True):
                    st.text_input("Subject", value=sel_sub, disabled=True)
                    new_topic_name = st.text_input("Topic Name")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("✅ Add"):
                            if new_topic_name.strip() and sel_sub in sub_map:
                                ok, msg, _ = add_topic(user_id, sub_map[sel_sub], new_topic_name.strip())
                                st.success(msg) if ok else st.error(msg)
                                st.session_state["log_show_add_topic"] = False
                                st.rerun()
                    with c2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state["log_show_add_topic"] = False
                            st.rerun()

            with st.form("add_log_form", clear_on_submit=True):
                prompt_text = st.text_area("Prompt / Question *", height=80)
                answer_text = st.text_area("Answer / Explanation *", height=80)
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    tag_text = st.text_input("Tag (optional)", placeholder="factual, concept, trap")
                with col_f2:
                    source_text = st.text_input("Source (optional)", placeholder="UPSC Prelims 2022")
                img_upload = st.file_uploader("Image (optional)", type=["png", "jpg", "jpeg"])

                if st.form_submit_button("💾 Save Log", use_container_width=True):
                    if not prompt_text.strip() or not answer_text.strip():
                        st.error("Prompt and Answer are required.")
                    elif sel_sub not in sub_map:
                        st.error("Select a valid subject.")
                    elif sel_topic not in topic_map:
                        st.error("Select a valid topic.")
                    else:
                        img_path = ""
                        if img_upload:
                            img_dir = Path(__file__).parent / "data" / "log_images"
                            img_dir.mkdir(parents=True, exist_ok=True)
                            img_path = str(img_dir / f"{user_id}_{img_upload.name}")
                            Path(img_path).write_bytes(img_upload.read())
                        ok, msg = add_log(
                            user_id, sub_map[sel_sub], topic_map[sel_topic],
                            prompt_text, answer_text, tag_text, source_text, img_path
                        )
                        st.success(msg) if ok else st.error(msg)

    # ── Browse Logs ───────────────────────────────────────────────────────────
    with facts_sub[3]:
        all_subjects = get_subjects(user_id)
        sub_filter_map = {"All": None} | {s["name"]: s["id"] for s in all_subjects}

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_sub = st.selectbox("Filter by Subject", list(sub_filter_map.keys()), key="browse_sub")
        with col_f2:
            if sub_filter_map[filter_sub]:
                filter_topics = get_topics(user_id, sub_filter_map[filter_sub])
                topic_filter_map = {"All": None} | {t["name"]: t["id"] for t in filter_topics}
            else:
                topic_filter_map = {"All": None}
            filter_topic = st.selectbox("Filter by Topic", list(topic_filter_map.keys()), key="browse_topic")

        logs = get_logs(user_id, sub_filter_map[filter_sub], topic_filter_map.get(filter_topic))

        if not logs:
            st.info("No logs found.")
        else:
            for log in logs:
                has_img = bool(log.get("image_path") and Path(log["image_path"]).exists())
                with st.expander(
                    f"📖 {log['subject_name']} › {log['topic_name']} | {log['prompt'][:60]}{'...' if len(log['prompt']) > 60 else ''}",
                    expanded=False
                ):
                    edit_key = f"edit_log_{log['id']}"
                    if not st.session_state.get(edit_key):
                        st.markdown(f"**Prompt:** {log['prompt']}")
                        st.markdown(f"**Answer:** {log['answer']}")
                        cols_meta = []
                        if log.get("tag"): cols_meta.append(f"🏷️ {log['tag']}")
                        if log.get("source"): cols_meta.append(f"📌 {log['source']}")
                        cols_meta.append(f"📅 Next review: {log['next_review_date']}")
                        if has_img: cols_meta.append("🖼️ Image")
                        st.caption(" | ".join(cols_meta))
                        if has_img:
                            st.image(log["image_path"], width=300)

                        col_b1, col_b2, col_b3 = st.columns(3)
                        with col_b1:
                            if st.button("✏️ Edit", key=f"edit_btn_{log['id']}"):
                                st.session_state[edit_key] = True
                                st.rerun()
                        with col_b2:
                            if st.button("🔄 Reset Review", key=f"reset_{log['id']}"):
                                reset_log_review(user_id, log["id"])
                                st.success("Review reset.")
                                st.rerun()
                        with col_b3:
                            if st.button("🗑️ Delete", key=f"del_log_{log['id']}"):
                                st.session_state[f"confirm_del_log_{log['id']}"] = True

                        if st.session_state.get(f"confirm_del_log_{log['id']}"):
                            st.warning("Delete this log?")
                            dc1, dc2 = st.columns(2)
                            with dc1:
                                if st.button("✅ Yes", key=f"yes_del_log_{log['id']}"):
                                    delete_log(user_id, log["id"])
                                    st.session_state.pop(f"confirm_del_log_{log['id']}", None)
                                    st.rerun()
                            with dc2:
                                if st.button("❌ No", key=f"no_del_log_{log['id']}"):
                                    st.session_state.pop(f"confirm_del_log_{log['id']}", None)
                                    st.rerun()
                    else:
                        # Edit form
                        edit_subjects = get_subjects(user_id)
                        edit_sub_map = {s["name"]: s["id"] for s in edit_subjects}
                        cur_sub = next((s["name"] for s in edit_subjects if s["id"] == log["subject_id"]), list(edit_sub_map.keys())[0])
                        with st.form(f"edit_log_form_{log['id']}"):
                            e_sub = st.selectbox("Subject", list(edit_sub_map.keys()),
                                                  index=list(edit_sub_map.keys()).index(cur_sub))
                            e_topics = get_topics(user_id, edit_sub_map[e_sub])
                            e_topic_map = {t["name"]: t["id"] for t in e_topics}
                            cur_topic = next((t["name"] for t in e_topics if t["id"] == log["topic_id"]), list(e_topic_map.keys())[0] if e_topic_map else "")
                            e_topic = st.selectbox("Topic", list(e_topic_map.keys()),
                                                    index=list(e_topic_map.keys()).index(cur_topic) if cur_topic in e_topic_map else 0)
                            e_prompt = st.text_area("Prompt", value=log["prompt"])
                            e_answer = st.text_area("Answer", value=log["answer"])
                            e_tag = st.text_input("Tag", value=log.get("tag", ""))
                            e_source = st.text_input("Source", value=log.get("source", ""))
                            e_img = st.file_uploader("Replace Image (optional)", type=["png", "jpg", "jpeg"])
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                if st.form_submit_button("💾 Save", use_container_width=True):
                                    img_path = log.get("image_path", "")
                                    if e_img:
                                        img_dir = Path(__file__).parent / "data" / "log_images"
                                        img_dir.mkdir(parents=True, exist_ok=True)
                                        img_path = str(img_dir / f"{user_id}_{e_img.name}")
                                        Path(img_path).write_bytes(e_img.read())
                                    update_log(user_id, log["id"], edit_sub_map[e_sub],
                                               e_topic_map.get(e_topic, log["topic_id"]),
                                               e_prompt, e_answer, e_tag, e_source, img_path)
                                    st.session_state.pop(edit_key, None)
                                    st.rerun()
                            with ec2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state.pop(edit_key, None)
                                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_notif:
    st.header("🔔 Notifications")
    st.caption("Configure Telegram bot to receive daily revision reminders at 8:00 AM.")

    # ── Bot Token ─────────────────────────────────────────────────────────────
    st.subheader("🤖 Telegram Bot Token")

    bt = get_bot_token(user_id)
    token_set = bool(bt["token"])

    if token_set:
        bt_active = bt["active"]
        border = "#10b981" if bt_active else "#94a3b8"
        bg = "rgba(16,185,129,0.05)" if bt_active else "rgba(148,163,184,0.05)"
        status_badge = "🟢 Active" if bt_active else "⚫ Disabled"
        masked = bt["token"][:6] + "•" * 20 + bt["token"][-4:]

        col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
        with col1:
            st.markdown(f"""
                <div style='padding:0.75rem 1rem;border-radius:10px;border-left:4px solid {border};background:{bg};'>
                    <p style='margin:0;font-weight:700;color:#1a202c;'>
                        Telegram Bot &nbsp;
                        <span style='font-size:0.8rem;color:#718096;font-weight:400;font-family:monospace;'>{masked}</span>
                    </p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"<br><span style='font-size:0.9rem;'>{status_badge}</span>", unsafe_allow_html=True)
        with col3:
            if st.button("⛔ Disable" if bt_active else "✅ Enable", key="bt_toggle"):
                set_bot_token_active(user_id, not bt_active)
                st.rerun()
        with col4:
            if st.button("🗑️ Delete", key="bt_delete"):
                delete_bot_token(user_id)
                st.rerun()
    else:
        with st.expander("➕ Add Bot Token", expanded=True):
            new_token = st.text_input("Bot Token", type="password", placeholder="7412365890:AAFxyz...")
            if st.button("💾 Save Token"):
                if new_token.strip():
                    save_bot_token(user_id, new_token.strip())
                    st.success("Bot token saved!")
                    st.rerun()
                else:
                    st.error("Token cannot be empty.")

    st.markdown("---")

    # ── Test Notification ─────────────────────────────────────────────────────
    if token_set and bt["active"]:
        if st.button("📤 Send Test Reminder Now"):
            from telegram_bot import send_daily_reminder
            pending_now = get_reviews_for_date(user_id, str(today_ist()))
            send_daily_reminder(user_id, user["username"], pending_now)
            st.success("Test reminder sent to all active groups!")

    st.markdown("---")

    # ── Telegram Groups ───────────────────────────────────────────────────────
    st.subheader("👥 Telegram Groups")

    with st.expander("➕ Add Telegram Group", expanded=False):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_gid = st.text_input("Group / Chat ID", placeholder="-100123456789")
        with col2:
            new_label = st.text_input("Label (optional)", placeholder="e.g. UPSC Study Group")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add"):
                if new_gid.strip():
                    add_telegram_group(user_id, new_gid.strip(), new_label.strip())
                    st.success("Group added!")
                    st.rerun()
                else:
                    st.error("Group ID is required.")

    st.markdown("---")

    groups = get_telegram_groups(user_id)
    if not groups:
        st.info("No Telegram groups configured. Add one above.")
    else:
        for g in groups:
            g_active = bool(g["active"])
            border = "#10b981" if g_active else "#94a3b8"
            bg = "rgba(16,185,129,0.05)" if g_active else "rgba(148,163,184,0.05)"
            status_badge = "🟢 Active" if g_active else "⚫ Disabled"

            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.markdown(f"""
                    <div style='padding:0.75rem 1rem;border-radius:10px;border-left:4px solid {border};background:{bg};'>
                        <p style='margin:0;font-weight:700;color:#1a202c;'>
                            {g['label'] or 'Unnamed'} &nbsp;
                            <span style='font-size:0.8rem;color:#718096;font-weight:400;'>{g['group_id']}</span>
                        </p>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"<br><span style='font-size:0.9rem;'>{status_badge}</span>", unsafe_allow_html=True)
            with col3:
                if st.button("⛔ Disable" if g_active else "✅ Enable", key=f"tg_toggle_{g['id']}"):
                    toggle_telegram_group(user_id, g["id"], not g_active)
                    st.rerun()
            with col4:
                if st.button("🗑️ Delete", key=f"tg_del_{g['id']}"):
                    delete_telegram_group(user_id, g["id"])
                    st.rerun()

    st.markdown("---")
    st.subheader("ℹ️ How to get your Telegram Group ID")
    st.markdown("""
    1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token
    2. Add your bot to the group
    3. Send a message in the group
    4. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
    5. Find `"chat": {"id": -100XXXXXXXXX}` — that's your Group ID
    """)
