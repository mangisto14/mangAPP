import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# הגדרות דף
st.set_page_config(page_title="GuardMaster", layout="wide")

# --- עיצוב מודרני מותאם למובייל (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Assistant', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* עיצוב כרטיסיות (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        font-weight: bold;
    }

    /* תיבת רשימה נגללת עם גלילה פנימית */
    .scroll-container {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 15px;
        background-color: #ffffff;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }

    /* עיצוב שורת שומר ברשימה */
    .guard-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px;
        border-bottom: 1px solid #eee;
    }

    /* כפתורים מודרניים */
    .stButton button {
        border-radius: 8px;
        transition: all 0.3s;
    }
    
    .whatsapp-btn {
        background-color: #25D366 !important;
        color: white !important;
        font-weight: bold !important;
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

# פונקציות שליפה
def get_guards():
    return pd.read_sql_query("SELECT * FROM guards ORDER BY name ASC", conn)

def get_shifts():
    return pd.read_sql_query("SELECT * FROM shifts ORDER BY start_time ASC", conn)

# --- לוגיקה ---
tab1, tab2, tab3 = st.tabs(["⚡ שיבוץ מהיר", "👥 ניהול צוות", "📊 דוח שעות"])

# --- טאב 1: שיבוץ מהיר (עיצוב מודרני + חיפוש) ---
with tab1:
    st.markdown("### 📅 יצירת משמרת")
    
    # חישוב זמן התחלה אוטומטי
    shifts_df = get_shifts()
    guards_list = get_guards()['name'].tolist()

    with st.container():
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            duration = st.select_slider("משך משמרת (דקות)", options=[30, 45, 60, 90, 120, 180, 240], value=60)
        with col_t2:
            num_per_shift = st.number_input("שומרים בעמדה", 1, 5, 1)

        # פקד רשימה עם חיפוש (Selectbox)
        selected_guards = st.multiselect("חפש ובחר שומרים למשמרת:", options=guards_list)

        if st.button("➕ שבץ למשמרת הבאה", use_container_width=True, type="primary"):
            if selected_guards:
                # לוגיקת זמן
                if not shifts_df.empty:
                    next_start = datetime.strptime(shifts_df.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S')
                else:
                    next_start = datetime.now().replace(minute=0, second=0, microsecond=0)
                
                next_end = next_start + timedelta(minutes=duration)
                guard_names = ", ".join(selected_guards)
                
                c = conn.cursor()
                c.execute("INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                          (next_start.strftime('%Y-%m-%d %H:%M:%S'), 
                           next_end.strftime('%Y-%m-%d %H:%M:%S'), guard_names))
                conn.commit()
                st.rerun()
            else:
                st.error("בחר לפחות שומר אחד מהרשימה")

    st.markdown("---")
    st.markdown('### 🕒 לו"ז נוכחי')
    
    # מסגרת גלילה לרשימת המשמרות
    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
    if not shifts_df.empty:
        for idx, row in shifts_df.iterrows():
            s = datetime.strptime(row['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            e = datetime.strptime(row['end_time'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            st.markdown(f"**{s} - {e}** | 🛡️ {row['names']}")
            if st.button(f"מחק {idx}", key=f"del_shift_{row['id']}", help="מחק משמרת"):
                conn.cursor().execute("DELETE FROM shifts WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
    else:
        st.write("אין משמרות משובצות")
    st.markdown('</div>', unsafe_allow_html=True)

    # וואטסאפ
    if not shifts_df.empty:
        msg = "📋 *סידור שמירה מעודכן:*\n"
        for _, r in shifts_df.iterrows():
            msg += f"• {r['start_time'][11:16]}-{r['end_time'][11:16]}: {r['names']}\n"
        st.link_button("📲 שלח בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)

# --- טאב 2: ניהול שומרים (עריכה ומחיקה בשורה אחת) ---
with tab2:
    st.markdown("### 👥 ניהול שומרים")
    
    with st.expander("➕ הוספה מרובה"):
        bulk = st.text_area("הדבק שמות מופרדים בפסיק:")
        if st.button("שמור רשימה"):
            names = [n.strip() for n in bulk.split(',') if n.strip()]
            for n in names:
                conn.cursor().execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (n,))
            conn.commit()
            st.rerun()

    st.markdown('### רשימת שומרים (גלילה)')
    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
    guards_df = get_guards()
    
    for _, row in guards_df.iterrows():
        col_name, col_edit, col_del = st.columns([3, 1, 1])
        
        # תצוגת שם / עריכה
        with col_name:
            new_name = st.text_input(f"שם", value=row['name'], key=f"edit_val_{row['id']}", label_visibility="collapsed")
        
        with col_edit:
            if st.button("💾", key=f"save_{row['id']}", help="שמור שינוי"):
                conn.cursor().execute("UPDATE guards SET name = ? WHERE id = ?", (new_name, row['id']))
                conn.commit()
                st.rerun()
        
        with col_del:
            if st.button("🗑️", key=f"del_{row['id']}", help="מחק שומר"):
                conn.cursor().execute("DELETE FROM guards WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- טאב 3: סטטיסטיקה ---
with tab3:
    st.markdown("### 📊 דוח נוכחות")
    # (הלוגיקה נשארת דומה אך בעיצוב נקי יותר)
    if not shifts_df.empty:
        st.bar_chart(data=None) # כאן אפשר להוסיף את הגרף הקודם
    else:
        st.info("מתין לנתונים...")
