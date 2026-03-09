import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# הגדרות דף ו-CSS עבור עברית (RTL)
st.set_page_config(page_title="ניהול שמירות", layout="wide")

# הזרקת CSS לימין לשמאל ותצוגה מותאמת לנייד
st.markdown("""
    <style>
    .reportview-container .main .block-container { direction: rtl; }
    div[data-testid="stVerticalBlock"] > div { direction: rtl; }
    .stButton button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    p, h1, h2, h3, h4, label, span { text-align: right; direction: rtl; }
    /* עיצוב כפתורי שומרים שייראו טוב בנייד */
    div.stButton > button:first-child {
        background-color: #f0f2f6;
        color: #31333F;
    }
    </style>
    """, unsafe_allow_html=True)

# --- פונקציות מסד נתונים עם תמיכה ב-Volume ---
def init_db():
    # הגדרת נתיב מסד הנתונים - בודק אם תיקיית ה-Volume קיימת ב-Railway
    db_dir = '/app/data'
    if os.path.exists(db_dir):
        db_path = os.path.join(db_dir, 'guard_system.db')
    else:
        # עבודה מקומית (במחשב שלך)
        db_path = 'guard_system.db'
        
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # יצירת טבלאות אם לא קיימות
    c.execute('''CREATE TABLE IF NOT EXISTS guards (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY, start_time TEXT, end_time TEXT, names TEXT)''')
    conn.commit()
    return conn

# יצירת חיבור גלובלי
conn = init_db()

def get_guards():
    return pd.read_sql_query("SELECT name FROM guards ORDER BY name ASC", conn)['name'].tolist()

def get_shifts():
    return pd.read_sql_query("SELECT * FROM shifts ORDER BY start_time ASC", conn)

# --- ממשק משתמש ---

tab1, tab2, tab3 = st.tabs(["📋 ניהול משמרות", "👥 רשימת שומרים", "📊 סטטיסטיקה"])

# --- טאב 1: ניהול משמרות ---
with tab1:
    st.header("שיבוץ משמרת")
    
    col1, col2 = st.columns(2)
    with col1:
        base_date = st.date_input("תאריך", datetime.now())
    with col2:
        duration = st.selectbox("משך (דקות)", [30, 45, 60, 90, 120, 180, 240], index=2)
    
    base_time = st.time_input("שעת התחלה (למשמרת ראשונה)", datetime.now().replace(minute=0))
    
    st.subheader("לחץ על שם לשבוץ:")
    all_guards = get_guards()
    
    # חישוב זמן התחלה אוטומטי למשמרת הבאה
    shifts_df = get_shifts()
    if not shifts_df.empty:
        last_end_str = shifts_df.iloc[-1]['end_time']
        next_start = datetime.strptime(last_end_str, '%Y-%m-%d %H:%M:%S')
    else:
        next_start = datetime.combine(base_date, base_time)

    # הצגת כפתורי שומרים בגריד של 3 עמודות לנייד
    if all_guards:
        grid = st.columns(3)
        for idx, name in enumerate(all_guards):
            if grid[idx % 3].button(name, key=f"assign_{name}"):
                end_time = next_start + timedelta(minutes=duration)
                c = conn.cursor()
                c.execute("INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                          (next_start.strftime('%Y-%m-%d %H:%M:%S'), 
                           end_time.strftime('%Y-%m-%d %H:%M:%S'), name))
                conn.commit()
                st.rerun() # רענון בטוח אחרי לחיצה
    else:
        st.info("רשימת השומרים ריקה. הוסף שומרים בטאב המתאים.")

    st.divider()
    
    if not shifts_df.empty:
        st.subheader("לו"ז נוכחי")
        # עיבוד התאריכים לתצוגה יפה
        display_df = shifts_df.copy()
        display_df['זמן'] = display_df.apply(lambda r: 
            f"{datetime.strptime(r['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')} - "
            f"{datetime.strptime(r['end_time'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')}", axis=1)
        
        st.table(display_df[['זמן', 'names']].rename(columns={'names': 'שומר'}))
        
        col_actions = st.columns(2)
        if col_actions[0].button("🗑️ מחק משמרת אחרונה"):
            conn.cursor().execute("DELETE FROM shifts WHERE id = (SELECT MAX(id) FROM shifts)")
            conn.commit()
            st.rerun()
            
        if col_actions[1].button("🧹 נקה הכל"):
            conn.cursor().execute("DELETE FROM shifts")
            conn.commit()
            st.rerun()

        # כפתור וואטסאפ
        msg = "📋 *סידור שמירה:*\n"
        for _, row in display_df.iterrows():
            msg += f"• {row['זמן']}: {row['names']}\n"
        
        encoded_msg = urllib.parse.quote(msg)
        st.markdown(f'''
            <a href="https://wa.me/?text={encoded_msg}" target="_blank">
                <button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:10px; font-weight:bold; cursor:pointer;">
                    📲 שלח בוואטסאפ
                </button>
            </a>
            ''', unsafe_allow_html=True)

# --- טאב 2: רשימת שומרים ---
with tab2:
    st.header("ניהול שומרים")
    
    raw_input = st.text_area("הוסף שמות (מופרדים בפסיק):", placeholder="שלמה מארק, טל אבלין, זיו יוספי...")
    if st.button("הוסף לרשימה"):
        if raw_input:
            names = [n.strip() for n in raw_input.split(',') if n.strip()]
            c = conn.cursor()
            for n in names:
                c.execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (n,))
            conn.commit()
            st.success(f"נוספו {len(names)} שומרים")
            st.rerun()

    st.subheader("שומרים רשומים:")
    guards = get_guards()
    for g in guards:
        c1, c2 = st.columns([4, 1])
        c1.write(g)
        if c2.button("🗑️", key=f"del_guard_{g}"):
            conn.cursor().execute("DELETE FROM guards WHERE name = ?", (g,))
            conn.commit()
            st.rerun()

# --- טאב 3: סטטיסטיקה ---
with tab3:
    st.header("סטטיסטיקה")
    if not shifts_df.empty:
        stats = {}
        for _, row in shifts_df.iterrows():
            s = datetime.strptime(row['start_time'], '%Y-%m-%d %H:%M:%S')
            e = datetime.strptime(row['end_time'], '%Y-%m-%d %H:%M:%S')
            duration_hr = (e - s).total_seconds() / 3600
            stats[row['names']] = stats.get(row['names'], 0) + duration_hr
        
        stat_data = pd.DataFrame(list(stats.items()), columns=['שם', 'סה"כ שעות'])
        st.bar_chart(stat_data.set_index('שם'))
        st.table(stat_data.sort_values(by='סה"כ שעות', ascending=False))
    else:
        st.info("אין מספיק נתונים להצגת סטטיסטיקה.")
