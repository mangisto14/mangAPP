import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import urllib.parse

st.set_page_config(page_title=“ניהול שמירות”, page_icon=“🛡️”, layout=“centered”)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown(”””

<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

*, *::before, *::after { font-family: 'Heebo', sans-serif !important; box-sizing: border-box; }
html, body, [class*="css"] { direction: rtl !important; }
.stApp { background: #0b0f1c !important; color: #f1f5f9; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0.5rem 0.75rem 5rem !important; max-width: 600px !important; }

/* ── HEADER ── */
.app-header {
  background: linear-gradient(135deg, #0f172a 0%, #1a3050 100%);
  border: 1px solid #1e2d45;
  border-radius: 16px;
  padding: 16px 20px 14px;
  margin-bottom: 14px;
  display: flex; align-items: center; gap: 12px;
}
.app-header-icon { font-size: 32px; line-height:1; }
.app-header h1 {
  font-size: 22px; font-weight: 900; margin: 0;
  background: linear-gradient(135deg, #60a5fa, #818cf8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.app-header p { font-size: 11px; color: #475569; margin: 2px 0 0; }

/* ── SECTION TITLE ── */
.sec-title {
  font-size: 11px; font-weight: 700; color: #64748b;
  text-transform: uppercase; letter-spacing: 1px;
  margin: 16px 0 8px; padding-right: 8px;
  border-right: 3px solid #3b82f6;
}

/* ── CARDS ── */
.card {
  background: #111827; border: 1px solid #1e2d45;
  border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
}

/* ── SHIFT ROW ── */
.shift-row {
  background: #0f1724; border: 1px solid #1e2d45;
  border-radius: 12px; padding: 12px 14px; margin-bottom: 8px;
  border-right: 3px solid #3b82f6; position: relative;
}
.shift-row.night { border-right-color: #8b5cf6; }
.shift-row.past { border-right-color: #374151; opacity: 0.6; }
.shift-time-big { font-size: 20px; font-weight: 900; color: #f1f5f9; letter-spacing: -0.5px; }
.shift-date-str { font-size: 11px; color: #475569; margin-top: 1px; }
.slot-badge {
  position: absolute; left: 12px; top: 12px;
  background: #1e2d45; border-radius: 8px; padding: 2px 8px;
  font-size: 11px; font-weight: 700; color: #64748b;
}
.gtag {
  display: inline-block; font-size: 12px; padding: 3px 10px;
  background: rgba(59,130,246,.15); border: 1px solid rgba(59,130,246,.3);
  border-radius: 10px; color: #93c5fd; font-weight: 600; margin: 2px 2px 0 0;
}
.gtag.empty {
  background: rgba(239,68,68,.1); border-color: rgba(239,68,68,.3); color: #fca5a5;
}

/* ── SLOT DISPLAY ── */
.slot-box {
  border-radius: 10px; padding: 8px 10px; text-align: center;
  border: 1px solid #1e2d45; background: #1a2236;
}
.slot-box.filled { background: rgba(59,130,246,.1); border-color: rgba(59,130,246,.4); }
.slot-num { font-size: 10px; color: #475569; margin-bottom: 2px; }
.slot-name { font-size: 13px; font-weight: 700; color: #475569; }
.slot-box.filled .slot-name { color: #93c5fd; }

/* ── GUARD CHIP ── */
.stButton button {
  border-radius: 20px !important; font-weight: 600 !important;
  font-size: 13px !important; transition: all .15s !important;
  border: 1px solid #1e2d45 !important;
  background: #1a2236 !important; color: #94a3b8 !important;
  padding: 4px 14px !important;
}
.stButton button:hover {
  background: #3b82f6 !important; color: white !important;
  border-color: #3b82f6 !important; transform: scale(1.04) !important;
}
button[kind="primary"] {
  background: #3b82f6 !important; color: white !important;
  border-color: #3b82f6 !important; border-radius: 10px !important;
}
button[kind="primary"]:hover { background: #2563eb !important; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
  background: #111827; border-radius: 12px; gap: 3px;
  padding: 4px; border: 1px solid #1e2d45;
}
.stTabs [data-baseweb="tab"] {
  background: transparent; color: #64748b; border-radius: 9px;
  font-weight: 600; font-size: 13px; padding: 8px 12px;
}
.stTabs [aria-selected="true"] {
  background: #3b82f6 !important; color: white !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 8px !important; }

/* ── INPUTS ── */
label { color: #64748b !important; font-size: 12px !important; font-weight: 600 !important; }
.stTextInput input, .stTextArea textarea {
  background: #1a2236 !important; border: 1px solid #1e2d45 !important;
  color: #f1f5f9 !important; border-radius: 10px !important; direction: rtl !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: #3b82f6 !important; box-shadow: 0 0 0 1px #3b82f6 !important;
}
.stSelectbox > div > div {
  background: #1a2236 !important; border: 1px solid #1e2d45 !important;
  color: #f1f5f9 !important; border-radius: 10px !important;
}
.stDateInput input, .stTimeInput input {
  background: #1a2236 !important; color: #f1f5f9 !important;
  border: 1px solid #1e2d45 !important; border-radius: 10px !important;
}

/* ── STATS ── */
.stat-box {
  background: #111827; border: 1px solid #1e2d45; border-radius: 12px;
  padding: 14px 10px; text-align: center;
}
.stat-num { font-size: 28px; font-weight: 900; color: #3b82f6; }
.stat-label { font-size: 10px; color: #475569; font-weight: 700; margin-top: 2px; text-transform: uppercase; }

/* ── GUARD AVATAR ── */
.g-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg,#3b82f6,#6366f1);
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px; color: white; flex-shrink: 0;
}

/* ── SHARE BOX ── */
.share-box {
  background: #0f1724; border: 1px solid #1e2d45; border-radius: 12px;
  padding: 14px; margin-bottom: 14px;
}
.share-text {
  background: #1a2236; border: 1px solid #1e2d45; border-radius: 8px;
  padding: 12px; font-size: 13px; color: #94a3b8;
  direction: rtl; white-space: pre-wrap; max-height: 180px;
  overflow-y: auto; margin-bottom: 10px; line-height: 1.7;
}

/* ── BOTTOM STICKY BAR ── */
.bottom-bar {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 100%; max-width: 600px;
  background: #0b0f1c; border-top: 1px solid #1e2d45;
  padding: 10px 16px 12px; z-index: 1000;
  display: flex; gap: 8px;
}

/* ── DATA TABLE ── */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
.stAlert { border-radius: 10px !important; }

/* ── DAY FILTER ── */
.day-filter-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.day-chip {
  padding: 5px 12px; border-radius: 16px; font-size: 12px; font-weight: 600;
  background: #1a2236; border: 1px solid #1e2d45; color: #64748b; cursor: pointer;
}
.day-chip.active { background: #3b82f6; border-color: #3b82f6; color: white; }

/* HR */
hr { border-color: #1e2d45 !important; margin: 14px 0 !important; }

@media (max-width: 480px) {
  .app-header h1 { font-size: 18px; }
  .shift-time-big { font-size: 17px; }
  .block-container { padding: 0.5rem 0.5rem 5rem !important; }
}
</style>

“””, unsafe_allow_html=True)

# ── DB ────────────────────────────────────────────────────────────────────────

DB = “guards.db”

def db():
c = sqlite3.connect(DB, check_same_thread=False)
c.execute(””“CREATE TABLE IF NOT EXISTS guards
(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)”””)
c.execute(””“CREATE TABLE IF NOT EXISTS shifts
(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, start_time TEXT,
end_time TEXT, duration INTEGER, slots INTEGER, guards TEXT)”””)
c.commit()
return c

def get_guards():
c = db(); df = pd.read_sql(“SELECT * FROM guards ORDER BY name”, c); c.close(); return df

def get_all_shifts():
c = db(); df = pd.read_sql(“SELECT * FROM shifts ORDER BY date, start_time”, c); c.close(); return df

def add_shift(d, st_, et, dur, sl, gl):
c = db()
c.execute(“INSERT INTO shifts (date,start_time,end_time,duration,slots,guards) VALUES (?,?,?,?,?,?)”,
(d, st_, et, dur, sl, “,”.join(gl)))
c.commit(); c.close()

def save_shift_edit(sid, d, st_, et, dur, sl, gl):
c = db()
c.execute(“UPDATE shifts SET date=?,start_time=?,end_time=?,duration=?,slots=?,guards=? WHERE id=?”,
(d, st_, et, dur, sl, “,”.join(gl), sid))
c.commit(); c.close()

def del_shift(sid):
c = db(); c.execute(“DELETE FROM shifts WHERE id=?”, (sid,)); c.commit(); c.close()

def add_guards_bulk(text):
names = [n.strip() for n in text.replace(”،”,”,”).split(”,”) if n.strip()]
c = db(); added = 0
for n in names:
try: c.execute(“INSERT INTO guards (name) VALUES (?)”, (n,)); added += 1
except: pass
c.commit(); c.close(); return added

def del_guard(gid):
c = db(); c.execute(“DELETE FROM guards WHERE id=?”, (gid,)); c.commit(); c.close()

def rename_guard(gid, old, new_name):
c = db()
try:
c.execute(“UPDATE guards SET name=? WHERE id=?”, (new_name, gid))
rows = c.execute(“SELECT id, guards FROM shifts”).fetchall()
for sid, sg in rows:
updated = “,”.join([new_name if g.strip()==old else g.strip() for g in sg.split(”,”)])
c.execute(“UPDATE shifts SET guards=? WHERE id=?”, (updated, sid))
c.commit()
except: pass
c.close()

def end_time(start, mins):
dt = datetime.strptime(start, “%H:%M”) + timedelta(minutes=int(mins))
return dt.strftime(”%H:%M”)

def fmt(mins):
mins = int(mins)
return f”{mins} דק’” if mins < 60 else f”{mins//60}{‘½’ if mins%60 else ‘’} שע’”

DAYS_HE  = [“שני”,“שלישי”,“רביעי”,“חמישי”,“שישי”,“שבת”,“ראשון”]
MONTHS_HE = [””,“ינואר”,“פברואר”,“מרץ”,“אפריל”,“מאי”,“יוני”,“יולי”,“אוגוסט”,“ספטמבר”,“אוקטובר”,“נובמבר”,“דצמבר”]

def hdate(ds, short=False):
try:
d = datetime.strptime(ds, “%Y-%m-%d”)
if short:
return f”{DAYS_HE[d.weekday()]} {d.day}/{d.month}”
return f”{DAYS_HE[d.weekday()]} {d.day} {MONTHS_HE[d.month]}”
except: return ds

def is_past(row):
try:
ts = datetime.strptime(f”{row[‘date’]} {row[‘end_time’]}”, “%Y-%m-%d %H:%M”)
return ts < datetime.now()
except: return False

def build_share_text(shifts_view):
lines = [“🛡️ *לוח משמרות שמירה*”, “”]
if shifts_view.empty:
return “אין משמרות”
cur_date = None
for _, r in shifts_view.iterrows():
if r[“date”] != cur_date:
cur_date = r[“date”]
lines.append(f”📅 *{hdate(r[‘date’])}*”)
gl = [g.strip() for g in r[“guards”].split(”,”) if g.strip()]
guard_str = “ | “.join(gl) if gl else “לא שובצו”
lines.append(f”  ⏰ {r[‘start_time’]}–{r[‘end_time’]}  👮 {guard_str}”)
lines += [””, “*נשלח ממערכת ניהול שמירות* 🛡️”]
return “\n”.join(lines)

# ── SESSION STATE ─────────────────────────────────────────────────────────────

defaults = {
“sel_guards”: [], “filter”: “future”, “edit_id”: None,
“rename_id”: None, “confirm_del”: None, “confirm_del_g”: None,
“share_days”: 7,
}
for k, v in defaults.items():
if k not in st.session_state:
st.session_state[k] = v

# ── HEADER ────────────────────────────────────────────────────────────────────

today = date.today()
st.markdown(f”””

<div class="app-header">
  <div class="app-header-icon">🛡️</div>
  <div>
    <h1>ניהול שמירות</h1>
    <p>{hdate(today.strftime('%Y-%m-%d'))} · {today.strftime('%d/%m/%Y')}</p>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([“📅 משמרות”, “👥 שומרים”, “📊 סטטיסטיקה”])

# ══════════════════════════════════════════════════════════════════════════════

# TAB 1 — SHIFTS

# ══════════════════════════════════════════════════════════════════════════════

with tab1:

```
# ── Form ─────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">פרטי משמרת</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1: sh_date = st.date_input("תאריך", value=today, label_visibility="visible")
with c2:
    all_sh = get_all_shifts()
    def_time = datetime.strptime("08:00", "%H:%M").time()
    if not all_sh.empty:
        ts = all_sh[all_sh["date"] == sh_date.strftime("%Y-%m-%d")]
        if not ts.empty:
            try: def_time = datetime.strptime(ts.iloc[-1]["end_time"], "%H:%M").time()
            except: pass
    sh_time = st.time_input("שעת התחלה", value=def_time)

c3, c4 = st.columns(2)
with c3: dur = st.selectbox("משך", [30,60,90,120,180,240], format_func=fmt)
with c4: slots = st.selectbox("שומרים", [1,2,3],
                               format_func=lambda x: f"{x} שומר{'ים' if x>1 else ''}")

# trim
if len(st.session_state.sel_guards) > slots:
    st.session_state.sel_guards = st.session_state.sel_guards[:slots]

# ── Slot display ──────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">שיבוץ שומרים</div>', unsafe_allow_html=True)
scols = st.columns(slots)
for i in range(slots):
    g = st.session_state.sel_guards[i] if i < len(st.session_state.sel_guards) else None
    with scols[i]:
        filled = "filled" if g else ""
        name   = g if g else "פנוי"
        st.markdown(f"""<div class="slot-box {filled}">
          <div class="slot-num">עמדה {i+1}</div>
          <div class="slot-name">{name}</div>
        </div>""", unsafe_allow_html=True)

gdf = get_guards()
if gdf.empty:
    st.info("הוסף שומרים בלשונית 'שומרים'")
else:
    ncols = min(len(gdf), 4)
    gbcols = st.columns(ncols)
    for i, (_, row) in enumerate(gdf.iterrows()):
        name = row["name"]
        sel  = name in st.session_state.sel_guards
        with gbcols[i % ncols]:
            if st.button(f"{'✓ ' if sel else ''}{name}", key=f"gb_{name}"):
                if sel:
                    st.session_state.sel_guards.remove(name)
                elif len(st.session_state.sel_guards) < slots:
                    st.session_state.sel_guards.append(name)
                else:
                    st.toast(f"כבר שובצו {slots} שומרים", icon="⚠️")
                st.rerun()

    if st.session_state.sel_guards:
        if st.button("🗑️ נקה בחירה", key="clr"):
            st.session_state.sel_guards = []; st.rerun()

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
if st.button("💾  שמור משמרת", type="primary", use_container_width=True):
    s = sh_time.strftime("%H:%M")
    e = end_time(s, dur)
    add_shift(sh_date.strftime("%Y-%m-%d"), s, e, dur, slots, st.session_state.sel_guards)
    st.session_state.sel_guards = []
    st.toast("✅ משמרת נשמרה!", icon="✅")
    st.rerun()

# ── Shifts list ───────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="sec-title">רשימת משמרות</div>', unsafe_allow_html=True)

fc = st.columns(3)
for i, (lbl, val) in enumerate([("⏩ עתידיות","future"),("⏮ עבר","past"),("📋 הכל","all")]):
    with fc[i]:
        t = "primary" if st.session_state.filter==val else "secondary"
        if st.button(lbl, type=t, key=f"f_{val}", use_container_width=True):
            st.session_state.filter = val; st.rerun()

all_sh = get_all_shifts()
if not all_sh.empty:
    all_sh["_past"] = all_sh.apply(is_past, axis=1)
    if st.session_state.filter == "future":
        view = all_sh[~all_sh["_past"]].copy()
    elif st.session_state.filter == "past":
        view = all_sh[all_sh["_past"]].iloc[::-1].copy()
    else:
        view = all_sh.copy()
else:
    view = pd.DataFrame()

if view.empty:
    msgs = {"future":"אין משמרות עתידיות","past":"אין משמרות עבר","all":"אין משמרות"}
    st.info(msgs[st.session_state.filter])
else:
    for _, r in view.iterrows():
        past_cls  = "past" if r.get("_past", False) else ""
        hr        = int(r["start_time"].split(":")[0]) if r["start_time"] else 0
        night_cls = "night" if hr >= 20 or hr < 6 else ""
        tags = "".join([f'<span class="gtag">{g.strip()}</span>'
                        for g in r["guards"].split(",") if g.strip()])
        if not tags: tags = '<span class="gtag empty">פנוי</span>'

        st.markdown(f"""
        <div class="shift-row {past_cls} {night_cls}">
          <div class="slot-badge">{r['slots']} עמדות</div>
          <div class="shift-time-big">{r['start_time']} – {r['end_time']}</div>
          <div class="shift-date-str">{hdate(r['date'])} · {fmt(r['duration'])}{' · ✓' if r.get('_past') else ''}</div>
          <div style="margin-top:7px">{tags}</div>
        </div>""", unsafe_allow_html=True)

        ac1, ac2 = st.columns([1,1])
        with ac1:
            if st.button("🗑️ מחק", key=f"ds_{r['id']}", use_container_width=True):
                st.session_state.confirm_del = r["id"]; st.rerun()
        with ac2:
            if st.button("✏️ ערוך", key=f"es_{r['id']}", use_container_width=True):
                st.session_state.edit_id = r["id"]; st.rerun()

        if st.session_state.confirm_del == r["id"]:
            st.warning("בטוח למחוק?")
            yc, nc = st.columns(2)
            with yc:
                if st.button("✅ כן, מחק", key=f"yd_{r['id']}", type="primary", use_container_width=True):
                    del_shift(r["id"]); st.session_state.confirm_del = None; st.rerun()
            with nc:
                if st.button("❌ ביטול", key=f"nd_{r['id']}", use_container_width=True):
                    st.session_state.confirm_del = None; st.rerun()

# ── Edit form ─────────────────────────────────────────────────────────────
if st.session_state.edit_id is not None:
    c = db()
    erow = c.execute("SELECT * FROM shifts WHERE id=?", (st.session_state.edit_id,)).fetchone()
    c.close()
    if erow:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="sec-title">✏️ עריכת משמרת</div>', unsafe_allow_html=True)
        ea, eb = st.columns(2)
        with ea: e_date = st.date_input("תאריך", value=datetime.strptime(erow[1],"%Y-%m-%d").date(), key="ed")
        with eb: e_time = st.time_input("שעה", value=datetime.strptime(erow[2],"%H:%M").time(), key="et2")
        ec, ed = st.columns(2)
        dur_opts = [30,60,90,120,180,240]
        with ec: e_dur = st.selectbox("משך", dur_opts,
            index=dur_opts.index(erow[4]) if erow[4] in dur_opts else 1,
            format_func=fmt, key="edu")
        with ed: e_slots = st.number_input("עמדות", min_value=1, max_value=3, value=int(erow[5]), key="esl")
        e_guards = st.text_input("שומרים (מופרדים בפסיק)", value=erow[6], key="eg2")
        sv, ca = st.columns(2)
        with sv:
            if st.button("💾 שמור", type="primary", use_container_width=True, key="save_ed"):
                es = e_time.strftime("%H:%M")
                save_shift_edit(st.session_state.edit_id,
                    e_date.strftime("%Y-%m-%d"), es, end_time(es, e_dur), e_dur, e_slots,
                    [g.strip() for g in e_guards.split(",") if g.strip()])
                st.session_state.edit_id = None
                st.toast("✅ עודכן!", icon="✅"); st.rerun()
        with ca:
            if st.button("ביטול", use_container_width=True, key="cancel_ed"):
                st.session_state.edit_id = None; st.rerun()

# ── SHARE SECTION ─────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="sec-title">📤 שיתוף משמרות</div>', unsafe_allow_html=True)

all_sh2 = get_all_shifts()
if all_sh2.empty:
    st.info("אין משמרות לשיתוף")
else:
    all_sh2["_past"] = all_sh2.apply(is_past, axis=1)
    future_sh = all_sh2[~all_sh2["_past"]].copy()

    # Day range filter
    st.markdown("**טווח ימים לשיתוף:**")
    day_opts = {"היום": 0, "3 ימים": 3, "שבוע": 7, "חודש": 30, "הכל": 999}
    dcols = st.columns(len(day_opts))
    for i, (lbl, val) in enumerate(day_opts.items()):
        with dcols[i]:
            t = "primary" if st.session_state.share_days == val else "secondary"
            if st.button(lbl, key=f"sd_{val}", type=t, use_container_width=True):
                st.session_state.share_days = val; st.rerun()

    # Filter by day range
    if st.session_state.share_days == 0:
        share_df = future_sh[future_sh["date"] == today.strftime("%Y-%m-%d")]
    elif st.session_state.share_days == 999:
        share_df = future_sh
    else:
        cutoff = (today + timedelta(days=st.session_state.share_days)).strftime("%Y-%m-%d")
        share_df = future_sh[future_sh["date"] <= cutoff]

    share_text = build_share_text(share_df)

    st.markdown(f'<div class="share-text">{share_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

    wa_url = "https://wa.me/?text=" + urllib.parse.quote(share_text)

    b1, b2 = st.columns(2)
    with b1:
        st.markdown(
            f'<a href="{wa_url}" target="_blank" style="text-decoration:none">'
            f'<button style="width:100%;background:#25D366;color:white;border:none;'
            f'border-radius:10px;padding:11px;font-size:14px;font-weight:700;'
            f'cursor:pointer;font-family:Heebo,sans-serif">📲 שלח בוואטסאפ</button></a>',
            unsafe_allow_html=True
        )
    with b2:
        st.text_area("העתק טקסט:", value=share_text, height=68, key="copy_ta", label_visibility="collapsed")
```

# ══════════════════════════════════════════════════════════════════════════════

# TAB 2 — GUARDS

# ══════════════════════════════════════════════════════════════════════════════

with tab2:
st.markdown(’<div class="sec-title">הוספת שומרים</div>’, unsafe_allow_html=True)
names_in = st.text_area(“שמות מופרדים בפסיק”, placeholder=“ישראל ישראלי, דוד כהן, רחל לוי…”,
height=80, key=“names_in”)
pa, pb = st.columns(2)
with pa:
if st.button(“🔍 תצוגה מקדימה”, key=“prev_g”, use_container_width=True):
if names_in.strip():
names = [n.strip() for n in names_in.replace(”،”,”,”).split(”,”) if n.strip()]
ex = get_guards()[“name”].tolist() if not get_guards().empty else []
new = [n for n in names if n not in ex]
if new: st.success(f”יתווספו: {’, ’.join(new)}”)
else: st.warning(“כל השמות כבר קיימים”)
with pb:
if st.button(“➕ הוסף לרשימה”, type=“primary”, key=“add_g”, use_container_width=True):
if names_in.strip():
added = add_guards_bulk(names_in)
st.toast(f”✅ נוספו {added} שומרים”, icon=“✅”); st.rerun()

```
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="sec-title">שומרים רשומים</div>', unsafe_allow_html=True)

gdf = get_guards()
if gdf.empty:
    st.info("אין שומרים ברשימה")
else:
    st.markdown(f"<div style='color:#475569;font-size:12px;margin-bottom:10px'>{len(gdf)} שומרים רשומים</div>",
                unsafe_allow_html=True)

    # Rename panel (outside loop)
    if st.session_state.rename_id is not None:
        rrow = gdf[gdf["id"] == st.session_state.rename_id]
        if not rrow.empty:
            rname = rrow.iloc[0]["name"]
            st.markdown(f'<div class="card"><strong>✏️ עריכת שם: {rname}</strong></div>',
                        unsafe_allow_html=True)
            new_name_val = st.text_input("שם חדש", value=rname, key="rename_input")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("💾 שמור", type="primary", key="save_rn", use_container_width=True):
                    if new_name_val.strip() and new_name_val.strip() != rname:
                        rename_guard(st.session_state.rename_id, rname, new_name_val.strip())
                        st.toast(f"✅ עודכן ל-{new_name_val.strip()}", icon="✅")
                    st.session_state.rename_id = None; st.rerun()
            with rc2:
                if st.button("ביטול", key="cancel_rn", use_container_width=True):
                    st.session_state.rename_id = None; st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)

    for _, row in gdf.iterrows():
        gc1, gc2, gc3, gc4 = st.columns([1, 4, 1, 1])
        with gc1:
            st.markdown(f'<div class="g-avatar">{row["name"][0]}</div>', unsafe_allow_html=True)
        with gc2:
            st.markdown(f"<div style='font-size:14px;font-weight:600;line-height:2.2'>{row['name']}</div>",
                        unsafe_allow_html=True)
        with gc3:
            if st.button("✏️", key=f"rn_{row['id']}", help="ערוך שם"):
                st.session_state.rename_id = row["id"]; st.rerun()
        with gc4:
            if st.button("✕", key=f"dg_{row['id']}", help="מחק"):
                st.session_state.confirm_del_g = row["id"]; st.rerun()

        if st.session_state.confirm_del_g == row["id"]:
            st.warning(f"בטוח למחוק את {row['name']}?")
            yy, nn = st.columns(2)
            with yy:
                if st.button("✅ כן", key=f"yg_{row['id']}", type="primary", use_container_width=True):
                    del_guard(row["id"]); st.session_state.confirm_del_g = None; st.rerun()
            with nn:
                if st.button("❌ לא", key=f"ng_{row['id']}", use_container_width=True):
                    st.session_state.confirm_del_g = None; st.rerun()
```

# ══════════════════════════════════════════════════════════════════════════════

# TAB 3 — STATS

# ══════════════════════════════════════════════════════════════════════════════

with tab3:
all_sh = get_all_shifts()
gdf    = get_guards()
total_min = int(all_sh[“duration”].sum()) if not all_sh.empty else 0
total_hrs = round(total_min / 60, 1)

```
s1, s2, s3, s4 = st.columns(4)
with s1: st.markdown(f'<div class="stat-box"><div class="stat-num">{len(all_sh)}</div><div class="stat-label">משמרות</div></div>', unsafe_allow_html=True)
with s2: st.markdown(f'<div class="stat-box"><div class="stat-num">{total_hrs}</div><div class="stat-label">שעות</div></div>', unsafe_allow_html=True)
with s3: st.markdown(f'<div class="stat-box"><div class="stat-num">{len(gdf)}</div><div class="stat-label">שומרים</div></div>', unsafe_allow_html=True)
with s4:
    active = 0
    if not all_sh.empty and not gdf.empty:
        all_g_str = " ".join(all_sh["guards"].tolist())
        active = sum(1 for n in gdf["name"] if n in all_g_str)
    st.markdown(f'<div class="stat-box"><div class="stat-num">{active}</div><div class="stat-label">פעילים</div></div>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="sec-title">שעות לפי שומר</div>', unsafe_allow_html=True)

if all_sh.empty or gdf.empty:
    st.info("אין נתונים עדיין")
else:
    rows = []
    for _, g in gdf.iterrows():
        mins = 0; cnt = 0
        for _, s in all_sh.iterrows():
            gl = [x.strip() for x in s["guards"].split(",")]
            if g["name"] in gl:
                mins += int(s["duration"]); cnt += 1
        if mins > 0:
            rows.append({"שם": g["name"], "משמרות": cnt, "שעות": round(mins/60,1), "_m": mins})

    if rows:
        sdf  = pd.DataFrame(rows).sort_values("_m", ascending=False)
        maxm = sdf["_m"].max()
        for _, r in sdf.iterrows():
            pct = int(r["_m"] / maxm * 100) if maxm else 0
            st.markdown(f"""
            <div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;
            padding:12px 16px;margin-bottom:8px">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:7px">
                <div style="font-size:14px;font-weight:700">{r['שם']}</div>
                <div style="display:flex;gap:8px;align-items:center">
                  <div style="font-size:11px;color:#475569">{r['משמרות']} משמרות</div>
                  <div style="font-size:13px;font-weight:800;color:#3b82f6;
                  background:rgba(59,130,246,.1);padding:2px 10px;border-radius:8px">{r['שעות']}ש'</div>
                </div>
              </div>
              <div style="height:7px;background:#1e2d45;border-radius:4px;overflow:hidden">
                <div style="width:{pct}%;height:100%;
                background:linear-gradient(90deg,#3b82f6,#6366f1);border-radius:4px"></div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        st.dataframe(sdf[["שם","משמרות","שעות"]], use_container_width=True, hide_index=True)
    else:
        st.info("אין שומרים עם משמרות משובצות")
```
