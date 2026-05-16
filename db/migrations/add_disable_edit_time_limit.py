"""
Migration: add disable_edit_time_limit to async_race_categories
Run this script against the target database before deploying the matching code change.
Usage: python db/migrations/add_disable_edit_time_limit.py [db_path]
       Defaults to AsyncRaceProd.db if no path is given.
"""
import sqlite3
import sys


def run(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Check whether the column already exists so the script is safe to re-run.
    cur.execute("PRAGMA table_info(async_race_categories)")
    columns = [row[1] for row in cur.fetchall()]
    if "disable_edit_time_limit" in columns:
        print(f"Column already exists in {db_path} — nothing to do.")
        con.close()
        return

    cur.execute(
        "ALTER TABLE async_race_categories "
        "ADD COLUMN disable_edit_time_limit INTEGER NOT NULL DEFAULT 0"
    )
    con.commit()
    print(f"Added disable_edit_time_limit to async_race_categories in {db_path}.")
    con.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "AsyncRaceProd.db"
    run(path)
