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
    border-radius: 14px; padding: 16px 18px;
    margin-bottom: 14px; backdrop-filter: blur(8px);
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
    margin: 18px 0 6px;
    font-size: .95rem; font-weight: 700; color: #93c5fd;
}

/* ── שורת משמרת בטאב ראשון ───────────────── */
/* (מבוסס columns, לא HTML טהור, למניעת שבירה) */
.s-time-cell {
    white-space: nowrap !important;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    padding: 6px 0;
}
.s-future { color: #60a5fa; }
.s-past   { color: #94a3b8; }
.s-badge {
    display: inline-block;
    padding: 3px 9px; border-radius: 6px;
    font-size: .88rem; white-space: nowrap;
}
.s-badge-f { background: rgba(37,99,235,0.18); }
.s-badge-p { background: rgba(100,116,139,0.18); }
.s-names-cell {
    color: #e2e8f0; font-size: .88rem;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding: 6px 0;
}

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

/* ── צ׳קבוקסים לבחירת שומרים ─────────────── */
.stCheckbox {
    margin-bottom: 4px !important;
}
.stCheckbox > label {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 8px !important;
    padding: 7px 10px !important;
    width: 100% !important;
    cursor: pointer;
    transition: all 0.15s;
    color: #cbd5e1 !important;
    font-size: .88rem !important;
    white-space: nowrap !important;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stCheckbox > label:hover {
    background: rgba(37,99,235,0.1) !important;
    border-color: rgba(59,130,246,0.3) !important;
}
.stCheckbox > label:has(input:checked) {
    background: rgba(37,99,235,0.2) !important;
    border-color: rgba(59,130,246,0.5) !important;
    color: #93c5fd !important;
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

/* כפתור אישור (ירוק) */
.confirm-btn > button {
    background: linear-gradient(135deg,#16a34a,#22c55e) !important;
    color: #fff !important; font-size: 1rem !important;
    box-shadow: 0 4px 16px rgba(22,163,74,.35) !important;
}

/* כפתורים קטנים בשורות (מחיקה / שמירה) */
div[data-testid="column"] .stButton > button {
    padding: 0.3rem 0.55rem !important;
    font-size: .82rem !important;
    min-height: unset !important;
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

/* ── date/time/selectbox ──────────────────── */
.stDateInput > div > div > input, .stTimeInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important; color: #e2e8f0 !important;
}
.stSelectbox > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 9px !important; color: #e2e8f0 !important;
}

/* ── pills לסטטיסטיקה ──────────────────────── */
.stat-row {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.06);
    direction: rtl;
}
.stat-row:last-child { border-bottom: none; }
.stat-rank {
    width: 28px; height: 28px; line-height: 28px; text-align: center;
    border-radius: 50%; font-size: .78rem; font-weight: 800; flex-shrink: 0;
    background: rgba(37,99,235,0.2); color: #93c5fd;
}
.rank-1 { background:rgba(250,204,21,.22); color:#fde047; }
.rank-2 { background:rgba(203,213,225,.22); color:#cbd5e1; }
.rank-3 { background:rgba(251,146,60,.22); color:#fb923c; }
.stat-name { flex: 1; font-weight: 700; color: #e2e8f0; font-size: .95rem; }
.stat-numbers { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.stat-pill {
    padding: 2px 10px; border-radius: 12px;
    font-size: .78rem; font-weight: 700; white-space: nowrap;
}
.pill-total  { background:rgba(37,99,235,.25); color:#93c5fd; }
.pill-past   { background:rgba(16,185,129,.2);  color:#6ee7b7; }
.pill-future { background:rgba(251,191,36,.18); color:#fcd34d; }
.stat-bar-wrap { width: 90px; flex-shrink: 0; }
.stat-bar { height: 8px; border-radius: 4px;
    background: linear-gradient(90deg,#2563eb,#60a5fa); min-width: 4px; }

/* ── metric ─────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 12px !important; padding: 14px !important;
    text-align: center;
}
[data-testid="stMetricLabel"] { color:#94a3b8 !important; font-size:.85rem !important; }
[data-testid="stMetricValue"] { color:#f1f5f9 !important; font-size:1.6rem !important; font-weight:800 !important; }

/* ── pill badge לשומרים ─────────────────────── */
.g-pill {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: .75rem; font-weight: 700; white-space: nowrap;
}
.g-past   { background:rgba(16,185,129,.18);  color:#6ee7b7; }
.g-future { background:rgba(251,191,36,.15);  color:#fcd34d; }

/* ── WhatsApp link button ────────────────────── */
.stLinkButton a {
    background: linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; border-radius:10px !important;
    font-family:'Assistant',sans-serif !important; font-weight:700 !important;
    padding:.55rem 1.2rem !important; text-decoration:none !important;
    box-shadow:0 4px 14px rgba(22,163,74,.35) !important; white-space:nowrap !important;
    display:inline-block;
}

hr { border-color: rgba(255,255,255,0.07) !important; margin: 14px 0 !important; }

/* ── מובייל ─────────────────────────────────── */
@media (max-width:640px) {
    .app-header h1 { font-size:1.3rem; }
    .app-header { padding:14px; }
    .card { padding:12px 10px; }
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
    cur.execute('CREATE TABLE IF NOT EXISTS guards (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
    cur.execute('''CREATE TABLE IF NOT EXISTS shifts
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT, end_time TEXT, names TEXT)''')
    c.commit()
    return c

conn = init_db()

# ────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────
HE_DAY = {
    'Sunday':'ראשון','Monday':'שני','Tuesday':'שלישי',
    'Wednesday':'רביעי','Thursday':'חמישי','Friday':'שישי','Saturday':'שבת'
}

def get_guards() -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM guards ORDER BY name ASC", conn)

def get_shifts() -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM shifts ORDER BY start_time ASC", conn)

def get_guard_stats(now: datetime) -> dict:
    """Returns {name: {'past': int, 'future': int}} for every guard."""
    guards = get_guards()
    shifts = get_shifts()
    result = {r['name']: {'past': 0, 'future': 0} for _, r in guards.iterrows()}
    if not shifts.empty:
        for _, r in shifts.iterrows():
            end_dt = datetime.strptime(r['end_time'], '%Y-%m-%d %H:%M:%S')
            bucket = 'past' if end_dt <= now else 'future'
            for n in r['names'].split(', '):
                n = n.strip()
                if n in result:
                    result[n][bucket] += 1
    return result

def last_end_time() -> datetime | None:
    """הזמן האחרון מ-DB + staging."""
    candidates = []
    shifts = get_shifts()
    if not shifts.empty:
        candidates.append(datetime.strptime(shifts.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S'))
    for sh in st.session_state.get('temp_shifts', []):
        candidates.append(sh['end'])
    return max(candidates) if candidates else None

# ── session state init ──
if 'temp_shifts' not in st.session_state:
    st.session_state.temp_shifts = []
if 'chk_ver' not in st.session_state:
    st.session_state.chk_ver = 0   # bump to reset checkboxes after adding

# ────────────────────────────────────────────────
# טאבים: 📋 משמרות | + | 👥 שומרים | 📊 סטטיסטיקה
# ────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 משמרות", "+", "👥 שומרים", "📊 סטטיסטיקה"])


# ════════════════════════════════════════════════
# TAB 1 – רשימת משמרות  (חיפוש טקסט + מחיקה בשורה)
# ════════════════════════════════════════════════
with tab1:
    shifts_df = get_shifts()
    now = datetime.now()

    # ── שדה חיפוש ──────────────────────────────
    search = st.text_input(
        "_", label_visibility="collapsed",
        placeholder="🔍  חפש לפי שם שומר או תאריך (dd/mm)...",
        key="shift_search"
    )

    if shifts_df.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("📭 אין משמרות. לחץ על '+' להתחיל.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        shifts_df['start_dt'] = pd.to_datetime(shifts_df['start_time'])
        shifts_df['end_dt']   = pd.to_datetime(shifts_df['end_time'])
        shifts_df['date']     = shifts_df['start_time'].str[:10]
        shifts_df['nice_date'] = shifts_df['start_dt'].dt.strftime('%d/%m/%Y')

        view = shifts_df.copy()
        if search.strip():
            q = search.strip().lower()
            view = view[
                view['names'].str.lower().str.contains(q, na=False) |
                view['nice_date'].str.contains(q, na=False)
            ]

        st.markdown(
            f"<span style='color:#475569;font-size:.82rem;'>"
            f"מוצגות {len(view)} מתוך {len(shifts_df)} משמרות</span>",
            unsafe_allow_html=True
        )

        if view.empty:
            st.info("לא נמצאו תוצאות לחיפוש.")
        else:
            delete_id = None

            st.markdown('<div class="scroll-box">', unsafe_allow_html=True)
            for day in view['date'].unique():
                d = datetime.strptime(day, '%Y-%m-%d')
                nice   = d.strftime('%d/%m/%Y')
                day_he = HE_DAY.get(d.strftime('%A'), '')
                st.markdown(
                    f'<div class="day-header">📅 יום {day_he} &nbsp;·&nbsp; {nice}</div>',
                    unsafe_allow_html=True
                )
                for _, r in view[view['date'] == day].iterrows():
                    s = r['start_time'][11:16]
                    e = r['end_time'][11:16]
                    is_past = r['end_dt'] <= now
                    cls  = "s-past s-badge s-badge-p" if is_past else "s-future s-badge s-badge-f"
                    icon = "⬜" if is_past else "🟦"

                    # 3 עמודות: זמן | שמות | מחיקה — white-space:nowrap בכולם
                    c_t, c_n, c_d = st.columns([22, 65, 8])
                    with c_t:
                        st.markdown(
                            f"<div class='s-time-cell {cls}'>{icon} {s}–{e}</div>",
                            unsafe_allow_html=True
                        )
                    with c_n:
                        st.markdown(
                            f"<div class='s-names-cell'>{r['names']}</div>",
                            unsafe_allow_html=True
                        )
                    with c_d:
                        if st.button("🗑️", key=f"ds_{r['id']}", help="מחק משמרת"):
                            delete_id = r['id']
            st.markdown('</div>', unsafe_allow_html=True)

            if delete_id is not None:
                conn.cursor().execute("DELETE FROM shifts WHERE id=?", (delete_id,))
                conn.commit()
                st.rerun()

            # ── WhatsApp ─────────────────────────────
            st.markdown('<br>', unsafe_allow_html=True)
            msg = "🛡️ *סידור שמירה*\n" + f"📆 {now.strftime('%d/%m/%Y %H:%M')}\n"
            for day in view['date'].unique():
                d = datetime.strptime(day, '%Y-%m-%d')
                msg += f"\n🗓️ *יום {HE_DAY.get(d.strftime('%A'),'')} {d.strftime('%d/%m')}:*\n"
                for _, r in view[view['date'] == day].iterrows():
                    msg += f"• {r['start_time'][11:16]}–{r['end_time'][11:16]} ▸ {r['names']}\n"
            msg += "\n_Smart Guard Manager_ 🛡️"
            st.link_button(
                "📲 שלח בוואטסאפ",
                f"https://wa.me/?text={urllib.parse.quote(msg)}",
                use_container_width=False
            )


# ════════════════════════════════════════════════
# TAB 2 – "+"  הוספת משמרות
# (ללא כותרות, תאריך/שעה חופשיים, צ'קבוקסים, קידום אוטומטי)
# ════════════════════════════════════════════════
with tab2:
    guards_df = get_guards()

    if guards_df.empty:
        st.warning("⚠️ אין שומרים. עבור לטאב 'שומרים' כדי להוסיף.")
    else:
        gstats_now = get_guard_stats(datetime.now())

        # ── רמז זמן הבא (לא נועל שדות) ──────────
        next_hint = last_end_time()

        # ── ערכי ברירת מחדל לשדות date/time ──────
        # session_state['add_date'] / ['add_time'] מוגדרים אחרי הוספה (auto-advance)
        if 'add_date' not in st.session_state:
            nr = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            st.session_state['add_date'] = nr.date()
            st.session_state['add_time'] = nr.time()

        if next_hint:
            st.markdown(
                f"<div style='background:rgba(37,99,235,.1);border:1px solid rgba(59,130,246,.25);"
                f"border-radius:9px;padding:7px 13px;margin-bottom:10px;font-size:.85rem;color:#93c5fd;'>"
                f"⏭️ רצף אוטומטי: המשמרת הבאה ב־<b>{next_hint.strftime('%d/%m %H:%M')}</b></div>",
                unsafe_allow_html=True
            )

        # ── שדות תאריך + שעה + משך (תמיד ניתנים לעריכה) ──
        d1, d2, d3 = st.columns(3)
        with d1:
            chosen_date = st.date_input("📅 תאריך", key="add_date")
        with d2:
            chosen_time = st.time_input("🕐 שעה", key="add_time", step=1800)
        with d3:
            duration = st.selectbox(
                "⏱️ משך (דק׳)",
                [30, 45, 60, 90, 120, 180, 240],
                index=2, key="add_dur"
            )

        # ── בחירת שומרים – צ'קבוקסים ─────────────
        st.markdown(
            "<div style='color:#94a3b8;font-size:.85rem;font-weight:600;margin:10px 0 6px;'>"
            "👤 בחר שומרים</div>",
            unsafe_allow_html=True
        )
        ver = st.session_state.chk_ver
        selected_guards = []

        with st.container(height=210, border=False):
            cols_chk = st.columns(2)
            for i, (_, g) in enumerate(guards_df.iterrows()):
                gs = gstats_now.get(g['name'], {'past': 0, 'future': 0})
                label = f"{g['name']}  ✅{gs['past']} · 🕐{gs['future']}"
                with cols_chk[i % 2]:
                    if st.checkbox(label, key=f"chk_{g['id']}_{ver}"):
                        selected_guards.append(g['name'])

        # ── כפתור הוסף לרשימה ─────────────────────
        if st.button("➕ הוסף לרשימה הממתינה", type="primary", use_container_width=True):
            if not selected_guards:
                st.warning("⚠️ בחר לפחות שומר אחד.")
            else:
                start = datetime.combine(chosen_date, chosen_time)
                end   = start + timedelta(minutes=int(duration))
                st.session_state.temp_shifts.append(
                    {'start': start, 'end': end, 'names': ', '.join(selected_guards)}
                )
                # ── קידום שעה אוטומטי ──
                st.session_state['add_date'] = end.date()
                st.session_state['add_time'] = end.time()
                st.session_state.chk_ver += 1  # reset checkboxes
                st.rerun()

        # ── רשימת staging ──────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        n_temp = len(st.session_state.temp_shifts)
        st.markdown(
            f"<div style='color:#64748b;font-size:.82rem;margin-bottom:8px;'>"
            f"📋 ממתינות לאישור"
            f"{'&nbsp;<b style=\"color:#60a5fa\">(' + str(n_temp) + ')</b>' if n_temp else ''}"
            f"</div>",
            unsafe_allow_html=True
        )

        temp = st.session_state.temp_shifts
        if not temp:
            st.markdown(
                '<div class="staging-empty">אין משמרות בהמתנה.<br>'
                '<small>השתמש בטופס למעלה להוסיף.</small></div>',
                unsafe_allow_html=True
            )
        else:
            del_idx = None
            for i, sh in enumerate(temp):
                c_s, c_d = st.columns([7, 1])
                with c_s:
                    s = sh['start'].strftime('%d/%m %H:%M')
                    e = sh['end'].strftime('%H:%M')
                    st.markdown(
                        f'<div class="staging-row">'
                        f'<span class="staging-time">🕐 {s} – {e}</span>'
                        f'<span class="staging-names">{sh["names"]}</span></div>',
                        unsafe_allow_html=True
                    )
                with c_d:
                    if st.button("🗑️", key=f"rm_{i}"):
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


# ════════════════════════════════════════════════
# TAB 3 – שומרים  (הוספה + רשימה עם סטטיסטיקה + עריכה ללא שבירה)
# ════════════════════════════════════════════════
with tab3:
    now3 = datetime.now()

    # ── הוספת שומרים (שמות בפסיק, שורה אחת) ─────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    add_col, btn_col = st.columns([5, 1])
    with add_col:
        bulk_input = st.text_input(
            "_", label_visibility="collapsed",
            placeholder="הוסף שומרים – שמות מופרדים בפסיק: ישראל, משה, דוד",
            key="bulk_add"
        )
    with btn_col:
        do_add = st.button("➕ הוסף", key="bulk_save", use_container_width=True)
    if do_add and bulk_input.strip():
        names = [x.strip() for x in bulk_input.split(',') if x.strip()]
        cur = conn.cursor(); added = 0
        for n in names:
            try:
                cur.execute("INSERT INTO guards (name) VALUES (?)", (n,)); added += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        if added:
            st.success(f"✅ נוספו {added} שומרים.")
            st.rerun()
        else:
            st.warning("כל השמות כבר קיימים.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── רשימת שומרים ──────────────────────────────
    g_list  = get_guards()
    gstats3 = get_guard_stats(now3)

    if g_list.empty:
        st.info("אין שומרים. הוסף שמות למעלה.")
    else:
        st.markdown(
            f"<span style='color:#475569;font-size:.82rem;'>סה\"כ {len(g_list)} שומרים</span>",
            unsafe_allow_html=True
        )

        # כותרת עמודות
        h1, h2, h3, h4, h5 = st.columns([5, 1, 1, 1, 1])
        with h1: st.markdown("<span style='color:#475569;font-size:.78rem;'>שם</span>", unsafe_allow_html=True)
        with h2: st.markdown("<span style='color:#475569;font-size:.78rem;text-align:center;display:block;'>שובץ</span>", unsafe_allow_html=True)
        with h3: st.markdown("<span style='color:#475569;font-size:.78rem;text-align:center;display:block;'>עתידי</span>", unsafe_allow_html=True)

        st.markdown('<div class="scroll-box" style="max-height:60vh;">', unsafe_allow_html=True)

        del_gid  = None
        save_map = {}

        for _, row in g_list.iterrows():
            gid  = row['id']
            gs   = gstats3.get(row['name'], {'past': 0, 'future': 0})

            # 5 עמודות בשורה אחת, ללא שבירה
            c1, c2, c3, c4, c5 = st.columns([5, 1, 1, 1, 1])
            with c1:
                new_name = st.text_input(
                    "שם", value=row['name'], key=f"gn_{gid}",
                    label_visibility="collapsed"
                )
            with c2:
                st.markdown(
                    f"<div style='padding-top:9px;text-align:center;'>"
                    f"<span class='g-pill g-past'>{gs['past']}</span></div>",
                    unsafe_allow_html=True
                )
            with c3:
                st.markdown(
                    f"<div style='padding-top:9px;text-align:center;'>"
                    f"<span class='g-pill g-future'>{gs['future']}</span></div>",
                    unsafe_allow_html=True
                )
            with c4:
                if st.button("💾", key=f"sv_{gid}", help="שמור שם"):
                    save_map[gid] = new_name.strip()
            with c5:
                if st.button("🗑️", key=f"dl_{gid}", help="מחק שומר"):
                    del_gid = gid

        st.markdown('</div>', unsafe_allow_html=True)

        # ביצוע פעולות אחרי הלולאה
        if del_gid:
            conn.cursor().execute("DELETE FROM guards WHERE id=?", (del_gid,))
            conn.commit(); st.rerun()
        if save_map:
            for gid, nm in save_map.items():
                if nm:
                    try:
                        conn.cursor().execute("UPDATE guards SET name=? WHERE id=?", (nm, gid))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        st.error(f"השם '{nm}' כבר קיים.")
            st.rerun()


# ════════════════════════════════════════════════
# TAB 4 – סטטיסטיקה
# ════════════════════════════════════════════════
with tab4:
    all_shifts = get_shifts()
    all_guards = get_guards()
    now4 = datetime.now()

    if all_guards.empty:
        st.info("אין נתונים.")
    else:
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
                        if r['end_dt'] <= now4:
                            guard_stats[n]['past'] += 1
                        else:
                            guard_stats[n]['future'] += 1

        sorted_guards = sorted(guard_stats.items(), key=lambda x: x[1]['total'], reverse=True)
        max_total = sorted_guards[0][1]['total'] if sorted_guards else 1

        total_shifts_db = len(all_shifts) if not all_shifts.empty else 0
        active      = sum(1 for _, v in guard_stats.items() if v['total'] > 0)
        past_total  = sum(v['past']   for _, v in guard_stats.items())
        future_total= sum(v['future'] for _, v in guard_stats.items())

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
                    continue
                bar_pct = int((v['total'] / max_total) * 100) if max_total > 0 else 0
                rc = f"rank-{rank}" if rank <= 3 else ""
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
