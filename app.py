import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# הגדרות דף
st.set_page_config(page_title="ניהול שמירות פרו", layout="wide")

# --- CSS מקצועי לתיקון ירידת שורות ועיצוב מובייל ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Assistant', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* תיקון קריטי למובייל: מניעת ירידת שורה בכל מחיר */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 8px !important;
    }
    
    /* הפיכת שדות טקסט וכפתורים לקטנים יותר שייכנסו בשורה */
    .stTextInput dict, .stTextInput input {
        min-width: 100px !important;
    }
    
    .stButton button {
        padding: 5px 10px !important;
        min-width: 45px !important;
        height: 38px !important;
    }

    /* תיבת גלילה לרשימות */
    .scroll-area {
        max-height: 380px;
        overflow-y: auto;
        border: 1px solid #eee;
        border-radius: 12px;
        padding: 12px;
        background: #fdfdfd;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);
    }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול מסד נתונים ---
def init_db():
    db_dir = '/app/data'
    db_path = os.path.join(db_dir, 'guard_system.db') if os.path.exists(db_dir) else 'guard_system.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS guards (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY, start_time TEXT, end_time TEXT, names TEXT)''')
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
            if n.strip() in counts:
                counts[n.strip()] += 1
    return counts

# --- טאבים ---
tab1, tab2, tab3 = st.tabs(["⚡ שיבוץ", "👥 צוות", "📊 סטטיסטיקה"])

# --- טאב 1: שיבוץ ---
with tab1:
    st.markdown("### 📅 הגדרות משמרת")
    
    c1, c2 = st.columns(2)
    with c1:
        chosen_date = st.date_input("תאריך", datetime.now())
        duration = st.selectbox("משך (דקות)", [30, 45, 60, 90, 120, 180, 240], index=2)
    with c2:
        chosen_time = st.time_input("שעת התחלה", datetime.now().replace(minute=0, second=0, microsecond=0))
        num_per_shift = st.number_input("שומרים בעמדה", 1, 5, 1)

    # הצגת כמות שמירות ליד השם בבחירה
    stats = get_stats()
    guards_list = get_guards()['name'].tolist()
    guards_options = [f"{name} ({stats.get(name, 0)})" for name in guards_list]
    
    selected_raw = st.multiselect("בחר שומרים:", options=guards_options)
    
    if st.button("🚀 שבץ למשמרת", use_container_width=True, type="primary"):
        if selected_raw:
            selected_names = [s.split(' (')[0] for s in selected_raw]
            shifts_df = get_shifts()
            
            # לוגיקת זמן: אם יש משמרות, המשך מהאחרונה. אם לא, קח מהפקד.
            if not shifts_df.empty:
                next_start = datetime.strptime(shifts_df.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S')
            else:
                next_start = datetime.combine(chosen_date, chosen_time)
            
            next_end = next_start + timedelta(minutes=duration)
            
            c = conn.cursor()
            c.execute("INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                      (next_start.strftime('%Y-%m-%d %H:%M:%S'), 
                       next_end.strftime('%Y-%m-%d %H:%M:%S'), ", ".join(selected_names)))
            conn.commit()
            st.rerun()

    st.markdown('### 🕒 לו"ז נוכחי')
    st.markdown('<div class="scroll-area">', unsafe_allow_html=True)
    shifts_data = get_shifts()
    for _, row in shifts_data.iterrows():
        sc1, sc2 = st.columns([4, 1])
        with sc1:
            st.write(f"**{row['start_time'][11:16]}-{row['end_time'][11:16]}** | {row['names']}")
        with sc2:
            if st.button("🗑️", key=f"s_del_{row['id']}"):
                conn.cursor().execute("DELETE FROM shifts WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if not shifts_data.empty:
        msg = "📋 *סידור שמירה מעודכן:*\n"
        for _, r in shifts_data.iterrows():
            msg += f"• {r['start_time'][11:16]}-{r['end_time'][11:16]}: {r['names']}\n"
        st.link_button("📲 שלח בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

# --- טאב 2: ניהול שומרים ---
with tab2:
    st.markdown("### 👥 ניהול צוות")
    with st.expander("➕ הוספה מרובה"):
        bulk = st.text_area("שמות (מופרדים בפסיק):")
        if st.button("שמור שומרים"):
            for n in [x.strip() for x in bulk.split(',') if x.strip()]:
                conn.cursor().execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (n,))
            conn.commit()
            st.rerun()

    st.markdown('<div class="scroll-area">', unsafe_allow_html=True)
    g_df = get_guards()
    for _, row in g_df.iterrows():
        # עמודות צמודות למניעת ירידת שורה
        gc1, gc2, gc3 = st.columns([3, 0.7, 0.7])
        with gc1:
            new_name = st.text_input("שם", value=row['name'], key=f"inp_{row['id']}", label_visibility="collapsed")
        with gc2:
            if st.button("💾", key=f"sv_{row['id']}"):
                conn.cursor().execute("UPDATE guards SET name = ? WHERE id = ?", (new_name, row['id']))
                conn.commit()
                st.rerun()
        with gc3:
            if st.button("🗑️", key=f"dl_{row['id']}"):
                conn.cursor().execute("DELETE FROM guards WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- טאב 3: סטטיסטיקה ---
with tab3:
    st.markdown("### 📊 נתוני שמירה")
    current_stats = get_stats()
    if current_stats:
        stat_df = pd.DataFrame(list(current_stats.items()), columns=['שומר', 'סה"כ שמירות']).sort_values(by='סה"כ שמירות', ascending=False)
        st.dataframe(stat_df, use_container_width=True, hide_index=True)
        st.bar_chart(stat_df.set_index('שומר'))
    else:
        st.info("אין נתונים")
