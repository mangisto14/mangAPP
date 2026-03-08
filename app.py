import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import urllib.parse

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ניהול שמירות",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── RTL + CUSTOM CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

* { font-family: 'Heebo', sans-serif !important; }

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
}

.stApp {
    background: #0a0e1a;
    color: #f1f5f9;
}

/* Header */
.main-header {
    background: linear-gradient(135deg, #0f172a, #1e3a5f);
    padding: 20px 24px 16px;
    border-radius: 16px;
    margin-bottom: 20px;
    border: 1px solid #1e2d45;
}
.main-header h1 {
    font-size: 28px;
    font-weight: 900;
    background: linear-gradient(135deg, #60a5fa, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.main-header p { color: #64748b; margin: 4px 0 0; font-size: 13px; }

/* Cards */
.section-card {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 16px;
}
.section-title {
    font-size: 13px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}

/* Guard buttons */
.guard-btn-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}

/* Shift cards */
.shift-item {
    background: #1a2236;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    border-right: 3px solid #3b82f6;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.shift-item.past { border-right-color: #6366f1; opacity: 0.7; }
.shift-time { font-size: 17px; font-weight: 800; }
.shift-meta { font-size: 11px; color: #64748b; margin-top: 2px; }
.shift-guards { display: flex; gap: 6px; flex-wrap: wrap; }
.guard-tag {
    font-size: 12px; padding: 2px 10px;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.3);
    border-radius: 10px; color: #93c5fd; font-weight: 600;
}

/* Stats */
.stat-box {
    background: #1a2236;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    border: 1px solid #1e2d45;
}
.stat-num { font-size: 32px; font-weight: 900; color: #3b82f6; }
.stat-label { font-size: 11px; color: #64748b; font-weight: 600; }

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    background: #111827;
    border-radius: 10px;
    gap: 4px;
    padding: 4px;
    border: 1px solid #1e2d45;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #64748b;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
    padding: 8px 16px;
}
.stTabs [aria-selected="true"] {
    background: #3b82f6 !important;
    color: white !important;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: #1a2236 !important;
    border: 1px solid #1e2d45 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
    direction: rtl !important;
}
.stDateInput input, .stTimeInput input {
    background: #1a2236 !important;
    color: #f1f5f9 !important;
    border: 1px solid #1e2d45 !important;
    direction: rtl !important;
}

/* Buttons */
.stButton button {
    background: #1a2236;
    color: #94a3b8;
    border: 1px solid #1e2d45;
    border-radius: 20px;
    font-weight: 600;
    font-size: 13px;
    transition: all 0.2s;
    font-family: 'Heebo', sans-serif !important;
}
.stButton button:hover {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
    transform: scale(1.05);
}
.primary-btn button {
    background: #3b82f6 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100%;
    padding: 10px !important;
}
.success-btn button {
    background: #10b981 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100%;
}
.danger-btn button {
    background: transparent !important;
    color: #ef4444 !important;
    border: 1px solid #ef4444 !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    padding: 4px 10px !important;
}
.wa-btn button {
    background: #25D366 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100%;
}

/* DataFrames */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* Labels */
label { color: #94a3b8 !important; font-size: 13px !important; font-weight: 500 !important; }

/* Selectbox */
.stSelectbox > div > div {
    background: #1a2236 !important;
    border: 1px solid #1e2d45 !important;
    color: #f1f5f9 !important;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── DATABASE ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect("guards.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration INTEGER NOT NULL,
            slots INTEGER NOT NULL,
            guards TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def get_guards():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM guards ORDER BY name", conn)
    conn.close()
    return df

def add_guards_bulk(names_str):
    conn = get_db()
    names = [n.strip() for n in names_str.replace("،", ",").split(",") if n.strip()]
    added = 0
    for name in names:
        try:
            conn.execute("INSERT INTO guards (name) VALUES (?)", (name,))
            added += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return added

def delete_guard(guard_id):
    conn = get_db()
    conn.execute("DELETE FROM guards WHERE id=?", (guard_id,))
    conn.commit()
    conn.close()

def get_shifts(filter_type="all"):
    conn = get_db()
    df = pd.read_sql("SELECT * FROM shifts ORDER BY date, start_time", conn)
    conn.close()
    if df.empty:
        return df
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    now_time = now.strftime("%H:%M")

    def is_past(row):
        if row["date"] < today_str:
            return True
        if row["date"] == today_str and row["end_time"] <= now_time:
            return True
        return False

    df["is_past"] = df.apply(is_past, axis=1)

    if filter_type == "future":
        return df[~df["is_past"]]
    elif filter_type == "past":
        return df[df["is_past"]]
    return df

def get_last_shift():
    conn = get_db()
    row = conn.execute(
        "SELECT date, end_time FROM shifts ORDER BY date DESC, end_time DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row

def add_shift(shift_date, start_time, end_time, duration, slots, guards_list):
    conn = get_db()
    conn.execute(
        "INSERT INTO shifts (date, start_time, end_time, duration, slots, guards) VALUES (?,?,?,?,?,?)",
        (shift_date, start_time, end_time, duration, slots, ",".join(guards_list))
    )
    conn.commit()
    conn.close()

def delete_shift(shift_id):
    conn = get_db()
    conn.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
    conn.commit()
    conn.close()

def update_shift(shift_id, shift_date, start_time, end_time, duration, slots, guards_list):
    conn = get_db()
    conn.execute(
        "UPDATE shifts SET date=?, start_time=?, end_time=?, duration=?, slots=?, guards=? WHERE id=?",
        (shift_date, start_time, end_time, duration, slots, ",".join(guards_list), shift_id)
    )
    conn.commit()
    conn.close()

def calc_end_time(start_time_str, duration_min):
    dt = datetime.strptime(start_time_str, "%H:%M")
    dt += timedelta(minutes=duration_min)
    return dt.strftime("%H:%M")

def fmt_duration(mins):
    if mins < 60:
        return f"{mins} דק'"
    h = mins // 60
    m = mins % 60
    return f"{h}{'½' if m else ''} שע'"

def hebrew_date(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        days = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
        months = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                  "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
        return f"{days[d.weekday()]} {d.day} {months[d.month]}"
    except:
        return date_str

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🛡️ ניהול שמירות</h1>
  <p>מערכת שיבוץ ומעקב משמרות</p>
</div>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "sel_guards" not in st.session_state:
    st.session_state.sel_guards = []
if "shift_filter" not in st.session_state:
    st.session_state.shift_filter = "future"
if "edit_shift_id" not in st.session_state:
    st.session_state.edit_shift_id = None

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📅 ניהול משמרות", "👥 ניהול שומרים", "📊 סטטיסטיקה"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SHIFT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Shift details form ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">⏰ פרטי משמרת</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        shift_date = st.date_input("תאריך", value=date.today(), label_visibility="visible")
    with col2:
        # Smart default: pick up from last shift
        last = get_last_shift()
        default_time = datetime.strptime("08:00", "%H:%M").time()
        if last:
            last_date, last_end = last
            if last_date == shift_date.strftime("%Y-%m-%d"):
                try:
                    default_time = datetime.strptime(last_end, "%H:%M").time()
                except:
                    pass
        shift_time = st.time_input("שעת התחלה", value=default_time)
    with col3:
        duration = st.selectbox("משך", [30, 60, 90, 120, 180, 240],
            format_func=lambda x: fmt_duration(x))
    with col4:
        slots = st.selectbox("שומרים", [1, 2, 3],
            format_func=lambda x: f"{x} שומר{'ים' if x > 1 else ''}")

    # ── Guard selection ──────────────────────────────────────────────────────
    st.markdown('<div class="section-title" style="margin-top:16px">🙋 שיבוץ שומרים</div>', unsafe_allow_html=True)

    guards_df = get_guards()

    if guards_df.empty:
        st.info("אין שומרים ברשימה. הוסף שומרים בלשונית 'ניהול שומרים'")
    else:
        # Show selected slots
        slot_cols = st.columns(slots)
        for i in range(slots):
            with slot_cols[i]:
                g = st.session_state.sel_guards[i] if i < len(st.session_state.sel_guards) else None
                if g:
                    st.markdown(f"""
                    <div style="background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.4);
                    border-radius:8px;padding:8px;text-align:center">
                    <div style="font-size:10px;color:#64748b">עמדה {i+1}</div>
                    <div style="font-size:13px;font-weight:700;color:#93c5fd">{g}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:#1a2236;border:1px solid #1e2d45;
                    border-radius:8px;padding:8px;text-align:center">
                    <div style="font-size:10px;color:#64748b">עמדה {i+1}</div>
                    <div style="font-size:13px;font-weight:700;color:#64748b">פנוי</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)

        # Guard buttons — dynamic columns
        guard_names = guards_df["name"].tolist()
        num_cols = min(len(guard_names), 5)
        gcols = st.columns(num_cols)
        for i, name in enumerate(guard_names):
            with gcols[i % num_cols]:
                selected = name in st.session_state.sel_guards
                label = f"✓ {name}" if selected else name
                if st.button(label, key=f"g_{name}"):
                    if selected:
                        st.session_state.sel_guards.remove(name)
                    else:
                        if len(st.session_state.sel_guards) < slots:
                            st.session_state.sel_guards.append(name)
                        else:
                            st.warning(f"כבר שובצו {slots} שומרים")
                    st.rerun()

        if st.session_state.sel_guards:
            if st.button("🗑️ נקה בחירה", key="clear_sel"):
                st.session_state.sel_guards = []
                st.rerun()

    # ── Save shift ───────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
    col_save, col_wa = st.columns([2, 1])
    with col_save:
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button("💾 שמור משמרת", key="save_shift"):
            start_str = shift_time.strftime("%H:%M")
            end_str = calc_end_time(start_str, duration)
            add_shift(
                shift_date.strftime("%Y-%m-%d"),
                start_str, end_str, duration, slots,
                st.session_state.sel_guards
            )
            st.session_state.sel_guards = []
            st.success("✅ משמרת נשמרה!")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Shifts list ──────────────────────────────────────────────────────────
    st.markdown("<hr style='border-color:#1e2d45;margin:20px 0'>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 רשימת משמרות</div>', unsafe_allow_html=True)

    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        if st.button("⏩ עתידיות", key="f_fut",
            type="primary" if st.session_state.shift_filter == "future" else "secondary"):
            st.session_state.shift_filter = "future"
            st.rerun()
    with fcol2:
        if st.button("⏮ עבר", key="f_past",
            type="primary" if st.session_state.shift_filter == "past" else "secondary"):
            st.session_state.shift_filter = "past"
            st.rerun()
    with fcol3:
        if st.button("📋 הכל", key="f_all",
            type="primary" if st.session_state.shift_filter == "all" else "secondary"):
            st.session_state.shift_filter = "all"
            st.rerun()

    shifts_df = get_shifts(st.session_state.shift_filter)

    if shifts_df.empty:
        msg = {"future": "אין משמרות עתידיות", "past": "אין משמרות עבר", "all": "אין משמרות"
               }[st.session_state.shift_filter]
        st.info(msg)
    else:
        # WhatsApp share button
        lines = ["🛡️ *לוח משמרות*\n"]
        for _, row in shifts_df.iterrows():
            g = row["guards"] if row["guards"] else "לא שובצו"
            lines.append(f"📅 {hebrew_date(row['date'])}")
            lines.append(f"⏰ {row['start_time']} – {row['end_time']} ({fmt_duration(row['duration'])})")
            lines.append(f"👮 {g}\n")
        wa_text = "\n".join(lines)
        wa_url = "https://wa.me/?text=" + urllib.parse.quote(wa_text)
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background:#25D366;color:white;border:none;border-radius:8px;padding:8px 20px;font-size:14px;font-weight:700;cursor:pointer;font-family:Heebo,sans-serif;margin-bottom:12px">📲 שתף בוואטסאפ</button></a>', unsafe_allow_html=True)

        for _, row in shifts_df.iterrows():
            past_cls = "past" if row.get("is_past", False) else ""
            guards_tags = "".join([
                f'<span class="guard-tag">{g.strip()}</span>'
                for g in row["guards"].split(",") if g.strip()
            ]) or '<span class="guard-tag" style="background:rgba(239,68,68,0.1);border-color:rgba(239,68,68,0.3);color:#fca5a5">פנוי</span>'

            st.markdown(f"""
            <div class="shift-item {past_cls}">
              <div>
                <div class="shift-time">{row['start_time']} – {row['end_time']}</div>
                <div class="shift-meta">{hebrew_date(row['date'])} · {fmt_duration(row['duration'])} · {row['slots']} עמדות</div>
                <div class="shift-guards" style="margin-top:6px">{guards_tags}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                if st.button("🗑️ מחק", key=f"del_{row['id']}"):
                    delete_shift(row["id"])
                    st.success("נמחק")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                if st.button("✏️ ערוך", key=f"edit_{row['id']}"):
                    st.session_state.edit_shift_id = row["id"]
                    st.rerun()

    # ── Edit form ────────────────────────────────────────────────────────────
    if st.session_state.edit_shift_id:
        conn = get_db()
        erow = conn.execute("SELECT * FROM shifts WHERE id=?",
                            (st.session_state.edit_shift_id,)).fetchone()
        conn.close()
        if erow:
            st.markdown("---")
            st.markdown('<div class="section-title">✏️ עריכת משמרת</div>', unsafe_allow_html=True)
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                e_date = st.date_input("תאריך", value=datetime.strptime(erow[1], "%Y-%m-%d").date(), key="e_date")
            with ec2:
                e_time = st.time_input("שעה", value=datetime.strptime(erow[2], "%H:%M").time(), key="e_time")
            with ec3:
                e_dur = st.selectbox("משך", [30,60,90,120,180,240],
                    index=[30,60,90,120,180,240].index(erow[4]) if erow[4] in [30,60,90,120,180,240] else 1,
                    format_func=lambda x: fmt_duration(x), key="e_dur")
            e_guards = st.text_input("שומרים (מופרדים בפסיק)", value=erow[6], key="e_guards")
            ec4, ec5 = st.columns(2)
            with ec4:
                if st.button("💾 שמור", key="save_edit"):
                    e_st = e_time.strftime("%H:%M")
                    e_end = calc_end_time(e_st, e_dur)
                    update_shift(st.session_state.edit_shift_id,
                        e_date.strftime("%Y-%m-%d"), e_st, e_end, e_dur, erow[5],
                        [g.strip() for g in e_guards.split(",") if g.strip()])
                    st.session_state.edit_shift_id = None
                    st.success("עודכן!")
                    st.rerun()
            with ec5:
                if st.button("ביטול", key="cancel_edit"):
                    st.session_state.edit_shift_id = None
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GUARDS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">➕ הוספת שומרים</div>', unsafe_allow_html=True)

    names_input = st.text_area(
        "שמות מופרדים בפסיק",
        placeholder="ישראל ישראלי, דוד כהן, רחל לוי...",
        height=80
    )

    col_prev, col_add = st.columns(2)
    with col_prev:
        if st.button("🔍 תצוגה מקדימה", key="preview_guards"):
            if names_input.strip():
                names = [n.strip() for n in names_input.replace("،",",").split(",") if n.strip()]
                existing = get_guards()["name"].tolist() if not get_guards().empty else []
                new_names = [n for n in names if n not in existing]
                if new_names:
                    st.success(f"יתווספו: {', '.join(new_names)}")
                else:
                    st.warning("כל השמות כבר קיימים")
    with col_add:
        st.markdown('<div class="success-btn">', unsafe_allow_html=True)
        if st.button("➕ הוסף לרשימה", key="add_guards"):
            if names_input.strip():
                added = add_guards_bulk(names_input)
                st.success(f"✅ נוספו {added} שומרים")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1e2d45;margin:16px 0'>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">👥 שומרים רשומים</div>', unsafe_allow_html=True)

    guards_df = get_guards()
    if guards_df.empty:
        st.info("אין שומרים ברשימה")
    else:
        st.markdown(f"<div style='color:#64748b;font-size:13px;margin-bottom:10px'>{len(guards_df)} שומרים</div>", unsafe_allow_html=True)
        for _, row in guards_df.iterrows():
            gc1, gc2, gc3 = st.columns([1, 3, 1])
            with gc1:
                st.markdown(f"""
                <div style="width:36px;height:36px;border-radius:50%;
                background:linear-gradient(135deg,#3b82f6,#6366f1);
                display:flex;align-items:center;justify-content:center;
                font-weight:800;font-size:14px;color:white">
                {row['name'][0]}</div>""", unsafe_allow_html=True)
            with gc2:
                # Inline edit
                new_name = st.text_input("", value=row["name"], key=f"gname_{row['id']}",
                                          label_visibility="collapsed")
                if new_name != row["name"] and new_name.strip():
                    conn = get_db()
                    try:
                        conn.execute("UPDATE guards SET name=? WHERE id=?", (new_name.strip(), row["id"]))
                        # Also update shifts
                        shifts_all = conn.execute("SELECT id, guards FROM shifts").fetchall()
                        for sid, sg in shifts_all:
                            updated = ",".join([
                                new_name.strip() if g.strip() == row["name"] else g.strip()
                                for g in sg.split(",")
                            ])
                            conn.execute("UPDATE shifts SET guards=? WHERE id=?", (updated, sid))
                        conn.commit()
                    except:
                        pass
                    conn.close()
            with gc3:
                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                if st.button("✕", key=f"del_g_{row['id']}"):
                    delete_guard(row["id"])
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    all_shifts = get_shifts("all")
    guards_df  = get_guards()

    total_shifts = len(all_shifts)
    total_mins   = all_shifts["duration"].sum() if not all_shifts.empty else 0
    total_hrs    = round(total_mins / 60, 1)

    # Summary stats
    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{total_shifts}</div><div class="stat-label">סה"כ משמרות</div></div>', unsafe_allow_html=True)
    with scol2:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{total_hrs}</div><div class="stat-label">סה"כ שעות</div></div>', unsafe_allow_html=True)
    with scol3:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{len(guards_df)}</div><div class="stat-label">שומרים רשומים</div></div>', unsafe_allow_html=True)
    with scol4:
        active = 0
        if not all_shifts.empty and not guards_df.empty:
            active = sum(1 for n in guards_df["name"] if any(
                n in (r["guards"] or "") for _, r in all_shifts.iterrows()
            ))
        st.markdown(f'<div class="stat-box"><div class="stat-num">{active}</div><div class="stat-label">שומרים פעילים</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin:20px 0 10px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">שעות לפי שומר</div>', unsafe_allow_html=True)

    if all_shifts.empty or guards_df.empty:
        st.info("אין נתונים עדיין")
    else:
        guard_stats = []
        for _, g in guards_df.iterrows():
            name = g["name"]
            mins = 0
            count = 0
            for _, s in all_shifts.iterrows():
                guard_list = [x.strip() for x in (s["guards"] or "").split(",")]
                if name in guard_list:
                    mins += s["duration"]
                    count += 1
            if mins > 0:
                guard_stats.append({
                    "שם": name,
                    "משמרות": count,
                    "שעות": round(mins / 60, 1),
                    "דקות": mins
                })

        if guard_stats:
            stats_df = pd.DataFrame(guard_stats).sort_values("דקות", ascending=False).reset_index(drop=True)
            max_mins = stats_df["דקות"].max()

            for _, row in stats_df.iterrows():
                pct = int(row["דקות"] / max_mins * 100) if max_mins > 0 else 0
                st.markdown(f"""
                <div style="background:#1a2236;border:1px solid #1e2d45;border-radius:10px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:12px">
                  <div style="min-width:90px;font-size:14px;font-weight:600">{row['שם']}</div>
                  <div style="flex:1;height:8px;background:#222e45;border-radius:4px;overflow:hidden">
                    <div style="width:{pct}%;height:100%;background:linear-gradient(90deg,#3b82f6,#6366f1);border-radius:4px"></div>
                  </div>
                  <div style="min-width:60px;text-align:left;font-size:13px;font-weight:700;color:#3b82f6;background:rgba(59,130,246,0.1);padding:3px 10px;border-radius:10px">{row['שעות']}ש'</div>
                  <div style="font-size:12px;color:#64748b">{row['משמרות']} משמרות</div>
                </div>
                """, unsafe_allow_html=True)

            # Full table
            st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
            display_df = stats_df[["שם", "משמרות", "שעות"]].copy()
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("אין שומרים עם משמרות משובצות")
