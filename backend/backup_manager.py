"""
backup_manager.py
-----------------
Hybrid data infrastructure:
  1. init_schema()              – ensure /app/data dir exists
  2. sync_from_supabase()       – one-time migration: Supabase → backup SQLite
  3. maybe_migrate()            – run sync only when backup DB is empty
  4. migrate_all_from_supabase()– one-time full migration to main guard_system.db
  5. run_backup()               – export shifts CSV → send to Telegram
  6. start/stop_scheduler()     – APScheduler background thread (03:00 UTC daily)

Env-vars required
-----------------
  SUPABASE_URL                 https://<project>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    eyJ...
  TELEGRAM_TOKEN               123456789:ABCdef...
  CHAT_ID                      -1001234567890
"""

import csv
import logging
import os
import sqlite3
import tempfile
from datetime import datetime

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH                  = os.getenv("DB_PATH", "/app/data/database.db")
SUPABASE_URL             = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
TELEGRAM_TOKEN           = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID                  = os.getenv("CHAT_ID", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [backup] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("backup")

# ── SQLite helpers ────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema() -> None:
    """Ensure the data directory exists. Tables are created by main.py init_db()."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    log.info("Schema initialised (or already exists).")


def _shifts_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0]

# ── Supabase migration ────────────────────────────────────────────────────────

def sync_from_supabase() -> int:
    """
    Pull all rows from Supabase `shifts` table and upsert into local SQLite.
    Returns number of rows written.
    Uses the Supabase REST API directly (no extra SDK dependency).
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for migration."
        )

    log.info("Fetching shifts from Supabase...")

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Accept": "application/json",
    }

    # Fetch all rows (Supabase REST default limit is 1000; use range header for >1000)
    rows: list[dict] = []
    page_size = 1000
    offset = 0

    while True:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/shifts",
            headers={
                **headers,
                "Range": f"{offset}-{offset + page_size - 1}",
                "Range-Unit": "items",
                "Prefer": "count=none",
            },
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    if not rows:
        log.info("Supabase returned 0 rows.")
        return 0

    # Detect columns dynamically from first row
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)

    with get_conn() as conn:
        # Rebuild table from Supabase schema (drop + create → always matches source)
        col_defs = ", ".join(
            "id INTEGER PRIMARY KEY" if c == "id" else f'"{c}" TEXT'
            for c in cols
        )
        conn.execute("DROP TABLE IF EXISTS shifts")
        conn.execute(f"CREATE TABLE shifts ({col_defs})")
        log.info("Recreated shifts table with columns: %s", cols)

        conn.executemany(
            f"INSERT INTO shifts ({col_names}) VALUES ({placeholders})",
            [tuple(row.get(c) for c in cols) for row in rows],
        )

    log.info("Migration complete: %d rows written to SQLite.", len(rows))
    return len(rows)


def maybe_migrate() -> None:
    """
    Run sync_from_supabase() only if the local shifts table is empty.
    Safe to call on every startup – no-op if data already exists.
    """
    try:
        count = _shifts_count()
        if count > 0:
            log.info("SQLite has %d rows – skipping Supabase migration.", count)
            return
        log.info("SQLite is empty – starting initial migration from Supabase...")
        written = sync_from_supabase()
        log.info("Initial migration done: %d rows imported.", written)
    except EnvironmentError as e:
        log.warning("Migration skipped (config missing): %s", e)
    except requests.RequestException as e:
        log.error("Error: Supabase fetch failed – %s", e)
    except Exception as e:  # noqa: BLE001
        log.error("Error: migration unexpected failure – %s", e)

# ── Full Supabase → guard_system.db migration ────────────────────────────────

# Tables in dependency order (parents before children)
_TABLES = [
    "guards",
    "settings",
    "shifts",
    "absences",
    "rotation_config",
    "rotation_roles",
    "rotation_slots",
    "rotation_period_ranges",
]


def _main_db_path() -> str:
    """Mirror main.py db_path() logic."""
    volume = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if volume:
        return os.path.join(volume, "database.db")
    if os.path.exists("/app/data"):
        return "/app/data/database.db"
    return "database.db"


def _fetch_table(table: str) -> list[dict]:
    """Fetch all rows from a Supabase table via REST API (paginated)."""
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Accept": "application/json",
        "Prefer": "count=none",
    }
    rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**headers, "Range": f"{offset}-{offset + page_size - 1}", "Range-Unit": "items"},
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return rows


def migrate_all_from_supabase(force: bool = False) -> dict:
    """
    Full migration: pull every table from Supabase → database.db.
    Skips if guards table already has data, unless force=True.
    Returns summary dict with row counts per table.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        log.info("Supabase env-vars not set – skipping full migration.")
        return {}

    main_db = _main_db_path()
    conn = sqlite3.connect(main_db)
    conn.row_factory = sqlite3.Row
    try:
        count = conn.execute("SELECT COUNT(*) FROM guards").fetchone()[0]
        if count > 0 and not force:
            log.info("database.db already has %d guards – skipping migration (use force=True to override).", count)
            return {}
    except sqlite3.OperationalError:
        log.info("guards table not found yet – will run after init_db.")
        conn.close()
        return {}

    log.info("Starting full migration from Supabase → %s (force=%s)...", main_db, force)
    summary: dict[str, int] = {}
    try:
        for table in _TABLES:
            try:
                rows = _fetch_table(table)
                if not rows:
                    log.info("  %s: 0 rows (skipped)", table)
                    summary[table] = 0
                    continue
                cols = list(rows[0].keys())
                col_names = ", ".join(f'"{c}"' for c in cols)
                placeholders = ", ".join("?" * len(cols))
                def _coerce(v):
                    if isinstance(v, bool):
                        return int(v)
                    return v

                conn.executemany(
                    f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})",
                    [tuple(_coerce(row.get(c)) for c in cols) for row in rows],
                )
                conn.commit()
                log.info("  %s: %d rows imported.", table, len(rows))
                summary[table] = len(rows)
            except requests.RequestException as e:
                log.error("  %s: fetch failed – %s", table, e)
                summary[table] = f"fetch error: {e}"
            except sqlite3.Error as e:
                log.error("  %s: insert failed – %s", table, e)
                conn.rollback()
                summary[table] = f"insert error: {e}"
        total = sum(v for v in summary.values() if isinstance(v, int) and v > 0)
        log.info("Full migration complete: %d total rows → %s", total, main_db)
        return summary
    finally:
        conn.close()


# ── Backup engine ─────────────────────────────────────────────────────────────

def _export_shifts_csv(path: str) -> int:
    """Write shifts table to CSV; returns row count."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM shifts ORDER BY shift_date").fetchall()

    if not rows:
        log.info("Shifts table is empty – nothing to export.")
        return 0

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(rows[0].keys())
        writer.writerows(rows)

    log.info("Exported %d rows to %s", len(rows), path)
    return len(rows)


def _send_to_telegram(path: str, caption: str) -> None:
    """Send a file to the configured Telegram chat."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise EnvironmentError("TELEGRAM_TOKEN and CHAT_ID env-vars must be set.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(path, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"document": f},
            timeout=30,
        )
    resp.raise_for_status()
    log.info("Telegram response: %s", resp.json().get("ok"))


def run_backup() -> None:
    """Full backup flow: export CSV → send to Telegram → delete temp file."""
    log.info("Starting Backup...")
    tmp_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".csv",
            prefix=f"shifts_{datetime.utcnow().strftime('%Y%m%d_')}",
            delete=False,
        )
        tmp_path = tmp.name
        tmp.close()

        row_count = _export_shifts_csv(tmp_path)
        if row_count == 0:
            log.info("Backup skipped – empty table.")
            return

        caption = (
            f"📦 Daily DB backup\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Rows: {row_count}"
        )
        _send_to_telegram(tmp_path, caption)
        log.info("Backup Sent ✓")

    except EnvironmentError as e:
        log.error("Error: missing config – %s", e)
    except requests.RequestException as e:
        log.error("Error: Telegram send failed – %s", e)
    except Exception as e:  # noqa: BLE001
        log.error("Error: unexpected – %s", e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                log.info("Temp file deleted.")
            except OSError as e:
                log.warning("Could not delete temp file: %s", e)

# ── Scheduler ─────────────────────────────────────────────────────────────────

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """
    Start the APScheduler background thread.
    Call once at application startup (FastAPI lifespan / Streamlit init).
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        log.warning("Scheduler already running.")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_backup,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_backup",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("Backup scheduler started – next run at 03:00 UTC.")


def stop_scheduler() -> None:
    """Graceful shutdown (call from app lifespan teardown)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Backup scheduler stopped.")
