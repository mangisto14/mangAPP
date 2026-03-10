"""
Smart Guard Manager – FastAPI Backend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sqlite3
import os
import urllib.parse

app = FastAPI(title="Smart Guard Manager API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────────────────────────────
OVERLOAD_THRESHOLD = int(os.getenv("OVERLOAD_THRESHOLD", "3"))

HE_DAY = {
    "Sunday": "ראשון", "Monday": "שני", "Tuesday": "שלישי",
    "Wednesday": "רביעי", "Thursday": "חמישי",
    "Friday": "שישי", "Saturday": "שבת",
}


# ── Database ──────────────────────────────────────────────────────────────────
def db_path() -> str:
    if os.path.exists("/app/data"):
        return "/app/data/guard_system.db"
    return "guard_system.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guards (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time   TEXT NOT NULL,
                names      TEXT NOT NULL
            )
        """)


init_db()


# ── Seed ──────────────────────────────────────────────────────────────────────
def seed_db() -> None:
    """Insert scheduled shifts on every startup (skips duplicates)."""
    shifts = [
        # ── רביעי 04/03/2026 ─────────────────────────────────────────
        ("2026-03-04T01:00:00", "2026-03-04T02:00:00", "גל עמר,יוסף מנגיסטו"),
        ("2026-03-04T02:00:00", "2026-03-04T03:00:00", "לירן טביבזאדה,נדב אברהם"),
        ("2026-03-04T03:00:00", "2026-03-04T04:00:00", "שלמה מארק,שי כהן"),
        ("2026-03-04T04:00:00", "2026-03-04T05:00:00", "טל אבלין,עוז גושן"),
        ("2026-03-04T05:00:00", "2026-03-04T06:00:00", "זיו יוספי,ירין וקנין"),
        ("2026-03-04T06:00:00", "2026-03-04T07:30:00", "גיל בוחניק,ישראל נעים"),
        ("2026-03-04T07:30:00", "2026-03-04T09:00:00", "בועז רפאלי,אביתר כהן"),
        # ── שישי 06/03/2026 ──────────────────────────────────────────
        ("2026-03-06T07:00:00", "2026-03-06T08:00:00", "אסף אבינועם,חן דנסינגר"),
        ("2026-03-06T08:00:00", "2026-03-06T09:00:00", "גיל שמואל,גיל פיצחאדה"),
        ("2026-03-06T10:00:00", "2026-03-06T11:00:00", "ירין וקנין,נדב אברהם"),
        ("2026-03-06T11:00:00", "2026-03-06T12:00:00", "אביתר ביטון,שלומי סויסה"),
        ("2026-03-06T12:00:00", "2026-03-06T13:00:00", "טלקר,שלומי בן ישי"),
        ("2026-03-06T13:00:00", "2026-03-06T14:00:00", "מתנאל בנימין,יוסי דדון"),
        ("2026-03-06T14:00:00", "2026-03-06T14:30:00", "חי מגנזי,רומן פלדמן"),
        # ── ראשון 08/03/2026 ─────────────────────────────────────────
        ("2026-03-08T08:00:00", "2026-03-08T09:00:00", "נוני איילים,נדב אברהם"),
        ("2026-03-08T09:00:00", "2026-03-08T10:00:00", "בועז רפאלי,אביתר כהן"),
        ("2026-03-08T10:00:00", "2026-03-08T11:00:00", "יהונתן קפיטל,אור הדר"),
        ("2026-03-08T11:00:00", "2026-03-08T12:00:00", "אריאל קרליך,רועי נגאוקר"),
        ("2026-03-08T12:00:00", "2026-03-08T13:00:00", "מתן קזז,טלקר"),
        ("2026-03-08T13:00:00", "2026-03-08T14:00:00", "תומר שמאי,עמיר אודיע"),
        # ── שלישי 10/03/2026 ─────────────────────────────────────────
        ("2026-03-10T08:00:00", "2026-03-10T09:00:00", "יוסי דדון,שלומי בן ישי"),
        ("2026-03-10T09:00:00", "2026-03-10T10:00:00", "טלקר,אביתר ביטון"),
        ("2026-03-10T10:00:00", "2026-03-10T11:00:00", "מתנאל בנימין,נוני איילים"),
        ("2026-03-10T11:00:00", "2026-03-10T12:00:00", "עמיר אודיע,שלומי סויסה"),
        ("2026-03-10T12:00:00", "2026-03-10T13:00:00", "רועי נגאוקר,מתן קזז"),
        ("2026-03-10T13:00:00", "2026-03-10T14:00:00", "תומר שמאי,טל ברוקר"),
        ("2026-03-10T14:00:00", "2026-03-10T15:00:00", "יובל מועלם,שי שני"),
    ]
    with get_conn() as conn:
        for start, end, names in shifts:
            exists = conn.execute(
                "SELECT 1 FROM shifts WHERE start_time = ? AND end_time = ? AND names = ?",
                (start, end, names),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                    (start, end, names),
                )


seed_db()


# ── Helpers ───────────────────────────────────────────────────────────────────
def compute_stats(now: datetime) -> dict:
    """Return {name: {past, future, last_past_date}} for every guard."""
    with get_conn() as conn:
        guards = conn.execute("SELECT name FROM guards").fetchall()
        shifts = conn.execute(
            "SELECT names, start_time, end_time FROM shifts"
        ).fetchall()

    stats: dict = {
        g["name"]: {"past": 0, "future": 0, "last_past_date": None}
        for g in guards
    }

    for s in shifts:
        end_dt = datetime.fromisoformat(s["end_time"])
        start_dt = datetime.fromisoformat(s["start_time"])
        is_past = end_dt <= now
        for name in s["names"].split(","):
            name = name.strip()
            if name not in stats:
                continue
            if is_past:
                stats[name]["past"] += 1
                if (
                    stats[name]["last_past_date"] is None
                    or start_dt > stats[name]["last_past_date"]
                ):
                    stats[name]["last_past_date"] = start_dt
            else:
                stats[name]["future"] += 1

    return stats


# ── Pydantic models ───────────────────────────────────────────────────────────
class GuardCreateBody(BaseModel):
    names: List[str]


class GuardUpdateBody(BaseModel):
    name: str


class ShiftItem(BaseModel):
    start_time: str
    end_time: str
    names: List[str]


class ShiftsBatchBody(BaseModel):
    shifts: List[ShiftItem]


# ── Guards ────────────────────────────────────────────────────────────────────
@app.get("/api/guards")
def list_guards():
    now = datetime.now()
    stats = compute_stats(now)
    with get_conn() as conn:
        guards = conn.execute("SELECT * FROM guards ORDER BY name").fetchall()
    result = []
    for g in guards:
        s = stats.get(g["name"], {"past": 0, "future": 0})
        result.append(
            {
                "id": g["id"],
                "name": g["name"],
                "past": s["past"],
                "future": s["future"],
                "total": s["past"] + s["future"],
                "overloaded": s["future"] >= OVERLOAD_THRESHOLD,
            }
        )
    return result


@app.post("/api/guards", status_code=201)
def add_guards(body: GuardCreateBody):
    added, skipped = [], []
    with get_conn() as conn:
        for raw in body.names:
            name = raw.strip()
            if not name:
                continue
            try:
                conn.execute("INSERT INTO guards (name) VALUES (?)", (name,))
                added.append(name)
            except sqlite3.IntegrityError:
                skipped.append(name)
    return {"added": added, "skipped": skipped}


@app.put("/api/guards/{guard_id}")
def update_guard(guard_id: int, body: GuardUpdateBody):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT name FROM guards WHERE id = ?", (guard_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Guard not found")
        old_name = row["name"]
        try:
            conn.execute(
                "UPDATE guards SET name = ? WHERE id = ?", (body.name, guard_id)
            )
            for shift in conn.execute(
                "SELECT id, names FROM shifts"
            ).fetchall():
                parts = [n.strip() for n in shift["names"].split(",")]
                if old_name in parts:
                    new_names = [
                        body.name if n == old_name else n for n in parts
                    ]
                    conn.execute(
                        "UPDATE shifts SET names = ? WHERE id = ?",
                        (",".join(new_names), shift["id"]),
                    )
        except sqlite3.IntegrityError:
            raise HTTPException(400, "Name already exists")
    return {"ok": True}


@app.delete("/api/guards/{guard_id}")
def delete_guard(guard_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM guards WHERE id = ?", (guard_id,))
    return {"ok": True}


# ── Shifts ────────────────────────────────────────────────────────────────────
@app.get("/api/shifts")
def list_shifts(filter: str = "all"):
    now = datetime.now()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM shifts ORDER BY start_time"
        ).fetchall()
    result = []
    for s in rows:
        end_dt = datetime.fromisoformat(s["end_time"])
        is_past = end_dt <= now
        if filter == "future" and is_past:
            continue
        if filter == "past" and not is_past:
            continue
        result.append(
            {
                "id": s["id"],
                "start_time": s["start_time"],
                "end_time": s["end_time"],
                "names": [n.strip() for n in s["names"].split(",")],
                "is_past": is_past,
            }
        )
    return result


@app.post("/api/shifts", status_code=201)
def add_shifts(body: ShiftsBatchBody):
    with get_conn() as conn:
        for shift in body.shifts:
            conn.execute(
                "INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                (shift.start_time, shift.end_time, ",".join(shift.names)),
            )
    return {"ok": True, "count": len(body.shifts)}


@app.delete("/api/shifts/{shift_id}")
def delete_shift(shift_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
    return {"ok": True}


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats():
    now = datetime.now()
    stats = compute_stats(now)
    with get_conn() as conn:
        total_shifts = conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0]

    guards_list = [
        {
            "name": name,
            "past": s["past"],
            "future": s["future"],
            "total": s["past"] + s["future"],
            "overloaded": s["future"] >= OVERLOAD_THRESHOLD,
        }
        for name, s in stats.items()
    ]
    guards_list.sort(key=lambda x: x["total"], reverse=True)

    return {
        "total_shifts": total_shifts,
        "total_past": sum(s["past"] for s in stats.values()),
        "total_future": sum(s["future"] for s in stats.values()),
        "active_guards": sum(
            1 for s in stats.values() if s["past"] + s["future"] > 0
        ),
        "overload_threshold": OVERLOAD_THRESHOLD,
        "guards": guards_list,
    }


# ── Suggest next shift ────────────────────────────────────────────────────────
@app.get("/api/suggest")
def suggest_next_shift(limit: int = 3):
    """
    Return guards most deserving of the next shift, sorted by:
      1. Fewest future shifts
      2. Fewest total shifts
      3. Oldest last-shift date (or never had a shift)
    """
    now = datetime.now()
    stats = compute_stats(now)
    if not stats:
        return []

    candidates = []
    for name, s in stats.items():
        last_dt = s["last_past_date"]
        candidates.append(
            {
                "name": name,
                "past": s["past"],
                "future": s["future"],
                "total": s["past"] + s["future"],
                "last_past_date": last_dt.isoformat() if last_dt else None,
                "overloaded": s["future"] >= OVERLOAD_THRESHOLD,
            }
        )

    # Sort: future ASC → total ASC → last_past_date ASC (None = never → priority)
    candidates.sort(
        key=lambda g: (
            g["future"],
            g["total"],
            g["last_past_date"] if g["last_past_date"] else "0000-00-00",
        )
    )
    return candidates[:limit]


# ── WhatsApp ──────────────────────────────────────────────────────────────────
@app.get("/api/whatsapp")
def get_whatsapp_url():
    now = datetime.now()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM shifts WHERE start_time > ? ORDER BY start_time",
            (now.isoformat(),),
        ).fetchall()

    if not rows:
        return {"url": "", "text": ""}

    lines = ["🛡️ *סידור שמירה*", f"📆 {now.strftime('%d/%m/%Y %H:%M')}", ""]
    current_date = None
    for s in rows:
        start_dt = datetime.fromisoformat(s["start_time"])
        end_dt = datetime.fromisoformat(s["end_time"])
        date_str = start_dt.strftime("%d/%m/%Y")
        day_name = HE_DAY.get(start_dt.strftime("%A"), "")
        if date_str != current_date:
            if current_date is not None:
                lines.append("")
            lines.append(f"🗓️ *יום {day_name} {date_str}:*")
            current_date = date_str
        time_str = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}"
        names_str = s["names"].replace(",", ", ")
        lines.append(f"• {time_str} ▸ {names_str}")

    lines.extend(["", "_Smart Guard Manager_ 🛡️"])
    text = "\n".join(lines)
    return {"url": f"https://wa.me/?text={urllib.parse.quote(text)}", "text": text}


# ── Config ────────────────────────────────────────────────────────────────────
@app.get("/api/config")
def get_config():
    return {"overload_threshold": OVERLOAD_THRESHOLD}


# ── Serve built React app ─────────────────────────────────────────────────────
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(_DIST):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_DIST, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
