"""
Migration: add Trials support
- Recreates async_race_servers with nullable mod_role_id/admin_role_id and new trials_* columns
- Creates trials table

Run against each target database before deploying the matching code change.
Usage: python db/migrations/add_trials_support.py [db_path]
       Defaults to AsyncRaceProd.db if no path is given.
"""
import sqlite3
import sys


def run(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # -------------------------------------------------------------------------
    # async_race_servers — recreate to make role IDs nullable and add trials_*
    # -------------------------------------------------------------------------
    cur.execute("PRAGMA table_info(async_race_servers)")
    columns = [row[1] for row in cur.fetchall()]

    if "trials_enabled" not in columns:
        # Create replacement table with nullable role IDs and new fields
        cur.execute("""
            CREATE TABLE "async_race_servers_new" (
                "id"                              INTEGER NOT NULL PRIMARY KEY,
                "name"                            VARCHAR(255) NOT NULL DEFAULT '',
                "mod_role_id"                     INTEGER,
                "admin_role_id"                   INTEGER,
                "enable_vc_create"                INTEGER NOT NULL DEFAULT 0,
                "trials_enabled"                  INTEGER NOT NULL DEFAULT 0,
                "trials_announcement_channel_id"  INTEGER,
                "trials_discord_category_id"      INTEGER
            )
        """)
        # Copy existing data; treat 0 as NULL for role IDs (0 is not a valid Discord snowflake)
        cur.execute("""
            INSERT INTO async_race_servers_new
                (id, name, mod_role_id, admin_role_id, enable_vc_create)
            SELECT
                id,
                COALESCE(name, ''),
                CASE WHEN mod_role_id   = 0 OR mod_role_id   IS NULL THEN NULL ELSE mod_role_id   END,
                CASE WHEN admin_role_id = 0 OR admin_role_id IS NULL THEN NULL ELSE admin_role_id END,
                enable_vc_create
            FROM async_race_servers
        """)
        con.commit()
        cur.execute("DROP TABLE async_race_servers")
        cur.execute("ALTER TABLE async_race_servers_new RENAME TO async_race_servers")
        con.commit()
        print(f"Migrated async_race_servers in {db_path}.")
    else:
        print(f"async_race_servers already migrated in {db_path} — skipping.")

    # -------------------------------------------------------------------------
    # trials — new table
    # -------------------------------------------------------------------------
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trials'")
    if cur.fetchone() is None:
        cur.execute("""
            CREATE TABLE "trials" (
                "id"                       INTEGER NOT NULL PRIMARY KEY,
                "server_id_id"             INTEGER NOT NULL REFERENCES "async_race_servers" ("id"),
                "short_name"               VARCHAR(255) NOT NULL,
                "display_name"             VARCHAR(255) NOT NULL,
                "short_description"        VARCHAR(255) NOT NULL DEFAULT '',
                "announcement_text"        TEXT,
                "state"                    INTEGER NOT NULL DEFAULT 0,
                "accept_signups"           INTEGER NOT NULL DEFAULT 1,
                "announcement_message_id"  INTEGER,
                "announcement_channel_id"  INTEGER,
                "general_channel_id"       INTEGER,
                "spoilers_channel_id"      INTEGER,
                "participant_role_id"      INTEGER,
                "finisher_role_id"         INTEGER,
                "category_id_id"           INTEGER REFERENCES "async_race_categories" ("id"),
                "current_race_id_id"       INTEGER REFERENCES "async_races" ("id"),
                "organizer_user_id"        INTEGER,
                "min_signups"              INTEGER,
                "min_signups_notified"     INTEGER NOT NULL DEFAULT 0
            )
        """)
        con.commit()
        print(f"Created trials table in {db_path}.")
    else:
        print(f"trials table already exists in {db_path} — skipping.")

    con.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "AsyncRaceProd.db"
    run(path)
