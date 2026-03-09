import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# הגדרות דף
st.set_page_config(page_title="ניהול שמירות", layout="wide")

# --- CSS מקצועי לתיקון ירידת שורות ועיצוב מובייל ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Assistant', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* תיקון קריטי: מניעת ירידת שורה ברשימת שומרים */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 5px !important;
    }
    
    /* הפיכת כפתורי המחיקה/שמירה לקטנים וצמודים */
    .stButton button {
        padding: 2px 10px !important;
        height: auto !important;
        min-width: 40px !important;
    }

    /* עיצוב רשימות נגללות */
    .scroll-area {
        max-height: 350px;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        background: #f9f9f9;
    }

    /* עיצוב כותרות ופקדים */
    .stSelectbox label, .stTimeInput label, .stDateInput label {
        font-weight: bold !important;
        color: #ff4b4b !important;
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

# חישוב סטטיסטיקה (כמות שמירות לכל שומר)
def get_stats():
    shifts = get_shifts()
    guards = get_guards()
    counts = {}
    for name in guards['name']:
        counts[name] = 0
    for names_str in shifts['names']:
        for n in names_str.split(', '):
            counts[n.strip()] = counts.get(n.strip(), 0) + 1
    return counts

# --- טאבים ---
tab1, tab2, tab3 = st.tabs(["⚡ שיבוץ מהיר", "👥 ניהול שומרים", "📊 סטטיסטיקה"])

# --- טאב 1: שיבוץ מהיר ---
with tab1:
    st.subheader("📅 הגדרת משמרת")
    
    col_d, col_t = st.columns(2)
    with col_d:
        chosen_date = st.date_input("בחר יום", datetime.now())
    with col_t:
        chosen_time = st.time_input("שעת התחלה", datetime.now().replace(minute=0))
    
    col_dur, col_num = st.columns(2)
    with col_dur:
        duration = st.selectbox("משך משמרת (דקות)", [30, 45, 60, 90, 120, 180], index=2)
    with col_num:
        num_per_shift = st.number_input("שומרים בעמדה", 1, 5, 2)

    # הצגת כמות שמירות ליד השם בבחירה
    stats = get_stats()
    guards_options = [f"{name} ({stats[name]})" for name in get_guards()['name']]
    
    selected_raw = st.multiselect("חפש ובחר שומרים:", options=guards_options)
    
    if st.button("➕ שבץ למשמרת הבאה", use_container_width=True, type="primary"):
        if selected_raw:
            selected_names = [s.split(' (')[0] for s in selected_raw]
            shifts_df = get_shifts()
            
            if not shifts_df.empty:
                next_start = datetime.strptime(shifts_df.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S')
            else:
                next_start = datetime.combine(chosen_date, chosen_time)
            
            next_end = next_start + timedelta(minutes=duration)
            names_str = ", ".join(selected_names)
            
            c = conn.cursor()
            c.execute("INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                      (next_start.strftime('%Y-%m-%d %H:%M:%S'), next_end.strftime('%Y-%m-%d %H:%M:%S'), names_str))
            conn.commit()
            st.rerun()

    st.markdown("---")
    st.markdown('### 🕒 לו"ז נוכחי')
    st.markdown('<div class="scroll-area">', unsafe_allow_html=True)
    shifts_df = get_shifts()
    for idx, row in shifts_df.iterrows():
        s = row['start_time'][11:16]
        e = row['end_time'][11:16]
        col_view, col_del = st.columns([4, 1])
        col_view.write(f"**{s}-{e}** | {row['names']}")
        if col_del.button("🗑️", key=f"del_sh_{row['id']}"):
            conn.cursor().execute("DELETE FROM shifts WHERE id = ?", (row['id'],))
            conn.commit()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if not shifts_df.empty:
        msg = "📋 *סידור שמירה:*\n"
        for _, r in shifts_df.iterrows():
            msg += f"• {r['start_time'][11:16]}-{r['end_time'][11:16]}: {r['names']}\n"
        st.link_button("📲 שלח בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

# --- טאב 2: ניהול שומרים ---
with tab2:
    st.subheader("👥 רשימת שומרים")
    
    with st.expander("➕ הוספה מרובה"):
        bulk = st.text_area("הכנס שמות (מופרדים בפסיק):")
        if st.button("שמור הכל"):
            for n in [x.strip() for x in bulk.split(',') if x.strip()]:
                conn.cursor().execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (n,))
            conn.commit()
            st.rerun()

    st.markdown('<div class="scroll-area">', unsafe_allow_html=True)
    guards_df = get_guards()
    for _, row in guards_df.iterrows():
        # שימוש ב-3 עמודות קבועות ללא ירידת שורה
        c_name, c_save, c_del = st.columns([3, 0.8, 0.8])
        with c_name:
            new_n = st.text_input("שם", value=row['name'], key=f"n_{row['id']}", label_visibility="collapsed")
        with c_save:
            if st.button("💾", key=f"sv_{row['id']}"):
                conn.cursor().execute("UPDATE guards SET name = ? WHERE id = ?", (new_n, row['id']))
                conn.commit()
                st.rerun()
        with c_del:
            if st.button("🗑️", key=f"dl_{row['id']}"):
                conn.cursor().execute("DELETE FROM guards WHERE name = ?", (row['name'],))
                conn.commit()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- טאב 3: סטטיסטיקה ---
with tab3:
    st.subheader("📊 סיכום שמירות לכל שומר")
    counts = get_stats()
    if counts:
        df_counts = pd.DataFrame(list(counts.items()), columns=['שם השומר', 'כמות שמירות']).sort_values(by='כמות שמירות', ascending=False)
        st.dataframe(df_counts, use_container_width=True, hide_index=True)
        st.bar_chart(df_counts.set_index('שם השומר'))
    else:
        st.info("אין נתונים להצגה")
