import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

st.set_page_config(page_title="Smart Guard Manager", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────────────────────────
# CSS  –  ניקי, ממוקד, ללא overrides גלובליים מסוכנים
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Assistant', sans-serif !important;
    direction: rtl; text-align: right;
}
.stApp { background: linear-gradient(135deg,#0f1923 0%,#1a2840 100%); min-height:100vh; }

/* ── Header ─── */
.app-header {
    background: linear-gradient(90deg,#1e3a5f,#2563eb,#1e3a5f);
    border-radius:16px; padding:18px 24px; margin-bottom:20px;
    text-align:center; box-shadow:0 8px 32px rgba(37,99,235,.3);
    border:1px solid rgba(255,255,255,.08);
}
.app-header h1 { color:#fff; font-size:1.7rem; font-weight:800; margin:0; }
.app-header p  { color:rgba(255,255,255,.65); font-size:.88rem; margin:4px 0 0; }

/* ── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    background:rgba(255,255,255,.05); border-radius:12px;
    padding:4px; gap:4px; border:1px solid rgba(255,255,255,.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius:9px !important; font-family:'Assistant',sans-serif !important;
    font-weight:600 !important; font-size:.92rem !important;
    color:rgba(255,255,255,.5) !important; padding:8px 14px !important;
    border:none !important; background:transparent !important;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color:#fff !important; box-shadow:0 4px 12px rgba(37,99,235,.4) !important;
}

/* ── Day header ─── */
.day-header {
    background:linear-gradient(90deg,rgba(37,99,235,.22),rgba(37,99,235,.03));
    border-right:4px solid #3b82f6; border-radius:8px;
    padding:8px 14px; margin:14px 0 4px;
    font-size:.92rem; font-weight:700; color:#93c5fd;
}

/* ── Shift row ─── */
.srow {
    display:flex; align-items:center; gap:8px;
    padding:7px 4px;
    border-bottom:1px solid rgba(255,255,255,.05);
}
.srow:last-child { border-bottom:none; }
/* CRITICAL: direction:ltr on time prevents RTL reversal of "07:00–08:00" */
.s-time {
    direction:ltr; display:inline-block;
    font-weight:700; font-size:.85rem; white-space:nowrap;
    padding:3px 9px; border-radius:6px; flex-shrink:0;
    font-variant-numeric:tabular-nums;
}
.s-fut  { color:#60a5fa; background:rgba(37,99,235,.18); }
.s-past { color:#94a3b8; background:rgba(100,116,139,.18); }
.s-names {
    flex:1; color:#e2e8f0; font-size:.86rem;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}

/* ── Staging ─── */
.st-row {
    display:flex; align-items:center; gap:10px;
    padding:8px 12px; border-radius:8px; margin-bottom:5px;
    background:rgba(37,99,235,.09); border:1px solid rgba(37,99,235,.22);
}
.st-time {
    direction:ltr; display:inline-block;
    font-weight:700; color:#60a5fa; white-space:nowrap;
    font-size:.88rem; min-width:115px;
}
.st-names { flex:1; color:#cbd5e1; font-size:.88rem; }
.st-empty {
    text-align:center; color:#475569; font-size:.88rem;
    padding:24px; border:2px dashed rgba(255,255,255,.07); border-radius:10px;
}

/* ── Guard-list pills ─── */
.gp-row { display:flex; gap:5px; align-items:center; justify-content:center; padding:7px 0; }
.gp {
    display:inline-block; padding:2px 8px; border-radius:10px;
    font-size:.75rem; font-weight:700; white-space:nowrap;
}
.gp-ok  { background:rgba(16,185,129,.18); color:#6ee7b7; }
.gp-fut { background:rgba(251,191,36,.14);  color:#fcd34d; }

/* ── Checkboxes ─── */
.stCheckbox { margin-bottom:4px !important; }
.stCheckbox > label {
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.09) !important;
    border-radius:8px !important; padding:7px 10px !important;
    width:100% !important; cursor:pointer; transition:all .15s;
    color:#cbd5e1 !important; font-size:.87rem !important;
}
.stCheckbox > label:hover { background:rgba(37,99,235,.1) !important; }
.stCheckbox > label:has(input:checked) {
    background:rgba(37,99,235,.2) !important;
    border-color:rgba(59,130,246,.5) !important; color:#93c5fd !important;
}

/* ── Buttons ─── */
.stButton > button {
    border-radius:9px !important; font-family:'Assistant',sans-serif !important;
    font-weight:600 !important; white-space:nowrap !important; transition:all .18s !important;
}
.stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#2563eb,#3b82f6) !important;
    color:#fff !important; box-shadow:0 3px 10px rgba(37,99,235,.35) !important;
}
.stButton > button[kind="primary"]:hover { transform:translateY(-1px) !important; }
.stButton > button:not([kind="primary"]) {
    background:rgba(255,255,255,.07) !important;
    color:#cbd5e1 !important; border:1px solid rgba(255,255,255,.1) !important;
}
/* confirm green */
.btn-green .stButton > button {
    background:linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; box-shadow:0 3px 10px rgba(22,163,74,.3) !important;
}
/* compact icon buttons inside guard rows */
.compact-btn .stButton > button {
    padding:0.25rem 0.4rem !important;
    font-size:.85rem !important;
    min-height:34px !important;
}

/* ── Inputs ─── */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input {
    background:rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.11) !important;
    border-radius:9px !important; color:#e2e8f0 !important;
    font-family:'Assistant',sans-serif !important; direction:rtl !important;
}
.stTextInput > div > div > input:focus { border-color:#3b82f6 !important; }
label { color:#94a3b8 !important; font-size:.86rem !important; font-weight:600 !important; }
.stSelectbox > div > div,
.stDateInput input, .stTimeInput input {
    background:rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.11) !important;
    border-radius:9px !important; color:#e2e8f0 !important;
}

/* ── Stats ─── */
.stat-row {
    display:flex; align-items:center; gap:12px;
    padding:9px 12px; border-bottom:1px solid rgba(255,255,255,.06);
}
.stat-row:last-child { border-bottom:none; }
.stat-rank {
    width:26px; height:26px; line-height:26px; text-align:center;
    border-radius:50%; font-size:.76rem; font-weight:800; flex-shrink:0;
    background:rgba(37,99,235,.2); color:#93c5fd;
}
.rk1 { background:rgba(250,204,21,.22); color:#fde047; }
.rk2 { background:rgba(203,213,225,.22); color:#cbd5e1; }
.rk3 { background:rgba(251,146,60,.22); color:#fb923c; }
.stat-name { flex:1; font-weight:700; color:#e2e8f0; font-size:.92rem; }
.stat-pills { display:flex; gap:6px; flex-shrink:0; }
.sp {
    padding:2px 9px; border-radius:12px;
    font-size:.76rem; font-weight:700; white-space:nowrap;
}
.sp-t { background:rgba(37,99,235,.25); color:#93c5fd; }
.sp-p { background:rgba(16,185,129,.2);  color:#6ee7b7; }
.sp-f { background:rgba(251,191,36,.18); color:#fcd34d; }
.stat-bar-w { width:80px; flex-shrink:0; }
.stat-bar { height:7px; border-radius:4px; background:linear-gradient(90deg,#2563eb,#60a5fa); min-width:3px; }

/* ── Metric ─── */
[data-testid="stMetric"] {
    background:rgba(255,255,255,.04) !important;
    border:1px solid rgba(255,255,255,.09) !important;
    border-radius:12px !important; padding:12px !important; text-align:center;
}
[data-testid="stMetricLabel"] { color:#94a3b8 !important; font-size:.82rem !important; }
[data-testid="stMetricValue"] { color:#f1f5f9 !important; font-size:1.45rem !important; font-weight:800 !important; }

/* ── WhatsApp link ─── */
.stLinkButton a {
    background:linear-gradient(135deg,#16a34a,#22c55e) !important;
    color:#fff !important; border-radius:9px !important;
    font-weight:700 !important; padding:.5rem 1.1rem !important;
    text-decoration:none !important; display:inline-block;
    box-shadow:0 3px 10px rgba(22,163,74,.3) !important; white-space:nowrap !important;
}

/* ── Hint box ─── */
.hint-box {
    background:rgba(37,99,235,.1); border:1px solid rgba(59,130,246,.25);
    border-radius:9px; padding:8px 13px; margin-bottom:12px;
    font-size:.85rem; color:#93c5fd;
}

/* ── Divider ─── */
hr { border-color:rgba(255,255,255,.07) !important; margin:12px 0 !important; }

/* ── Mobile ─── */
@media (max-width:640px) {
    .app-header h1 { font-size:1.3rem; }
    .app-header { padding:13px 14px; }
    .stat-bar-w { width:48px; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Header
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
    sh = get_shifts()
    if not sh.empty:
        candidates.append(datetime.strptime(sh.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S'))
    for s in st.session_state.get('temp_shifts', []):
        candidates.append(s['end'])
    return max(candidates) if candidates else None

# ─────────────────────────────────────────────────────────────
# Session state  (all init before any widget)
# ─────────────────────────────────────────────────────────────
if 'temp_shifts'  not in st.session_state: st.session_state.temp_shifts  = []
if 'chk_ver'      not in st.session_state: st.session_state.chk_ver      = 0
if 'filt'         not in st.session_state: st.session_state.filt          = "הכל"
if '_do_advance'  not in st.session_state: st.session_state._do_advance   = False

# Default date/time for add-shift tab
_nr = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
if 'w_date' not in st.session_state: st.session_state['w_date'] = _nr.date()
if 'w_time' not in st.session_state: st.session_state['w_time'] = _nr.time()

# Auto-advance: set widget keys BEFORE widgets render
if st.session_state._do_advance:
    st.session_state['w_date']    = st.session_state.get('_adv_date', st.session_state['w_date'])
    st.session_state['w_time']    = st.session_state.get('_adv_time', st.session_state['w_time'])
    st.session_state._do_advance  = False

# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 משמרות", "+", "👥 שומרים", "📊 סטטיסטיקה"])


# ═════════════════════════════════════════════════════════════
# TAB 1 – משמרות
# ═════════════════════════════════════════════════════════════
with tab1:
    shifts_df = get_shifts()
    now       = datetime.now()

    # ── Pill filter (actual buttons, no CSS magic needed) ─────
    fb1, fb2, fb3, fb_space = st.columns([1, 1, 1, 3])
    with fb1:
        if st.button("הכל",   key="fb_all",
                     type="primary" if st.session_state.filt=="הכל"   else "secondary",
                     use_container_width=True):
            st.session_state.filt = "הכל";   st.rerun()
    with fb2:
        if st.button("עתידי", key="fb_fut",
                     type="primary" if st.session_state.filt=="עתידי" else "secondary",
                     use_container_width=True):
            st.session_state.filt = "עתידי"; st.rerun()
    with fb3:
        if st.button("עבר",   key="fb_past",
                     type="primary" if st.session_state.filt=="עבר"   else "secondary",
                     use_container_width=True):
            st.session_state.filt = "עבר";   st.rerun()

    if shifts_df.empty:
        st.info("📭 אין משמרות. לחץ על '+' להוסיף.")
    else:
        shifts_df['start_dt'] = pd.to_datetime(shifts_df['start_time'])
        shifts_df['end_dt']   = pd.to_datetime(shifts_df['end_time'])
        shifts_df['date']     = shifts_df['start_time'].str[:10]

        filt = st.session_state.filt
        if filt == "עתידי":
            view = shifts_df[shifts_df['start_dt'] > now].copy()
        elif filt == "עבר":
            view = shifts_df[shifts_df['end_dt'] <= now].copy()
        else:
            view = shifts_df.copy()

        st.markdown(
            f"<div style='color:#475569;font-size:.8rem;margin:6px 0 10px;'>"
            f"מוצגות {len(view)} מתוך {len(shifts_df)} משמרות</div>",
            unsafe_allow_html=True
        )

        if view.empty:
            st.info("אין משמרות בקטגוריה זו.")
        else:
            delete_id = None

            # st.container(height=X) — scrollable box that properly contains widgets
            with st.container(height=460, border=False):
                for day in view['date'].unique():
                    d      = datetime.strptime(day, '%Y-%m-%d')
                    nice   = d.strftime('%d/%m/%Y')
                    day_he = HE_DAY.get(d.strftime('%A'), '')
                    st.markdown(
                        f'<div class="day-header">📅 יום {day_he} &nbsp;·&nbsp; {nice}</div>',
                        unsafe_allow_html=True
                    )
                    for _, r in view[view['date'] == day].iterrows():
                        s      = r['start_time'][11:16]
                        e      = r['end_time'][11:16]
                        is_past = r['end_dt'] <= now
                        tcls   = "s-past" if is_past else "s-fut"
                        icon   = "⬜" if is_past else "🟦"

                        # 2 cols: info (HTML flex, LTR time) | delete btn
                        ci, cd = st.columns([9, 1])
                        with ci:
                            # direction:ltr on .s-time prevents RTL reversal of "07:00–08:00"
                            st.markdown(
                                f"<div class='srow'>"
                                f"<span class='s-time {tcls}'>{icon} {s}–{e}</span>"
                                f"<span class='s-names'>{r['names']}</span>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with cd:
                            st.markdown("<div class='compact-btn'>", unsafe_allow_html=True)
                            if st.button("🗑️", key=f"ds_{r['id']}", help="מחק"):
                                delete_id = r['id']
                            st.markdown("</div>", unsafe_allow_html=True)

            if delete_id is not None:
                conn.cursor().execute("DELETE FROM shifts WHERE id=?", (delete_id,))
                conn.commit(); st.rerun()

            # WhatsApp
            st.markdown("<br>", unsafe_allow_html=True)
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
# TAB 2 – "+" הוספת משמרת
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
                f"<div class='hint-box'>⏭️ רצף אוטומטי: "
                f"<b>{next_hint.strftime('%d/%m/%Y %H:%M')}</b></div>",
                unsafe_allow_html=True
            )

        # ── Date / Time / Duration ─────────────────────
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            chosen_date = st.date_input("📅 תאריך", key="w_date")
        with dc2:
            chosen_time = st.time_input("🕐 שעה", key="w_time", step=1800)
        with dc3:
            duration = st.selectbox("⏱️ משך (דק׳)",
                                    [30, 45, 60, 90, 120, 180, 240],
                                    index=2, key="add_dur")

        # ── Guard checkboxes ───────────────────────────
        st.markdown(
            "<div style='color:#94a3b8;font-size:.84rem;font-weight:600;margin:10px 0 6px;'>"
            "👤 בחר שומרים</div>", unsafe_allow_html=True
        )
        ver = st.session_state.chk_ver
        selected_guards = []

        with st.container(height=210, border=False):
            cols_chk = st.columns(2)
            for i, (_, g) in enumerate(guards_df.iterrows()):
                gs    = gstats_now.get(g['name'], {'past': 0, 'future': 0})
                label = f"{g['name']}  ✅{gs['past']} · 🕐{gs['future']}"
                with cols_chk[i % 2]:
                    if st.checkbox(label, key=f"chk_{g['id']}_{ver}"):
                        selected_guards.append(g['name'])

        # ── Add to staging ─────────────────────────────
        if st.button("➕ הוסף לרשימה הממתינה", type="primary", use_container_width=True):
            if not selected_guards:
                st.warning("⚠️ בחר לפחות שומר אחד.")
            else:
                start = datetime.combine(chosen_date, chosen_time)
                end   = start + timedelta(minutes=int(duration))
                st.session_state.temp_shifts.append(
                    {'start': start, 'end': end, 'names': ', '.join(selected_guards)}
                )
                st.session_state['_adv_date']  = end.date()
                st.session_state['_adv_time']  = end.time()
                st.session_state._do_advance   = True
                st.session_state.chk_ver      += 1
                st.rerun()

        # ── Staging list ───────────────────────────────
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
                '<div class="st-empty">אין משמרות בהמתנה.<br>'
                '<small>השתמש בטופס למעלה להוסיף.</small></div>',
                unsafe_allow_html=True
            )
        else:
            del_idx = None
            for i, sh in enumerate(temp):
                sr, sd = st.columns([7, 1])
                with sr:
                    s = sh['start'].strftime('%d/%m %H:%M')
                    e = sh['end'].strftime('%H:%M')
                    st.markdown(
                        f"<div class='st-row'>"
                        f"<span class='st-time'>{s} – {e}</span>"
                        f"<span class='st-names'>{sh['names']}</span></div>",
                        unsafe_allow_html=True
                    )
                with sd:
                    st.markdown("<div class='compact-btn'>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"rm_{i}"):
                        del_idx = i
                    st.markdown("</div>", unsafe_allow_html=True)
            if del_idx is not None:
                st.session_state.temp_shifts.pop(del_idx); st.rerun()

            st.markdown('<br>', unsafe_allow_html=True)
            cok, ccancel = st.columns(2)
            with cok:
                st.markdown('<div class="btn-green">', unsafe_allow_html=True)
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
# TAB 3 – שומרים
# ═════════════════════════════════════════════════════════════
with tab3:
    now3 = datetime.now()

    # ── Add guards ─────────────────────────────────
    ac, bc = st.columns([5, 1])
    with ac:
        bulk_input = st.text_input(
            "_", label_visibility="collapsed",
            placeholder="הוסף שמות מופרדים בפסיק: ישראל ישראלי, משה כהן",
            key="bulk_add"
        )
    with bc:
        do_add = st.button("➕ הוסף", key="bulk_save", use_container_width=True)
    if do_add and bulk_input.strip():
        names = [x.strip() for x in bulk_input.split(',') if x.strip()]
        cur   = conn.cursor(); added = 0
        for n in names:
            try:
                cur.execute("INSERT INTO guards (name) VALUES (?)", (n,)); added += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        if added: st.success(f"✅ נוספו {added} שומרים."); st.rerun()
        else: st.warning("כל השמות כבר קיימים.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Guard list ─────────────────────────────────
    g_list  = get_guards()
    gstats3 = get_guard_stats(now3)

    if g_list.empty:
        st.info("אין שומרים. הוסף שמות למעלה.")
    else:
        st.markdown(
            f"<div style='color:#475569;font-size:.8rem;margin-bottom:8px;'>"
            f"סה\"כ {len(g_list)} שומרים</div>", unsafe_allow_html=True
        )

        # Column headers – same ratios as data rows
        h1, h2, h3, h4 = st.columns([5, 2, 1, 1])
        with h1: st.markdown("<span style='color:#475569;font-size:.76rem;'>שם</span>",
                             unsafe_allow_html=True)
        with h2: st.markdown("<span style='color:#475569;font-size:.76rem;display:block;text-align:center;'>שובץ / עתידי</span>",
                             unsafe_allow_html=True)

        del_gid  = None
        save_map = {}

        # st.container(height=X) — proper scrollable container
        with st.container(height=460, border=False):
            for _, row in g_list.iterrows():
                gid = row['id']
                gs  = gstats3.get(row['name'], {'past': 0, 'future': 0})

                c1, c2, c3, c4 = st.columns([5, 2, 1, 1])
                with c1:
                    new_name = st.text_input("n", value=row['name'], key=f"gn_{gid}",
                                             label_visibility="collapsed")
                with c2:
                    # Both pills in one HTML cell — stays on same row
                    st.markdown(
                        f"<div class='gp-row'>"
                        f"<span class='gp gp-ok'>✅{gs['past']}</span>"
                        f"<span class='gp gp-fut'>🕐{gs['future']}</span>"
                        f"</div>", unsafe_allow_html=True
                    )
                with c3:
                    st.markdown("<div class='compact-btn'>", unsafe_allow_html=True)
                    if st.button("💾", key=f"sv_{gid}", help="שמור", use_container_width=True):
                        save_map[gid] = new_name.strip()
                    st.markdown("</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown("<div class='compact-btn'>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"dl_{gid}", help="מחק", use_container_width=True):
                        del_gid = gid
                    st.markdown("</div>", unsafe_allow_html=True)

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
    now4       = datetime.now()

    if all_guards.empty:
        st.info("אין נתונים.")
    else:
        gst4 = {}
        for _, g in all_guards.iterrows():
            gst4[g['name']] = {'past': 0, 'future': 0, 'total': 0}

        if not all_shifts.empty:
            all_shifts['end_dt'] = pd.to_datetime(all_shifts['end_time'])
            for _, r in all_shifts.iterrows():
                for n in r['names'].split(', '):
                    n = n.strip()
                    if n in gst4:
                        gst4[n]['total'] += 1
                        if r['end_dt'] <= now4:
                            gst4[n]['past'] += 1
                        else:
                            gst4[n]['future'] += 1

        sorted_g  = sorted(gst4.items(), key=lambda x: x[1]['total'], reverse=True)
        max_total = sorted_g[0][1]['total'] if sorted_g else 1
        total_db  = len(all_shifts) if not all_shifts.empty else 0
        active    = sum(1 for _, v in gst4.items() if v['total'] > 0)
        past_tot  = sum(v['past']   for _, v in gst4.items())
        fut_tot   = sum(v['future'] for _, v in gst4.items())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("סה\"כ", total_db)
        m2.metric("בוצעו", past_tot)
        m3.metric("עתידיות", fut_tot)
        m4.metric("שומרים פעילים", active)

        if not any(v['total'] > 0 for _, v in gst4.items()):
            st.info("אין נתוני משמרות עדיין.")
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            rows_html = ""
            for rank, (name, v) in enumerate(sorted_g, 1):
                if v['total'] == 0 and rank > 3:
                    continue
                bar_pct = int(v['total'] / max_total * 100) if max_total else 0
                rk = f"rk{rank}" if rank <= 3 else ""
                rows_html += f"""
                <div class="stat-row">
                  <div class="stat-rank {rk}">{rank}</div>
                  <div class="stat-name">{name}</div>
                  <div class="stat-pills">
                    <span class="sp sp-t">{v['total']}</span>
                    <span class="sp sp-p">✅{v['past']}</span>
                    <span class="sp sp-f">🕐{v['future']}</span>
                  </div>
                  <div class="stat-bar-w">
                    <div class="stat-bar" style="width:{bar_pct}%;"></div>
                  </div>
                </div>"""
            st.markdown(rows_html, unsafe_allow_html=True)

            if total_db > 0:
                st.markdown("<br>", unsafe_allow_html=True)
                chart_data = pd.DataFrame(
                    [(n, v['past'], v['future']) for n, v in sorted_g if v['total'] > 0],
                    columns=['שומר', 'בוצעו', 'עתידיות']
                ).set_index('שומר')
                st.bar_chart(chart_data, color=["#3b82f6", "#f59e0b"], use_container_width=True)
