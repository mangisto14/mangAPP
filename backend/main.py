"""מצבת כוח – FastAPI Backend v3"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sqlite3, os, urllib.parse, csv, io

app = FastAPI(title="מצבת כוח API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT UNIQUE NOT NULL,
                phone TEXT,
                role  TEXT
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS absences (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guard_id    INTEGER NOT NULL,
                left_at     TEXT NOT NULL,
                returned_at TEXT,
                reason      TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Safe migrations for existing DBs
        for sql in [
            "ALTER TABLE guards ADD COLUMN phone TEXT",
            "ALTER TABLE guards ADD COLUMN role TEXT",
            "ALTER TABLE absences ADD COLUMN reason TEXT",
        ]:
            try:
                conn.execute(sql)
            except Exception:
                pass
        # One-time: set reason='חופשה' for open absences with no reason
        migrated = conn.execute(
            "SELECT value FROM settings WHERE key='migration_open_reason_set'"
        ).fetchone()
        if not migrated:
            conn.execute(
                "UPDATE absences SET reason='חופשה' WHERE returned_at IS NULL AND reason IS NULL"
            )
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES ('migration_open_reason_set', '1')"
            )


init_db()


# ── Seed ──────────────────────────────────────────────────────────────────────
def seed_db() -> None:
    shifts = [
        ("2026-03-04T01:00:00", "2026-03-04T02:00:00", "גל עמר,יוסף מנגיסטו"),
        ("2026-03-04T02:00:00", "2026-03-04T03:00:00", "לירן טביבזאדה,נדב אברהם"),
        ("2026-03-04T03:00:00", "2026-03-04T04:00:00", "שלמה מארק,שי כהן"),
        ("2026-03-04T04:00:00", "2026-03-04T05:00:00", "טל אבלין,עוז גושן"),
        ("2026-03-04T05:00:00", "2026-03-04T06:00:00", "זיו יוספי,ירין וקנין"),
        ("2026-03-04T06:00:00", "2026-03-04T07:30:00", "גיל בוחניק,ישראל נעים"),
        ("2026-03-04T07:30:00", "2026-03-04T09:00:00", "בועז רפאלי,אביתר כהן"),
        ("2026-03-06T07:00:00", "2026-03-06T08:00:00", "אסף אבינועם,חן דנסינגר"),
        ("2026-03-06T08:00:00", "2026-03-06T09:00:00", "גיל שמואל,גיל פיצחאדה"),
        ("2026-03-06T10:00:00", "2026-03-06T11:00:00", "ירין וקנין,נדב אברהם"),
        ("2026-03-06T11:00:00", "2026-03-06T12:00:00", "אביתר ביטון,שלומי סויסה"),
        ("2026-03-06T12:00:00", "2026-03-06T13:00:00", "טלקר,שלומי בן ישי"),
        ("2026-03-06T13:00:00", "2026-03-06T14:00:00", "מתנאל בנימין,יוסי דדון"),
        ("2026-03-06T14:00:00", "2026-03-06T14:30:00", "חי מגנזי,רומן פלדמן"),
        ("2026-03-08T08:00:00", "2026-03-08T09:00:00", "נוני איילים,נדב אברהם"),
        ("2026-03-08T09:00:00", "2026-03-08T10:00:00", "בועז רפאלי,אביתר כהן"),
        ("2026-03-08T10:00:00", "2026-03-08T11:00:00", "יהונתן קפיטל,אור הדר"),
        ("2026-03-08T11:00:00", "2026-03-08T12:00:00", "אריאל קרליך,רועי נגאוקר"),
        ("2026-03-08T12:00:00", "2026-03-08T13:00:00", "מתן קזז,טלקר"),
        ("2026-03-08T13:00:00", "2026-03-08T14:00:00", "תומר שמאי,עמיר אודיע"),
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
                "SELECT 1 FROM shifts WHERE start_time=? AND end_time=? AND names=?",
                (start, end, names),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO shifts (start_time,end_time,names) VALUES (?,?,?)",
                    (start, end, names),
                )


seed_db()


# ── Helpers ───────────────────────────────────────────────────────────────────
def compute_stats(now: datetime) -> dict:
    with get_conn() as conn:
        guards = conn.execute("SELECT name FROM guards").fetchall()
        shifts = conn.execute("SELECT names,start_time,end_time FROM shifts").fetchall()

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
                if stats[name]["last_past_date"] is None or start_dt > stats[name]["last_past_date"]:
                    stats[name]["last_past_date"] = start_dt
            else:
                stats[name]["future"] += 1
    return stats


# ── Pydantic models ───────────────────────────────────────────────────────────
class GuardCreateBody(BaseModel):
    names: List[str]


class GuardUpdateBody(BaseModel):
    name: str
    phone: Optional[str] = None
    role: Optional[str] = None


class ShiftItem(BaseModel):
    start_time: str
    end_time: str
    names: List[str]


class ShiftsBatchBody(BaseModel):
    shifts: List[ShiftItem]


class AbsenceLeaveBody(BaseModel):
    guard_id: int
    reason: Optional[str] = None


class AbsenceActionBody(BaseModel):
    guard_id: int


class SettingsBody(BaseModel):
    alert_minutes: Optional[int] = None


class SeedAbsenceItem(BaseModel):
    name: str
    left_at: str


class SeedAbsencesBody(BaseModel):
    guards: list[SeedAbsenceItem]


# ── PIN ───────────────────────────────────────────────────────────────────────
@app.get("/api/pin/required")
def pin_required():
    return {"required": bool(os.getenv("PIN_CODE", ""))}


@app.get("/api/pin/verify")
def verify_pin(pin: str = Query(...)):
    expected = os.getenv("PIN_CODE", "")
    if not expected:
        return {"ok": True}
    return {"ok": pin == expected}


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
        result.append({
            "id": g["id"],
            "name": g["name"],
            "phone": g["phone"],
            "role": g["role"],
            "past": s["past"],
            "future": s["future"],
            "total": s["past"] + s["future"],
            "overloaded": s["future"] >= OVERLOAD_THRESHOLD,
        })
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
        row = conn.execute("SELECT name FROM guards WHERE id=?", (guard_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Guard not found")
        old_name = row["name"]
        try:
            conn.execute(
                "UPDATE guards SET name=?,phone=?,role=? WHERE id=?",
                (body.name, body.phone, body.role, guard_id),
            )
            if body.name != old_name:
                for shift in conn.execute("SELECT id,names FROM shifts").fetchall():
                    parts = [n.strip() for n in shift["names"].split(",")]
                    if old_name in parts:
                        new_names = [body.name if n == old_name else n for n in parts]
                        conn.execute(
                            "UPDATE shifts SET names=? WHERE id=?",
                            (",".join(new_names), shift["id"]),
                        )
        except sqlite3.IntegrityError:
            raise HTTPException(400, "Name already exists")
    return {"ok": True}


@app.delete("/api/guards/{guard_id}")
def delete_guard(guard_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM guards WHERE id=?", (guard_id,))
    return {"ok": True}


# ── Shifts ────────────────────────────────────────────────────────────────────
@app.get("/api/shifts")
def list_shifts(
    filter: str = "all",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    now = datetime.now()
    from_dt = datetime.fromisoformat(date_from) if date_from else None
    to_dt = datetime.fromisoformat(date_to + "T23:59:59") if date_to else None
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM shifts ORDER BY start_time DESC").fetchall()
    result = []
    for s in rows:
        start_dt = datetime.fromisoformat(s["start_time"])
        end_dt = datetime.fromisoformat(s["end_time"])
        is_past = end_dt <= now
        if filter == "future" and is_past:
            continue
        if filter == "past" and not is_past:
            continue
        if from_dt and start_dt < from_dt:
            continue
        if to_dt and start_dt > to_dt:
            continue
        result.append({
            "id": s["id"],
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "names": [n.strip() for n in s["names"].split(",")],
            "is_past": is_past,
        })
    return result


@app.post("/api/shifts", status_code=201)
def add_shifts(body: ShiftsBatchBody):
    with get_conn() as conn:
        for shift in body.shifts:
            conn.execute(
                "INSERT INTO shifts (start_time,end_time,names) VALUES (?,?,?)",
                (shift.start_time, shift.end_time, ",".join(shift.names)),
            )
    return {"ok": True, "count": len(body.shifts)}


@app.delete("/api/shifts/{shift_id}")
def delete_shift(shift_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
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
        "active_guards": sum(1 for s in stats.values() if s["past"] + s["future"] > 0),
        "overload_threshold": OVERLOAD_THRESHOLD,
        "guards": guards_list,
    }


# ── Suggest ───────────────────────────────────────────────────────────────────
@app.get("/api/suggest")
def suggest_next_shift(limit: int = 3):
    now = datetime.now()
    stats = compute_stats(now)
    if not stats:
        return []
    candidates = []
    for name, s in stats.items():
        last_dt = s["last_past_date"]
        candidates.append({
            "name": name,
            "past": s["past"],
            "future": s["future"],
            "total": s["past"] + s["future"],
            "last_past_date": last_dt.isoformat() if last_dt else None,
            "overloaded": s["future"] >= OVERLOAD_THRESHOLD,
        })
    candidates.sort(key=lambda g: (
        g["future"],
        g["total"],
        g["last_past_date"] if g["last_past_date"] else "0000-00-00",
    ))
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
    lines.extend(["", "_מצבת כוח_ 🛡️"])
    text = "\n".join(lines)
    return {"url": f"https://wa.me/?text={urllib.parse.quote(text)}", "text": text}


# ── Config ────────────────────────────────────────────────────────────────────
@app.get("/api/config")
def get_config():
    return {"overload_threshold": OVERLOAD_THRESHOLD}


# ── Settings ──────────────────────────────────────────────────────────────────
@app.get("/api/settings")
def get_settings():
    with get_conn() as conn:
        rows = conn.execute("SELECT key,value FROM settings").fetchall()
    s = {row["key"]: row["value"] for row in rows}
    return {"alert_minutes": int(s["alert_minutes"]) if s.get("alert_minutes") else None}


@app.post("/api/settings")
def update_settings(body: SettingsBody):
    with get_conn() as conn:
        if body.alert_minutes is not None:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key,value) VALUES ('alert_minutes',?)",
                (str(body.alert_minutes),),
            )
        else:
            conn.execute("DELETE FROM settings WHERE key='alert_minutes'")
    return {"ok": True}


# ── Absences ──────────────────────────────────────────────────────────────────
@app.get("/api/absences")
def list_absences():
    with get_conn() as conn:
        guards = conn.execute("SELECT * FROM guards ORDER BY name").fetchall()
        open_absences = conn.execute(
            "SELECT * FROM absences WHERE returned_at IS NULL"
        ).fetchall()
        exit_counts = conn.execute(
            "SELECT guard_id, COUNT(*) as cnt FROM absences GROUP BY guard_id"
        ).fetchall()
    open_map = {row["guard_id"]: row for row in open_absences}
    count_map = {row["guard_id"]: row["cnt"] for row in exit_counts}
    result = []
    for g in guards:
        absence = open_map.get(g["id"])
        result.append({
            "guard_id": g["id"],
            "name": g["name"],
            "is_out": absence is not None,
            "left_at": absence["left_at"] if absence else None,
            "absence_id": absence["id"] if absence else None,
            "reason": absence["reason"] if absence else None,
            "total_exits": count_map.get(g["id"], 0),
        })
    return result


@app.post("/api/absences/leave", status_code=201)
def mark_leave(body: AbsenceLeaveBody):
    with get_conn() as conn:
        already = conn.execute(
            "SELECT id FROM absences WHERE guard_id=? AND returned_at IS NULL",
            (body.guard_id,),
        ).fetchone()
        if already:
            raise HTTPException(400, "Guard is already out")
        conn.execute(
            "INSERT INTO absences (guard_id,left_at,reason) VALUES (?,?,?)",
            (body.guard_id, datetime.now().isoformat(), body.reason),
        )
    return {"ok": True}


@app.post("/api/absences/return")
def mark_return(body: AbsenceActionBody):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM absences WHERE guard_id=? AND returned_at IS NULL",
            (body.guard_id,),
        ).fetchone()
        if not row:
            raise HTTPException(400, "Guard is not marked as out")
        conn.execute(
            "UPDATE absences SET returned_at=? WHERE id=?",
            (datetime.now().isoformat(), row["id"]),
        )
    return {"ok": True}


@app.post("/api/absences/reset")
def reset_absence(body: AbsenceActionBody):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM absences WHERE guard_id=? AND returned_at IS NULL",
            (body.guard_id,),
        ).fetchone()
        if not row:
            raise HTTPException(400, "Guard is not marked as out")
        now = datetime.now().isoformat()
        conn.execute("UPDATE absences SET returned_at=? WHERE id=?", (now, row["id"]))
        conn.execute(
            "INSERT INTO absences (guard_id,left_at) VALUES (?,?)",
            (body.guard_id, now),
        )
    return {"ok": True}


@app.get("/api/absences/history")
def absences_history(
    guard_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    with get_conn() as conn:
        query = """
            SELECT a.id, g.name, g.id as guard_id,
                   a.left_at, a.returned_at, a.reason
            FROM absences a
            JOIN guards g ON g.id = a.guard_id
            WHERE 1=1
        """
        params: list = []
        if guard_id:
            query += " AND a.guard_id = ?"
            params.append(guard_id)
        if date_from:
            query += " AND a.left_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND a.left_at <= ?"
            params.append(date_to + "T23:59:59")
        query += " ORDER BY a.left_at DESC"
        rows = conn.execute(query, params).fetchall()

    result = []
    for r in rows:
        duration_min = None
        if r["returned_at"]:
            try:
                left = datetime.fromisoformat(r["left_at"])
                ret = datetime.fromisoformat(r["returned_at"])
                duration_min = int((ret - left).total_seconds() / 60)
            except Exception:
                pass
        result.append({
            "id": r["id"],
            "guard_id": r["guard_id"],
            "name": r["name"],
            "left_at": r["left_at"],
            "returned_at": r["returned_at"],
            "reason": r["reason"],
            "duration_min": duration_min,
        })
    return result


@app.get("/api/absences/history.csv")
def history_csv(
    guard_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    history = absences_history(guard_id=guard_id, date_from=date_from, date_to=date_to)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["שם", "סיבה", "שעת יציאה", "שעת חזרה", "משך (דקות)"])
    for row in history:
        left_fmt = ""
        ret_fmt = ""
        try:
            if row["left_at"]:
                left_fmt = datetime.fromisoformat(row["left_at"]).strftime("%d/%m/%Y %H:%M")
            if row["returned_at"]:
                ret_fmt = datetime.fromisoformat(row["returned_at"]).strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
        writer.writerow([
            row["name"],
            row["reason"] or "",
            left_fmt,
            ret_fmt,
            row["duration_min"] if row["duration_min"] is not None else "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=absences_history.csv"},
    )


@app.post("/api/admin/seed-absences", status_code=201)
def seed_absences(body: SeedAbsencesBody):
    with get_conn() as conn:
        for item in body.guards:
            existing = conn.execute(
                "SELECT id FROM guards WHERE name=?", (item.name,)
            ).fetchone()
            if existing:
                guard_id = existing["id"]
            else:
                cur = conn.execute("INSERT INTO guards (name) VALUES (?)", (item.name,))
                guard_id = cur.lastrowid
            conn.execute(
                "UPDATE absences SET returned_at=? WHERE guard_id=? AND returned_at IS NULL",
                (item.left_at, guard_id),
            )
            conn.execute(
                "INSERT INTO absences (guard_id,left_at) VALUES (?,?)",
                (guard_id, item.left_at),
            )
    return {"ok": True, "count": len(body.guards)}


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
