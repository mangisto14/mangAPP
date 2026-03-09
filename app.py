import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# ────────────────────────────────────────────────
# הגדרות דף
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Guard Manager",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ────────────────────────────────────────────────
# CSS מקצועי – RTL, מובייל, עיצוב מלא
# ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');

/* ── בסיס גלובלי ── */
html, body, [class*="css"] {
    font-family: 'Assistant', sans-serif !important;
    direction: rtl;
    text-align: right;
}

/* ── רקע כללי ── */
.stApp {
    background: linear-gradient(135deg, #0f1923 0%, #1a2840 100%);
    min-height: 100vh;
}

/* ── כותרת ראשית ── */
.app-header {
    background: linear-gradient(90deg, #1e3a5f 0%, #2563eb 50%, #1e3a5f 100%);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    text-align: center;
    box-shadow: 0 8px 32px rgba(37,99,235,0.3);
    border: 1px solid rgba(255,255,255,0.08);
}
.app-header h1 {
    color: #fff;
    font-size: 2rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.5px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.4);
}
.app-header p {
    color: rgba(255,255,255,0.7);
    font-size: 0.95rem;
    margin: 6px 0 0 0;
}

/* ── טאבים ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
    border: 1px solid rgba(255,255,255,0.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important;
    font-family: 'Assistant', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    color: rgba(255,255,255,0.6) !important;
    padding: 10px 20px !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.25s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    color: #fff !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
}

/* ── כרטיסים (sections) ── */
.card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 18px;
    backdrop-filter: blur(8px);
}
.card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #93c5fd;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}

/* ── כותרת יום ── */
.day-header {
    background: linear-gradient(90deg, rgba(37,99,235,0.25) 0%, rgba(37,99,235,0.08) 100%);
    border-right: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 10px 16px;
    margin: 22px 0 10px 0;
    font-size: 1rem;
    font-weight: 700;
    color: #93c5fd;
    letter-spacing: 0.3px;
}

/* ── טבלת משמרות – מובייל-בטוחה ── */
.shift-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}
.shift-table tr:last-child td { border-bottom: none; }
.shift-table tr:hover { background: rgba(255,255,255,0.03); }
.shift-table td {
    padding: 11px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    vertical-align: middle;
    color: #e2e8f0;
    font-size: 0.95rem;
    /* ← מניעת שבירת שורה */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.time-col {
    width: 28%;
    font-weight: 700;
    color: #60a5fa;
    font-size: 0.95rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap !important;
}
.names-col {
    width: 72%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.shift-num {
    display: inline-block;
    background: rgba(37,99,235,0.2);
    color: #93c5fd;
    border-radius: 5px;
    padding: 1px 7px;
    font-size: 0.78rem;
    font-weight: 700;
    margin-left: 6px;
    white-space: nowrap;
}

/* ── גלילה לרשימות ── */
.scroll-box {
    max-height: 420px;
    overflow-y: auto;
    border-radius: 10px;
    padding: 4px 0;
    scrollbar-width: thin;
    scrollbar-color: rgba(96,165,250,0.4) transparent;
}
.scroll-box::-webkit-scrollbar { width: 5px; }
.scroll-box::-webkit-scrollbar-thumb {
    background: rgba(96,165,250,0.4);
    border-radius: 4px;
}

/* ── שורת שומר – שמירה על שורה אחת ── */
.guard-row {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 8px !important;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    flex-wrap: nowrap !important;
}
.guard-row .guard-name-field {
    flex: 1 1 auto;
    min-width: 0;
}

/* ── כפתורים ── */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'Assistant', sans-serif !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    border: none !important;
    white-space: nowrap !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
    padding: 0.6rem 1.4rem !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(37,99,235,0.5) !important;
}
.stButton > button:not([kind="primary"]) {
    background: rgba(255,255,255,0.07) !important;
    color: #cbd5e1 !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: rgba(255,255,255,0.12) !important;
    color: #fff !important;
}

/* ── כפתור מחיקה אדום ── */
button[data-testid*="delete"], button[aria-label*="delete"] {
    color: #f87171 !important;
}

/* ── שדות קלט ── */
.stTextInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important;
    color: #e2e8f0 !important;
    font-family: 'Assistant', sans-serif !important;
    direction: rtl !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.25) !important;
}

/* ── תוויות ── */
label, .stSelectbox label, .stMultiSelect label {
    color: #94a3b8 !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    font-family: 'Assistant', sans-serif !important;
}

/* ── multiselect ── */
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(37,99,235,0.3) !important;
    border-radius: 6px !important;
    color: #93c5fd !important;
    white-space: nowrap !important;
}
.stMultiSelect span { white-space: normal !important; }
.stMultiSelect > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important;
}

/* ── date/time inputs ── */
.stDateInput > div > div > input,
.stTimeInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important;
    color: #e2e8f0 !important;
}

/* ── divider ── */
hr { border-color: rgba(255,255,255,0.07) !important; margin: 20px 0 !important; }

/* ── info / success / warning boxes ── */
.stAlert {
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}

/* ── טבלת סטטיסטיקה ── */
.stats-table {
    width: 100%;
    border-collapse: collapse;
}
.stats-table th {
    background: rgba(37,99,235,0.2);
    color: #93c5fd;
    padding: 10px 14px;
    font-size: 0.9rem;
    font-weight: 700;
    border-bottom: 2px solid rgba(59,130,246,0.3);
}
.stats-table td {
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    color: #e2e8f0;
    font-size: 0.92rem;
}
.stats-table tr:hover td { background: rgba(255,255,255,0.03); }
.stats-bar {
    height: 10px;
    background: linear-gradient(90deg, #2563eb, #60a5fa);
    border-radius: 5px;
    min-width: 6px;
}
.rank-badge {
    display: inline-block;
    width: 26px;
    height: 26px;
    line-height: 26px;
    text-align: center;
    border-radius: 50%;
    font-size: 0.78rem;
    font-weight: 800;
    background: rgba(37,99,235,0.25);
    color: #93c5fd;
}
.rank-1 { background: rgba(250,204,21,0.25); color: #fde047; }
.rank-2 { background: rgba(203,213,225,0.25); color: #cbd5e1; }
.rank-3 { background: rgba(251,146,60,0.25); color: #fb923c; }

/* ── expander ── */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 9px !important;
    color: #94a3b8 !important;
    font-family: 'Assistant', sans-serif !important;
    font-weight: 600 !important;
}

/* ── link button (WhatsApp) ── */
.stLinkButton a {
    background: linear-gradient(135deg, #16a34a, #22c55e) !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-family: 'Assistant', sans-serif !important;
    font-weight: 700 !important;
    padding: 0.6rem 1.4rem !important;
    text-decoration: none !important;
    box-shadow: 0 4px 14px rgba(22,163,74,0.35) !important;
    white-space: nowrap !important;
    display: inline-block;
}
.stLinkButton a:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(22,163,74,0.5) !important;
}

/* ── מספר עמדה ── */
.stNumberInput { direction: ltr; }
.stNumberInput > div { direction: rtl; }

/* ── רספונסיבי למובייל ── */
@media (max-width: 640px) {
    .app-header h1 { font-size: 1.4rem; }
    .app-header { padding: 16px; }
    .card { padding: 14px 12px; }
    .shift-table td { padding: 9px 8px; font-size: 0.88rem; }
    .time-col { font-size: 0.88rem; }
}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# כותרת ראשית
# ────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🛡️ Smart Guard Manager</h1>
    <p>מערכת ניהול שמירות חכמה • Real-Time Scheduling</p>
</div>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# מסד נתונים
# ────────────────────────────────────────────────
@st.cache_resource
def init_db():
    db_dir = '/app/data'
    db_path = os.path.join(db_dir, 'guard_system.db') if os.path.exists(db_dir) else 'guard_system.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS guards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shifts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  start_time TEXT, end_time TEXT, names TEXT)''')
    conn.commit()
    return conn

conn = init_db()


def get_guards():
    return pd.read_sql_query("SELECT * FROM guards ORDER BY name ASC", conn)


def get_shifts():
    return pd.read_sql_query("SELECT * FROM shifts ORDER BY start_time ASC", conn)


def get_stats():
    shifts = get_shifts()
    guards = get_guards()
    counts = {name: 0 for name in guards['name']}
    for names_str in shifts['names']:
        for n in names_str.split(', '):
            n = n.strip()
            if n in counts:
                counts[n] += 1
    return counts


# ────────────────────────────────────────────────
# טאבים
# ────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["⚡ שיבוץ", "👥 צוות", "📊 סטטיסטיקה"])


# ════════════════════════════════════════════════
# TAB 1 – שיבוץ
# ════════════════════════════════════════════════
with tab1:

    # ── הגדרות משמרת ──
    st.markdown('<div class="card"><div class="card-title">⚙️ הגדרות משמרת</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        chosen_date = st.date_input("📅 תאריך התחלה", datetime.now(), key="shift_date")
        duration = st.selectbox(
            "⏱️ משך משמרת (דקות)",
            [30, 45, 60, 90, 120, 180, 240],
            index=2,
            key="duration"
        )
    with col_b:
        chosen_time = st.time_input(
            "🕐 שעת התחלה",
            datetime.now().replace(minute=0, second=0, microsecond=0),
            key="shift_time"
        )
        num_per_shift = st.number_input("👥 שומרים בעמדה", min_value=1, max_value=10, value=2, key="num_guards")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── בחירת שומרים ──
    st.markdown('<div class="card"><div class="card-title">👤 בחירת שומרים למשמרת</div>', unsafe_allow_html=True)

    stats = get_stats()
    guards_df = get_guards()

    if guards_df.empty:
        st.info("⚠️ אין שומרים במערכת. הוסף שומרים בטאב 'צוות'.")
    else:
        options = [f"{r['name']} ({stats.get(r['name'], 0)})" for _, r in guards_df.iterrows()]
        selected_raw = st.multiselect(
            "חפש ובחר שומרים (מספר בסוגריים = כמות משמרות):",
            options=options,
            placeholder="הקלד שם לחיפוש...",
            key="guard_select"
        )

        btn_col, info_col = st.columns([1, 3])
        with btn_col:
            assign_clicked = st.button("🚀 שבץ משמרת", type="primary", use_container_width=True)
        with info_col:
            if selected_raw:
                st.markdown(
                    f"<span style='color:#93c5fd;font-size:0.9rem;'>נבחרו: <b>{len(selected_raw)}</b> שומרים</span>",
                    unsafe_allow_html=True
                )

        if assign_clicked:
            if not selected_raw:
                st.warning("⚠️ יש לבחור לפחות שומר אחד.")
            else:
                selected_names = [s.rsplit(' (', 1)[0] for s in selected_raw]
                all_shifts = get_shifts()

                if not all_shifts.empty:
                    last_end = all_shifts.iloc[-1]['end_time']
                    next_start = datetime.strptime(last_end, '%Y-%m-%d %H:%M:%S')
                else:
                    next_start = datetime.combine(chosen_date, chosen_time)

                next_end = next_start + timedelta(minutes=int(duration))

                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                    (next_start.strftime('%Y-%m-%d %H:%M:%S'),
                     next_end.strftime('%Y-%m-%d %H:%M:%S'),
                     ", ".join(selected_names))
                )
                conn.commit()
                st.success(
                    f"✅ משמרת נוספה: {next_start.strftime('%H:%M')}–{next_end.strftime('%H:%M')} | "
                    f"{', '.join(selected_names)}"
                )
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── לו"ז נוכחי ──
    st.markdown('<div class="card"><div class="card-title">🕒 לו"ז משמרות</div>', unsafe_allow_html=True)

    shifts_df = get_shifts()

    if not shifts_df.empty:
        shifts_df['date'] = shifts_df['start_time'].str[:10]
        unique_days = shifts_df['date'].unique()

        total_shifts = len(shifts_df)
        st.markdown(
            f"<span style='color:#64748b;font-size:0.85rem;'>סה\"כ {total_shifts} משמרות ב-{len(unique_days)} ימים</span>",
            unsafe_allow_html=True
        )

        # גלילה לרשימת משמרות
        st.markdown('<div class="scroll-box">', unsafe_allow_html=True)

        for idx, day in enumerate(unique_days):
            nice_date = datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m/%Y')
            day_name_map = {
                'Monday': 'שני', 'Tuesday': 'שלישי', 'Wednesday': 'רביעי',
                'Thursday': 'חמישי', 'Friday': 'שישי', 'Saturday': 'שבת', 'Sunday': 'ראשון'
            }
            day_en = datetime.strptime(day, '%Y-%m-%d').strftime('%A')
            day_he = day_name_map.get(day_en, day_en)

            st.markdown(
                f'<div class="day-header">📅 יום {day_he} &nbsp;·&nbsp; {nice_date}</div>',
                unsafe_allow_html=True
            )

            day_shifts = shifts_df[shifts_df['date'] == day]
            table_html = '<table class="shift-table">'
            for i, (_, row) in enumerate(day_shifts.iterrows()):
                s = row['start_time'][11:16]
                e = row['end_time'][11:16]
                names_display = row['names']
                table_html += (
                    f'<tr>'
                    f'<td class="time-col">{s}–{e}</td>'
                    f'<td class="names-col">{names_display}</td>'
                    f'</tr>'
                )
            table_html += '</table>'
            st.markdown(table_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<br>', unsafe_allow_html=True)

        # ── פעולות ──
        action_c1, action_c2 = st.columns(2)
        with action_c1:
            if st.button("🗑️ מחק משמרת אחרונה", use_container_width=True):
                conn.cursor().execute("DELETE FROM shifts WHERE id = (SELECT MAX(id) FROM shifts)")
                conn.commit()
                st.rerun()
        with action_c2:
            if st.button("🗑️ מחק הכל", use_container_width=True):
                conn.cursor().execute("DELETE FROM shifts")
                conn.commit()
                st.rerun()

        # ── WhatsApp ──
        st.markdown('<br>', unsafe_allow_html=True)
        summary = "🛡️ *סידור שמירה מעודכן*\n"
        summary += f"📆 עודכן: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        for day in unique_days:
            nice_date = datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m')
            day_en = datetime.strptime(day, '%Y-%m-%d').strftime('%A')
            day_he = {'Monday': 'שני', 'Tuesday': 'שלישי', 'Wednesday': 'רביעי',
                      'Thursday': 'חמישי', 'Friday': 'שישי', 'Saturday': 'שבת', 'Sunday': 'ראשון'}.get(day_en, day_en)
            summary += f"\n🗓️ *יום {day_he} {nice_date}:*\n"
            day_shifts = shifts_df[shifts_df['date'] == day]
            for _, r in day_shifts.iterrows():
                summary += f"• {r['start_time'][11:16]}–{r['end_time'][11:16]} ▸ {r['names']}\n"
        summary += "\n_שלח ע\"י Smart Guard Manager_ 🛡️"

        st.link_button(
            "📲 שלח סידור בוואטסאפ",
            f"https://wa.me/?text={urllib.parse.quote(summary)}",
            use_container_width=True
        )

    else:
        st.info("📭 אין משמרות משובצות. השתמש בטופס למעלה כדי להוסיף משמרת.")

    st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
# TAB 2 – ניהול צוות
# ════════════════════════════════════════════════
with tab2:

    # ── הוספה מהירה ──
    st.markdown('<div class="card"><div class="card-title">➕ הוספת שומרים</div>', unsafe_allow_html=True)

    with st.expander("הוספה מרובה (מהירה) – הדבק שמות מופרדים בפסיק"):
        bulk = st.text_area(
            "שמות (מופרדים בפסיק):",
            placeholder="ישראל ישראלי, משה כהן, דוד לוי",
            key="bulk_add"
        )
        if st.button("💾 שמור הכל", key="bulk_save", use_container_width=False):
            names = [x.strip() for x in bulk.split(',') if x.strip()]
            if names:
                cur = conn.cursor()
                added = 0
                for n in names:
                    try:
                        cur.execute("INSERT INTO guards (name) VALUES (?)", (n,))
                        added += 1
                    except sqlite3.IntegrityError:
                        pass
                conn.commit()
                st.success(f"✅ נוספו {added} שומרים.")
                st.rerun()

    # ── הוספה בודדת ──
    with st.expander("הוספה בודדת"):
        single_name = st.text_input("שם שומר:", placeholder="הכנס שם...", key="single_add")
        if st.button("➕ הוסף", key="single_save"):
            if single_name.strip():
                try:
                    conn.cursor().execute("INSERT INTO guards (name) VALUES (?)", (single_name.strip(),))
                    conn.commit()
                    st.success(f"✅ {single_name.strip()} נוסף.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("⚠️ שם זה כבר קיים במערכת.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── רשימת שומרים ──
    st.markdown('<div class="card"><div class="card-title">👥 רשימת שומרים</div>', unsafe_allow_html=True)

    g_list = get_guards()
    cur_stats = get_stats()

    if g_list.empty:
        st.info("אין שומרים במערכת.")
    else:
        st.markdown(
            f"<span style='color:#64748b;font-size:0.85rem;'>סה\"כ {len(g_list)} שומרים</span>",
            unsafe_allow_html=True
        )
        st.markdown('<div class="scroll-box">', unsafe_allow_html=True)

        for _, row in g_list.iterrows():
            gid = row['id']
            shift_count = cur_stats.get(row['name'], 0)

            # שורה אחת: שם | ספירה | שמור | מחק
            c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
            with c1:
                new_name = st.text_input(
                    "שם",
                    value=row['name'],
                    key=f"name_{gid}",
                    label_visibility="collapsed"
                )
            with c2:
                st.markdown(
                    f"<div style='padding-top:8px;text-align:center;'>"
                    f"<span class='shift-num'>{shift_count}</span></div>",
                    unsafe_allow_html=True
                )
            with c3:
                if st.button("💾", key=f"save_{gid}", help="שמור שם"):
                    if new_name.strip():
                        try:
                            conn.cursor().execute(
                                "UPDATE guards SET name = ? WHERE id = ?",
                                (new_name.strip(), gid)
                            )
                            conn.commit()
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("שם כבר קיים.")
            with c4:
                if st.button("🗑️", key=f"del_{gid}", help="מחק שומר"):
                    conn.cursor().execute("DELETE FROM guards WHERE id = ?", (gid,))
                    conn.commit()
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
# TAB 3 – סטטיסטיקה
# ════════════════════════════════════════════════
with tab3:

    st.markdown('<div class="card"><div class="card-title">📊 סיכום משמרות לשומר</div>', unsafe_allow_html=True)

    current_stats = get_stats()

    if not current_stats or all(v == 0 for v in current_stats.values()):
        st.info("אין נתוני סטטיסטיקה עדיין. שבץ משמרות כדי לצפות בנתונים.")
    else:
        sorted_stats = sorted(current_stats.items(), key=lambda x: x[1], reverse=True)
        max_val = sorted_stats[0][1] if sorted_stats else 1

        # ── טבלה מעוצבת ──
        table_html = """
        <table class="stats-table">
          <thead>
            <tr>
              <th style="width:8%">#</th>
              <th style="width:30%">שומר</th>
              <th style="width:15%">משמרות</th>
              <th style="width:47%">גרף</th>
            </tr>
          </thead>
          <tbody>
        """
        for rank, (name, count) in enumerate(sorted_stats, 1):
            bar_pct = int((count / max_val) * 100) if max_val > 0 else 0
            rank_class = f"rank-{rank}" if rank <= 3 else "rank-badge"
            table_html += f"""
            <tr>
              <td><span class="rank-badge {rank_class}">{rank}</span></td>
              <td><b>{name}</b></td>
              <td style="text-align:center;font-weight:700;color:#60a5fa;">{count}</td>
              <td>
                <div class="stats-bar" style="width:{bar_pct}%;"></div>
              </td>
            </tr>
            """
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)

        st.markdown('<br>', unsafe_allow_html=True)

        # ── גרף bar chart ──
        chart_df = pd.DataFrame(sorted_stats, columns=['שומר', 'משמרות']).set_index('שומר')
        st.bar_chart(chart_df, color="#3b82f6", use_container_width=True)

        # ── סיכום נוסף ──
        total_s = sum(current_stats.values())
        active_guards = sum(1 for v in current_stats.values() if v > 0)

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("סה\"כ משמרות", total_s)
        with m2:
            st.metric("שומרים פעילים", active_guards)
        with m3:
            avg = round(total_s / active_guards, 1) if active_guards else 0
            st.metric("ממוצע לשומר", avg)

    st.markdown('</div>', unsafe_allow_html=True)
