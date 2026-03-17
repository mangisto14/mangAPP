# 🛡️ Smart Guard Manager

ניהול משמרות שמירה חכם — FastAPI + React

## מבנה הפרויקט

```
mangAPP/
├── backend/
│   ├── __init__.py
│   └── main.py               # FastAPI — כל ה-API endpoints
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts
│       ├── types.ts
│       ├── index.css
│       ├── components/
│       └── features/
├── .env.example
├── .gitignore
├── requirements.txt
├── Procfile
└── railway.json
```

## הרצה מקומית

```bash
# 1. סביבת Python
pip install -r requirements.txt

# 2. קובץ .env (מבוסס על .env.example)
cp .env.example .env
# ערוך את DATABASE_URL ב-.env

# 3. הפעלת Backend
uvicorn backend.main:app --reload

# 4. Frontend (טרמינל נפרד)
cd frontend && npm install && npm run dev
```

## פריסה — Railway (Backend) + Vercel (Frontend)

### Railway

1. צור פרויקט חדש → **Deploy from GitHub repo**
2. הוסף **PostgreSQL** service לפרויקט
3. ב-Service → **Settings**:
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port 8080`
4. ב-**Variables** הוסף:

| Variable | ערך |
|---|---|
| `DATABASE_URL` | מסופק אוטומטית ע"י Railway Postgres |
| `PIN_CODE` | קוד גישה (אופציונלי) |
| `OVERLOAD_THRESHOLD` | `3` (ברירת מחדל) |

### Vercel

1. צור פרויקט חדש → **Import Git Repository**
2. הגדר:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. ב-**Environment Variables** הוסף:

| Variable | ערך |
|---|---|
| `VITE_API_URL` | `https://<your-railway-url>.up.railway.app` (ללא slash בסוף) |

4. לחץ **Deploy**

> אחרי כל שינוי ב-Environment Variables ב-Vercel — יש לבצע **Redeploy**.

## פיצ׳רים

- 📋 רשימת משמרות עם פילטר עבר/עתיד
- ➕ הוספת משמרות בבאצ׳ עם auto-advance זמן
- ⚠️ התראה אם שומר משובץ יותר מדי (3+ משמרות עתידיות)
- ✨ המלצה חכמה: מי מגיע לו המשמרת הבאה
- 👥 ניהול אנשים — הוסף / ערוך / מחק / ייצא רשימה
- 📊 סטטיסטיקה ודירוג עם גרפי עמודות
- 📱 WhatsApp share למשמרות עתידיות
- 🔄 ניהול היעדרויות
- 📅 לוח סבב שבועי
- 🌐 ממשק עברית RTL, מותאם מובייל
