import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# הגדרות דף
st.set_page_config(page_title="ניהול שמירות פרו", layout="wide")

# --- CSS מקצועי לתיקון תצוגה, טבלאות וחלוקה לימים ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Assistant', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* עיצוב כותרת יום */
    .day-header {
        background-color: #f0f2f6;
        padding: 8px 15px;
        border-radius: 8px;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
        color: #1f77b4;
        border-right: 5px solid #1f77b4;
    }

    /* טבלת משמרות נקייה למובייל */
    .shift-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 10px;
    }
    .shift-table td {
        padding: 12px 8px;
        border-bottom: 1px solid #eee;
        vertical-align: middle;
    }
    .time-col { font-weight: bold; width: 30%; color: #333; }
    .names-col { width: 70%; color: #555; }

    /* תיקון פקדי קלט */
    .stMultiSelect span { white-space: normal !important; }
    .stButton button { width: 100%; border-radius: 10px; height: 3em; }
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
    st.subheader("📅 הגדרות משמרת")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        chosen_date = st.date_input("תאריך התחלה", datetime.now())
        duration = st.selectbox("משך משמרת (דקות)", [30, 45, 60, 90, 120, 180], index=2)
    with col_t2:
        chosen_time = st.time_input("שעת התחלה", datetime.now().replace(minute=0, second=0))
        num_per_shift = st.number_input("שומרים בעמדה", 1, 5, 2)

    stats = get_stats()
    guards_df = get_guards()
    options = [f"{r['name']} ({stats.get(r['name'], 0)})" for _, r in guards_df.iterrows()]
    selected_raw = st.multiselect("בחר שומרים:", options=options)
    
    if st.button("🚀 שבץ למשמרת הבאה", type="primary"):
        if selected_raw:
            selected_names = [s.split(' (')[0] for s in selected_raw]
            all_shifts = get_shifts()
            
            if not all_shifts.empty:
                next_start = datetime.strptime(all_shifts.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S')
            else:
                next_start = datetime.combine(chosen_date, chosen_time)
            
            next_end = next_start + timedelta(minutes=duration)
            
            c = conn.cursor()
            c.execute("INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                      (next_start.strftime('%Y-%m-%d %H:%M:%S'), 
                       next_end.strftime('%Y-%m-%d %H:%M:%S'), ", ".join(selected_names)))
            conn.commit()
            st.rerun()

    st.divider()
    st.subheader('🕒 לו"ז נוכחי')
    
    shifts_df = get_shifts()
    if not shifts_df.empty:
        # חלוקה לקבוצות לפי ימים
        shifts_df['date'] = shifts_df['start_time'].apply(lambda x: x[:10])
        unique_days = shifts_df['date'].unique()

        for day in unique_days:
            # המרת תאריך לפורמט יפה (למשל: 09/03/2026)
            nice_date = datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m/%Y')
            st.markdown(f'<div class="day-header">📅 יום {nice_date}</div>', unsafe_allow_html=True)
            
            day_shifts = shifts_df[shifts_df['date'] == day]
            
            # בניית טבלה לכל יום
            table_html = '<table class="shift-table">'
            for _, row in day_shifts.iterrows():
                s = row['start_time'][11:16]
                e = row['end_time'][11:16]
                table_html += f'<tr><td class="time-col">{s}-{e}</td><td class="names-col">{row["names"]}</td></tr>'
            table_html += '</table>'
            st.write(table_html, unsafe_allow_html=True)

        if st.button("🗑️ מחק משמרת אחרונה"):
            conn.cursor().execute("DELETE FROM shifts WHERE id = (SELECT MAX(id) FROM shifts)")
            conn.commit()
            st.rerun()

        # וואטסאפ
        summary = "📋 *סידור שמירה מעודכן:*\n"
        for day in unique_days:
            nice_date = datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m')
            summary += f"\n🗓️ *יום {nice_date}:*\n"
            day_shifts = shifts_df[shifts_df['date'] == day]
            for _, r in day_shifts.iterrows():
                summary += f"• {r['start_time'][11:16]}-{r['end_time'][11:16]}: {r['names']}\n"
        
        st.link_button("📲 שלח סידור בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(summary)}")
    else:
        st.info("אין משמרות משובצות.")

# --- טאב 2: ניהול צוות ---
with tab2:
    st.subheader("👥 ניהול צוות")
    with st.expander("➕ הוספת שומרים"):
        bulk = st.text_area("הכנס שמות מופרדים בפסיק:")
        if st.button("שמור"):
            for n in [x.strip() for x in bulk.split(',') if x.strip()]:
                conn.cursor().execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (n,))
            conn.commit()
            st.rerun()

    g_list = get_guards()
    for _, row in g_list.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            name_val = st.text_input("שם", value=row['name'], key=f"e_{row['id']}", label_visibility="collapsed")
        with c2:
            if st.button("💾", key=f"s_{row['id']}"):
                conn.cursor().execute("UPDATE guards SET name = ? WHERE id = ?", (name_val, row['id']))
                conn.commit()
                st.rerun()
        with c3:
            if st.button("🗑️", key=f"d_{row['id']}"):
                conn.cursor().execute("DELETE FROM guards WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()

# --- טאב 3: סטטיסטיקה ---
with tab3:
    st.subheader("📊 סיכום שמירות")
    current_stats = get_stats()
    if current_stats:
        final_df = pd.DataFrame(list(current_stats.items()), columns=['שומר', 'כמות שמירות']).sort_values(by='כמות שמירות', ascending=False)
        st.table(final_df)
        st.bar_chart(final_df.set_index('שומר'))
