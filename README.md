# 🛡️ Smart Guard Manager

ניהול משמרות שמירה חכם — FastAPI + React

## מבנה הפרויקט

```
mangAPP/
├── backend/
│   ├── __init__.py
│   └── main.py          # FastAPI — כל ה-API endpoints
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   ├── types.ts
│   │   └── components/
│   │       ├── ShiftsTab.tsx   # רשימת משמרות
│   │       ├── AddShiftTab.tsx # הוספה + המלצה
│   │       ├── GuardsTab.tsx   # ניהול שומרים
│   │       └── StatsTab.tsx    # סטטיסטיקה
│   ├── dist/            # Build מוכן לפריסה
│   ├── package.json
│   └── vite.config.ts
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
