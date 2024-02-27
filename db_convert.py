import argparse
from asyncRaceBotConversion.convert_arb_db import *

# Define the command line arguments: --write_server_id, --clear_first, --clear_all
parser = argparse.ArgumentParser(description='Convert an asyncRaceBot database to the zBot database format')
parser.add_argument('--server_id', type=int, default=arb_server_id, help='The server id the database items will be stored as')
parser.add_argument('--clear_only', action='store_true', help='Clears the database rather than converting')
parser.add_argument('--clear_all', action='store_true', help='With `--clear-only will clear all database tables. Without this flag will only clear the data for `arb_server_id`')
parser.add_argument('--create_assignments', action='store_true', help='Creates race assignments for all of its category assignments')
args = parser.parse_args()

if args.clear_only:
    clear_database(clear_all=args.clear_all)
elif args.create_assignments:
    create_race_assignments_from_category_assignments(args.server_id)
else:
    convert_database(write_server_id=args.server_id)