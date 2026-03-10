import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

st.set_page_config(page_title="Smart Guard Manager", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Assistant', sans-serif !important;
    direction: rtl; text-align: right;
}
.stApp { background: linear-gradient(135deg,#0f1923 0%,#1a2840 100%); min-height:100vh; }

/* ── כותרת ─── */
.app-header {
    background: linear-gradient(90deg,#1e3a5f,#2563eb,#1e3a5f);
    border-radius:16px; padding:18px 24px; margin-bottom:18px;
    text-align:center; box-shadow:0 8px 32px rgba(37,99,235,.3);
    border:1px solid rgba(255,255,255,.08);
}
.app-header h1 { color:#fff; font-size:1.7rem; font-weight:800; margin:0; }
.app-header p  { color:rgba(255,255,255,.65); font-size:.88rem; margin:3px 0 0; }

/* ── טאבים ─── */
.stTabs [data-baseweb="tab-list"] {
    background:rgba(255,255,255,.05); border-radius:12px;
    padding:4px; gap:4px; border:1px solid rgba(255,255,255,.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius:9px !important; font-family:'Assistant',sans-serif !important;
    font-weight:600 !important; font-size:.93rem !important;
    color:rgba(255,255,255,.55) !important; padding:8px 14px !important;
    border:none !important; background:transparent !important; transition:all .2s;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color:#fff !important; box-shadow:0 4px 12px rgba(37,99,235,.4) !important;
}

/* ── כרטיסים ─── */
.card {
    background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09);
    border-radius:14px; padding:14px 16px; margin-bottom:14px;
}
.card-title {
    font-size:.97rem; font-weight:700; color:#93c5fd;
    margin-bottom:10px; padding-bottom:8px;
    border-bottom:1px solid rgba(255,255,255,.07);
}

/* ── כותרת יום ─── */
.day-header {
    background:linear-gradient(90deg,rgba(37,99,235,.22),rgba(37,99,235,.04));
    border-right:4px solid #3b82f6; border-radius:8px;
    padding:8px 14px; margin:16px 0 5px;
    font-size:.92rem; font-weight:700; color:#93c5fd;
}

/* ── שורת משמרת (flex HTML + עמודת מחיקה) ─── */
.shift-row-inner {
    display:flex; align-items:center; gap:8px;
    padding:5px 2px; min-height:34px;
}
.s-time {
    flex-shrink:0; white-space:nowrap; font-weight:700;
    font-variant-numeric:tabular-nums; font-size:.86rem;
    padding:3px 9px; border-radius:6px;
}
.s-future { color:#60a5fa; background:rgba(37,99,235,.18); }
.s-past   { color:#94a3b8; background:rgba(100,116,139,.18); }
.s-names  {
    flex:1; color:#e2e8f0; font-size:.86rem;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}

/* ── פילטר pills (radio) ─── */
.stRadio > div {
    flex-direction:row !important; gap:6px !important; flex-wrap:nowrap !important;
}
.stRadio label {
    background:rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.1) !important;
    border-radius:20px !important; padding:4px 14px !important;
    color:#94a3b8 !important; font-size:.85rem !important;
    font-weight:600 !important; cursor:pointer; white-space:nowrap;
    transition:all .2s;
}
.stRadio label:has(input:checked) {
    background:rgba(37,99,235,.35) !important;
    border-color:#3b82f6 !important; color:#93c5fd !important;
}
.stRadio [data-testid="stMarkdownContainer"] { display:none; }

/* ── גלילה ─── */
.scroll-box {
    max-height:52vh; overflow-y:auto;
    scrollbar-width:thin; scrollbar-color:rgba(96,165,250,.35) transparent;
}
.scroll-box::-webkit-scrollbar { width:4px; }
.scroll-box::-webkit-scrollbar-thumb { background:rgba(96,165,250,.35); border-radius:4px; }

/* ── staging ─── */
.staging-row {
    display:flex; align-items:center; gap:10px;
    padding:8px 12px; border-radius:8px; margin-bottom:5px;
    background:rgba(37,99,235,.08); border:1px solid rgba(37,99,235,.2);
}
.staging-time { font-weight:700; color:#60a5fa; white-space:nowrap; font-size:.88rem; min-width:112px; }
.staging-names { flex:1; color:#cbd5e1; font-size:.88rem; }
.staging-empty {
    text-align:center; color:#475569; font-size:.88rem;
    padding:24px; border:2px dashed rgba(255,255,255,.08); border-radius:10px;
}

/* ── צ'קבוקסים ─── */
.stCheckbox { margin-bottom:3px !important; }
.stCheckbox > label {
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.09) !important;
    border-radius:8px !important; padding:6px 10px !important;
    width:100% !important; cursor:pointer; transition:all .15s;
    color:#cbd5e1 !important; font-size:.87rem !important;
    white-space:nowrap !important; overflow:hidden; text-overflow:ellipsis;
}
.stCheckbox > label:hover { background:rgba(37,99,235,.1) !important; border-color:rgba(59,130,246,.3) !important; }
.stCheckbox > label:has(input:checked) {
    background:rgba(37,99,235,.2) !important;
    border-color:rgba(59,130,246,.5) !important; color:#93c5fd !important;
}

/* ═══════════════════════════════════════════════
   CRITICAL: prevent columns from wrapping/stacking
   (fixes guard rows + shift delete rows on mobile)
═══════════════════════════════════════════════ */
[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 4px !important;
}
[data-testid="column"] {
    min-width: 0 !important;
    overflow: hidden;
}

/* ── שורת שומר ─── */
.g-pills {
    display:flex; gap:4px; justify-content:center; flex-wrap:nowrap;
    padding:8px 0;
}
.g-pill {
    display:inline-block; padding:2px 7px; border-radius:10px;
    font-size:.74rem; font-weight:700; white-space:nowrap;
}
.g-past   { background:rgba(16,185,129,.18); color:#6ee7b7; }
.g-future { background:rgba(251,191,36,.15); color:#fcd34d; }

/* ── כפתורים ─── */
.stButton > button {
    border-radius:9px !important; font-family:'Assistant',sans-serif !important;
    font-weight:600 !important; white-space:nowrap !important; transition:all .2s !important;
}
.stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color:#fff !important; box-shadow:0 4px 12px rgba(37,99,235,.35) !important;
}
.stButton > button[kind="primary"]:hover { transform:translateY(-1px) !important; }
.stButton > button:not([kind="primary"]) {
    background:rgba(255,255,255,.07) !important;
    color:#cbd5e1 !important; border:1px solid rgba(255,255,255,.11) !important;
}
/* כפתורי icon קטנים בשורות */
[data-testid="column"] .stButton > button {
    padding:0.28rem 0.45rem !important;
    font-size:.85rem !important;
    width:100% !important;
}
.confirm-btn > button {
    background:linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; box-shadow:0 4px 14px rgba(22,163,74,.3) !important;
}

/* ── שדות קלט ─── */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput > div > div > input {
    background:rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.11) !important;
    border-radius:9px !important; color:#e2e8f0 !important;
    font-family:'Assistant',sans-serif !important; direction:rtl !important;
}
.stTextInput > div > div > input:focus, .stTextArea textarea:focus {
    border-color:#3b82f6 !important; box-shadow:0 0 0 2px rgba(59,130,246,.22) !important;
}
label { color:#94a3b8 !important; font-size:.86rem !important; font-weight:600 !important; }

.stSelectbox > div > div,
.stDateInput > div > div > input,
.stTimeInput > div > div > input {
    background:rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.11) !important;
    border-radius:9px !important; color:#e2e8f0 !important;
}

/* ── סטטיסטיקה ─── */
.stat-row {
    display:flex; align-items:center; gap:12px;
    padding:9px 12px; border-bottom:1px solid rgba(255,255,255,.06); direction:rtl;
}
.stat-row:last-child { border-bottom:none; }
.stat-rank {
    width:26px; height:26px; line-height:26px; text-align:center;
    border-radius:50%; font-size:.76rem; font-weight:800; flex-shrink:0;
    background:rgba(37,99,235,.2); color:#93c5fd;
}
.rank-1 { background:rgba(250,204,21,.22); color:#fde047; }
.rank-2 { background:rgba(203,213,225,.22); color:#cbd5e1; }
.rank-3 { background:rgba(251,146,60,.22); color:#fb923c; }
.stat-name { flex:1; font-weight:700; color:#e2e8f0; font-size:.92rem; }
.stat-numbers { display:flex; gap:7px; align-items:center; flex-shrink:0; }
.stat-pill {
    padding:2px 9px; border-radius:12px;
    font-size:.76rem; font-weight:700; white-space:nowrap;
}
.pill-total  { background:rgba(37,99,235,.25); color:#93c5fd; }
.pill-past   { background:rgba(16,185,129,.2);  color:#6ee7b7; }
.pill-future { background:rgba(251,191,36,.18); color:#fcd34d; }
.stat-bar-wrap { width:85px; flex-shrink:0; }
.stat-bar { height:7px; border-radius:4px; background:linear-gradient(90deg,#2563eb,#60a5fa); min-width:3px; }

/* ── metric ─── */
[data-testid="stMetric"] {
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.09) !important;
    border-radius:12px !important; padding:12px !important; text-align:center;
}
[data-testid="stMetricLabel"] { color:#94a3b8 !important; font-size:.82rem !important; }
[data-testid="stMetricValue"] { color:#f1f5f9 !important; font-size:1.5rem !important; font-weight:800 !important; }

/* ── WhatsApp ─── */
.stLinkButton a {
    background:linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; border-radius:9px !important;
    font-family:'Assistant',sans-serif !important; font-weight:700 !important;
    padding:.5rem 1.1rem !important; text-decoration:none !important;
    box-shadow:0 4px 12px rgba(22,163,74,.3) !important;
    display:inline-block; white-space:nowrap !important;
}

hr { border-color:rgba(255,255,255,.07) !important; margin:12px 0 !important; }

@media (max-width:640px) {
    .app-header h1 { font-size:1.3rem; }
    .app-header { padding:13px; }
    .card { padding:10px 12px; }
    .stat-bar-wrap { width:50px; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# כותרת
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🛡️ Smart Guard Manager</h1>
    <p>מערכת ניהול שמירות חכמה • ניהול, שיבוץ וסטטיסטיקות</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def init_db():
    db_dir = '/app/data'
    path = os.path.join(db_dir, 'guard_system.db') if os.path.exists(db_dir) else 'guard_system.db'
    cn = sqlite3.connect(path, check_same_thread=False)
    cur = cn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS guards (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
    cur.execute('''CREATE TABLE IF NOT EXISTS shifts
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT, end_time TEXT, names TEXT)''')
    cn.commit()
    return cn

conn = init_db()

HE_DAY = {'Sunday':'ראשון','Monday':'שני','Tuesday':'שלישי',
           'Wednesday':'רביעי','Thursday':'חמישי','Friday':'שישי','Saturday':'שבת'}

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def get_guards():
    return pd.read_sql_query("SELECT * FROM guards ORDER BY name ASC", conn)

def get_shifts():
    return pd.read_sql_query("SELECT * FROM shifts ORDER BY start_time ASC", conn)

def get_guard_stats(now: datetime) -> dict:
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

def last_staging_or_db_end():
    candidates = []
    shifts = get_shifts()
    if not shifts.empty:
        candidates.append(datetime.strptime(shifts.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S'))
    for sh in st.session_state.get('temp_shifts', []):
        candidates.append(sh['end'])
    return max(candidates) if candidates else None

# ─────────────────────────────────────────────────────────────
# Session state init  (MUST be before any widget)
# ─────────────────────────────────────────────────────────────
if 'temp_shifts' not in st.session_state:
    st.session_state.temp_shifts = []
if 'chk_ver' not in st.session_state:
    st.session_state.chk_ver = 0

# Auto-advance: אם flag דלוק, קדם את שדות התאריך/שעה לפני שהwidget יתרנדר
_now_r = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
if 'w_date' not in st.session_state:
    st.session_state['w_date'] = _now_r.date()
if 'w_time' not in st.session_state:
    st.session_state['w_time'] = _now_r.time()

# אם יש flag קידום — נגדיר את ערכי הwidget לפני הרינדור שלו
if st.session_state.get('_do_advance', False):
    st.session_state['w_date'] = st.session_state.get('_adv_date', st.session_state['w_date'])
    st.session_state['w_time'] = st.session_state.get('_adv_time', st.session_state['w_time'])
    st.session_state['_do_advance'] = False

# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 משמרות", "+", "👥 שומרים", "📊 סטטיסטיקה"])


# ═════════════════════════════════════════════════════════════
# TAB 1 – משמרות  (פילטר הכל/עתידי/עבר + מחיקה בשורה)
# ═════════════════════════════════════════════════════════════
with tab1:
    shifts_df = get_shifts()
    now = datetime.now()

    # ── פילטר pills ────────────────────────────────
    fc1, fc2 = st.columns([3, 4])
    with fc1:
        filt = st.radio("סינון", ["הכל","עתידי","עבר"],
                        horizontal=True, key="shift_filter",
                        label_visibility="collapsed")

    if shifts_df.empty:
        with fc2:
            st.markdown("")
        st.info("📭 אין משמרות. לחץ על '+' להתחיל.")
    else:
        shifts_df['start_dt'] = pd.to_datetime(shifts_df['start_time'])
        shifts_df['end_dt']   = pd.to_datetime(shifts_df['end_time'])
        shifts_df['date']     = shifts_df['start_time'].str[:10]

        if filt == "עתידי":
            view = shifts_df[shifts_df['start_dt'] > now].copy()
        elif filt == "עבר":
            view = shifts_df[shifts_df['end_dt'] <= now].copy()
        else:
            view = shifts_df.copy()

        with fc2:
            st.markdown(
                f"<span style='color:#475569;font-size:.82rem;line-height:2.6;'>"
                f"מוצגות {len(view)} מתוך {len(shifts_df)}</span>",
                unsafe_allow_html=True
            )

        if view.empty:
            st.info("אין משמרות בקטגוריה זו.")
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
                    tcls = "s-past" if is_past else "s-future"
                    icon = "⬜" if is_past else "🟦"

                    # עמודה רחבה (info) + עמודה צרה (מחיקה) — לא נשבר
                    ci, cd = st.columns([9, 1])
                    with ci:
                        # כל השורה ב-HTML flex אחד — הזמן והשמות בשורה אחת
                        st.markdown(
                            f"<div class='shift-row-inner'>"
                            f"<span class='s-time {tcls}'>{icon} {s}–{e}</span>"
                            f"<span class='s-names'>{r['names']}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with cd:
                        if st.button("🗑️", key=f"ds_{r['id']}", help="מחק"):
                            delete_id = r['id']

            st.markdown('</div>', unsafe_allow_html=True)

            if delete_id is not None:
                conn.cursor().execute("DELETE FROM shifts WHERE id=?", (delete_id,))
                conn.commit(); st.rerun()

            # WhatsApp
            st.markdown('<br>', unsafe_allow_html=True)
            msg = "🛡️ *סידור שמירה*\n" + f"📆 {now.strftime('%d/%m/%Y %H:%M')}\n"
            for day in view['date'].unique():
                d = datetime.strptime(day, '%Y-%m-%d')
                msg += f"\n🗓️ *יום {HE_DAY.get(d.strftime('%A'),'')} {d.strftime('%d/%m')}:*\n"
                for _, r in view[view['date'] == day].iterrows():
                    msg += f"• {r['start_time'][11:16]}–{r['end_time'][11:16]} ▸ {r['names']}\n"
            msg += "\n_Smart Guard Manager_ 🛡️"
            st.link_button("📲 שלח בוואטסאפ",
                           f"https://wa.me/?text={urllib.parse.quote(msg)}",
                           use_container_width=False)


# ═════════════════════════════════════════════════════════════
# TAB 2 – "+"  הוספת משמרת
# תיקון: auto-advance דרך flag (לא מגדירים session_state של widget אחרי רינדור)
# ═════════════════════════════════════════════════════════════
with tab2:
    guards_df = get_guards()

    if guards_df.empty:
        st.warning("⚠️ עבור לטאב 'שומרים' כדי להוסיף שומרים תחילה.")
    else:
        gstats_now = get_guard_stats(datetime.now())
        next_hint  = last_staging_or_db_end()

        if next_hint:
            st.markdown(
                f"<div style='background:rgba(37,99,235,.1);border:1px solid rgba(59,130,246,.25);"
                f"border-radius:9px;padding:7px 13px;margin-bottom:10px;font-size:.85rem;color:#93c5fd;'>"
                f"⏭️ רצף אוטומטי: <b>{next_hint.strftime('%d/%m/%Y %H:%M')}</b></div>",
                unsafe_allow_html=True
            )

        # ── תאריך + שעה + משך ──────────────────────
        d1, d2, d3 = st.columns(3)
        with d1:
            # w_date key נשלט ע"י ה-flag שמוגדר לפני כל הטאבים
            chosen_date = st.date_input("📅 תאריך", key="w_date")
        with d2:
            chosen_time = st.time_input("🕐 שעה", key="w_time", step=1800)
        with d3:
            duration = st.selectbox("⏱️ משך (דק׳)",
                                    [30,45,60,90,120,180,240], index=2, key="add_dur")

        # ── צ'קבוקסים ──────────────────────────────
        st.markdown("<div style='color:#94a3b8;font-size:.84rem;font-weight:600;"
                    "margin:10px 0 6px;'>👤 בחר שומרים</div>", unsafe_allow_html=True)

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

        # ── הוסף לרשימה ────────────────────────────
        if st.button("➕ הוסף לרשימה הממתינה", type="primary", use_container_width=True):
            if not selected_guards:
                st.warning("⚠️ בחר לפחות שומר אחד.")
            else:
                start = datetime.combine(chosen_date, chosen_time)
                end   = start + timedelta(minutes=int(duration))
                st.session_state.temp_shifts.append(
                    {'start': start, 'end': end, 'names': ', '.join(selected_guards)}
                )
                # קידום אוטומטי: שמור ערכים חדשים, הדלק flag
                # (הwidget יעודכן בריצה הבאה לפני שהוא מתרנדר)
                st.session_state['_adv_date']   = end.date()
                st.session_state['_adv_time']   = end.time()
                st.session_state['_do_advance'] = True
                st.session_state.chk_ver += 1
                st.rerun()

        # ── staging list ────────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        n_temp = len(st.session_state.temp_shifts)
        st.markdown(
            f"<div style='color:#64748b;font-size:.82rem;margin-bottom:8px;'>"
            f"📋 ממתינות לאישור"
            f"{'&nbsp;<b style=\"color:#60a5fa\">(' + str(n_temp) + ')</b>' if n_temp else ''}"
            f"</div>", unsafe_allow_html=True
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
                cs, cd2 = st.columns([7, 1])
                with cs:
                    s = sh['start'].strftime('%d/%m %H:%M')
                    e = sh['end'].strftime('%H:%M')
                    st.markdown(
                        f'<div class="staging-row">'
                        f'<span class="staging-time">🕐 {s} – {e}</span>'
                        f'<span class="staging-names">{sh["names"]}</span></div>',
                        unsafe_allow_html=True
                    )
                with cd2:
                    if st.button("🗑️", key=f"rm_{i}"):
                        del_idx = i
            if del_idx is not None:
                st.session_state.temp_shifts.pop(del_idx); st.rerun()

            st.markdown('<br>', unsafe_allow_html=True)
            cok, ccancel = st.columns(2)
            with cok:
                st.markdown('<div class="confirm-btn">', unsafe_allow_html=True)
                if st.button("✅ אשר הכל ושמור", type="primary", use_container_width=True):
                    cur = conn.cursor()
                    for sh in st.session_state.temp_shifts:
                        cur.execute(
                            "INSERT INTO shifts (start_time,end_time,names) VALUES (?,?,?)",
                            (sh['start'].strftime('%Y-%m-%d %H:%M:%S'),
                             sh['end'].strftime('%Y-%m-%d %H:%M:%S'), sh['names'])
                        )
                    conn.commit()
                    n = len(st.session_state.temp_shifts)
                    st.session_state.temp_shifts = []
                    st.success(f"✅ {n} משמרות נשמרו!"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with ccancel:
                if st.button("✖️ בטל הכל", use_container_width=True):
                    st.session_state.temp_shifts = []; st.rerun()


# ═════════════════════════════════════════════════════════════
# TAB 3 – שומרים  (שורה אחת ברשימה)
# ═════════════════════════════════════════════════════════════
with tab3:
    now3 = datetime.now()

    # ── הוספה ──────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    ac, bc = st.columns([5, 1])
    with ac:
        bulk_input = st.text_input("_", label_visibility="collapsed",
                                   placeholder="הוסף שומרים – שמות מופרדים בפסיק: ישראל, משה, דוד",
                                   key="bulk_add")
    with bc:
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
        if added: st.success(f"✅ נוספו {added} שומרים."); st.rerun()
        else: st.warning("כל השמות כבר קיימים.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── רשימה ──────────────────────────────────────
    g_list  = get_guards()
    gstats3 = get_guard_stats(now3)

    if g_list.empty:
        st.info("אין שומרים. הוסף שמות למעלה.")
    else:
        st.markdown(
            f"<span style='color:#475569;font-size:.82rem;'>סה\"כ {len(g_list)} שומרים</span>",
            unsafe_allow_html=True
        )

        # כותרת עמודות — אותם יחסים כמו שורות הנתונים
        hh1, hh2, hh3, hh4 = st.columns([5, 2, 1, 1])
        with hh1: st.markdown("<span style='color:#475569;font-size:.76rem;'>שם</span>", unsafe_allow_html=True)
        with hh2: st.markdown("<span style='color:#475569;font-size:.76rem;text-align:center;display:block;'>שובץ&nbsp;/&nbsp;עתידי</span>", unsafe_allow_html=True)

        st.markdown('<div class="scroll-box" style="max-height:60vh;">', unsafe_allow_html=True)

        del_gid  = None
        save_map = {}

        for _, row in g_list.iterrows():
            gid = row['id']
            gs  = gstats3.get(row['name'], {'past': 0, 'future': 0})

            # 4 עמודות: שם (רחב) | שתי כמויות (בHTML) | 💾 | 🗑️
            c1, c2, c3, c4 = st.columns([5, 2, 1, 1])
            with c1:
                new_name = st.text_input("שם", value=row['name'], key=f"gn_{gid}",
                                         label_visibility="collapsed")
            with c2:
                # שתי הכמויות בתא HTML אחד — לא שוברות שורה
                st.markdown(
                    f"<div class='g-pills'>"
                    f"<span class='g-pill g-past'>✅{gs['past']}</span>"
                    f"<span class='g-pill g-future'>🕐{gs['future']}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with c3:
                if st.button("💾", key=f"sv_{gid}", help="שמור"):
                    save_map[gid] = new_name.strip()
            with c4:
                if st.button("🗑️", key=f"dl_{gid}", help="מחק"):
                    del_gid = gid

        st.markdown('</div>', unsafe_allow_html=True)

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


# ═════════════════════════════════════════════════════════════
# TAB 4 – סטטיסטיקה
# ═════════════════════════════════════════════════════════════
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
            all_shifts['end_dt'] = pd.to_datetime(all_shifts['end_time'])
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

        total_db   = len(all_shifts) if not all_shifts.empty else 0
        active     = sum(1 for _, v in guard_stats.items() if v['total'] > 0)
        past_tot   = sum(v['past']   for _, v in guard_stats.items())
        future_tot = sum(v['future'] for _, v in guard_stats.items())

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("סה\"כ משמרות", total_db)
        mc2.metric("בוצעו",  past_tot)
        mc3.metric("עתידיות", future_tot)
        mc4.metric("שומרים פעילים", active)

        st.markdown('<div class="card" style="margin-top:14px;"><div class="card-title">📊 ניתוח לפי שומר</div>',
                    unsafe_allow_html=True)
        if not any(v['total'] > 0 for _, v in guard_stats.items()):
            st.info("אין נתוני משמרות עדיין.")
        else:
            rows_html = ""
            for rank, (name, v) in enumerate(sorted_guards, 1):
                if v['total'] == 0 and rank > 3:
                    continue
                bar_pct = int(v['total'] / max_total * 100) if max_total else 0
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
                </div>"""
            st.markdown(rows_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if total_db > 0 and any(v['total'] > 0 for _, v in guard_stats.items()):
            st.markdown('<div class="card"><div class="card-title">📈 גרף משמרות</div>', unsafe_allow_html=True)
            chart_data = pd.DataFrame(
                [(n, v['past'], v['future']) for n, v in sorted_guards if v['total'] > 0],
                columns=['שומר', 'בוצעו', 'עתידיות']
            ).set_index('שומר')
            st.bar_chart(chart_data, color=["#3b82f6", "#f59e0b"], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
