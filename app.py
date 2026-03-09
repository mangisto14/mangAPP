import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import urllib.parse

st.set_page_config(page_title="Guard Shifts", page_icon="shield", layout="centered")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700;800;900&display=swap');
*, *::before, *::after { font-family: 'Heebo', sans-serif !important; }
html, body, [class*="css"] { direction: rtl !important; }
.stApp { background: #0b0f1c !important; color: #f1f5f9; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0.5rem 0.75rem 5rem !important; max-width: 600px !important; }
.app-header { background: linear-gradient(135deg,#0f172a,#1a3050); border:1px solid #1e2d45;
  border-radius:16px; padding:16px 20px 14px; margin-bottom:14px; }
.app-header h1 { font-size:22px; font-weight:900; margin:0;
  background:linear-gradient(135deg,#60a5fa,#818cf8);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.app-header p { font-size:11px; color:#475569; margin:2px 0 0; }
.sec-title { font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase;
  letter-spacing:1px; margin:16px 0 8px; padding-right:8px; border-right:3px solid #3b82f6; }
.shift-row { background:#0f1724; border:1px solid #1e2d45; border-radius:12px;
  padding:12px 14px; margin-bottom:8px; border-right:3px solid #3b82f6; position:relative; }
.shift-row.night { border-right-color:#8b5cf6; }
.shift-row.past  { border-right-color:#374151; opacity:0.6; }
.shift-time-big  { font-size:20px; font-weight:900; color:#f1f5f9; }
.shift-date-str  { font-size:11px; color:#475569; margin-top:1px; }
.slot-badge { position:absolute; left:12px; top:12px; background:#1e2d45; border-radius:8px;
  padding:2px 8px; font-size:11px; font-weight:700; color:#64748b; }
.gtag { display:inline-block; font-size:12px; padding:3px 10px; margin:2px;
  background:rgba(59,130,246,.15); border:1px solid rgba(59,130,246,.3);
  border-radius:10px; color:#93c5fd; font-weight:600; }
.gtag.empty { background:rgba(239,68,68,.1); border-color:rgba(239,68,68,.3); color:#fca5a5; }
.slot-box { border-radius:10px; padding:8px 10px; text-align:center;
  border:1px solid #1e2d45; background:#1a2236; margin-bottom:6px; }
.slot-box.filled { background:rgba(59,130,246,.1); border-color:rgba(59,130,246,.4); }
.slot-num  { font-size:10px; color:#475569; margin-bottom:2px; }
.slot-name { font-size:13px; font-weight:700; color:#475569; }
.slot-box.filled .slot-name { color:#93c5fd; }
.stButton button { border-radius:20px !important; font-weight:600 !important;
  font-size:13px !important; background:#1a2236 !important; color:#94a3b8 !important;
  border:1px solid #1e2d45 !important; }
.stButton button:hover { background:#3b82f6 !important; color:white !important;
  border-color:#3b82f6 !important; }
button[kind="primary"] { background:#3b82f6 !important; color:white !important;
  border-color:#3b82f6 !important; border-radius:10px !important; }
.stTabs [data-baseweb="tab-list"] { background:#111827; border-radius:12px;
  gap:3px; padding:4px; border:1px solid #1e2d45; }
.stTabs [data-baseweb="tab"] { background:transparent; color:#64748b;
  border-radius:9px; font-weight:600; font-size:13px; padding:8px 12px; }
.stTabs [aria-selected="true"] { background:#3b82f6 !important; color:white !important; }
label { color:#64748b !important; font-size:12px !important; font-weight:600 !important; }
.stTextInput input, .stTextArea textarea { background:#1a2236 !important;
  border:1px solid #1e2d45 !important; color:#f1f5f9 !important;
  border-radius:10px !important; direction:rtl !important; }
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color:#3b82f6 !important; box-shadow:0 0 0 1px #3b82f6 !important; }
.stSelectbox > div > div { background:#1a2236 !important; border:1px solid #1e2d45 !important;
  color:#f1f5f9 !important; border-radius:10px !important; }
.stDateInput input, .stTimeInput input { background:#1a2236 !important;
  color:#f1f5f9 !important; border:1px solid #1e2d45 !important; border-radius:10px !important; }
.stat-box { background:#111827; border:1px solid #1e2d45; border-radius:12px;
  padding:14px 10px; text-align:center; }
.stat-num   { font-size:28px; font-weight:900; color:#3b82f6; }
.stat-label { font-size:10px; color:#475569; font-weight:700; margin-top:2px; text-transform:uppercase; }
.g-avatar { width:36px; height:36px; border-radius:50%;
  background:linear-gradient(135deg,#3b82f6,#6366f1);
  display:inline-flex; align-items:center; justify-content:center;
  font-weight:800; font-size:14px; color:white; }
.share-text { background:#1a2236; border:1px solid #1e2d45; border-radius:8px;
  padding:12px; font-size:13px; color:#94a3b8; direction:rtl; white-space:pre-wrap;
  max-height:200px; overflow-y:auto; margin-bottom:10px; line-height:1.7; }
hr { border-color:#1e2d45 !important; margin:14px 0 !important; }
</style>""", unsafe_allow_html=True)

# ── DB ────────────────────────────────────────────────────────────────────────
DB = "guards.db"

def get_conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("CREATE TABLE IF NOT EXISTS guards (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS shifts  (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, start_time TEXT, end_time TEXT, duration INTEGER, slots INTEGER, guards TEXT)")
    c.commit()
    return c

def q(sql, params=()):
    c = get_conn(); r = c.execute(sql, params).fetchall(); c.close(); return r

def run(sql, params=()):
    c = get_conn(); c.execute(sql, params); c.commit(); c.close()

def get_guards():
    c = get_conn(); df = pd.read_sql("SELECT * FROM guards ORDER BY name", c); c.close(); return df

def get_shifts():
    c = get_conn(); df = pd.read_sql("SELECT * FROM shifts ORDER BY date, start_time", c); c.close(); return df

def add_shift(d, st_, et, dur, sl, gl):
    run("INSERT INTO shifts (date,start_time,end_time,duration,slots,guards) VALUES (?,?,?,?,?,?)",
        (d, st_, et, dur, sl, ",".join(gl)))

def save_edit(sid, d, st_, et, dur, sl, gl):
    run("UPDATE shifts SET date=?,start_time=?,end_time=?,duration=?,slots=?,guards=? WHERE id=?",
        (d, st_, et, dur, sl, ",".join(gl), sid))

def del_shift(sid):  run("DELETE FROM shifts WHERE id=?", (sid,))
def del_guard(gid):  run("DELETE FROM guards WHERE id=?", (gid,))

def add_guards_bulk(text):
    names = [n.strip() for n in text.replace(",",",").split(",") if n.strip()]
    c = get_conn(); added = 0
    for n in names:
        try: c.execute("INSERT INTO guards (name) VALUES (?)", (n,)); added += 1
        except: pass
    c.commit(); c.close(); return added

def rename_guard(gid, old, new):
    c = get_conn()
    try:
        c.execute("UPDATE guards SET name=? WHERE id=?", (new, gid))
        for sid, sg in c.execute("SELECT id, guards FROM shifts").fetchall():
            upd = ",".join([new if g.strip()==old else g.strip() for g in sg.split(",")])
            c.execute("UPDATE shifts SET guards=? WHERE id=?", (upd, sid))
        c.commit()
    except: pass
    c.close()

def calc_end(start, mins):
    return (datetime.strptime(start, "%H:%M") + timedelta(minutes=int(mins))).strftime("%H:%M")

def fmt_dur(mins):
    mins = int(mins)
    if mins < 60: return str(mins) + " min"
    h = mins // 60; m = mins % 60
    return str(h) + ("h30" if m else "h")

DAYS   = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
MONTHS = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]

def hdate(ds):
    try:
        d = datetime.strptime(ds, "%Y-%m-%d")
        return DAYS[d.weekday()] + " " + str(d.day) + " " + MONTHS[d.month]
    except: return ds

def is_past(row):
    try:
        return datetime.strptime(row["date"] + " " + row["end_time"], "%Y-%m-%d %H:%M") < datetime.now()
    except: return False

def build_share(df):
    if df.empty: return "אין משמרות"
    out = ["🛡️ *לוח משמרות שמירה*", ""]
    cur = None
    for _, r in df.iterrows():
        if r["date"] != cur:
            cur = r["date"]; out.append("📅 *" + hdate(cur) + "*")
        gl = [g.strip() for g in r["guards"].split(",") if g.strip()]
        gs = " | ".join(gl) if gl else "לא שובצו"
        out.append("  ⏰ " + r["start_time"] + "–" + r["end_time"] + "  👮 " + gs)
    out += ["", "_נשלח ממערכת ניהול שמירות_ 🛡️"]
    return "\n".join(out)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
SS = st.session_state
for k, v in [
    ("sel_guards", []),
    ("shift_filter", "future"),
    ("edit_id", None),
    ("del_id", None),
    ("rename_id", None),
    ("del_guard_id", None),
    ("share_days", 7),
    ("last_slots", 1),
]:
    if k not in SS: SS[k] = v

# Callbacks — all state changes happen here, BEFORE widgets render
def cb_toggle_guard(name, slots):
    if name in SS.sel_guards:
        SS.sel_guards = [g for g in SS.sel_guards if g != name]
    elif len(SS.sel_guards) < slots:
        SS.sel_guards = SS.sel_guards + [name]

def cb_clear_guards():
    SS.sel_guards = []

def cb_set_filter(v):
    SS.shift_filter = v
    SS.del_id = None
    SS.edit_id = None

def cb_set_share_days(v):
    SS.share_days = v

def cb_del_shift(sid):
    SS.del_id = sid
    SS.edit_id = None

def cb_confirm_del():
    if SS.del_id is not None:
        del_shift(SS.del_id)
        SS.del_id = None

def cb_cancel_del():
    SS.del_id = None

def cb_edit_shift(sid):
    SS.edit_id = sid
    SS.del_id = None

def cb_cancel_edit():
    SS.edit_id = None

def cb_rename(gid):
    SS.rename_id = gid

def cb_cancel_rename():
    SS.rename_id = None

def cb_del_guard(gid):
    SS.del_guard_id = gid

def cb_confirm_del_guard():
    if SS.del_guard_id is not None:
        del_guard(SS.del_guard_id)
        SS.del_guard_id = None

def cb_cancel_del_guard():
    SS.del_guard_id = None

# ── HEADER ────────────────────────────────────────────────────────────────────
today = date.today()
st.markdown(
    "<div class=\"app-header\"><h1>\U0001f6e1\ufe0f \u05e0\u05d9\u05d4\u05d5\u05dc \u05e9\u05de\u05d9\u05e8\u05d5\u05ea</h1>"
    "<p>" + hdate(today.strftime("%Y-%m-%d")) + " &middot; " + today.strftime("%d/%m/%Y") + "</p></div>",
    unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs([
    "📅 משמרות",
    "👥 שומרים",
    "📊 סטטיסטיקה"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<div class=\"sec-title\">פרטי משמרת</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        sh_date = st.date_input("תאריך", value=today, key="sh_date")
    with col2:
        shifts_all = get_shifts()
        def_time = datetime.strptime("08:00", "%H:%M").time()
        if not shifts_all.empty:
            ts = shifts_all[shifts_all["date"] == sh_date.strftime("%Y-%m-%d")]
            if not ts.empty:
                try: def_time = datetime.strptime(ts.iloc[-1]["end_time"], "%H:%M").time()
                except: pass
        sh_time = st.time_input("שעת התחלה", value=def_time, key="sh_time")

    col3, col4 = st.columns(2)
    with col3:
        dur_options = [30, 60, 90, 120, 180, 240]
        dur_labels  = [fmt_dur(d) for d in dur_options]
        dur_idx = st.selectbox("משך", range(len(dur_options)),
                               format_func=lambda i: dur_labels[i], key="sh_dur")
        dur = dur_options[dur_idx]
    with col4:
        slots = st.selectbox(
            "שומרים",
            [1, 2, 3],
            format_func=lambda x: str(x) + (" שומרים" if x > 1 else " שומר"),
            key="sh_slots"
        )

    # Trim selection if slots decreased — do this via session state, no rerun
    if len(SS.sel_guards) > slots:
        SS.sel_guards = SS.sel_guards[:slots]

    # ── Slot boxes (always render 3, hide extras) ─────────────────────────────
    st.markdown("<div class=\"sec-title\">שיבוץ שומרים</div>", unsafe_allow_html=True)
    bc1, bc2, bc3 = st.columns(3)
    slot_cols = [bc1, bc2, bc3]
    for i in range(3):
        with slot_cols[i]:
            if i < slots:
                g = SS.sel_guards[i] if i < len(SS.sel_guards) else None
                filled = "filled" if g else ""
                nm = g if g else "פנוי"
                st.markdown(
                    f"<div class=\"slot-box {filled}\"><div class=\"slot-num\">עמדה {i+1}</div>"
                    f"<div class=\"slot-name\">{nm}</div></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<div style=\"height:52px\"></div>", unsafe_allow_html=True)

    # ── Guard buttons ─────────────────────────────────────────────────────────
    gdf = get_guards()
    if gdf.empty:
        st.info("הוסף שומרים בלשונית שומרים")
    else:
        guard_names = gdf["name"].tolist()
        ncols = min(len(guard_names), 4)
        gcols = st.columns(ncols)
        for i, name in enumerate(guard_names):
            sel = name in SS.sel_guards
            lbl = ("✓ " if sel else "") + name
            with gcols[i % ncols]:
                st.button(lbl, key="gb_" + name,
                          on_click=cb_toggle_guard, args=(name, slots))

        if SS.sel_guards:
            st.button("🗑️ נקה בחירה", key="clr_guards",
                      on_click=cb_clear_guards)

    st.markdown("<div style=\"height:8px\"></div>", unsafe_allow_html=True)

    # ── Save button ───────────────────────────────────────────────────────────
    if st.button("💾  שמור משמרת", type="primary",
                 use_container_width=True, key="save_shift"):
        s = sh_time.strftime("%H:%M")
        add_shift(sh_date.strftime("%Y-%m-%d"), s, calc_end(s, dur), dur, slots, SS.sel_guards)
        SS.sel_guards = []
        st.success("✅ משמרת נשמרה!")
        st.rerun()

    # ── Shifts list ───────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class=\"sec-title\">רשימת משמרות</div>", unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    labels_filters = [
        ("⏩ עתידיות", "future", fc1),
        ("⏮ עבר",                          "past",   fc2),
        ("📋 הכל",                      "all",    fc3),
    ]
    for lbl, val, col in labels_filters:
        with col:
            t = "primary" if SS.shift_filter == val else "secondary"
            st.button(lbl, type=t, key="filt_" + val,
                      on_click=cb_set_filter, args=(val,),
                      use_container_width=True)

    shifts_all = get_shifts()
    if not shifts_all.empty:
        shifts_all["_past"] = shifts_all.apply(is_past, axis=1)
        if SS.shift_filter == "future":
            view = shifts_all[~shifts_all["_past"]].copy()
        elif SS.shift_filter == "past":
            view = shifts_all[shifts_all["_past"]].iloc[::-1].copy()
        else:
            view = shifts_all.copy()
    else:
        view = pd.DataFrame()

    no_msg = {"future": "אין משמרות עתידיות",
              "past":   "אין משמרות עבר",
              "all":    "אין משמרות"}
    if view.empty:
        st.info(no_msg[SS.shift_filter])
    else:
        for _, r in view.iterrows():
            rid       = int(r["id"])
            past_cls  = "past"  if r.get("_past", False) else ""
            hr        = int(r["start_time"].split(":")[0]) if r["start_time"] else 0
            night_cls = "night" if (hr >= 20 or hr < 6)   else ""
            tags = "".join([f"<span class=\"gtag\">{g.strip()}</span>"
                            for g in r["guards"].split(",") if g.strip()])
            if not tags: tags = "<span class=\"gtag empty\">פנוי</span>"

            st.markdown(
                f"<div class=\"shift-row {past_cls} {night_cls}\">"
                f"<div class=\"slot-badge\">{r['slots']} עמדות</div>"
                f"<div class=\"shift-time-big\">{r['start_time']} – {r['end_time']}</div>"
                f"<div class=\"shift-date-str\">{hdate(r['date'])} &middot; {fmt_dur(r['duration'])}"
                f"{'  &middot; ✓' if r.get('_past') else ''}</div>"
                f"<div style=\"margin-top:7px\">{tags}</div></div>",
                unsafe_allow_html=True
            )

            ac1, ac2 = st.columns(2)
            with ac1:
                st.button("🗑️ מחק", key=f"ds_{rid}",
                          on_click=cb_del_shift, args=(rid,),
                          use_container_width=True)
            with ac2:
                st.button("✏️ ערוך", key=f"es_{rid}",
                          on_click=cb_edit_shift, args=(rid,),
                          use_container_width=True)

            if SS.del_id == rid:
                st.warning("בטוח למחוק?")
                yc, nc = st.columns(2)
                with yc:
                    st.button("✅ כן, מחק", key=f"yd_{rid}",
                              type="primary", on_click=cb_confirm_del,
                              use_container_width=True)
                with nc:
                    st.button("❌ ביטול", key=f"nd_{rid}",
                              on_click=cb_cancel_del, use_container_width=True)

    # ── Edit form ─────────────────────────────────────────────────────────────
    if SS.edit_id is not None:
        erows = q("SELECT * FROM shifts WHERE id=?", (SS.edit_id,))
        if erows:
            erow = erows[0]
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<div class=\"sec-title\">✏️ עריכת משמרת</div>", unsafe_allow_html=True)
            ea, eb = st.columns(2)
            with ea:
                e_date = st.date_input("תאריך",
                                       value=datetime.strptime(erow[1], "%Y-%m-%d").date(),
                                       key="e_date")
            with eb:
                e_time = st.time_input("שעה",
                                       value=datetime.strptime(erow[2], "%H:%M").time(),
                                       key="e_time")
            ec, ed = st.columns(2)
            with ec:
                e_dur_idx = st.selectbox("משך", range(len(dur_options)),
                    index=dur_options.index(erow[4]) if erow[4] in dur_options else 1,
                    format_func=lambda i: dur_labels[i], key="e_dur")
                e_dur = dur_options[e_dur_idx]
            with ed:
                e_slots = st.number_input("עמדות",
                                          min_value=1, max_value=3, value=int(erow[5]),
                                          key="e_slots")
            e_guards = st.text_input("שומרים (מופרדים בפסיק)",
                                     value=erow[6], key="e_guards")
            sv, ca = st.columns(2)
            with sv:
                if st.button("💾 שמור", type="primary",
                             use_container_width=True, key="save_edit"):
                    es = e_time.strftime("%H:%M")
                    save_edit(SS.edit_id, e_date.strftime("%Y-%m-%d"),
                              es, calc_end(es, e_dur), e_dur, e_slots,
                              [g.strip() for g in e_guards.split(",") if g.strip()])
                    SS.edit_id = None
                    st.success("✅ עודכן!")
                    st.rerun()
            with ca:
                st.button("ביטול", use_container_width=True,
                          key="cancel_edit", on_click=cb_cancel_edit)

    # ── Share section ─────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class=\"sec-title\">📤 שיתוף משמרות</div>", unsafe_allow_html=True)

    shifts_all2 = get_shifts()
    if shifts_all2.empty:
        st.info("אין משמרות לשיתוף")
    else:
        shifts_all2["_past"] = shifts_all2.apply(is_past, axis=1)
        future_sh = shifts_all2[~shifts_all2["_past"]].copy()

        st.markdown("<div style=\"font-size:12px;color:#64748b;margin-bottom:6px\">טווח ימים:</div>", unsafe_allow_html=True)
        day_opts = [("היום", 0), ("3 ימים", 3),
                    ("שבוע", 7), ("חודש", 30),
                    ("הכל", 999)]
        dcols = st.columns(len(day_opts))
        for i, (lbl, val) in enumerate(day_opts):
            with dcols[i]:
                t = "primary" if SS.share_days == val else "secondary"
                st.button(lbl, key="sd_" + str(val), type=t,
                          on_click=cb_set_share_days, args=(val,),
                          use_container_width=True)

        if SS.share_days == 0:
            share_df = future_sh[future_sh["date"] == today.strftime("%Y-%m-%d")]
        elif SS.share_days == 999:
            share_df = future_sh
        else:
            cutoff = (today + timedelta(days=SS.share_days)).strftime("%Y-%m-%d")
            share_df = future_sh[future_sh["date"] <= cutoff]

        share_text = build_share(share_df)
        st.markdown(
            "<div class=\"share-text\">" + share_text.replace("\n", "<br>") + "</div>",
            unsafe_allow_html=True
        )
        wa_url = "https://wa.me/?text=" + urllib.parse.quote(share_text)
        b1, b2 = st.columns(2)
        with b1:
            st.markdown(
                f"<a href=\"{wa_url}\" target=\"_blank\" style=\"text-decoration:none\">"
                "<button style=\"width:100%;background:#25D366;color:white;border:none;"
                "border-radius:10px;padding:11px;font-size:14px;font-weight:700;"
                "cursor:pointer;font-family:Heebo,sans-serif;\">"
                "📲 שלח בוואטסאפ"
                "</button></a>",
                unsafe_allow_html=True
            )
        with b2:
            st.text_area("", value=share_text, height=70,
                         key="cp_ta", label_visibility="collapsed")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<div class=\"sec-title\">הוספת שומרים</div>", unsafe_allow_html=True)
    names_in = st.text_area(
        "שמות מופרדים בפסיק",
        placeholder="ישראל ישראלי, דוד כהן, רחל לוי...",
        height=80, key="names_in"
    )
    pa, pb = st.columns(2)
    with pa:
        if st.button("🔍 תצוגה מקדימה",
                     key="prev_g", use_container_width=True):
            if names_in.strip():
                names = [n.strip() for n in names_in.replace(",",",").split(",") if n.strip()]
                ex = get_guards()["name"].tolist() if not get_guards().empty else []
                new = [n for n in names if n not in ex]
                if new:   st.success("יתווספו: " + ", ".join(new))
                else:     st.warning("כל השמות כבר קיימים")
    with pb:
        if st.button("➕ הוסף לרשימה",
                     type="primary", key="add_g", use_container_width=True):
            if names_in.strip():
                added = add_guards_bulk(names_in)
                st.success("✅ " + str(added) + " שומרים נוספו")
                st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class=\"sec-title\">שומרים רשומים</div>", unsafe_allow_html=True)

    gdf = get_guards()
    if gdf.empty:
        st.info("אין שומרים ברשימה")
    else:
        st.markdown(f"<div style=\"color:#475569;font-size:12px;margin-bottom:10px\">{len(gdf)} שומרים</div>",
                    unsafe_allow_html=True)

        # Rename panel — outside the loop
        if SS.rename_id is not None:
            rrow = gdf[gdf["id"] == SS.rename_id]
            if not rrow.empty:
                rname = rrow.iloc[0]["name"]
                new_name_val = st.text_input("שם חדש",
                                             value=rname, key="rename_val")
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("💾 שמור", type="primary",
                                 key="save_rn", use_container_width=True):
                        if new_name_val.strip() and new_name_val.strip() != rname:
                            rename_guard(int(SS.rename_id), rname, new_name_val.strip())
                            st.success("✅ " + new_name_val.strip())
                        SS.rename_id = None
                        st.rerun()
                with rc2:
                    st.button("ביטול", key="cancel_rn",
                              on_click=cb_cancel_rename, use_container_width=True)
                st.markdown("<hr>", unsafe_allow_html=True)

        for _, row in gdf.iterrows():
            gid = int(row["id"])
            gc1, gc2, gc3, gc4 = st.columns([1, 4, 1, 1])
            with gc1:
                st.markdown(f"<div class=\"g-avatar\">{row['name'][0]}</div>", unsafe_allow_html=True)
            with gc2:
                st.markdown(f"<div style=\"font-size:14px;font-weight:600;line-height:2.4\">{row['name']}</div>",
                            unsafe_allow_html=True)
            with gc3:
                st.button("✏️", key=f"rn_{gid}",
                          on_click=cb_rename, args=(gid,), help="ערוך שם")
            with gc4:
                st.button("✕", key=f"dg_{gid}",
                          on_click=cb_del_guard, args=(gid,), help="מחק")

            if SS.del_guard_id == gid:
                st.warning(row["name"] + " — בטוח למחוק?")
                yy, nn = st.columns(2)
                with yy:
                    st.button("✅ כן", key=f"yg_{gid}", type="primary",
                              on_click=cb_confirm_del_guard, use_container_width=True)
                with nn:
                    st.button("❌ לא", key=f"ng_{gid}",
                              on_click=cb_cancel_del_guard, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    all_sh = get_shifts()
    gdf    = get_guards()
    total_min = int(all_sh["duration"].sum()) if not all_sh.empty else 0
    total_hrs = round(total_min / 60, 1)

    s1, s2, s3, s4 = st.columns(4)
    with s1: st.markdown(f"<div class=\"stat-box\"><div class=\"stat-num\">{len(all_sh)}</div><div class=\"stat-label\">משמרות</div></div>", unsafe_allow_html=True)
    with s2: st.markdown(f"<div class=\"stat-box\"><div class=\"stat-num\">{total_hrs}</div><div class=\"stat-label\">שעות</div></div>", unsafe_allow_html=True)
    with s3: st.markdown(f"<div class=\"stat-box\"><div class=\"stat-num\">{len(gdf)}</div><div class=\"stat-label\">שומרים</div></div>", unsafe_allow_html=True)
    with s4:
        active = 0
        if not all_sh.empty and not gdf.empty:
            all_g_str = " ".join(all_sh["guards"].tolist())
            active = sum(1 for n in gdf["name"] if n in all_g_str)
        st.markdown(f"<div class=\"stat-box\"><div class=\"stat-num\">{active}</div><div class=\"stat-label\">פעילים</div></div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class=\"sec-title\">שעות לפי שומר</div>", unsafe_allow_html=True)

    if all_sh.empty or gdf.empty:
        st.info("אין נתונים עדיין")
    else:
        rows = []
        for _, g in gdf.iterrows():
            mins = 0; cnt = 0
            for _, s in all_sh.iterrows():
                if g["name"] in [x.strip() for x in s["guards"].split(",")]:
                    mins += int(s["duration"]); cnt += 1
            if mins > 0:
                rows.append({"name": g["name"], "shifts": cnt, "hours": round(mins/60,1), "_m": mins})
        if rows:
            sdf  = pd.DataFrame(rows).sort_values("_m", ascending=False)
            maxm = sdf["_m"].max()
            for _, r in sdf.iterrows():
                pct = int(r["_m"] / maxm * 100) if maxm else 0
                st.markdown(
                    f"<div style=\"background:#111827;border:1px solid #1e2d45;border-radius:12px;"
                    f"padding:12px 16px;margin-bottom:8px\">"
                    f"<div style=\"display:flex;align-items:center;justify-content:space-between;margin-bottom:7px\">"
                    f"<div style=\"font-size:14px;font-weight:700\">{r['name']}</div>"
                    f"<div style=\"display:flex;gap:8px;align-items:center\">"
                    f"<div style=\"font-size:11px;color:#475569\">{r['shifts']} משמרות</div>"
                    f"<div style=\"font-size:13px;font-weight:800;color:#3b82f6;"
                    f"background:rgba(59,130,246,.1);padding:2px 10px;border-radius:8px\">"
                    f"{r['hours']}ש'</div></div></div>"
                    f"<div style=\"height:7px;background:#1e2d45;border-radius:4px;overflow:hidden\">"
                    f"<div style=\"width:{pct}%;height:100%;background:linear-gradient(90deg,#3b82f6,#6366f1);"
                    f"border-radius:4px\"></div></div></div>",
                    unsafe_allow_html=True
                )
            st.dataframe(
                sdf.rename(columns={"name":"שם","shifts":"משמרות","hours":"שעות"})[
                    ["שם","משמרות","שעות"]
                ],
                use_container_width=True, hide_index=True
            )
        else:
            st.info("אין שומרים עם משמרות")
