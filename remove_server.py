#!/usr/bin/env python3
"""
remove_server.py - Delete a server and all associated data from a zBot SQLite database.

Usage:
  python remove_server.py <db_path> <server_id> [--confirm]

Without --confirm, prints a summary of rows that would be deleted (dry run).
With    --confirm, performs the deletion.
"""
import sqlite3
import sys


def count(cur, table, where, params):
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params)
    return cur.fetchone()[0]


def delete(cur, table, where, params):
    cur.execute(f"DELETE FROM {table} WHERE {where}", params)
    return cur.rowcount


def placeholder_list(ids):
    return "({})".format(",".join("?" * len(ids)))


def run(db_path: str, server_id: int, confirm: bool) -> None:
    verb = "Deleting" if confirm else "Would delete"
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT id, name FROM async_race_servers WHERE id = ?", (server_id,))
    row = cur.fetchone()
    if row is None:
        print(f"Server {server_id} not found in {db_path}.")
        con.close()
        return
    print(f"Server: {row[1]} (ID {row[0]}) in {db_path}")
    print()

    # Collect IDs for cascade deletes
    cur.execute("SELECT id FROM async_race_categories WHERE server_id = ?", (server_id,))
    category_ids = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT id FROM async_races WHERE server_id = ?", (server_id,))
    race_ids = [r[0] for r in cur.fetchall()]

    submission_ids = []
    if race_ids:
        cur.execute(
            f"SELECT id FROM async_submissions WHERE race_id IN {placeholder_list(race_ids)}",
            race_ids)
        submission_ids = [r[0] for r in cur.fetchall()]

    steps = []

    if submission_ids:
        w = f"submission_id IN {placeholder_list(submission_ids)}"
        steps.append(("async_race_extra_info", w, submission_ids,
                       count(cur, "async_race_extra_info", w, submission_ids)))

    if race_ids:
        w = f"race_id IN {placeholder_list(race_ids)}"
        steps.append(("async_submissions", w, race_ids,
                       count(cur, "async_submissions", w, race_ids)))
        steps.append(("async_race_rosters", w, race_ids,
                       count(cur, "async_race_rosters", w, race_ids)))

    # ExtraInfo assignments: server_id is a plain IntegerField; category_id and race_id are FKs
    ei_clauses, ei_params = ["server_id = ?"], [server_id]
    if category_ids:
        ei_clauses.append(f"category_id IN {placeholder_list(category_ids)}")
        ei_params.extend(category_ids)
    if race_ids:
        ei_clauses.append(f"race_id IN {placeholder_list(race_ids)}")
        ei_params.extend(race_ids)
    ei_where = " OR ".join(ei_clauses)
    steps.append(("async_race_extra_info_assignments", ei_where, ei_params,
                   count(cur, "async_race_extra_info_assignments", ei_where, ei_params)))

    if category_ids:
        for tbl, col in [
            ("async_race_category_points",    "category_id"),
            ("async_race_true_skill_params",  "category_id"),
            ("async_race_category_draw_threshold", "category_id"),
        ]:
            w = f"{col} IN {placeholder_list(category_ids)}"
            steps.append((tbl, w, category_ids, count(cur, tbl, w, category_ids)))

    # server_id is a plain IntegerField in these tables
    for tbl in ("async_race_messages", "startup_restore_state"):
        steps.append((tbl, "server_id = ?", (server_id,),
                       count(cur, tbl, "server_id = ?", (server_id,))))

    # server_id is a FK in these tables (column name is still just 'server_id' — peewee
    # does not append _id when the field name already ends in _id)
    for tbl in ("server_utils_vc_list", "trials"):
        steps.append((tbl, "server_id = ?", (server_id,),
                       count(cur, tbl, "server_id = ?", (server_id,))))

    if race_ids:
        steps.append(("async_races", "server_id = ?", (server_id,),
                       count(cur, "async_races", "server_id = ?", (server_id,))))

    if category_ids:
        steps.append(("async_race_categories", "server_id = ?", (server_id,),
                       count(cur, "async_race_categories", "server_id = ?", (server_id,))))

    steps.append(("async_race_extra_info_types", "server_id = ?", (server_id,),
                   count(cur, "async_race_extra_info_types", "server_id = ?", (server_id,))))

    steps.append(("async_race_servers", "id = ?", (server_id,), 1))

    total = 0
    for table, where, params, n in steps:
        print(f"  {verb} {n:>5} row(s) from {table}")
        total += n
        if confirm and n > 0:
            deleted = delete(cur, table, where, params)
            if deleted != n:
                print(f"    WARNING: expected {n}, deleted {deleted}")

    print()
    print(f"  Total: {total} row(s)")

    if confirm:
        con.commit()
        print()
        print("Done.")
    else:
        print()
        print("Dry run — nothing changed. Re-run with --confirm to apply.")

    con.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python remove_server.py <db_path> <server_id> [--confirm]")
        sys.exit(1)

    db_path = sys.argv[1]
    try:
        server_id = int(sys.argv[2])
    except ValueError:
        print(f"Invalid server_id: {sys.argv[2]}")
        sys.exit(1)

    confirm = "--confirm" in sys.argv
    run(db_path, server_id, confirm)
