"""
Migration: add disable_auto_forfeit to async_race_categories and async_races
Run this script against the target database before deploying the matching code change.
Usage: python db/migrations/add_disable_auto_forfeit.py [db_path]
       Defaults to AsyncRaceProd.db if no path is given.
"""
import sqlite3
import sys


def run(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("PRAGMA table_info(async_race_categories)")
    columns = [row[1] for row in cur.fetchall()]
    if "disable_auto_forfeit" not in columns:
        cur.execute(
            "ALTER TABLE async_race_categories "
            "ADD COLUMN disable_auto_forfeit INTEGER NOT NULL DEFAULT 0"
        )
        con.commit()
        print(f"Added disable_auto_forfeit to async_race_categories in {db_path}.")
    else:
        print(f"async_race_categories.disable_auto_forfeit already exists in {db_path} — skipping.")

    cur.execute("PRAGMA table_info(async_races)")
    columns = [row[1] for row in cur.fetchall()]
    if "disable_auto_forfeit" not in columns:
        cur.execute(
            "ALTER TABLE async_races "
            "ADD COLUMN disable_auto_forfeit INTEGER NOT NULL DEFAULT 0"
        )
        con.commit()
        print(f"Added disable_auto_forfeit to async_races in {db_path}.")
    else:
        print(f"async_races.disable_auto_forfeit already exists in {db_path} — skipping.")

    con.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "AsyncRaceProd.db"
    run(path)
