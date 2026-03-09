import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.parse

# הגדרות דף
st.set_page_config(page_title="GuardMaster Pro", layout="wide")

# --- CSS מקצועי סופי לתיקון מוחלט של התצוגה ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Assistant', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* תיקון טבלאות שייראו מעולה במובייל */
    .mobile-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 14px;
    }
    .mobile-table td {
        padding: 8px 4px;
        border-bottom: 1px solid #eee;
        vertical-align: middle;
    }
    .time-cell { font-weight: bold; width: 30%; }
    .name-cell { width: 60%; }
    .action-cell { width: 10%; text-align: center; }

    /* עיצוב כפתורי וואטסאפ ושליחה */
    .stButton button {
        border-radius: 8px;
        font-weight: bold;
    }

    /* תיקון רענון דף ומרווחים */
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- פונקציות מסד נתונים ---
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
            clean_n = n.strip()
            if clean_n in counts:
                counts[clean_n] += 1
    return counts

# --- טאבים ---
tab1, tab2, tab3 = st.tabs(["⚡ שיבוץ", "👥 צוות", "📊 סטטיסטיקה"])

# --- טאב 1: שיבוץ ---
with tab1:
    st.markdown("### 📅 הגדרות משמרת")
    
    # פקדי זמן ותאריך
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        chosen_date = st.date_input("תאריך", datetime.now())
        duration = st.selectbox("משך (דקות)", [30, 45, 60, 90, 120, 180, 240], index=2)
    with col_t2:
        chosen_time = st.time_input("שעת התחלה", datetime.now().replace(minute=0, second=0, microsecond=0))
        num_per_shift = st.number_input("שומרים בעמדה", 1, 5, 2)

    # בחירת שומרים עם סטטיסטיקה
    stats = get_stats()
    guards_df = get_guards()
    options = [f"{r['name']} ({stats.get(r['name'], 0)})" for _, r in guards_df.iterrows()]
    
    selected_raw = st.multiselect("בחר שומרים למשמרת:", options=options)
    
    if st.button("🚀 שבץ למשמרת הבאה", use_container_width=True, type="primary"):
        if selected_raw:
            selected_names = [s.split(' (')[0] for s in selected_raw]
            all_shifts = get_shifts()
            
            # לוגיקת זמן מדויקת:
            if not all_shifts.empty:
                # ממשיך מהסוף של המשמרת האחרונה במסד הנתונים
                last_end = datetime.strptime(all_shifts.iloc[-1]['end_time'], '%Y-%m-%d %H:%M:%S')
                start_dt = last_end
            else:
                # משמרת ראשונה אי פעם - לוקח מהבחירה של המשתמש
                start_dt = datetime.combine(chosen_date, chosen_time)
            
            end_dt = start_dt + timedelta(minutes=duration)
            
            c = conn.cursor()
            c.execute("INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                      (start_dt.strftime('%Y-%m-%d %H:%M:%S'), 
                       end_dt.strftime('%Y-%m-%d %H:%M:%S'), ", ".join(selected_names)))
            conn.commit()
            st.rerun()

    st.markdown('### 🕒 לו"ז נוכחי')
    current_shifts = get_shifts()
    
    if not current_shifts.empty:
        # בניית טבלה ב-HTML למניעת קריסת עמודות במובייל
        table_html = '<table class="mobile-table">'
        for idx, row in current_shifts.iterrows():
            st_time = row['start_time'][11:16]
            en_time = row['end_time'][11:16]
            table_html += f'''
                <tr>
                    <td class="time-cell">{st_time}-{en_time}</td>
                    <td class="name-cell">{row['names']}</td>
                    <td class="action-cell"></td>
                </tr>
            '''
        table_html += '</table>'
        st.markdown(table_html, unsafe_allow_html=True)
        
        # כפתור מחיקה אחרונה מתחת לטבלה
        if st.button("🗑️ מחק משמרת אחרונה", use_container_width=True):
            conn.cursor().execute("DELETE FROM shifts WHERE id = (SELECT MAX(id) FROM shifts)")
            conn.commit()
            st.rerun()

        # וואטסאפ
        summary = "📋 *סידור שמירה:*\n"
        for _, r in current_shifts.iterrows():
            summary += f"• {r['start_time'][11:16]}-{r['end_time'][11:16]}: {r['names']}\n"
        st.link_button("📲 שלח סידור בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(summary)}", use_container_width=True)
    else:
        st.info("אין משמרות משובצות עדיין.")

# --- טאב 2: ניהול צוות ---
with tab2:
    st.markdown("### 👥 ניהול צוות")
    
    # הוספה מהירה
    with st.expander("➕ הוספת שומרים"):
        new_names = st.text_area("הכנס שמות מופרדים בפסיק:")
        if st.button("שמור שומרים"):
            for n in [x.strip() for x in new_names.split(',') if x.strip()]:
                conn.cursor().execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (n,))
            conn.commit()
            st.rerun()

    # רשימת שומרים עם עריכה
    st.markdown("---")
    g_list = get_guards()
    for _, row in g_list.iterrows():
        # שימוש בעמודות של Streamlit לעריכה (כאן הרוחב פחות בעייתי)
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            name_val = st.text_input("שם", value=row['name'], key=f"edit_{row['id']}", label_visibility="collapsed")
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
    st.markdown("### 📊 כמות שמירות לכל שומר")
    current_stats = get_stats()
    if current_stats:
        final_df = pd.DataFrame(list(current_stats.items()), columns=['שם השומר', 'כמות שמירות']).sort_values(by='כמות שמירות', ascending=False)
        st.dataframe(final_df, use_container_width=True, hide_index=True)
        st.bar_chart(final_df.set_index('שם השומר'))
    else:
        st.info("אין נתונים להצגה.")
