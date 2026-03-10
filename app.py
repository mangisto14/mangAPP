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

/* header */
.app-header {
    background: linear-gradient(90deg,#1e3a5f,#2563eb,#1e3a5f);
    border-radius:14px; padding:16px 24px; margin-bottom:18px;
    text-align:center; box-shadow:0 6px 28px rgba(37,99,235,.3);
    border:1px solid rgba(255,255,255,.08);
}
.app-header h1 { color:#fff; font-size:1.6rem; font-weight:800; margin:0; }
.app-header p  { color:rgba(255,255,255,.6); font-size:.85rem; margin:3px 0 0; }

/* tabs */
.stTabs [data-baseweb="tab-list"] {
    background:rgba(255,255,255,.05); border-radius:12px;
    padding:4px; gap:4px; border:1px solid rgba(255,255,255,.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius:9px !important; font-family:'Assistant',sans-serif !important;
    font-weight:600 !important; font-size:.9rem !important;
    color:rgba(255,255,255,.55) !important; padding:8px 14px !important;
    border:none !important; background:transparent !important; transition:all .2s;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color:#fff !important; box-shadow:0 4px 12px rgba(37,99,235,.4) !important;
}

/* card */
.card {
    background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09);
    border-radius:12px; padding:14px 16px; margin-bottom:14px;
}
.sec-label {
    font-size:.82rem; font-weight:700; color:#64748b;
    text-transform:uppercase; letter-spacing:.5px;
    margin-bottom:8px;
}

/* day header */
.day-header {
    background:linear-gradient(90deg,rgba(37,99,235,.22),rgba(37,99,235,.04));
    border-right:4px solid #3b82f6; border-radius:8px;
    padding:8px 14px; margin:18px 0 6px;
    font-size:.9rem; font-weight:700; color:#93c5fd;
}

/* shift row */
.shift-row {
    display:flex; align-items:center; gap:10px;
    padding:8px 10px; border-radius:8px; margin-bottom:4px;
    background:rgba(255,255,255,.025);
    border:1px solid rgba(255,255,255,.06); transition:background .15s;
}
.shift-row:hover { background:rgba(255,255,255,.05); }
.s-time {
    font-size:.88rem; font-weight:700; white-space:nowrap;
    font-variant-numeric:tabular-nums;
    padding:3px 9px; border-radius:6px; flex-shrink:0;
}
.s-past   { color:#94a3b8; background:rgba(100,116,139,.18); }
.s-future { color:#60a5fa; background:rgba(37,99,235,.18); }
.s-names  { flex:1; color:#e2e8f0; font-size:.88rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* staging */
.staging-row {
    display:flex; align-items:center; gap:10px;
    padding:8px 12px; border-radius:8px; margin-bottom:5px;
    background:rgba(37,99,235,.08); border:1px solid rgba(37,99,235,.22);
}
.st-time  { font-weight:700; color:#60a5fa; white-space:nowrap; font-size:.88rem; min-width:115px; }
.st-names { flex:1; color:#cbd5e1; font-size:.88rem; }
.staging-empty {
    text-align:center; color:#475569; font-size:.88rem;
    padding:24px; border:2px dashed rgba(255,255,255,.07); border-radius:10px;
}

/* checkboxes – guard picker */
.stCheckbox > label {
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.09) !important;
    border-radius:8px !important; padding:7px 10px !important;
    width:100%; cursor:pointer; transition:all .15s;
    color:#cbd5e1 !important; font-size:.9rem !important;
}
.stCheckbox > label:has(input:checked) {
    background:rgba(37,99,235,.18) !important;
    border-color:rgba(59,130,246,.45) !important;
    color:#93c5fd !important;
}
.stCheckbox > label:hover {
    background:rgba(255,255,255,.07) !important;
}

/* scroll */
.scroll-box {
    max-height:52vh; overflow-y:auto;
    scrollbar-width:thin; scrollbar-color:rgba(96,165,250,.3) transparent;
}
.scroll-box::-webkit-scrollbar { width:4px; }
.scroll-box::-webkit-scrollbar-thumb { background:rgba(96,165,250,.3); border-radius:4px; }

/* guard list */
.guard-pill {
    display:inline-block; padding:2px 9px; border-radius:10px;
    font-size:.75rem; font-weight:700; white-space:nowrap; margin-right:4px;
}
.gp-fut  { background:rgba(251,191,36,.18); color:#fcd34d; }
.gp-past { background:rgba(16,185,129,.18); color:#6ee7b7; }

/* stats */
.stat-row {
    display:flex; align-items:center; gap:12px;
    padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.06);
}
.stat-row:last-child { border-bottom:none; }
.stat-rank {
    width:26px; height:26px; line-height:26px; text-align:center;
    border-radius:50%; font-size:.75rem; font-weight:800; flex-shrink:0;
    background:rgba(37,99,235,.2); color:#93c5fd;
}
.rank-1 { background:rgba(250,204,21,.22); color:#fde047; }
.rank-2 { background:rgba(203,213,225,.22); color:#cbd5e1; }
.rank-3 { background:rgba(251,146,60,.22); color:#fb923c; }
.stat-name { flex:1; font-weight:700; color:#e2e8f0; font-size:.92rem; }
.stat-nums { display:flex; gap:6px; flex-shrink:0; flex-wrap:nowrap; }
.stat-bar-w { width:80px; flex-shrink:0; }
.stat-bar   { height:7px; border-radius:4px; background:linear-gradient(90deg,#2563eb,#60a5fa); min-width:3px; }

/* buttons */
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
.btn-green > button {
    background:linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; box-shadow:0 4px 12px rgba(22,163,74,.3) !important;
}

/* inputs */
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
.stSelectbox > div > div, .stDateInput > div > div > input, .stTimeInput > div > div > input {
    background:rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.11) !important;
    border-radius:9px !important; color:#e2e8f0 !important;
}
label { color:#94a3b8 !important; font-size:.85rem !important; font-weight:600 !important; }

/* multiselect tags */
.stMultiSelect [data-baseweb="tag"] {
    background:rgba(37,99,235,.3) !important; border-radius:5px !important; color:#93c5fd !important;
}
.stMultiSelect > div > div {
    background:rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.11) !important; border-radius:9px !important;
}

/* metric */
[data-testid="stMetric"] {
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.08) !important;
    border-radius:12px !important; padding:12px !important; text-align:center;
}
[data-testid="stMetricLabel"] { color:#94a3b8 !important; font-size:.82rem !important; }
[data-testid="stMetricValue"] { color:#f1f5f9 !important; font-size:1.5rem !important; font-weight:800 !important; }

/* link button */
.stLinkButton a {
    background:linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; border-radius:9px !important;
    font-family:'Assistant',sans-serif !important; font-weight:700 !important;
    padding:.5rem 1.1rem !important; text-decoration:none !important;
    box-shadow:0 4px 12px rgba(22,163,74,.3) !important;
    display:inline-block; white-space:nowrap !important;
}

/* search input icon */
.search-wrap { position:relative; }

hr { border-color:rgba(255,255,255,.07) !important; margin:12px 0 !important; }

@media (max-width:640px) {
    .app-header h1 { font-size:1.25rem; }
    .app-header { padding:12px; }
    .card { padding:10px; }
    .s-time { font-size:.82rem; }
    .stat-bar-w { width:50px; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# כותרת
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🛡️ Smart Guard Manager</h1>
    <p>ניהול שמירות • שיבוץ • סטטיסטיקות</p>
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
    """Returns {name: {past, future}} for all guards."""
    guards = get_guards()
    shifts = get_shifts()
    result = {r['name']: {'past': 0, 'future': 0} for _, r in guards.iterrows()}
    if not shifts.empty:
        for _, r in shifts.iterrows():
            end_dt = datetime.strptime(r['end_time'], '%Y-%m-%d %H:%M:%S')
            key = 'past' if end_dt <= now else 'future'
            for n in r['names'].split(', '):
                n = n.strip()
                if n in result:
                    result[n][key] += 1
    return result

def last_staging_or_db_end() -> datetime | None:
    candidates = []
    shifts = get_shifts()
    if not shifts.empty:
        candidates.append(datetime.strptime(shifts.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S'))
    for sh in st.session_state.get('temp_shifts', []):
        candidates.append(sh['end'])
    return max(candidates) if candidates else None

# ─────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────
if 'temp_shifts' not in st.session_state:
    st.session_state.temp_shifts = []
if 'chk_ver' not in st.session_state:
    st.session_state.chk_ver = 0   # bump to reset checkboxes

# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 משמרות", "➕ הוספת משמרת", "👥 שומרים", "📊 סטטיסטיקה"])


# ═════════════════════════════════════════════════════════════
# TAB 1 – משמרות  (חיפוש + מחיקה בשורה)
# ═════════════════════════════════════════════════════════════
with tab1:
    shifts_df = get_shifts()
    now = datetime.now()

    # ── חיפוש טקסט ──────────────────────────────────────────
    search = st.text_input(
        "חיפוש", placeholder="🔍  חפש לפי שם שומר או תאריך (dd/mm/yyyy)...",
        key="shift_search", label_visibility="collapsed"
    )

    if shifts_df.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("📭 אין משמרות. לחץ על 'הוספת משמרת' להתחיל.")
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

        delete_id = None

        st.markdown('<div class="scroll-box">', unsafe_allow_html=True)
        for day in view['date'].unique():
            d = datetime.strptime(day, '%Y-%m-%d')
            nice = d.strftime('%d/%m/%Y')
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

                # שורה: זמן | שמות | 🗑️
                c_time, c_names, c_del = st.columns([2, 6, 1])
                with c_time:
                    st.markdown(
                        f'<div style="padding-top:4px;">'
                        f'<span class="s-time {tcls}">{icon} {s}–{e}</span></div>',
                        unsafe_allow_html=True
                    )
                with c_names:
                    st.markdown(
                        f'<div style="padding-top:8px;color:#e2e8f0;font-size:.88rem;'
                        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
                        f'{r["names"]}</div>',
                        unsafe_allow_html=True
                    )
                with c_del:
                    if st.button("🗑️", key=f"ds_{r['id']}", help="מחק משמרת זו"):
                        delete_id = r['id']

        st.markdown('</div>', unsafe_allow_html=True)

        if delete_id is not None:
            conn.cursor().execute("DELETE FROM shifts WHERE id=?", (delete_id,))
            conn.commit()
            st.rerun()

        # ── WhatsApp ─────────────────────────────────────────
        if not view.empty:
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
# TAB 2 – הוספת משמרת  (staging, צ'קבוקסים, date/time חופשי)
# ═════════════════════════════════════════════════════════════
with tab2:
    guards_df = get_guards()

    if guards_df.empty:
        st.warning("⚠️ אין שומרים. הוסף שומרים בטאב 'שומרים' תחילה.")
    else:
        now_stats = get_guard_stats(datetime.now())

        # ── רמז זמן אוטומטי ─────────────────────────────────
        next_hint = last_staging_or_db_end()
        if next_hint:
            st.markdown(
                f"<div style='background:rgba(37,99,235,.1);border:1px solid rgba(59,130,246,.25);"
                f"border-radius:9px;padding:8px 14px;margin-bottom:12px;font-size:.88rem;color:#93c5fd;'>"
                f"⏭️ לרצף אוטומטי — המשמרת הבאה ב: <b>{next_hint.strftime('%d/%m/%Y %H:%M')}</b></div>",
                unsafe_allow_html=True
            )
            init_date = next_hint.date()
            init_time = next_hint.time()
        else:
            nr = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            init_date, init_time = nr.date(), nr.time()

        # ── תאריך + שעה (תמיד עריכה חופשית) ────────────────
        d1, d2, d3 = st.columns(3)
        with d1:
            chosen_date = st.date_input("📅 תאריך", value=init_date, key="add_date")
        with d2:
            chosen_time = st.time_input("🕐 שעה", value=init_time, key="add_time", step=1800)
        with d3:
            duration = st.selectbox("⏱️ משך (דק׳)", [30,45,60,90,120,180,240], index=2, key="add_dur")

        # ── בחירת שומרים – צ'קבוקסים ────────────────────────
        st.markdown(
            "<div class='sec-label' style='margin-top:10px;'>👤 בחר שומרים</div>",
            unsafe_allow_html=True
        )

        ver = st.session_state.chk_ver
        selected_guards = []

        with st.container(height=220, border=False):
            cols_chk = st.columns(2)
            for i, (_, g) in enumerate(guards_df.iterrows()):
                s = now_stats.get(g['name'], {'past':0,'future':0})
                label = f"{g['name']}  ✅{s['past']} · 🕐{s['future']}"
                with cols_chk[i % 2]:
                    if st.checkbox(label, key=f"chk_{g['id']}_{ver}"):
                        selected_guards.append(g['name'])

        # ── הוסף לרשימה ──────────────────────────────────────
        if st.button("➕ הוסף לרשימה הממתינה", type="primary", use_container_width=True):
            if not selected_guards:
                st.warning("⚠️ בחר לפחות שומר אחד.")
            else:
                start = datetime.combine(chosen_date, chosen_time)
                end   = start + timedelta(minutes=int(duration))
                st.session_state.temp_shifts.append(
                    {'start': start, 'end': end, 'names': ', '.join(selected_guards)}
                )
                st.session_state.chk_ver += 1   # reset checkboxes
                st.rerun()

        # ── רשימת staging ────────────────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        n_temp = len(st.session_state.temp_shifts)
        st.markdown(
            f"<div class='sec-label'>📋 ממתינות לאישור"
            f"{'&nbsp;<span style=\"color:#60a5fa\">(' + str(n_temp) + ')</span>' if n_temp else ''}"
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
                        f'<span class="st-time">🕐 {s} – {e}</span>'
                        f'<span class="st-names">{sh["names"]}</span></div>',
                        unsafe_allow_html=True
                    )
                with c_d:
                    if st.button("🗑️", key=f"rm_{i}"):
                        del_idx = i
            if del_idx is not None:
                st.session_state.temp_shifts.pop(del_idx)
                st.rerun()

            st.markdown('<br>', unsafe_allow_html=True)
            ok_col, cancel_col = st.columns(2)
            with ok_col:
                st.markdown('<div class="btn-green">', unsafe_allow_html=True)
                if st.button("✅ אשר הכל ושמור", type="primary", use_container_width=True):
                    cur = conn.cursor()
                    for sh in st.session_state.temp_shifts:
                        cur.execute(
                            "INSERT INTO shifts (start_time,end_time,names) VALUES (?,?,?)",
                            (sh['start'].strftime('%Y-%m-%d %H:%M:%S'),
                             sh['end'].strftime('%Y-%m-%d %H:%M:%S'),
                             sh['names'])
                        )
                    conn.commit()
                    n = len(st.session_state.temp_shifts)
                    st.session_state.temp_shifts = []
                    st.success(f"✅ {n} משמרות נשמרו!")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with cancel_col:
                if st.button("✖️ בטל הכל", use_container_width=True):
                    st.session_state.temp_shifts = []
                    st.rerun()


# ═════════════════════════════════════════════════════════════
# TAB 3 – שומרים  (הוספה + רשימה עם סטטיסטיקה + עריכה)
# ═════════════════════════════════════════════════════════════
with tab3:
    now3 = datetime.now()

    # ── הוספה ────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="sec-label">➕ הוספת שומרים (שמות מופרדים בפסיק)</div>',
                unsafe_allow_html=True)
    bulk_col, btn_col = st.columns([5, 1])
    with bulk_col:
        bulk = st.text_input("שמות:", placeholder="ישראל ישראלי, משה כהן, דוד לוי",
                              key="bulk_add", label_visibility="collapsed")
    with btn_col:
        do_add = st.button("➕ הוסף", key="bulk_save", use_container_width=True)
    if do_add and bulk.strip():
        names = [x.strip() for x in bulk.split(',') if x.strip()]
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

    # ── רשימת שומרים ─────────────────────────────────────────
    g_list = get_guards()
    gstats = get_guard_stats(now3)

    if g_list.empty:
        st.info("אין שומרים. הוסף שמות למעלה.")
    else:
        st.markdown(
            f"<span style='color:#475569;font-size:.82rem;'>סה\"כ {len(g_list)} שומרים</span>",
            unsafe_allow_html=True
        )
        st.markdown('<div class="scroll-box" style="max-height:60vh;">', unsafe_allow_html=True)

        del_gid = None
        save_map = {}

        for _, row in g_list.iterrows():
            gid  = row['id']
            gs   = gstats.get(row['name'], {'past': 0, 'future': 0})
            past = gs['past']; fut = gs['future']

            gc1, gc2, gc3, gc4, gc5 = st.columns([4, 1, 1, 1, 1])
            with gc1:
                new_name = st.text_input(
                    "שם", value=row['name'], key=f"gn_{gid}",
                    label_visibility="collapsed"
                )
            with gc2:
                st.markdown(
                    f"<div style='padding-top:8px;text-align:center;'>"
                    f"<span class='guard-pill gp-past'>✅ {past}</span></div>",
                    unsafe_allow_html=True
                )
            with gc3:
                st.markdown(
                    f"<div style='padding-top:8px;text-align:center;'>"
                    f"<span class='guard-pill gp-fut'>🕐 {fut}</span></div>",
                    unsafe_allow_html=True
                )
            with gc4:
                if st.button("💾", key=f"sv_{gid}", help="שמור שם"):
                    save_map[gid] = new_name.strip()
            with gc5:
                if st.button("🗑️", key=f"dl_{gid}", help="מחק שומר"):
                    del_gid = gid

        st.markdown('</div>', unsafe_allow_html=True)

        if del_gid:
            conn.cursor().execute("DELETE FROM guards WHERE id=?", (del_gid,))
            conn.commit(); st.rerun()
        for gid, nm in save_map.items():
            if nm:
                try:
                    conn.cursor().execute("UPDATE guards SET name=? WHERE id=?", (nm, gid))
                    conn.commit()
                except sqlite3.IntegrityError:
                    st.error(f"השם '{nm}' כבר קיים.")
            if save_map:
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
        gstats4 = get_guard_stats(now4)
        sorted_g = sorted(
            gstats4.items(),
            key=lambda x: x[1]['past'] + x[1]['future'],
            reverse=True
        )
        total_sh = len(all_shifts)
        past_tot = sum(v['past']   for _, v in gstats4.items())
        fut_tot  = sum(v['future'] for _, v in gstats4.items())
        active   = sum(1 for _, v in gstats4.items() if v['past']+v['future'] > 0)

        # ── Metric cards ──────────────────────────────────────
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("סה\"כ משמרות", total_sh)
        mc2.metric("בוצעו", past_tot)
        mc3.metric("עתידיות", fut_tot)
        mc4.metric("שומרים פעילים", active)

        # ── טבלת שומרים ──────────────────────────────────────
        st.markdown('<div class="card" style="margin-top:14px;">', unsafe_allow_html=True)
        if not any(v['past']+v['future'] > 0 for _, v in gstats4.items()):
            st.info("אין נתוני משמרות עדיין.")
        else:
            max_tot = max((v['past']+v['future'] for _, v in sorted_g), default=1)
            rows_html = ""
            for rank, (name, v) in enumerate(sorted_g, 1):
                tot = v['past'] + v['future']
                if tot == 0 and rank > 3:
                    continue
                bar_pct = int(tot / max_tot * 100) if max_tot else 0
                rc = f"rank-{rank}" if rank <= 3 else ""
                rows_html += f"""
                <div class="stat-row">
                  <div class="stat-rank {rc}">{rank}</div>
                  <div class="stat-name">{name}</div>
                  <div class="stat-nums">
                    <span class="guard-pill pill-total" style="background:rgba(37,99,235,.22);color:#93c5fd;">
                      {tot}</span>
                    <span class="guard-pill gp-past">✅ {v['past']}</span>
                    <span class="guard-pill gp-fut">🕐 {v['future']}</span>
                  </div>
                  <div class="stat-bar-w">
                    <div class="stat-bar" style="width:{bar_pct}%;"></div>
                  </div>
                </div>
                """
            st.markdown(rows_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── גרף ─────────────────────────────────────────────
        if total_sh > 0:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            chart_data = pd.DataFrame(
                [(n, v['past'], v['future']) for n, v in sorted_g if v['past']+v['future'] > 0],
                columns=['שומר', 'בוצעו', 'עתידיות']
            ).set_index('שומר')
            st.bar_chart(chart_data, color=["#3b82f6", "#f59e0b"], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
