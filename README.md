# 🛡️ Smart Guard Manager

ניהול משמרות שמירה חכם — FastAPI + React

## מבנה הפרויקט

```
mangAPP/
├── backend/
│   ├── __init__.py
│   └── main.py               # FastAPI — כל ה-API endpoints
├── frontend/
│   ├── index.html             # נקודת כניסה HTML (RTL, Hebrew font)
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── dist/                  # Build מוכן לפריסה (נוצר ע"י npm run build)
│   └── src/
│       ├── main.tsx           # React entry point
│       ├── App.tsx            # Tabs navigation
│       ├── api.ts             # כל קריאות ה-API
│       ├── types.ts           # TypeScript interfaces
│       ├── index.css          # Tailwind + global styles
│       └── components/
│           ├── ShiftsTab.tsx  # רשימת משמרות + WhatsApp
│           ├── AddShiftTab.tsx # הוספה + המלצה חכמה + אזהרת עומס
│           ├── GuardsTab.tsx  # ניהול שומרים + התראת עומס יתר
│           └── StatsTab.tsx   # סטטיסטיקה ודירוג
├── .gitignore
├── requirements.txt
├── Procfile
└── railway.json
```

## הרצה מקומית

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend (טרמינל נפרד)
cd frontend && npm install && npm run dev
```

## פריסה ל-Railway

```bash
cd frontend && npm run build
git push
```

## פיצ׳רים

- 📋 רשימת משמרות עם פילטר עבר/עתיד
- ➕ הוספת משמרות בבאצ׳ עם auto-advance זמן
- ⚠️ התראה אם שומר משובץ יותר מדי (3+ משמרות עתידיות)
- ✨ המלצה חכמה: מי מגיע לו המשמרת הבאה
- 👥 ניהול שומרים (הוסף / ערוך / מחק)
- 📊 סטטיסטיקה ודירוג עם גרפי עמודות
- 📱 WhatsApp share למשמרות עתידיות
- 🌐 ממשק עברית RTL, מותאם מובייל
