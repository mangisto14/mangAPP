"""
backup_manager.py
-----------------
Daily SQLite backup → Telegram bot.
Schedule: every day at 03:00 (UTC) via APScheduler background thread.
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

DB_PATH       = os.getenv("DB_PATH", "/app/data/database.db")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID        = os.getenv("CHAT_ID", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [backup] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("backup")

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema() -> None:
    """Create tables if they don't exist yet (idempotent)."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS shifts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guard_name  TEXT    NOT NULL,
                shift_date  TEXT    NOT NULL,
                shift_type  TEXT    NOT NULL,
                notes       TEXT    DEFAULT ''
            );
        """)
    log.info("Schema initialised (or already exists).")

# ── Backup engine ─────────────────────────────────────────────────────────────

def _export_shifts_csv(path: str) -> int:
    """Write shifts table to CSV file; returns row count."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM shifts ORDER BY shift_date").fetchall()

    if not rows:
        log.info("Shifts table is empty – nothing to export.")
        return 0

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(rows[0].keys())   # header
        writer.writerows(rows)

    log.info("Exported %d rows to %s", len(rows), path)
    return len(rows)


def _send_to_telegram(path: str, caption: str) -> None:
    """Send a file to the configured Telegram chat."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise EnvironmentError(
            "TELEGRAM_TOKEN and CHAT_ID env-vars must be set."
        )

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
    """Full backup flow: export → send → cleanup."""
    log.info("Starting Backup...")

    tmp_path = None
    try:
        # 1. Export
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

        # 2. Send
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
        # 3. Cleanup – always delete temp file
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
    Call once at application startup (e.g. from FastAPI lifespan).
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        log.warning("Scheduler already running.")
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_backup,
        trigger=CronTrigger(hour=3, minute=0),   # 03:00 UTC daily
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
