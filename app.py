import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# הגדרות דף
st.set_page_config(page_title="ניהול שמירות", layout="wide")

# הזרקת CSS לימין לשמאל (RTL) ותצוגה מותאמת לנייד
st.markdown("""
    <style>
    .reportview-container .main .block-container { direction: rtl; }
    div[data-testid="stVerticalBlock"] > div { direction: rtl; }
    .stButton button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; margin-bottom: 5px; }
    p, h1, h2, h3, h4, label, span { text-align: right; direction: rtl; }
    /* שיפור תצוגת טבלאות בנייד */
    .stTable { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול מסד נתונים (Persistence) ---
def init_db():
    # בדיקה אם קיים Volume ב-Railway
    db_dir = '/app/data'
    if os.path.exists(db_dir):
        db_path = os.path.join(db_dir, 'guard_system.db')
    else:
        db_path = 'guard_system.db'
        
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS guards (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY, start_time TEXT, end_time TEXT, names TEXT)''')
    conn.commit()
    return conn

conn = init_db()

def get_guards():
    return pd.read_sql_query("SELECT name FROM guards ORDER BY name ASC", conn)['name'].tolist()

def get_shifts():
    return pd.read_sql_query("SELECT * FROM shifts ORDER BY start_time ASC", conn)

# --- ממשק הטאבים ---
tab1, tab2, tab3 = st.tabs(["📅 ניהול משמרות", "👥 רשימת שומרים", "📊 סטטיסטיקה"])

# --- טאב 1: ניהול משמרות ---
with tab1:
    st.header("שיבוץ משמרות")
    
    col_config1, col_config2 = st.columns(2)
    with col_config1:
        base_date = st.date_input("תאריך התחלה", datetime.now())
        num_guards_per_shift = st.number_input("שומרים במשמרת", min_value=1, max_value=5, value=1)
    with col_config2:
        duration = st.selectbox("משך משמרת (דקות)", [30, 45, 60, 90, 120, 180], index=2)
        base_time = st.time_input("שעת התחלה ראשונה", datetime.now().replace(minute=0, second=0, microsecond=0))

    st.subheader("בחר שומר לשיבוץ:")
    guards = get_guards()
    
    # חישוב זמן התחלה אוטומטי
    current_shifts = get_shifts()
    if not current_shifts.empty:
        last_end_str = current_shifts.iloc[-1]['end_time']
        # בדיקה אם שובצו כבר מספיק שומרים לאותה משמרת
        last_start_str = current_shifts.iloc[-1]['start_time']
        count_last_slot = len(current_shifts[current_shifts['start_time'] == last_start_str])
        
        if count_last_slot < num_guards_per_shift:
            next_start = datetime.strptime(last_start_str, '%Y-%m-%d %H:%M:%S')
        else:
            next_start = datetime.strptime(last_end_str, '%Y-%m-%d %H:%M:%S')
    else:
        next_start = datetime.combine(base_date, base_time)

    # כפתורי שומרים (גריד)
    if guards:
        cols = st.columns(3)
        for idx, name in enumerate(guards):
            if cols[idx % 3].button(name, key=f"btn_{name}"):
                next_end = next_start + timedelta(minutes=duration)
                c = conn.cursor()
                c.execute("INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                          (next_start.strftime('%Y-%m-%d %H:%M:%S'), 
                           next_end.strftime('%Y-%m-%d %H:%M:%S'), name))
                conn.commit()
                st.rerun()
    else:
        st.warning("לא נמצאו שומרים. הוסף אותם בטאב רשימת שומרים.")

    st.divider()
    
    if not current_shifts.empty:
        st.subheader('לו"ז נוכחי')
        
        # תצוגה נקייה של הטבלה
        df_display = current_shifts.copy()
        df_display['זמן'] = df_display.apply(lambda r: 
            f"{datetime.strptime(r['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')} - "
            f"{datetime.strptime(r['end_time'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')}", axis=1)
        
        st.table(df_display[['זמן', 'names']].rename(columns={'names': 'שם השומר'}))
        
        # כפתורי פעולה
        c1, c2 = st.columns(2)
        if c1.button("🗑️ מחק משמרת אחרונה"):
            conn.cursor().execute("DELETE FROM shifts WHERE id = (SELECT MAX(id) FROM shifts)")
            conn.commit()
            st.rerun()
        if c2.button("🧹 נקה הכל"):
            conn.cursor().execute("DELETE FROM shifts")
            conn.commit()
            st.rerun()

        # שיתוף בוואטסאפ
        summary = "📋 *סידור שמירה:*\n"
        for _, row in df_display.iterrows():
            summary += f"• {row['זמן']}: {row['names']}\n"
        
        whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(summary)}"
        st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; width:100%; border:none; padding:15px; border-radius:10px; font-weight:bold;">📲 שלח סידור בוואטסאפ</button></a>', unsafe_allow_html=True)

# --- טאב 2: רשימת שומרים ---
with tab2:
    st.header("ניהול רשימת שומרים")
    
    bulk_input = st.text_area("הוסף שמות (מופרדים בפסיק):", placeholder="ישראל ישראלי, פלוני אלמוני...")
    if st.button("הוסף שומרים"):
        if bulk_input:
            new_names = [n.strip() for n in bulk_input.split(',') if n.strip()]
            c = conn.cursor()
            for name in new_names:
                c.execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (name,))
            conn.commit()
            st.success(f"נוספו {len(new_names)} שומרים בהצלחה!")
            st.rerun()

    st.subheader("שומרים קיימים:")
    current_guards = get_guards()
    for g in current_guards:
        gc1, gc2 = st.columns([4, 1])
        gc1.write(g)
        if gc2.button("❌", key=f"del_{g}"):
            conn.cursor().execute("DELETE FROM guards WHERE name = ?", (g,))
            conn.commit()
            st.rerun()

# --- טאב 3: סטטיסטיקה ---
with tab3:
    st.header("סיכום שעות")
    if not current_shifts.empty:
        stats = {}
        for _, row in current_shifts.iterrows():
            start = datetime.strptime(row['start_time'], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(row['end_time'], '%Y-%m-%d %H:%M:%S')
            duration_hrs = (end - start).total_seconds() / 3600
            stats[row['names']] = stats.get(row['names'], 0) + duration_hrs
        
        stats_df = pd.DataFrame(list(stats.items()), columns=['שם', 'שעות']).sort_values(by='שעות', ascending=False)
        st.bar_chart(stats_df.set_index('שם'))
        st.table(stats_df)
    else:
        st.info("אין נתונים להצגה עדיין.")
