"""
Migration: add startup_restore_state table + fix race info message data

Run against any target DB file:
    python db/migrate_add_startup_restore_state.py AsyncRaceTest.db
    python db/migrate_add_startup_restore_state.py AsyncRaceProd.db

Steps performed:
  1. Create startup_restore_state table (idempotent).
  2. Delete duplicate RaceInfo entries that have neither race_id nor category_id.
     These are the orphaned half of a double-save that occurred in pin_race_info.
  3. Backfill race_id on RaceInfo entries that have category_id but no race_id.
     These come from the auto-activate pinning path. Each is updated with the
     most recent active race for its category so startup restore can recreate them.
"""
import sys
import sqlite3


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS startup_restore_state (
    id           INTEGER PRIMARY KEY,
    server_id    INTEGER NOT NULL,
    channel_id   INTEGER NOT NULL,
    message_type INTEGER NOT NULL,
    category_id  INTEGER REFERENCES async_race_categories (id),
    race_id      INTEGER REFERENCES async_races (id)
);
"""

# Remove orphaned RaceInfo rows with no race_id and no category_id.
# These are the extra entries created by the now-fixed double-save in pin_race_info.
DELETE_ORPHANS = """
DELETE FROM async_race_messages
WHERE message_type = 1
  AND race_id IS NULL
  AND category_id IS NULL;
"""

# For RaceInfo entries that have category_id but no race_id (auto-activate pinning path),
# backfill race_id with the most recent active race (status=1) for that category.
BACKFILL_RACE_ID = """
UPDATE async_race_messages
SET race_id = (
    SELECT ar.id
    FROM async_races ar
    WHERE ar.category_id = async_race_messages.category_id
      AND ar.state = 1
    ORDER BY ar.id DESC
    LIMIT 1
)
WHERE message_type = 1
  AND race_id IS NULL
  AND category_id IS NOT NULL;
"""


def migrate(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(CREATE_TABLE)
        conn.commit()

        table_exists = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='startup_restore_state'"
        ).fetchone()[0]
        if table_exists:
            print(f"OK  startup_restore_state table present in {db_path}")
        else:
            print(f"ERROR  table creation silently failed in {db_path}")
            sys.exit(1)

        result = conn.execute(DELETE_ORPHANS)
        conn.commit()
        print(f"OK  removed {result.rowcount} orphaned RaceInfo row(s) with no race_id and no category_id")

        result = conn.execute(BACKFILL_RACE_ID)
        conn.commit()
        print(f"OK  backfilled race_id on {result.rowcount} RaceInfo row(s) from auto-activate pinning path")

    except Exception as e:
        print(f"ERROR  {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python db/migrate_add_startup_restore_state.py <db_file>")
        sys.exit(1)
    migrate(sys.argv[1])
