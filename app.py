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
# CSS
# ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Assistant', sans-serif !important;
    direction: rtl;
    text-align: right;
}

.stApp {
    background: linear-gradient(135deg, #0f1923 0%, #1a2840 100%);
    min-height: 100vh;
}

/* ── כותרת ─────────────────────────────────── */
.app-header {
    background: linear-gradient(90deg, #1e3a5f 0%, #2563eb 50%, #1e3a5f 100%);
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 8px 32px rgba(37,99,235,0.3);
    border: 1px solid rgba(255,255,255,0.08);
}
.app-header h1 { color:#fff; font-size:1.8rem; font-weight:800; margin:0; }
.app-header p  { color:rgba(255,255,255,0.65); font-size:0.9rem; margin:4px 0 0; }

/* ── טאבים ────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.05);
    border-radius: 12px; padding: 4px; gap: 4px;
    border: 1px solid rgba(255,255,255,0.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important;
    font-family: 'Assistant', sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    color: rgba(255,255,255,0.55) !important; padding: 9px 16px !important;
    border: none !important; background: transparent !important;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    color: #fff !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
}

/* ── כרטיסים ──────────────────────────────── */
.card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px; padding: 18px 20px;
    margin-bottom: 16px; backdrop-filter: blur(8px);
}
.card-title {
    font-size: 1rem; font-weight: 700; color: #93c5fd;
    margin-bottom: 12px; padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}

/* ── כותרת יום ────────────────────────────── */
.day-header {
    background: linear-gradient(90deg,rgba(37,99,235,.22) 0%,rgba(37,99,235,.05) 100%);
    border-right: 4px solid #3b82f6;
    border-radius: 8px; padding: 9px 14px;
    margin: 20px 0 8px;
    font-size: .95rem; font-weight: 700; color: #93c5fd;
}

/* ── שורת משמרת (כרטיס) ──────────────────── */
.shift-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: 9px;
    border: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 6px;
    background: rgba(255,255,255,0.025);
    transition: background 0.15s;
}
.shift-card:hover { background: rgba(255,255,255,0.05); }
.shift-time {
    font-size: .92rem; font-weight: 700; color: #60a5fa;
    white-space: nowrap; min-width: 100px; flex-shrink: 0;
    font-variant-numeric: tabular-nums;
    background: rgba(37,99,235,0.15);
    padding: 4px 10px; border-radius: 6px;
}
.shift-names {
    font-size: .9rem; color: #e2e8f0; flex: 1;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.shift-badge-past   { background:rgba(100,116,139,.2); color:#94a3b8; }
.shift-badge-future { background:rgba(37,199,235,.12); color:#7dd3fc; }

/* ── פילטר (pills) ────────────────────────── */
div[data-testid="stHorizontalBlock"] .stRadio label {
    cursor: pointer;
}
.stRadio > div { flex-direction: row !important; gap: 6px !important; flex-wrap: nowrap !important; }
.stRadio label {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 20px !important; padding: 5px 14px !important;
    color: #94a3b8 !important; font-size: .88rem !important;
    font-weight: 600 !important; cursor: pointer;
    transition: all 0.2s; white-space: nowrap;
}
.stRadio label:has(input:checked) {
    background: rgba(37,99,235,0.35) !important;
    border-color: #3b82f6 !important; color: #93c5fd !important;
}
.stRadio [data-testid="stMarkdownContainer"] { display: none; }

/* ── גלילה ────────────────────────────────── */
.scroll-box {
    max-height: 55vh; overflow-y: auto;
    scrollbar-width: thin; scrollbar-color: rgba(96,165,250,.35) transparent;
    padding-left: 2px;
}
.scroll-box::-webkit-scrollbar { width: 4px; }
.scroll-box::-webkit-scrollbar-thumb { background:rgba(96,165,250,.35); border-radius:4px; }

/* ── רשימה זמנית (staging) ───────────────── */
.staging-row {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 12px;
    border-radius: 8px; margin-bottom: 6px;
    background: rgba(37,99,235,0.08);
    border: 1px solid rgba(37,99,235,0.2);
}
.staging-time { font-weight: 700; color: #60a5fa; white-space: nowrap; font-size: .9rem; min-width: 110px; }
.staging-names { flex: 1; color: #cbd5e1; font-size: .9rem; }
.staging-empty {
    text-align: center; color: #475569; font-size: .9rem;
    padding: 28px; border: 2px dashed rgba(255,255,255,0.08); border-radius: 10px;
}

/* ── כפתורים ──────────────────────────────── */
.stButton > button {
    border-radius: 10px !important; font-family: 'Assistant', sans-serif !important;
    font-weight: 600 !important; transition: all 0.2s !important;
    white-space: nowrap !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color: #fff !important; box-shadow: 0 4px 14px rgba(37,99,235,.35) !important;
}
.stButton > button[kind="primary"]:hover { transform:translateY(-1px) !important; }
.stButton > button:not([kind="primary"]) {
    background: rgba(255,255,255,0.07) !important;
    color: #cbd5e1 !important; border: 1px solid rgba(255,255,255,0.12) !important;
}

/* ── כפתור אישור ── */
.confirm-btn > button {
    background: linear-gradient(135deg,#16a34a,#22c55e) !important;
    color: #fff !important; font-size: 1rem !important;
    box-shadow: 0 4px 16px rgba(22,163,74,.35) !important;
}

/* ── שדות קלט ────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important; color: #e2e8f0 !important;
    font-family: 'Assistant', sans-serif !important; direction: rtl !important;
}
.stTextInput > div > div > input:focus, .stTextArea textarea:focus {
    border-color: #3b82f6 !important; box-shadow: 0 0 0 2px rgba(59,130,246,.25) !important;
}
label { color: #94a3b8 !important; font-size: .88rem !important; font-weight: 600 !important; }

/* ── multiselect ──────────────────────────── */
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(37,99,235,0.3) !important; border-radius: 6px !important;
    color: #93c5fd !important; white-space: nowrap !important;
}
.stMultiSelect > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important; border-radius: 9px !important;
}

/* ── date/time ────────────────────────────── */
.stDateInput > div > div > input, .stTimeInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important; color: #e2e8f0 !important;
}

/* ── selectbox ────────────────────────────── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important; color: #e2e8f0 !important;
}

/* ── סטטיסטיקה ────────────────────────────── */
.stat-row {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.06);
    direction: rtl;
}
.stat-row:last-child { border-bottom: none; }
.stat-rank {
    width: 28px; height: 28px; line-height: 28px; text-align: center;
    border-radius: 50%; font-size: .78rem; font-weight: 800;
    flex-shrink: 0;
    background: rgba(37,99,235,0.2); color: #93c5fd;
}
.rank-1 { background:rgba(250,204,21,.22); color:#fde047; }
.rank-2 { background:rgba(203,213,225,.22); color:#cbd5e1; }
.rank-3 { background:rgba(251,146,60,.22); color:#fb923c; }
.stat-name { flex: 1; font-weight: 700; color: #e2e8f0; font-size: .95rem; }
.stat-numbers {
    display: flex; gap: 8px; align-items: center; flex-shrink: 0;
}
.stat-pill {
    padding: 2px 10px; border-radius: 12px;
    font-size: .78rem; font-weight: 700; white-space: nowrap;
}
.pill-total   { background:rgba(37,99,235,.25); color:#93c5fd; }
.pill-past    { background:rgba(16,185,129,.2);  color:#6ee7b7; }
.pill-future  { background:rgba(251,191,36,.18); color:#fcd34d; }
.stat-bar-wrap { width: 90px; flex-shrink: 0; }
.stat-bar {
    height: 8px; border-radius: 4px;
    background: linear-gradient(90deg,#2563eb,#60a5fa); min-width: 4px;
}

/* ── metric cards ─────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 12px !important; padding: 14px !important;
    text-align: center;
}
[data-testid="stMetricLabel"] { color:#94a3b8 !important; font-size:.85rem !important; }
[data-testid="stMetricValue"] { color:#f1f5f9 !important; font-size:1.6rem !important; font-weight:800 !important; }

/* ── link button WhatsApp ─────────────────── */
.stLinkButton a {
    background: linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; border-radius:10px !important;
    font-family:'Assistant',sans-serif !important; font-weight:700 !important;
    padding:.55rem 1.2rem !important; text-decoration:none !important;
    box-shadow:0 4px 14px rgba(22,163,74,.35) !important; white-space:nowrap !important;
    display:inline-block;
}

hr { border-color: rgba(255,255,255,0.07) !important; margin: 16px 0 !important; }

/* ── רספונסיבי ────────────────────────────── */
@media (max-width:640px) {
    .app-header h1 { font-size:1.3rem; }
    .app-header { padding:14px; }
    .card { padding:12px 10px; }
    .shift-time { min-width:90px; font-size:.85rem; }
    .stat-bar-wrap { width:55px; }
}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# כותרת
# ────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🛡️ Smart Guard Manager</h1>
    <p>מערכת ניהול שמירות חכמה • ניהול, שיבוץ וסטטיסטיקות</p>
</div>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# מסד נתונים
# ────────────────────────────────────────────────
@st.cache_resource
def init_db():
    db_dir = '/app/data'
    path = os.path.join(db_dir, 'guard_system.db') if os.path.exists(db_dir) else 'guard_system.db'
    c = sqlite3.connect(path, check_same_thread=False)
    cur = c.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS guards
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS shifts
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT, end_time TEXT, names TEXT)''')
    c.commit()
    return c

conn = init_db()

# ────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────
HE_DAY = {
    'Sunday':'ראשון','Monday':'שני','Tuesday':'שלישי',
    'Wednesday':'רביעי','Thursday':'חמישי','Friday':'שישי','Saturday':'שבת'
}

def get_guards() -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM guards ORDER BY name ASC", conn)

def get_shifts() -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM shifts ORDER BY start_time ASC", conn)

def guard_shift_counts() -> dict:
    shifts = get_shifts()
    guards = get_guards()
    counts = {r['name']: 0 for _, r in guards.iterrows()}
    for names_str in shifts['names']:
        for n in names_str.split(', '):
            n = n.strip()
            if n in counts:
                counts[n] += 1
    return counts

def last_end_time() -> datetime | None:
    """מחזיר את זמן סיום המשמרת האחרונה (DB + staging)."""
    db_end = None
    shifts = get_shifts()
    if not shifts.empty:
        db_end = datetime.strptime(shifts.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S')
    staging = st.session_state.get('temp_shifts', [])
    staging_end = staging[-1]['end'] if staging else None
    candidates = [t for t in [db_end, staging_end] if t]
    return max(candidates) if candidates else None

# ── session state ──
if 'temp_shifts' not in st.session_state:
    st.session_state.temp_shifts = []

# ────────────────────────────────────────────────
# טאבים
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 משמרות", "➕ הוספת משמרת", "📊 סטטיסטיקה", "👥 צוות"])


# ════════════════════════════════════════════════
# TAB 1 – רשימת משמרות
# ════════════════════════════════════════════════
with tab1:
    shifts_df = get_shifts()
    now = datetime.now()

    # ── פילטר ──────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)

    top_c1, top_c2 = st.columns([2, 3])
    with top_c1:
        filt = st.radio(
            "סינון:",
            ["הכל", "עתידי", "עבר"],
            horizontal=True,
            key="shift_filter",
            label_visibility="collapsed"
        )

    if not shifts_df.empty:
        shifts_df['start_dt'] = pd.to_datetime(shifts_df['start_time'])
        shifts_df['end_dt']   = pd.to_datetime(shifts_df['end_time'])

        if filt == "עתידי":
            view = shifts_df[shifts_df['start_dt'] > now].copy()
        elif filt == "עבר":
            view = shifts_df[shifts_df['end_dt'] <= now].copy()
        else:
            view = shifts_df.copy()

        with top_c2:
            st.markdown(
                f"<span style='color:#64748b;font-size:.85rem;line-height:2.5;'>"
                f"מוצגות {len(view)} מתוך {len(shifts_df)} משמרות</span>",
                unsafe_allow_html=True
            )

        st.markdown('</div>', unsafe_allow_html=True)

        if view.empty:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.info("אין משמרות להצגה בפילטר שנבחר.")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            view['date'] = view['start_time'].str[:10]
            unique_days = view['date'].unique()

            st.markdown('<div class="scroll-box">', unsafe_allow_html=True)
            for day in unique_days:
                d = datetime.strptime(day, '%Y-%m-%d')
                day_he = HE_DAY.get(d.strftime('%A'), '')
                nice   = d.strftime('%d/%m/%Y')
                st.markdown(
                    f'<div class="day-header">📅 יום {day_he} &nbsp;·&nbsp; {nice}</div>',
                    unsafe_allow_html=True
                )
                day_rows = view[view['date'] == day]
                for _, r in day_rows.iterrows():
                    s = r['start_time'][11:16]
                    e = r['end_time'][11:16]
                    is_past = r['end_dt'] <= now
                    badge_cls = "shift-badge-past" if is_past else "shift-badge-future"
                    indicator = "⬜" if is_past else "🟦"
                    st.markdown(
                        f'<div class="shift-card {badge_cls}">'
                        f'  <span class="shift-time">{indicator} {s} – {e}</span>'
                        f'  <span class="shift-names">{r["names"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            st.markdown('</div>', unsafe_allow_html=True)

            # ── פעולות + WhatsApp ──
            st.markdown('<div class="card" style="margin-top:14px;">', unsafe_allow_html=True)
            act1, act2, act3 = st.columns(3)
            with act1:
                if st.button("🗑️ מחק אחרונה", use_container_width=True):
                    conn.cursor().execute("DELETE FROM shifts WHERE id=(SELECT MAX(id) FROM shifts)")
                    conn.commit(); st.rerun()
            with act2:
                if st.button("🗑️ מחק הכל", use_container_width=True):
                    conn.cursor().execute("DELETE FROM shifts")
                    conn.commit(); st.rerun()
            with act3:
                # בניית הודעת וואטסאפ
                msg = "🛡️ *סידור שמירה*\n"
                msg += f"📆 {now.strftime('%d/%m/%Y %H:%M')}\n"
                for day in view['date'].unique():
                    d = datetime.strptime(day, '%Y-%m-%d')
                    msg += f"\n🗓️ *יום {HE_DAY.get(d.strftime('%A'),'')} {d.strftime('%d/%m')}:*\n"
                    for _, r in view[view['date']==day].iterrows():
                        msg += f"• {r['start_time'][11:16]}–{r['end_time'][11:16]} ▸ {r['names']}\n"
                msg += "\n_Smart Guard Manager_ 🛡️"
                st.link_button("📲 וואטסאפ",
                               f"https://wa.me/?text={urllib.parse.quote(msg)}",
                               use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("📭 אין משמרות. לחץ על 'הוספת משמרת' כדי להתחיל.")
        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
# TAB 2 – הוספת משמרות (staging)
# ════════════════════════════════════════════════
with tab2:
    guards_df = get_guards()

    if guards_df.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.warning("⚠️ אין שומרים. הוסף שומרים בטאב 'צוות' תחילה.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        counts = guard_shift_counts()

        # ── חישוב זמן התחלה אוטומטי ──
        last_end = last_end_time()

        # ── טופס הוספה ────────────────────────────────
        st.markdown('<div class="card"><div class="card-title">⚙️ הגדרות משמרת</div>', unsafe_allow_html=True)

        if last_end:
            st.markdown(
                f"<div style='color:#60a5fa;font-size:.88rem;margin-bottom:10px;'>"
                f"⏭️ המשמרת הבאה תתחיל ב: <b>{last_end.strftime('%d/%m %H:%M')}</b>"
                f" (בהמשך לקודמת)</div>",
                unsafe_allow_html=True
            )
            init_date = last_end.date()
            init_time = last_end.time()
        else:
            now_r = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            init_date = now_r.date()
            init_time = now_r.time()

        f1, f2 = st.columns(2)
        with f1:
            if last_end:
                st.date_input("📅 תאריך התחלה", value=init_date, key="add_date", disabled=True)
            else:
                chosen_date = st.date_input("📅 תאריך התחלה", value=init_date, key="add_date")
        with f2:
            if last_end:
                st.time_input("🕐 שעת התחלה", value=init_time, key="add_time", disabled=True)
            else:
                chosen_time = st.time_input("🕐 שעת התחלה", value=init_time, key="add_time")

        f3, f4 = st.columns(2)
        with f3:
            duration = st.selectbox(
                "⏱️ משך (דקות)",
                [30, 45, 60, 90, 120, 180, 240],
                index=2, key="add_dur"
            )
        with f4:
            num_per = st.number_input("👥 שומרים בעמדה", 1, 10, 2, key="add_num")

        # multiselect עם ספירת משמרות
        options = [f"{r['name']} ({counts.get(r['name'],0)})" for _, r in guards_df.iterrows()]
        selected_raw = st.multiselect(
            "👤 בחר שומרים (מספר בסוגריים = כמות משמרות):",
            options=options,
            placeholder="הקלד שם לחיפוש...",
            key="add_guards"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── כפתור הוסף לרשימה ──────────────────────────
        if st.button("➕ הוסף לרשימה הממתינה", type="primary", use_container_width=True):
            if not selected_raw:
                st.warning("⚠️ בחר לפחות שומר אחד.")
            else:
                selected_names = [s.rsplit(' (', 1)[0] for s in selected_raw]
                le = last_end_time()
                if le:
                    start = le
                else:
                    d = st.session_state.get('add_date', init_date)
                    t = st.session_state.get('add_time', init_time)
                    start = datetime.combine(d, t)
                end = start + timedelta(minutes=int(duration))
                st.session_state.temp_shifts.append({
                    'start': start, 'end': end,
                    'names': ', '.join(selected_names)
                })
                st.rerun()

        # ── רשימה ממתינה ───────────────────────────────
        st.markdown('<div class="card"><div class="card-title">📋 משמרות ממתינות לאישור</div>',
                    unsafe_allow_html=True)

        temp = st.session_state.temp_shifts

        if not temp:
            st.markdown(
                '<div class="staging-empty">אין משמרות בהמתנה.<br>'
                '<span style="font-size:.8rem;color:#334155;">השתמש בטופס למעלה להוסיף.</span></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='color:#60a5fa;font-size:.85rem;margin-bottom:10px;'>"
                f"📌 {len(temp)} משמרות מוכנות לאישור</div>",
                unsafe_allow_html=True
            )
            del_idx = None
            for i, sh in enumerate(temp):
                c_row, c_del = st.columns([6, 1])
                with c_row:
                    s = sh['start'].strftime('%d/%m %H:%M')
                    e = sh['end'].strftime('%H:%M')
                    st.markdown(
                        f'<div class="staging-row">'
                        f'  <span class="staging-time">🕐 {s} – {e}</span>'
                        f'  <span class="staging-names">{sh["names"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with c_del:
                    if st.button("🗑️", key=f"rm_{i}", help="הסר"):
                        del_idx = i

            if del_idx is not None:
                st.session_state.temp_shifts.pop(del_idx)
                st.rerun()

            st.markdown('<br>', unsafe_allow_html=True)
            col_ok, col_cancel = st.columns(2)
            with col_ok:
                st.markdown('<div class="confirm-btn">', unsafe_allow_html=True)
                if st.button("✅ אשר הכל ושמור", type="primary", use_container_width=True):
                    cur = conn.cursor()
                    for sh in st.session_state.temp_shifts:
                        cur.execute(
                            "INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                            (sh['start'].strftime('%Y-%m-%d %H:%M:%S'),
                             sh['end'].strftime('%Y-%m-%d %H:%M:%S'),
                             sh['names'])
                        )
                    conn.commit()
                    n = len(st.session_state.temp_shifts)
                    st.session_state.temp_shifts = []
                    st.success(f"✅ {n} משמרות נשמרו בהצלחה!")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with col_cancel:
                if st.button("✖️ בטל הכל", use_container_width=True):
                    st.session_state.temp_shifts = []
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
# TAB 3 – סטטיסטיקה
# ════════════════════════════════════════════════
with tab3:
    all_shifts = get_shifts()
    all_guards = get_guards()
    now = datetime.now()

    if all_guards.empty:
        st.info("אין נתונים.")
    else:
        # ── חישוב נתונים ──
        guard_stats = {}
        for _, g in all_guards.iterrows():
            guard_stats[g['name']] = {'past': 0, 'future': 0, 'total': 0}

        if not all_shifts.empty:
            all_shifts['start_dt'] = pd.to_datetime(all_shifts['start_time'])
            all_shifts['end_dt']   = pd.to_datetime(all_shifts['end_time'])
            for _, r in all_shifts.iterrows():
                for n in r['names'].split(', '):
                    n = n.strip()
                    if n in guard_stats:
                        guard_stats[n]['total'] += 1
                        if r['end_dt'] <= now:
                            guard_stats[n]['past'] += 1
                        else:
                            guard_stats[n]['future'] += 1

        sorted_guards = sorted(guard_stats.items(), key=lambda x: x[1]['total'], reverse=True)
        max_total = sorted_guards[0][1]['total'] if sorted_guards else 1

        # ── כרטיסי סיכום ──
        total_shifts_db = len(all_shifts) if not all_shifts.empty else 0
        active = sum(1 for _, v in guard_stats.items() if v['total'] > 0)
        past_total = sum(v['past'] for _, v in guard_stats.items())
        future_total = sum(v['future'] for _, v in guard_stats.items())

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("סה\"כ משמרות", total_shifts_db)
        mc2.metric("בוצעו", past_total)
        mc3.metric("עתידיות", future_total)
        mc4.metric("שומרים פעילים", active)

        st.markdown('<div class="card" style="margin-top:16px;"><div class="card-title">📊 ניתוח לפי שומר</div>',
                    unsafe_allow_html=True)

        if not any(v['total'] > 0 for _, v in guard_stats.items()):
            st.info("אין נתוני משמרות עדיין.")
        else:
            rows_html = ""
            for rank, (name, v) in enumerate(sorted_guards, 1):
                if v['total'] == 0 and rank > 3:
                    continue  # הסתר שומרים ללא משמרות מעמדה 4+
                bar_pct = int((v['total'] / max_total) * 100) if max_total > 0 else 0
                rc = f"rank-{rank}" if rank <= 3 else ""
                avg_per = round(v['total'] / max(total_shifts_db, 1) * 100, 1)
                rows_html += f"""
                <div class="stat-row">
                  <div class="stat-rank {rc}">{rank}</div>
                  <div class="stat-name">{name}</div>
                  <div class="stat-numbers">
                    <span class="stat-pill pill-total">סה"כ {v['total']}</span>
                    <span class="stat-pill pill-past">✅ {v['past']}</span>
                    <span class="stat-pill pill-future">🕐 {v['future']}</span>
                  </div>
                  <div class="stat-bar-wrap">
                    <div class="stat-bar" style="width:{bar_pct}%;"></div>
                  </div>
                </div>
                """
            st.markdown(rows_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        if not all_shifts.empty and any(v['total'] > 0 for _, v in guard_stats.items()):
            st.markdown('<div class="card"><div class="card-title">📈 גרף משמרות</div>', unsafe_allow_html=True)
            chart_data = pd.DataFrame(
                [(n, v['past'], v['future']) for n, v in sorted_guards if v['total'] > 0],
                columns=['שומר', 'בוצעו', 'עתידיות']
            ).set_index('שומר')
            st.bar_chart(chart_data, color=["#3b82f6", "#f59e0b"], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
# TAB 4 – ניהול צוות
# ════════════════════════════════════════════════
with tab4:

    # ── הוספה מרובה ──
    st.markdown('<div class="card"><div class="card-title">➕ הוספת שומרים</div>', unsafe_allow_html=True)
    with st.expander("הוספה מרובה (שמות מופרדים בפסיק)"):
        bulk = st.text_area("שמות:", placeholder="ישראל ישראלי, משה כהן, דוד לוי", key="bulk_add")
        if st.button("💾 שמור הכל", key="bulk_save"):
            names = [x.strip() for x in bulk.split(',') if x.strip()]
            added = 0
            cur = conn.cursor()
            for n in names:
                try:
                    cur.execute("INSERT INTO guards (name) VALUES (?)", (n,)); added += 1
                except sqlite3.IntegrityError:
                    pass
            conn.commit()
            if added: st.success(f"✅ נוספו {added} שומרים."); st.rerun()

    with st.expander("הוספה בודדת"):
        sname = st.text_input("שם:", placeholder="הכנס שם...", key="single_add")
        if st.button("➕ הוסף", key="single_save"):
            if sname.strip():
                try:
                    conn.cursor().execute("INSERT INTO guards (name) VALUES (?)", (sname.strip(),))
                    conn.commit(); st.success(f"✅ {sname.strip()} נוסף."); st.rerun()
                except sqlite3.IntegrityError:
                    st.error("שם כבר קיים.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── רשימת שומרים ──
    st.markdown('<div class="card"><div class="card-title">👥 רשימת שומרים</div>', unsafe_allow_html=True)
    g_list = get_guards()
    cur_counts = guard_shift_counts()

    if g_list.empty:
        st.info("אין שומרים במערכת.")
    else:
        st.markdown(f"<span style='color:#64748b;font-size:.85rem;'>סה\"כ {len(g_list)} שומרים</span>",
                    unsafe_allow_html=True)
        st.markdown('<div class="scroll-box">', unsafe_allow_html=True)
        del_id = None
        save_data = {}
        for _, row in g_list.iterrows():
            gid = row['id']
            c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
            with c1:
                new_name = st.text_input("שם", value=row['name'], key=f"gn_{gid}",
                                         label_visibility="collapsed")
            with c2:
                n_shifts = cur_counts.get(row['name'], 0)
                st.markdown(
                    f"<div style='text-align:center;padding-top:8px;'>"
                    f"<span style='background:rgba(37,99,235,.2);color:#93c5fd;"
                    f"border-radius:5px;padding:2px 8px;font-size:.78rem;font-weight:700;'>{n_shifts}</span></div>",
                    unsafe_allow_html=True
                )
            with c3:
                if st.button("💾", key=f"sv_{gid}"):
                    save_data[gid] = new_name.strip()
            with c4:
                if st.button("🗑️", key=f"dl_{gid}"):
                    del_id = gid

        if del_id:
            conn.cursor().execute("DELETE FROM guards WHERE id=?", (del_id,))
            conn.commit(); st.rerun()
        for gid, name in save_data.items():
            if name:
                try:
                    conn.cursor().execute("UPDATE guards SET name=? WHERE id=?", (name, gid))
                    conn.commit()
                except sqlite3.IntegrityError:
                    st.error("שם כבר קיים.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
