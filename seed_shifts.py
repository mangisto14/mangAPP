"""
Seed script – inserts the scheduled shifts into the database.
Usage:
  Local:   python seed_shifts.py
  Railway: railway run python seed_shifts.py
"""

import sqlite3
import os

def db_path() -> str:
    if os.path.exists("/app/data"):
        return "/app/data/guard_system.db"
    return "guard_system.db"


def main():
    path = db_path()
    print(f"Connecting to: {path}")

    conn = sqlite3.connect(path)
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
    conn.commit()

    shifts = [
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

    inserted = 0
    skipped = 0
    for start, end, names in shifts:
        exists = conn.execute(
            "SELECT 1 FROM shifts WHERE start_time = ? AND end_time = ? AND names = ?",
            (start, end, names),
        ).fetchone()
        if exists:
            skipped += 1
        else:
            conn.execute(
                "INSERT INTO shifts (start_time, end_time, names) VALUES (?, ?, ?)",
                (start, end, names),
            )
            inserted += 1

    conn.commit()
    conn.close()

    total = conn.execute if False else inserted + skipped
    print(f"✅ הוכנסו: {inserted}  |  כבר קיימות: {skipped}  |  סה\"כ בסקריפט: {total}")


if __name__ == "__main__":
    main()
