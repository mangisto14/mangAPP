"""
backup_manager.py
-----------------
  1. init_schema()        – ensure /app/data dir exists
  2. run_backup()         – export all tables → ZIP → Telegram
  3. start/stop_scheduler() – APScheduler background thread (03:00 UTC daily)
  4. schedule_test_backup() – one-time test run N minutes from now

Env-vars required
-----------------
  TELEGRAM_TOKEN   123456789:ABCdef...
  CHAT_ID          -1001234567890
"""

import csv
import io
import logging
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH        = os.getenv("DB_PATH", "/app/data/database.db")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID        = os.getenv("CHAT_ID", "")

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




# ── Backup engine ─────────────────────────────────────────────────────────────

def _get_all_tables(conn: sqlite3.Connection) -> list[str]:
    """Return all user table names from the SQLite DB dynamically."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r["name"] for r in rows]


def _export_all_tables_zip(path: str) -> dict[str, int]:
    """
    Export every table in the DB to a CSV inside a ZIP file.
    Returns {table_name: row_count} for all tables.
    New tables are picked up automatically — no hardcoded names.
    """
    summary: dict[str, int] = {}
    with get_conn() as conn:
        tables = _get_all_tables(conn)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for table in tables:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                buf = io.StringIO()
                writer = csv.writer(buf)
                if rows:
                    writer.writerow(rows[0].keys())   # dynamic headers
                    writer.writerows(rows)
                else:
                    writer.writerow([])               # empty table → empty CSV
                zf.writestr(f"{table}.csv", buf.getvalue())
                summary[table] = len(rows)
                log.info("  %s: %d rows", table, len(rows))
    return summary


def _send_to_telegram(path: str, caption: str, filename: str) -> None:
    """Send a file to the configured Telegram chat."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise EnvironmentError("TELEGRAM_TOKEN and CHAT_ID env-vars must be set.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(path, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"document": (filename, f)},
            timeout=60,
        )
    resp.raise_for_status()
    log.info("Telegram response: %s", resp.json().get("ok"))


def run_backup() -> None:
    """Full backup flow: export all tables → ZIP → send to Telegram → cleanup."""
    log.info("Starting Backup...")
    tmp_path = None
    try:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        tmp = tempfile.NamedTemporaryFile(
            suffix=".zip",
            prefix=f"backup_{stamp}_",
            delete=False,
        )
        tmp_path = tmp.name
        tmp.close()

        summary = _export_all_tables_zip(tmp_path)
        total_rows = sum(summary.values())

        if total_rows == 0:
            log.info("Backup skipped – all tables empty.")
            return

        table_lines = "\n".join(f"  {t}: {n}" for t, n in summary.items())
        caption = (
            f"📦 Daily DB backup\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"Tables: {len(summary)} | Rows: {total_rows}\n"
            f"{table_lines}"
        )
        filename = f"backup_{stamp}.zip"
        _send_to_telegram(tmp_path, caption, filename)
        log.info("Backup Sent ✓ (%d tables, %d rows)", len(summary), total_rows)

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

# ── Recurring Reminders ───────────────────────────────────────────────────────

def _send_telegram_message(text: str) -> None:
    """Send a plain text message to the configured Telegram chat."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise EnvironmentError("TELEGRAM_TOKEN and CHAT_ID env-vars must be set.")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=30,
    )
    resp.raise_for_status()


def process_reminders() -> None:
    """Check and send due recurring reminders. Runs every minute."""
    from datetime import date as _date
    import sqlite3 as _sqlite3

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM recurring_reminders WHERE is_active=1 AND send_time=?",
                (current_time,),
            ).fetchall()

            for r in rows:
                # Skip if already sent today
                if r["last_sent_date"] == today_str:
                    continue

                # Check if today is a send day
                try:
                    start = _date.fromisoformat(r["start_date"])
                    today = _date.fromisoformat(today_str)
                    days_since_start = (today - start).days
                    if days_since_start < 0:
                        continue
                    if days_since_start % r["interval_days"] != 0:
                        continue
                except Exception:
                    continue

                # Send message
                try:
                    _send_telegram_message(r["message_text"])
                    conn.execute(
                        "UPDATE recurring_reminders SET last_sent_date=? WHERE id=?",
                        (today_str, r["id"]),
                    )
                    log.info("Reminder sent: %s (id=%d)", r["task_name"], r["id"])
                except Exception as e:
                    log.error("Failed to send reminder id=%d: %s", r["id"], e)

    except Exception as e:
        log.error("process_reminders error: %s", e)


def add_reminder(
    task_name: str,
    start_date: str,
    interval_days: int,
    send_time: str,
    message_text: str,
) -> int:
    """Helper: insert a new recurring reminder. Returns new row id."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO recurring_reminders
               (task_name, start_date, interval_days, send_time, message_text)
               VALUES (?, ?, ?, ?, ?)""",
            (task_name, start_date, interval_days, send_time, message_text),
        )
        log.info("Reminder added: %s (id=%d)", task_name, cur.lastrowid)
        return cur.lastrowid


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
    _scheduler.add_job(
        process_reminders,
        trigger="interval",
        minutes=1,
        id="process_reminders",
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


def schedule_test_backup(delay_minutes: int = 2) -> str:
    """Schedule a one-time test backup N minutes from now. Returns scheduled time."""
    global _scheduler
    if not _scheduler or not _scheduler.running:
        raise RuntimeError("Scheduler is not running.")
    run_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
    _scheduler.add_job(
        run_backup,
        trigger="date",
        run_date=run_at,
        id="test_backup",
        replace_existing=True,
    )
    log.info("Test backup scheduled for %s UTC", run_at.strftime("%H:%M:%S"))
    return run_at.strftime("%Y-%m-%d %H:%M:%S UTC")
