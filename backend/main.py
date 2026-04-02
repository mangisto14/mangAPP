"""מצבת כוח – FastAPI Backend v3"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import os, urllib.parse, csv, io, logging, traceback

from backend.backup_manager import init_schema, start_scheduler, stop_scheduler, schedule_test_backup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_log = logging.getLogger("mangapp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="מצבת כוח API", version="3.0.0", lifespan=lifespan)

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
import sqlite3

_IntegrityError = sqlite3.IntegrityError

# Primary key column definition
_SERIAL_PK = "id INTEGER PRIMARY KEY AUTOINCREMENT"



def db_path() -> str:
    volume_path = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_path:
        return os.path.join(volume_path, "database.db")
    if os.path.exists("/app/data"):
        return "/app/data/database.db"
    return "database.db"


@contextmanager
def get_conn():
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
                name      TEXT UNIQUE NOT NULL,
                phone     TEXT,
                role      TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
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
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS rotation_period_ranges (
                {_SERIAL_PK},
                slot_num   INTEGER NOT NULL UNIQUE,
                start_date TEXT NOT NULL,
                end_date   TEXT NOT NULL
            )
        """)
        # Safe migrations for existing DBs
        migrations = [
            "ALTER TABLE guards ADD COLUMN phone TEXT",
            "ALTER TABLE guards ADD COLUMN role TEXT",
            "ALTER TABLE absences ADD COLUMN reason TEXT",
            "ALTER TABLE guards ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        ]
        for sql in migrations:
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


try:
    init_db()
    _log.info("init_db: OK")
except Exception:
    _log.error("init_db FAILED (server will still start):\n%s", traceback.format_exc())


# ── Seed Rotation ─────────────────────────────────────────────────────────────
import json as _json

_DEFAULT_ROTATION = {
    "start_date": "2025-03-08",
    "period_days": 2,
    # מחזור 7-ימי: א-ג (ראשון+שני 2י), ג-ה (שלישי+רביעי 2י, חמישי=חזרה), ו-א (שישי+שבת 2י)
    # slot[0]=א-ג, slot[1]=ג-ה, slot[2]=ו-א  (נוסחה: ((1-שבוע-תקופה)%3+3)%3)
    "roles": [
        {"name": "קצינים",  "slots": [["טל"], ["שלמה"], ["זיו"]]},
        {"name": "מפקדים", "slots": [["יוסף"], ["אביתר"], ["בועז"]]},
        {"name": "פקחים",  "slots": [
            ["שי כהן", "גיל בוחניק", "עוז", "חי מגנזי"],
            ["דדון", "שלומי", "טלקר", "ביטון"],
            ["חן", "גיל שמואל", "ירין"],
        ]},
        {"name": "נהגים",  "slots": [["גיל", "עוז"], ["מתנאל", "נוני"], ["ישראל", "רומן"]]},
        {"name": "מטהרים", "slots": [["אסף", "אליאב"], ["גל", "עמיר", "שלומי"], ["נדב", "לירן"]]},
        {"name": "עתודאים", "slots": [
            ["שי שני", "דוד סויסה", "יובל מועלם"],
            ["רועי נגאוקר", "טל ברוקר", "מתן קזז", "תומר שמאי"],
            ["יהונתן קפיטל", "אור הדר", "אריאל קרליך"],
        ]},
    ],
}

# מחזור 9-תקופות: כל תקופה עם שיבוץ עצמאי (3 שבועות × 3 תקופות/שבוע)
# slot 0=08/3(א-ג), 1=10/3(ג-ה), 2=13/3(ו-א), 3=15/3(א-ג), 4=17/3(ג-ה),
#       5=20/3(ו-א), 6=22/3(א-ג), 7=24/3(ג-ה), 8=27/3(ו-א)
_ROTATION_9SLOTS: dict = {
    "start_date": "2026-03-08",
    "roles": {
        "קצינים": [
            ["טל"], ["זיו"], ["שלמה"], ["זיו"], ["שלמה"],
            ["טל"], ["שלמה"], ["טל"], ["זיו"],
        ],
        "מפקדים": [
            ["יוסף"], ["בועז"], ["אביתר"], ["בועז"], ["אביתר"],
            ["יוסף"], ["אביתר"], ["יוסף"], ["בועז"],
        ],
        "פקחים": [
            ["שי כהן", "גיל בוחניק", "עוז", "חי מגנזי"],   # 0: 08/3
            ["חן", "גיל שמואל", "ירין"],                    # 1: 10/3
            ["דדון", "שלומי", "טלקר", "ביטון"],             # 2: 13/3
            ["שי כהן", "גיל בוחניק", "עוז", "חי מגנזי"],   # 3: 15/3
            ["דדון", "שלומי", "טלקר", "ביטון"],             # 4: 17/3
            ["חן", "גיל בוחניק", "ירין"],                   # 5: 20/3
            ["דדון", "שלומי", "טלקר", "ביטון"],             # 6: 22/3
            ["חן", "גיל בוחניק", "ירין"],                   # 7: 24/3
            ["שי כהן", "גיל בוחניק", "עוז", "חי מגנזי"],   # 8: 27/3
        ],
        "נהגים": [
            ["גיל", "עוז"], ["ישראל", "רומן"], ["מתנאל", "נוני"],
            ["גיל", "עוז"], ["מתנאל", "נוני"], ["ישראל", "רומן"],
            ["מתנאל", "נוני"], ["ישראל", "רומן"], ["גיל", "עוז"],
        ],
        "מטהרים": [
            ["אסף", "אליאב"], ["נדב", "לירן", "גל"], ["עמיר", "שלומי ס"],
            ["אסף", "אליאב"], ["עמיר", "שלומי ס"], ["נדב", "לירן", "גל"],
            ["עמיר", "שלומי ס"], ["נדב", "לירן", "גל"], ["אסף", "אליאב"],
        ],
        "עתודאים": [
            ["שי שני", "דוד סויסה", "יובל מועלם", "טל ברוקר"],  # 0: 08/3
            ["יהונתן פריאל", "אור הדר", "אריאל קרליך"],          # 1: 10/3
            ["רועי נגאוקר", "מתן קזז", "תומר שמאי"],             # 2: 13/3
            ["יהונתן פריאל", "אור הדר", "אריאל קרליך"],          # 3: 15/3
            ["רועי נגאוקר", "מתן קזז", "תומר שמאי"],             # 4: 17/3
            ["שי שני", "דוד סויסה", "יובל מועלם", "טל ברוקר"],  # 5: 20/3
            ["רועי נגאוקר", "מתן קזז", "תומר שמאי"],             # 6: 22/3
            ["שי שני", "דוד סויסה", "יובל מועלם", "טל ברוקר"],  # 7: 24/3
            ["יהונתן פריאל", "אור הדר", "אריאל קרליך"],          # 8: 27/3
        ],
    },
}


def seed_rotation() -> None:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM rotation_config").fetchone()
        if existing:
            return
        conn.execute(
            "INSERT INTO rotation_config (id, start_date, period_days) VALUES (1, ?, ?)",
            (_DEFAULT_ROTATION["start_date"], _DEFAULT_ROTATION["period_days"]),
        )
        for pos, role_data in enumerate(_DEFAULT_ROTATION["roles"]):
            cur = conn.execute(
                "INSERT INTO rotation_roles (name, position) VALUES (?, ?)",
                (role_data["name"], pos),
            )
            role_id = cur.lastrowid
            for slot_num, names in enumerate(role_data["slots"]):
                conn.execute(
                    "INSERT INTO rotation_slots (role_id, slot_num, names) VALUES (?, ?, ?)",
                    (role_id, slot_num, _json.dumps(names, ensure_ascii=False)),
                )


try:
    seed_rotation()
    _log.info("seed_rotation: OK")
except Exception:
    _log.error("seed_rotation FAILED:\n%s", traceback.format_exc())


def migrate_rotation_v2() -> None:
    """מיגרציה חד-פעמית: תיקון סדר slots לפי מחזור ו-א/א-ג/ג-ה הנכון."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT value FROM settings WHERE key='rotation_v2_migrated'"
        ).fetchone()
        if already:
            return
        for role_data in _DEFAULT_ROTATION["roles"]:
            role = conn.execute(
                "SELECT id FROM rotation_roles WHERE name=?",
                (role_data["name"],),
            ).fetchone()
            if not role:
                continue
            role_id = role["id"]
            for slot_num, names in enumerate(role_data["slots"]):
                conn.execute(
                    "UPDATE rotation_slots SET names=? WHERE role_id=? AND slot_num=?",
                    (_json.dumps(names, ensure_ascii=False), role_id, slot_num),
                )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value)"
            " VALUES ('rotation_v2_migrated', '1')"
        )


try:
    migrate_rotation_v2()
    _log.info("migrate_rotation_v2: OK")
except Exception:
    _log.error("migrate_rotation_v2 FAILED:\n%s", traceback.format_exc())


def migrate_rotation_v3() -> None:
    """מיגרציה חד-פעמית: תיקון שמות פקחים ועתודאים + החלפת slots עתודאים."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT value FROM settings WHERE key='rotation_v3_migrated'"
        ).fetchone()
        if already:
            return
        for role_data in _DEFAULT_ROTATION["roles"]:
            role = conn.execute(
                "SELECT id FROM rotation_roles WHERE name=?",
                (role_data["name"],),
            ).fetchone()
            if not role:
                continue
            role_id = role["id"]
            for slot_num, names in enumerate(role_data["slots"]):
                conn.execute(
                    "UPDATE rotation_slots SET names=? WHERE role_id=? AND slot_num=?",
                    (_json.dumps(names, ensure_ascii=False), role_id, slot_num),
                )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value)"
            " VALUES ('rotation_v3_migrated', '1')"
        )


try:
    migrate_rotation_v3()
    _log.info("migrate_rotation_v3: OK")
except Exception:
    _log.error("migrate_rotation_v3 FAILED:\n%s", traceback.format_exc())


def migrate_rotation_v4() -> None:
    """מיגרציה חד-פעמית: גיל ש → גיל שמואל בפקחים + החזרת start_date ל-2025-03-08."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT value FROM settings WHERE key='rotation_v4_migrated'"
        ).fetchone()
        if already:
            return
        conn.execute(
            "UPDATE rotation_config SET start_date='2025-03-08' WHERE start_date='2026-03-08'"
        )
        role = conn.execute(
            "SELECT id FROM rotation_roles WHERE name='פקחים'"
        ).fetchone()
        if role:
            slot = conn.execute(
                "SELECT id, names FROM rotation_slots WHERE role_id=? AND slot_num=2",
                (role["id"],),
            ).fetchone()
            if slot:
                names = _json.loads(slot["names"])
                names = ["גיל שמואל" if n == "גיל ש" else n for n in names]
                conn.execute(
                    "UPDATE rotation_slots SET names=? WHERE id=?",
                    (_json.dumps(names, ensure_ascii=False), slot["id"]),
                )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value)"
            " VALUES ('rotation_v4_migrated', '1')"
        )


try:
    migrate_rotation_v4()
    _log.info("migrate_rotation_v4: OK")
except Exception:
    _log.error("migrate_rotation_v4 FAILED:\n%s", traceback.format_exc())


def migrate_rotation_v5() -> None:
    """מיגרציה חד-פעמית: החזרת start_date ל-2025-03-08 (תיקון v4 שרץ בטעות)."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT value FROM settings WHERE key='rotation_v5_migrated'"
        ).fetchone()
        if already:
            return
        conn.execute(
            "UPDATE rotation_config SET start_date='2025-03-08'"
        )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value)"
            " VALUES ('rotation_v5_migrated', '1')"
        )


try:
    migrate_rotation_v5()
    _log.info("migrate_rotation_v5: OK")
except Exception:
    _log.error("migrate_rotation_v5 FAILED:\n%s", traceback.format_exc())


def migrate_rotation_v6() -> None:
    """מיגרציה חד-פעמית: בוחניק → גיל בוחניק בפקחים slot[0]."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT value FROM settings WHERE key='rotation_v6_migrated'"
        ).fetchone()
        if already:
            return
        role = conn.execute(
            "SELECT id FROM rotation_roles WHERE name='פקחים'"
        ).fetchone()
        if role:
            slot = conn.execute(
                "SELECT id, names FROM rotation_slots WHERE role_id=? AND slot_num=0",
                (role["id"],),
            ).fetchone()
            if slot:
                names = _json.loads(slot["names"])
                names = ["גיל בוחניק" if n == "בוחניק" else n for n in names]
                conn.execute(
                    "UPDATE rotation_slots SET names=? WHERE id=?",
                    (_json.dumps(names, ensure_ascii=False), slot["id"]),
                )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value)"
            " VALUES ('rotation_v6_migrated', '1')"
        )


try:
    migrate_rotation_v6()
    _log.info("migrate_rotation_v6: OK")
except Exception:
    _log.error("migrate_rotation_v6 FAILED:\n%s", traceback.format_exc())


def migrate_rotation_v7() -> None:
    """מיגרציה חד-פעמית: מעבר ל-9 slots — כל תקופה עם שיבוץ עצמאי."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT value FROM settings WHERE key='rotation_v7_migrated'"
        ).fetchone()
        if already:
            return
        conn.execute("UPDATE rotation_config SET start_date='2026-03-08' WHERE id=1")
        for role_name, slots in _ROTATION_9SLOTS["roles"].items():
            role = conn.execute(
                "SELECT id FROM rotation_roles WHERE name=?", (role_name,)
            ).fetchone()
            if not role:
                continue
            role_id = role["id"]
            for slot_num, names in enumerate(slots):
                existing = conn.execute(
                    "SELECT id FROM rotation_slots WHERE role_id=? AND slot_num=?",
                    (role_id, slot_num),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE rotation_slots SET names=? WHERE role_id=? AND slot_num=?",
                        (_json.dumps(names, ensure_ascii=False), role_id, slot_num),
                    )
                else:
                    conn.execute(
                        "INSERT INTO rotation_slots (role_id, slot_num, names) VALUES (?, ?, ?)",
                        (role_id, slot_num, _json.dumps(names, ensure_ascii=False)),
                    )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('rotation_v7_migrated', '1')"
        )


try:
    migrate_rotation_v7()
    _log.info("migrate_rotation_v7: OK")
except Exception:
    _log.error("migrate_rotation_v7 FAILED:\n%s", traceback.format_exc())


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
            conn.execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (name,))
            gid = conn.execute(
                "SELECT id FROM guards WHERE name=?", (name,)
            ).fetchone()["id"]

            conn.execute(
                "INSERT INTO absences (guard_id, left_at, returned_at, reason) VALUES (?,?,?,?)",
                (gid, left_at, returned_at, reason),
            )

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
        guards = conn.execute("SELECT name FROM guards WHERE is_active = 1").fetchall()
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
    is_active: Optional[bool] = None


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


class AlertThresholdItem(BaseModel):
    minutes: int
    level: str  # "warning" | "danger" | "critical"


class SettingsBody(BaseModel):
    alert_minutes: Optional[int] = None
    alert_thresholds: Optional[List[AlertThresholdItem]] = None


class SeedAbsenceItem(BaseModel):
    name: str
    left_at: str


class SeedAbsencesBody(BaseModel):
    guards: list[SeedAbsenceItem]


class RotationConfigUpdateBody(BaseModel):
    start_date: str
    period_days: int = 2


class RotationPeriodUpdateBody(BaseModel):
    start_date: str
    end_date: str


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
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()]
            counts = {}
            for t in tables:
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        return {"status": "ok", "db": "sqlite", "tables": counts}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── PIN ───────────────────────────────────────────────────────────────────────
@app.get("/api/pin/required")
def pin_required():
    return {"required": bool(os.getenv("PIN_CODE", ""))}


@app.get("/api/pin/verify")
def verify_pin(pin: str = Query(...)):
    admin_pin = os.getenv("PIN_CODE", "")
    viewer_pin = os.getenv("VIEWER_PIN_CODE", "")
    if not admin_pin:
        return {"ok": True, "mode": "admin"}
    if pin == admin_pin:
        return {"ok": True, "mode": "admin"}
    if viewer_pin and pin == viewer_pin:
        return {"ok": True, "mode": "viewer"}
    return {"ok": False}


# ── Guards ────────────────────────────────────────────────────────────────────
@app.get("/api/guards")
def list_guards(include_inactive: bool = False):
    now = datetime.now()
    stats = compute_stats(now)
    with get_conn() as conn:
        if include_inactive:
            guards = conn.execute("SELECT * FROM guards ORDER BY name").fetchall()
        else:
            guards = conn.execute("SELECT * FROM guards WHERE is_active = 1 ORDER BY name").fetchall()
    result = []
    for g in guards:
        s = stats.get(g["name"], {"past": 0, "future": 0})
        result.append({
            "id": g["id"],
            "name": g["name"],
            "phone": g["phone"],
            "role": g["role"],
            "is_active": bool(g["is_active"]),
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
            cur = conn.execute("INSERT OR IGNORE INTO guards (name) VALUES (?)", (name,))
            if cur.rowcount > 0:
                added.append(name)
            else:
                skipped.append(name)
    return {"added": added, "skipped": skipped}


@app.put("/api/guards/{guard_id}")
def update_guard(guard_id: int, body: GuardUpdateBody):
    with get_conn() as conn:
        row = conn.execute("SELECT name, is_active FROM guards WHERE id=?", (guard_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Guard not found")
        old_name = row["name"]
        next_is_active = int(body.is_active) if body.is_active is not None else int(row["is_active"])
        try:
            conn.execute(
                "UPDATE guards SET name=?,phone=?,role=?,is_active=? WHERE id=?",
                (body.name, body.phone, body.role, next_is_active, guard_id),
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
                # Propagate name change to rotation_slots
                for slot in conn.execute("SELECT id,names FROM rotation_slots").fetchall():
                    names_list = _json.loads(slot["names"])
                    if old_name in names_list:
                        new_names_list = [body.name if n == old_name else n for n in names_list]
                        conn.execute(
                            "UPDATE rotation_slots SET names=? WHERE id=?",
                            (_json.dumps(new_names_list, ensure_ascii=False), slot["id"]),
                        )
        except _IntegrityError:
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


@app.put("/api/shifts/{shift_id}")
def update_shift(shift_id: int, body: ShiftItem):
    with get_conn() as conn:
        conn.execute(
            "UPDATE shifts SET start_time=?, end_time=?, names=? WHERE id=?",
            (body.start_time, body.end_time, ",".join(body.names), shift_id),
        )
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
    thresholds = []
    if s.get("alert_thresholds"):
        try:
            thresholds = _json.loads(s["alert_thresholds"])
        except Exception:
            thresholds = []
    return {
        "alert_minutes": int(s["alert_minutes"]) if s.get("alert_minutes") else None,
        "alert_thresholds": thresholds,
    }


def _upsert_setting(conn, key: str, value: str):
    conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))


@app.post("/api/settings")
def update_settings(body: SettingsBody):
    with get_conn() as conn:
        if body.alert_minutes is not None:
            _upsert_setting(conn, "alert_minutes", str(body.alert_minutes))
        else:
            conn.execute("DELETE FROM settings WHERE key='alert_minutes'")
        if body.alert_thresholds is not None:
            _upsert_setting(conn, "alert_thresholds", _json.dumps([t.dict() for t in body.alert_thresholds]))
    return {"ok": True}


# ── Absences ──────────────────────────────────────────────────────────────────
@app.get("/api/absences")
def list_absences():
    with get_conn() as conn:
        guards = conn.execute("SELECT * FROM guards WHERE is_active = 1 ORDER BY name").fetchall()
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


@app.get("/api/absences/active-on")
def absences_active_on(date: str):
    """
    Return absences that were ACTIVE on the given date (YYYY-MM-DD).
    Overlap query: left_at <= date AND (returned_at IS NULL OR returned_at >= date)
    """
    day_start = date + "T00:00:00"
    day_end   = date + "T23:59:59"
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT g.name, a.reason
            FROM absences a
            JOIN guards g ON g.id = a.guard_id
            WHERE a.left_at <= ?
              AND (a.returned_at IS NULL OR a.returned_at >= ?)
            """,
            (day_end, day_start),
        ).fetchall()
    return [{"name": r["name"], "reason": r["reason"]} for r in rows]


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


@app.post("/api/admin/test-backup")
def test_backup_endpoint(delay_minutes: int = 2):
    """Schedule a one-time test backup N minutes from now."""
    import traceback
    try:
        scheduled_at = schedule_test_backup(delay_minutes)
        return {"ok": True, "scheduled_at": scheduled_at, "message": f"גיבוי בדיקה מתוזמן ל-{scheduled_at}"}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}



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


# ── Rotation ──────────────────────────────────────────────────────────────────
def _default_rotation_period_ranges(start_date: str, count: int) -> List[dict]:
    try:
        origin = date.fromisoformat(start_date)
    except Exception:
        origin = date.today()

    # First Sunday on/after origin
    days_to_sunday = 0 if origin.weekday() == 6 else (6 - origin.weekday())
    anchor = origin + timedelta(days=days_to_sunday)
    today = date.today()
    days_since_anchor = (today - anchor).days
    cycle_number = max(0, days_since_anchor // 21)
    cycle_start = anchor + timedelta(days=cycle_number * 21)

    # א-ג, ג-ה, ו-א
    period_offsets = [0, 2, 5]
    rows: List[dict] = []
    for i in range(count):
        week = i // 3
        period_idx = i % 3
        start_d = cycle_start + timedelta(days=week * 7 + period_offsets[period_idx])
        end_d = start_d + timedelta(days=2)
        rows.append({
            "slot_num": i,
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
        })
    return rows


def _ensure_rotation_period_ranges(conn, start_date: str, max_slots: int) -> None:
    existing = conn.execute("SELECT slot_num FROM rotation_period_ranges").fetchall()
    existing_slots = {int(r["slot_num"]) for r in existing}
    defaults = _default_rotation_period_ranges(start_date, max_slots)
    for p in defaults:
        if p["slot_num"] in existing_slots:
            continue
        conn.execute(
            "INSERT INTO rotation_period_ranges (slot_num, start_date, end_date) VALUES (?, ?, ?)",
            (p["slot_num"], p["start_date"], p["end_date"]),
        )


def _build_rotation_response(conn) -> dict:
    cfg = conn.execute("SELECT start_date, period_days FROM rotation_config WHERE id=1").fetchone()
    roles = conn.execute("SELECT * FROM rotation_roles ORDER BY position").fetchall()
    slots_all = conn.execute("SELECT * FROM rotation_slots ORDER BY slot_num").fetchall()
    slots_map: dict = {}
    for sl in slots_all:
        slots_map.setdefault(sl["role_id"], {})[sl["slot_num"]] = _json.loads(sl["names"])
    # Dynamic slot count: use max slot_num across all roles (at least 9)
    all_slot_nums = [sl["slot_num"] for sl in slots_all]
    max_slots = max(all_slot_nums) + 1 if all_slot_nums else 9
    max_slots = max(max_slots, 9)
    cfg_start = cfg["start_date"] if cfg else "2025-03-08"
    _ensure_rotation_period_ranges(conn, cfg_start, max_slots)

    roles_out = []
    for r in roles:
        s = slots_map.get(r["id"], {})
        roles_out.append({
            "id": r["id"],
            "name": r["name"],
            "position": r["position"],
            "slots": [s.get(i, []) for i in range(max_slots)],
        })

    period_rows = conn.execute(
        "SELECT slot_num, start_date, end_date FROM rotation_period_ranges ORDER BY slot_num"
    ).fetchall()
    period_map = {int(p["slot_num"]): p for p in period_rows}
    default_periods = _default_rotation_period_ranges(cfg_start, max_slots)
    periods_out = []
    for i in range(max_slots):
        row = period_map.get(i) or default_periods[i]
        periods_out.append({
            "slot_num": i,
            "start_date": row["start_date"],
            "end_date": row["end_date"],
        })

    return {
        "start_date": cfg_start,
        "period_days": cfg["period_days"] if cfg else 2,
        "periods": periods_out,
        "roles": roles_out,
    }


@app.get("/api/rotation")
def get_rotation():
    with get_conn() as conn:
        return _build_rotation_response(conn)


@app.put("/api/rotation/config")
def update_rotation_config(body: RotationConfigUpdateBody):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO rotation_config (id, start_date, period_days) VALUES (1, ?, ?)",
            (body.start_date, body.period_days),
        )
    return {"ok": True}


@app.put("/api/rotation/periods/{slot_num}")
def update_rotation_period(slot_num: int, body: RotationPeriodUpdateBody, force: bool = False):
    if slot_num < 0:
        raise HTTPException(400, "slot_num must be >= 0")
    try:
        start_d = date.fromisoformat(body.start_date)
        end_d = date.fromisoformat(body.end_date)
    except Exception:
        raise HTTPException(400, "Dates must be in YYYY-MM-DD format")
    if end_d <= start_d:
        raise HTTPException(400, "end_date must be after start_date")

    with get_conn() as conn:
        if not force:
            overlaps = conn.execute(
                "SELECT slot_num, start_date, end_date FROM rotation_period_ranges "
                "WHERE slot_num <> ?",
                (slot_num,),
            ).fetchall()
            for row in overlaps:
                other_start = date.fromisoformat(row["start_date"])
                other_end = date.fromisoformat(row["end_date"])
                # Half-open interval overlap: [start, end)
                if start_d < other_end and end_d > other_start:
                    raise HTTPException(
                        400,
                        f"Date range overlaps with slot {row['slot_num']} ({row['start_date']}..{row['end_date']})",
                    )

        conn.execute(
            "INSERT INTO rotation_period_ranges (slot_num, start_date, end_date) VALUES (?, ?, ?) "
            "ON CONFLICT (slot_num) DO UPDATE SET start_date=EXCLUDED.start_date, end_date=EXCLUDED.end_date",
            (slot_num, body.start_date, body.end_date),
        )
    return {"ok": True}


@app.delete("/api/rotation/slots/all")
def clear_all_rotation_slots():
    """Clear all guard assignments from all slots (keeps roles and period ranges)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM rotation_slots")
    return {"ok": True}


@app.delete("/api/rotation/periods/{slot_num}")
def delete_rotation_period(slot_num: int):
    if slot_num < 0:
        raise HTTPException(400, "slot_num must be >= 0")
    with get_conn() as conn:
        # Remove this slot's date range and guard assignments
        conn.execute("DELETE FROM rotation_period_ranges WHERE slot_num = ?", (slot_num,))
        conn.execute("DELETE FROM rotation_slots WHERE slot_num = ?", (slot_num,))
        # Shift every slot after the deleted one down by 1
        conn.execute(
            "UPDATE rotation_period_ranges SET slot_num = slot_num - 1 WHERE slot_num > ?",
            (slot_num,),
        )
        conn.execute(
            "UPDATE rotation_slots SET slot_num = slot_num - 1 WHERE slot_num > ?",
            (slot_num,),
        )
    return {"ok": True}


@app.post("/api/rotation/roles", status_code=201)
def add_rotation_role(body: RotationRoleCreateBody):
    with get_conn() as conn:
        max_pos = conn.execute("SELECT MAX(position) as m FROM rotation_roles").fetchone()["m"]
        pos = (max_pos or 0) + 1
        cur = conn.execute(
            "INSERT INTO rotation_roles (name, position) VALUES (?, ?)",
            (body.name, pos),
        )
        role_id = cur.lastrowid
        for slot_num in range(9):
            conn.execute(
                "INSERT INTO rotation_slots (role_id, slot_num, names) VALUES (?, ?, ?)",
                (role_id, slot_num, "[]"),
            )
    return {"ok": True, "id": role_id}


@app.put("/api/rotation/roles/{role_id}")
def update_rotation_role(role_id: int, body: RotationRoleUpdateBody):
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM rotation_roles WHERE id=?", (role_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Role not found")
        if body.position is not None:
            conn.execute(
                "UPDATE rotation_roles SET name=?, position=? WHERE id=?",
                (body.name, body.position, role_id),
            )
        else:
            conn.execute(
                "UPDATE rotation_roles SET name=? WHERE id=?",
                (body.name, role_id),
            )
    return {"ok": True}


@app.delete("/api/rotation/roles/{role_id}")
def delete_rotation_role(role_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM rotation_slots WHERE role_id=?", (role_id,))
        conn.execute("DELETE FROM rotation_roles WHERE id=?", (role_id,))
    return {"ok": True}


@app.put("/api/rotation/roles/{role_id}/slots")
def update_rotation_slots(role_id: int, body: RotationSlotsUpdateBody):
    if len(body.slots) < 9:
        raise HTTPException(400, "Must provide at least 9 slots")
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM rotation_roles WHERE id=?", (role_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Role not found")
        conn.execute("DELETE FROM rotation_slots WHERE role_id=?", (role_id,))
        for slot_num, names in enumerate(body.slots):
            conn.execute(
                "INSERT INTO rotation_slots (role_id, slot_num, names) VALUES (?, ?, ?)",
                (role_id, slot_num, _json.dumps(names, ensure_ascii=False)),
            )
    return {"ok": True}


# ── Sync helpers ──────────────────────────────────────────────────────────────

def _apply_sync(conn, name_to_roles: dict, guards_all: list) -> dict:
    """
    Given a name→{role_name,...} map (from rotation or schedule), match guards
    using prefix matching and return a sync result dict.

    Prefix rule: a rotation/schedule token T matches a guard G when
      G["name"].startswith(T)  (case-insensitive, stripped)
    If T matches multiple guards it becomes a conflict.
    If multiple rotation tokens resolve to the same guard they also conflict.
    Guards not matched at all are left unchanged.
    """
    # Build guard lookup: lower-cased name → guard row
    guard_by_lower = {g["name"].lower(): g for g in guards_all}

    # For each token in name_to_roles, find matching guards (prefix match)
    # token_to_guard_roles: guard_name → {role_name, ...}
    token_to_guard_roles: dict = {}  # guard_name -> set of roles
    unresolved: list = []            # tokens that matched 0 or 2+ guards

    for token, roles_set in name_to_roles.items():
        token_lower = token.lower()
        matches = [
            g["name"] for g in guards_all
            if g["name"].lower().startswith(token_lower)
        ]
        if len(matches) == 0:
            unresolved.append(token)
        elif len(matches) > 1:
            # Ambiguous prefix — treat as conflict for all matched guards
            for gname in matches:
                for role_name in roles_set:
                    token_to_guard_roles.setdefault(gname, set()).add(role_name)
        else:
            gname = matches[0]
            for role_name in roles_set:
                token_to_guard_roles.setdefault(gname, set()).add(role_name)

    # Guards whose resolved roles conflict (appear in multiple roles)
    conflicts = [
        {"name": gname, "roles": list(roles_set)}
        for gname, roles_set in token_to_guard_roles.items()
        if len(roles_set) > 1
    ]
    conflict_guard_names = {c["name"] for c in conflicts}

    # Update guards that have exactly one resolved role
    updated = []
    for gname, roles_set in token_to_guard_roles.items():
        if gname in conflict_guard_names:
            continue
        new_role = next(iter(roles_set))
        g = guard_by_lower.get(gname.lower())
        if g is None:
            continue
        if g["role"] != new_role:
            conn.execute(
                "UPDATE guards SET role=? WHERE id=?",
                (new_role, g["id"]),
            )
            updated.append({
                "name": g["name"],
                "old_role": g["role"],
                "new_role": new_role,
            })

    return {
        "updated": updated,
        "conflicts": conflicts,
        "unknown_in_rotation": unresolved,
    }


# ── Sync rotation ↔ guards ────────────────────────────────────────────────────

@app.post("/api/sync/rotation-guards")
def sync_rotation_guards():
    """
    Cross-reference rotation_slots ↔ guards using prefix matching:
    1. Build name→role map from rotation slots
    2. Match guards by prefix (e.g. "שלומי" matches "שלומי בן ישי")
    3. Update each guard's role if uniquely resolved
    4. Return summary: updated, conflicts, unknown tokens
    """
    with get_conn() as conn:
        roles = conn.execute("SELECT id, name FROM rotation_roles").fetchall()
        slots_all = conn.execute("SELECT role_id, names FROM rotation_slots").fetchall()
        guards_all = conn.execute("SELECT id, name, role FROM guards").fetchall()

        # Build name → {role_name, ...} map from rotation slots
        name_to_roles: dict = {}
        for slot in slots_all:
            role_name = next((r["name"] for r in roles if r["id"] == slot["role_id"]), None)
            if not role_name:
                continue
            for name in _json.loads(slot["names"]):
                name = name.strip()
                if not name:
                    continue
                name_to_roles.setdefault(name, set()).add(role_name)

        return _apply_sync(conn, name_to_roles, guards_all)


# ── Sync schedule ↔ guards ────────────────────────────────────────────────────

@app.post("/api/sync/schedule-guards")
def sync_schedule_guards():
    """
    Cross-reference schedule rows ↔ guards using prefix matching.
    The schedule has rows: [{role: "קצינים", cells: [[name,...], ...]}, ...]
    All unique names across all cells for a given role are used to assign that role.
    """
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='schedule_json'").fetchone()
        guards_all = conn.execute("SELECT id, name, role FROM guards").fetchall()

    schedule = _json.loads(row["value"]) if row else _DEFAULT_SCHEDULE

    # Build name → {role_name, ...} map from schedule rows
    name_to_roles: dict = {}
    for srow in schedule.get("rows", []):
        role_name = srow.get("role", "").strip()
        if not role_name:
            continue
        for cell in srow.get("cells", []):
            for name in cell:
                name = name.strip()
                if not name:
                    continue
                name_to_roles.setdefault(name, set()).add(role_name)

    with get_conn() as conn:
        return _apply_sync(conn, name_to_roles, guards_all)


# ── Schedule ──────────────────────────────────────────────────────────────────
_DEFAULT_SCHEDULE = {
  "periods": [
    "08/3–10/3","10/3–12/3","13/3–15/3","15/3–17/3","17/3–19/3",
    "20/3–22/3","22/3–24/3","24/3–26/3","27/3–29/3"
  ],
  "rows": [
    {"role":"קצינים","cells":[["טל אבלין"],["זיו יוספי"],["שלמה מארק"],["זיו יוספי"],["שלמה מארק"],["טל אבלין"],["שלמה מארק"],["טל אבלין"],["זיו יוספי"]]},
    {"role":"מפקדים","cells":[["יוסף מנגיסטו"],["בועז רפאלי"],["אביתר כהן"],["בועז רפאלי"],["אביתר כהן"],["יוסף מנגיסטו"],["אביתר כהן"],["יוסף מנגיסטו"],["בועז רפאלי"]]},
    {"role":"פקחים","cells":[["שי כהן","גיל בוחניק","עוז גושן","חי מגנזי"],["חן דנסינגר","גיל שמואל","ירין וקנין"],["יוסי דדון","שלומי בן ישי","טלקר","אביתר ביטון"],["שי כהן","גיל בוחניק","עוז גושן","חי מגנזי"],["יוסי דדון","שלומי בן ישי","טלקר","אביתר ביטון"],["חן דנסינגר","גיל שמואל","ירין וקנין"],["יוסי דדון","שלומי בן ישי","טלקר","אביתר ביטון"],["חן דנסינגר","גיל שמואל","ירין וקנין"],["שי כהן","גיל בוחניק","עוז גושן","חי מגנזי"]]},
    {"role":"נהגים","cells":[["גיל פיצחאדה","עוז עובדיה"],["ישראל נעים","רומן פלדמן"],["מתנאל בנימין","נוני איילים"],["גיל פיצחאדה","עוז עובדיה"],["מתנאל בנימין","נוני איילים"],["ישראל נעים","רומן פלדמן"],["מתנאל בנימין","נוני איילים"],["ישראל נעים","רומן פלדמן"],["גיל פיצחאדה","עוז עובדיה"]]},
    {"role":"מטהרים","cells":[["אסף אבינועם","אליאב פדידה"],["נדב אברהם","לירן טביבזאדה","גל עמר"],["עמיר אודיע","שלומי סויסה"],["אסף אבינועם","אליאב פדידה"],["עמיר אודיע","שלומי סויסה"],["נדב אברהם","לירן טביבזאדה","גל עמר"],["עמיר אודיע","שלומי סויסה"],["נדב אברהם","לירן טביבזאדה","גל עמר"],["אסף אבינועם","אליאב פדידה"]]},
    {"role":"עתודאים","cells":[["שי שני","דוד סויסה","יובל מועלם","טל ברוקר"],["יהונתן פריאל","אור הדר","אריאל קרליך"],["רועי נגאוקר","מתן קזז","תומר שמאי"],["יהונתן פריאל","אור הדר","אריאל קרליך"],["רועי נגאוקר","מתן קזז","תומר שמאי"],["שי שני","דוד סויסה","יובל מועלם","טל ברוקר"],["רועי נגאוקר","מתן קזז","תומר שמאי"],["שי שני","דוד סויסה","יובל מועלם","טל ברוקר"],["יהונתן פריאל","אור הדר","אריאל קרליך"]]}
  ]
}


@app.get("/api/schedule")
def get_schedule():
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='schedule_json'").fetchone()
    if row:
        return _json.loads(row["value"])
    return _DEFAULT_SCHEDULE


@app.put("/api/schedule")
def update_schedule(body: dict):
    value = _json.dumps(body, ensure_ascii=False)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key,value) VALUES ('schedule_json',?)",
            (value,),
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
        if full_path.startswith("api") or full_path in ("docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(os.path.join(_DIST, "index.html"))
