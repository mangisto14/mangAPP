"""מצבת כוח – FastAPI Backend v3"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from contextlib import contextmanager
import os, urllib.parse, csv, io, logging, traceback

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_log = logging.getLogger("mangapp")

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
DATABASE_URL = os.getenv("DATABASE_URL")
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg2
    import psycopg2.extras
    import psycopg2.errors
else:
    import sqlite3


def _q(sql: str) -> str:
    """Replace ? placeholders with %s for PostgreSQL"""
    if IS_PG:
        return sql.replace("?", "%s")
    return sql


_IntegrityError = psycopg2.errors.UniqueViolation if IS_PG else sqlite3.IntegrityError  # type: ignore[name-defined]

# Primary key column definition
_SERIAL_PK = "id SERIAL PRIMARY KEY" if IS_PG else "id INTEGER PRIMARY KEY AUTOINCREMENT"


class PgConn:
    """Wraps psycopg2 connection to expose a sqlite3-compatible execute() interface"""

    def __init__(self, raw):
        self._raw = raw
        self._cur = raw.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def execute(self, sql, params=()):
        self._cur.execute(sql, params if params else None)
        return self._cur

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


def db_path() -> str:
    volume_path = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_path:
        return os.path.join(volume_path, "guard_system.db")
    if os.path.exists("/app/data"):
        return "/app/data/guard_system.db"
    return "guard_system.db"


@contextmanager
def get_conn():
    if IS_PG:
        url = DATABASE_URL
        # Supabase sometimes provides postgres:// – psycopg2 prefers postgresql://
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        # Ensure SSL for Supabase / hosted PG
        if "sslmode" not in url:
            sep = "&" if "?" in url else "?"
            url = url + sep + "sslmode=require"
        raw = psycopg2.connect(url)
        conn = PgConn(raw)
    else:
        raw = sqlite3.connect(db_path())
        raw.row_factory = sqlite3.Row
        conn = raw
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS guards (
                {_SERIAL_PK},
                name  TEXT UNIQUE NOT NULL,
                phone TEXT,
                role  TEXT
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS shifts (
                {_SERIAL_PK},
                start_time TEXT NOT NULL,
                end_time   TEXT NOT NULL,
                names      TEXT NOT NULL
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS absences (
                {_SERIAL_PK},
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rotation_config (
                id           INTEGER PRIMARY KEY,
                start_date   TEXT NOT NULL,
                period_days  INTEGER NOT NULL DEFAULT 2
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS rotation_roles (
                {_SERIAL_PK},
                name     TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS rotation_slots (
                {_SERIAL_PK},
                role_id  INTEGER NOT NULL REFERENCES rotation_roles(id) ON DELETE CASCADE,
                slot_num INTEGER NOT NULL,
                names    TEXT NOT NULL DEFAULT '[]'
            )
        """)
        # Safe migrations for existing DBs
        migrations = [
            "ALTER TABLE guards ADD COLUMN phone TEXT",
            "ALTER TABLE guards ADD COLUMN role TEXT",
            "ALTER TABLE absences ADD COLUMN reason TEXT",
        ]
        for sql in migrations:
            if IS_PG:
                # PostgreSQL: use IF NOT EXISTS to avoid transaction abort
                safe_sql = sql.replace(
                    "ADD COLUMN ", "ADD COLUMN IF NOT EXISTS "
                )
                conn.execute(safe_sql)
            else:
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
            if IS_PG:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('migration_open_reason_set', '1') ON CONFLICT (key) DO NOTHING"
                )
            else:
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES ('migration_open_reason_set', '1')"
                )


try:
    init_db()
    _log.info("init_db: OK (IS_PG=%s)", IS_PG)
except Exception:
    _log.error("init_db FAILED (server will still start):\n%s", traceback.format_exc())


# ── Seed Rotation ─────────────────────────────────────────────────────────────
import json as _json

_DEFAULT_ROTATION = {
    "start_date": "2025-03-08",
    "period_days": 2,
    "roles": [
        {"name": "קצינים",  "slots": [["זיו"], ["טל"], ["שלמה"]]},
        {"name": "מפקדים", "slots": [["בועז"], ["יוסף"], ["אביתר"]]},
        {"name": "פקחים",  "slots": [
            ["שי", "בוחניק", "עוז", "חי"],
            ["חן", "גיל", "ירין", "ביטון"],
            ["דדון", "שלומי", "תלקר", "חי מגנזי"],
        ]},
        {"name": "נהגים",  "slots": [["גיל", "עוז"], ["ישראל", "רומן"], ["מתנאל", "נוני"]]},
        {"name": "מטהרים", "slots": [["אסף", "אליאב"], ["נדב", "לירן"], ["גל", "עמיר", "שלומי"]]},
        {"name": "עתודאים", "slots": [
            ["יהונתן קפיטל", "אור הדר", "אריאל קרליך"],
            ["שי שני", "דוד סויסה", "יובל מועלם", "תומר שמאי"],
            ["רועי נגאוקר", "טל ברוקר", "מתן קזז", "תומר שמאי"],
        ]},
    ],
}


def seed_rotation() -> None:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM rotation_config").fetchone()
        if existing:
            return
        if IS_PG:
            conn.execute(
                "INSERT INTO rotation_config (id, start_date, period_days) VALUES (1, %s, %s) ON CONFLICT (id) DO NOTHING",
                (_DEFAULT_ROTATION["start_date"], _DEFAULT_ROTATION["period_days"]),
            )
        else:
            conn.execute(
                "INSERT INTO rotation_config (id, start_date, period_days) VALUES (1, ?, ?)",
                (_DEFAULT_ROTATION["start_date"], _DEFAULT_ROTATION["period_days"]),
            )
        for pos, role_data in enumerate(_DEFAULT_ROTATION["roles"]):
            if IS_PG:
                cur = conn.execute(
                    "INSERT INTO rotation_roles (name, position) VALUES (%s, %s) RETURNING id",
                    (role_data["name"], pos),
                )
                role_id = cur.fetchone()["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO rotation_roles (name, position) VALUES (?, ?)",
                    (role_data["name"], pos),
                )
                role_id = cur.lastrowid
            for slot_num, names in enumerate(role_data["slots"]):
                conn.execute(
                    _q("INSERT INTO rotation_slots (role_id, slot_num, names) VALUES (?, ?, ?)"),
                    (role_id, slot_num, _json.dumps(names, ensure_ascii=False)),
                )


try:
    seed_rotation()
    _log.info("seed_rotation: OK")
except Exception:
    _log.error("seed_rotation FAILED:\n%s", traceback.format_exc())


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
                _q("SELECT 1 FROM shifts WHERE start_time=? AND end_time=? AND names=?"),
                (start, end, names),
            ).fetchone()
            if not exists:
                conn.execute(
                    _q("INSERT INTO shifts (start_time,end_time,names) VALUES (?,?,?)"),
                    (start, end, names),
                )


try:
    seed_db()
    _log.info("seed_db: OK")
except Exception:
    _log.error("seed_db FAILED:\n%s", traceback.format_exc())


# ── Seed Absences ─────────────────────────────────────────────────────────────
def seed_absences_data() -> None:
    """Seed historical absence data (runs once, skipped if already seeded)."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT value FROM settings WHERE key='seed_absences_v1'"
        ).fetchone()
        if already:
            return

        records = [
            # (name, reason, left_at, returned_at)  — None = still out
            ("תומר שמאי",     "מחלה",  "2026-03-10T20:58:00", None),
            ("אסף אבינועם",   "אישי",  "2026-03-10T19:32:00", "2026-03-10T20:58:00"),
            ("מתנאל בנימין",  "אישי",  "2026-03-10T19:30:00", "2026-03-10T20:58:00"),
            ("אביתר ביטון",   "אישי",  "2026-03-10T16:28:00", "2026-03-10T16:28:00"),
            ("אביתר ביטון",   None,    "2026-03-10T14:04:00", "2026-03-10T14:25:00"),
            ("אור הדר",       None,    "2026-03-10T14:01:00", "2026-03-10T14:01:00"),
            ("אביתר ביטון",   None,    "2026-03-10T13:50:00", "2026-03-10T14:01:00"),
            ("אביתר כהן",     None,    "2026-03-10T13:50:00", "2026-03-10T14:01:00"),
            ("אביתר ביטון",   None,    "2026-03-10T13:49:00", "2026-03-10T13:50:00"),
            ("זיו יוספי",     "חופשה", "2026-03-10T10:00:00", None),
            ("בועז רפאלי",    "חופשה", "2026-03-10T10:00:00", None),
            ("חן דנסינגר",    "חופשה", "2026-03-10T10:00:00", None),
            ("גיל שמואל",     "חופשה", "2026-03-10T10:00:00", None),
            ("ירין וקנין",    "חופשה", "2026-03-10T10:00:00", None),
            ("ישראל נעים",    "חופשה", "2026-03-10T10:00:00", None),
            ("רומן פלדמן",    "חופשה", "2026-03-10T10:00:00", None),
            ("נדב אברהם",     "חופשה", "2026-03-10T10:00:00", None),
            ("לירן טביבזאדה", "חופשה", "2026-03-10T10:00:00", None),
            ("גל עמר",        "חופשה", "2026-03-10T10:00:00", None),
            ("אור הדר",       "חופשה", "2026-03-10T10:00:00", None),
            ("אריאל קרליך",   "חופשה", "2026-03-10T10:00:00", None),
            ("יהונתן פריאל",  "חופשה", "2026-03-10T10:00:00", None),
        ]

        for name, reason, left_at, returned_at in records:
            if IS_PG:
                cur = conn.execute(
                    "INSERT INTO guards (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id",
                    (name,),
                )
                row = cur.fetchone()
                if row:
                    gid = row["id"]
                else:
                    gid = conn.execute(
                        "SELECT id FROM guards WHERE name=%s", (name,)
                    ).fetchone()["id"]
            else:
                conn.execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (name,))
                gid = conn.execute(
                    "SELECT id FROM guards WHERE name=?", (name,)
                ).fetchone()["id"]

            conn.execute(
                _q("INSERT INTO absences (guard_id, left_at, returned_at, reason) VALUES (?,?,?,?)"),
                (gid, left_at, returned_at, reason),
            )

        if IS_PG:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('seed_absences_v1', '1') ON CONFLICT (key) DO NOTHING"
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES ('seed_absences_v1', '1')"
            )


try:
    seed_absences_data()
    _log.info("seed_absences_data: OK")
except Exception:
    _log.error("seed_absences_data FAILED:\n%s", traceback.format_exc())


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


class RotationConfigUpdateBody(BaseModel):
    start_date: str
    period_days: int = 2


class RotationRoleCreateBody(BaseModel):
    name: str


class RotationRoleUpdateBody(BaseModel):
    name: str
    position: Optional[int] = None


class RotationSlotsUpdateBody(BaseModel):
    slots: List[List[str]]  # 3 lists, one per slot


# ── Health / Debug ────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    try:
        with get_conn() as conn:
            if IS_PG:
                tables = [r[0] for r in conn.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
                ).fetchall()]
            else:
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()]
            counts = {}
            for t in tables:
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        return {"status": "ok", "db": "pg" if IS_PG else "sqlite", "tables": counts}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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
            if IS_PG:
                cur = conn.execute(
                    "INSERT INTO guards (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                    (name,),
                )
            else:
                cur = conn.execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (name,))
            if cur.rowcount > 0:
                added.append(name)
            else:
                skipped.append(name)
    return {"added": added, "skipped": skipped}


@app.put("/api/guards/{guard_id}")
def update_guard(guard_id: int, body: GuardUpdateBody):
    with get_conn() as conn:
        row = conn.execute(_q("SELECT name FROM guards WHERE id=?"), (guard_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Guard not found")
        old_name = row["name"]
        try:
            conn.execute(
                _q("UPDATE guards SET name=?,phone=?,role=? WHERE id=?"),
                (body.name, body.phone, body.role, guard_id),
            )
            if body.name != old_name:
                for shift in conn.execute("SELECT id,names FROM shifts").fetchall():
                    parts = [n.strip() for n in shift["names"].split(",")]
                    if old_name in parts:
                        new_names = [body.name if n == old_name else n for n in parts]
                        conn.execute(
                            _q("UPDATE shifts SET names=? WHERE id=?"),
                            (",".join(new_names), shift["id"]),
                        )
        except _IntegrityError:
            raise HTTPException(400, "Name already exists")
    return {"ok": True}


@app.delete("/api/guards/{guard_id}")
def delete_guard(guard_id: int):
    with get_conn() as conn:
        conn.execute(_q("DELETE FROM guards WHERE id=?"), (guard_id,))
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
                _q("INSERT INTO shifts (start_time,end_time,names) VALUES (?,?,?)"),
                (shift.start_time, shift.end_time, ",".join(shift.names)),
            )
    return {"ok": True, "count": len(body.shifts)}


@app.delete("/api/shifts/{shift_id}")
def delete_shift(shift_id: int):
    with get_conn() as conn:
        conn.execute(_q("DELETE FROM shifts WHERE id=?"), (shift_id,))
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
    with get_conn() as conn:
        absent_rows = conn.execute(
            "SELECT g.name FROM absences a JOIN guards g ON g.id = a.guard_id WHERE a.returned_at IS NULL"
        ).fetchall()
    absent_names = {row["name"] for row in absent_rows}
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
            "is_out": name in absent_names,
        })
    candidates.sort(key=lambda g: (
        1 if g["is_out"] else 0,
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
            _q("SELECT * FROM shifts WHERE start_time > ? ORDER BY start_time"),
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
            if IS_PG:
                conn.execute(
                    "INSERT INTO settings (key,value) VALUES ('alert_minutes',%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                    (str(body.alert_minutes),),
                )
            else:
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
            _q("SELECT id FROM absences WHERE guard_id=? AND returned_at IS NULL"),
            (body.guard_id,),
        ).fetchone()
        if already:
            raise HTTPException(400, "Guard is already out")
        conn.execute(
            _q("INSERT INTO absences (guard_id,left_at,reason) VALUES (?,?,?)"),
            (body.guard_id, datetime.now().isoformat(), body.reason),
        )
    return {"ok": True}


@app.post("/api/absences/return")
def mark_return(body: AbsenceActionBody):
    with get_conn() as conn:
        row = conn.execute(
            _q("SELECT id FROM absences WHERE guard_id=? AND returned_at IS NULL"),
            (body.guard_id,),
        ).fetchone()
        if not row:
            raise HTTPException(400, "Guard is not marked as out")
        conn.execute(
            _q("UPDATE absences SET returned_at=? WHERE id=?"),
            (datetime.now().isoformat(), row["id"]),
        )
    return {"ok": True}


@app.post("/api/absences/reset")
def reset_absence(body: AbsenceActionBody):
    with get_conn() as conn:
        row = conn.execute(
            _q("SELECT id FROM absences WHERE guard_id=? AND returned_at IS NULL"),
            (body.guard_id,),
        ).fetchone()
        if not row:
            raise HTTPException(400, "Guard is not marked as out")
        now = datetime.now().isoformat()
        conn.execute(_q("UPDATE absences SET returned_at=? WHERE id=?"), (now, row["id"]))
        conn.execute(
            _q("INSERT INTO absences (guard_id,left_at) VALUES (?,?)"),
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
        ph = "%s" if IS_PG else "?"
        query = """
            SELECT a.id, g.name, g.id as guard_id,
                   a.left_at, a.returned_at, a.reason
            FROM absences a
            JOIN guards g ON g.id = a.guard_id
            WHERE 1=1
        """
        params: list = []
        if guard_id:
            query += f" AND a.guard_id = {ph}"
            params.append(guard_id)
        if date_from:
            query += f" AND a.left_at >= {ph}"
            params.append(date_from)
        if date_to:
            query += f" AND a.left_at <= {ph}"
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
                _q("SELECT id FROM guards WHERE name=?"), (item.name,)
            ).fetchone()
            if existing:
                guard_id = existing["id"]
            else:
                if IS_PG:
                    cur = conn.execute(
                        "INSERT INTO guards (name) VALUES (%s) RETURNING id", (item.name,)
                    )
                    guard_id = cur.fetchone()["id"]
                else:
                    cur = conn.execute("INSERT INTO guards (name) VALUES (?)", (item.name,))
                    guard_id = cur.lastrowid
            conn.execute(
                _q("UPDATE absences SET returned_at=? WHERE guard_id=? AND returned_at IS NULL"),
                (item.left_at, guard_id),
            )
            conn.execute(
                _q("INSERT INTO absences (guard_id,left_at) VALUES (?,?)"),
                (guard_id, item.left_at),
            )
    return {"ok": True, "count": len(body.guards)}


# ── Rotation ──────────────────────────────────────────────────────────────────
def _build_rotation_response(conn) -> dict:
    cfg = conn.execute("SELECT start_date, period_days FROM rotation_config WHERE id=1").fetchone()
    roles = conn.execute("SELECT * FROM rotation_roles ORDER BY position").fetchall()
    slots_all = conn.execute("SELECT * FROM rotation_slots ORDER BY slot_num").fetchall()
    slots_map: dict = {}
    for sl in slots_all:
        slots_map.setdefault(sl["role_id"], {})[sl["slot_num"]] = _json.loads(sl["names"])
    roles_out = []
    for r in roles:
        s = slots_map.get(r["id"], {})
        roles_out.append({
            "id": r["id"],
            "name": r["name"],
            "position": r["position"],
            "slots": [s.get(i, []) for i in range(3)],
        })
    return {
        "start_date": cfg["start_date"] if cfg else "2025-03-08",
        "period_days": cfg["period_days"] if cfg else 2,
        "roles": roles_out,
    }


@app.get("/api/rotation")
def get_rotation():
    with get_conn() as conn:
        return _build_rotation_response(conn)


@app.put("/api/rotation/config")
def update_rotation_config(body: RotationConfigUpdateBody):
    with get_conn() as conn:
        if IS_PG:
            conn.execute(
                "INSERT INTO rotation_config (id, start_date, period_days) VALUES (1, %s, %s) ON CONFLICT (id) DO UPDATE SET start_date=EXCLUDED.start_date, period_days=EXCLUDED.period_days",
                (body.start_date, body.period_days),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO rotation_config (id, start_date, period_days) VALUES (1, ?, ?)",
                (body.start_date, body.period_days),
            )
    return {"ok": True}


@app.post("/api/rotation/roles", status_code=201)
def add_rotation_role(body: RotationRoleCreateBody):
    with get_conn() as conn:
        max_pos = conn.execute("SELECT MAX(position) as m FROM rotation_roles").fetchone()["m"]
        pos = (max_pos or 0) + 1
        if IS_PG:
            cur = conn.execute(
                "INSERT INTO rotation_roles (name, position) VALUES (%s, %s) RETURNING id",
                (body.name, pos),
            )
            role_id = cur.fetchone()["id"]
        else:
            cur = conn.execute(
                "INSERT INTO rotation_roles (name, position) VALUES (?, ?)",
                (body.name, pos),
            )
            role_id = cur.lastrowid
        for slot_num in range(3):
            conn.execute(
                _q("INSERT INTO rotation_slots (role_id, slot_num, names) VALUES (?, ?, ?)"),
                (role_id, slot_num, "[]"),
            )
    return {"ok": True, "id": role_id}


@app.put("/api/rotation/roles/{role_id}")
def update_rotation_role(role_id: int, body: RotationRoleUpdateBody):
    with get_conn() as conn:
        row = conn.execute(_q("SELECT id FROM rotation_roles WHERE id=?"), (role_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Role not found")
        if body.position is not None:
            conn.execute(
                _q("UPDATE rotation_roles SET name=?, position=? WHERE id=?"),
                (body.name, body.position, role_id),
            )
        else:
            conn.execute(
                _q("UPDATE rotation_roles SET name=? WHERE id=?"),
                (body.name, role_id),
            )
    return {"ok": True}


@app.delete("/api/rotation/roles/{role_id}")
def delete_rotation_role(role_id: int):
    with get_conn() as conn:
        conn.execute(_q("DELETE FROM rotation_slots WHERE role_id=?"), (role_id,))
        conn.execute(_q("DELETE FROM rotation_roles WHERE id=?"), (role_id,))
    return {"ok": True}


@app.put("/api/rotation/roles/{role_id}/slots")
def update_rotation_slots(role_id: int, body: RotationSlotsUpdateBody):
    if len(body.slots) != 3:
        raise HTTPException(400, "Must provide exactly 3 slots")
    with get_conn() as conn:
        row = conn.execute(_q("SELECT id FROM rotation_roles WHERE id=?"), (role_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Role not found")
        conn.execute(_q("DELETE FROM rotation_slots WHERE role_id=?"), (role_id,))
        for slot_num, names in enumerate(body.slots):
            conn.execute(
                _q("INSERT INTO rotation_slots (role_id, slot_num, names) VALUES (?, ?, ?)"),
                (role_id, slot_num, _json.dumps(names, ensure_ascii=False)),
            )
    return {"ok": True}


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
        # Let real API routes handle themselves – only catch non-API paths for SPA
        if full_path.startswith("api") :
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(os.path.join(_DIST, "index.html"))
