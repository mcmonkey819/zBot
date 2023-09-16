# -*- coding: utf-8 -*-
from peewee import *
import config.bot_config as bot_config

db_path = bot_config.PRODUCTION_DB
if bot_config.TEST_MODE:
    db_path = bot_config.TEST_DB
db = SqliteDatabase(db_path)

class AsyncRaceServer(Model):
    id                   = IntegerField(primary_key=True)
    name                 = CharField()
    mod_role_id          = IntegerField()
    admin_role_id        = IntegerField()
    category_mod_message = IntegerField(null=True)
    race_mod_message     = IntegerField(null=True)

    class Meta:
        table_name = 'async_race_servers'
        database = db

class AsyncRaceMessage(Model):
    id         = IntegerField(primary_key= True)
    server_id  = ForeignKeyField(AsyncRaceServer, backref='messages')
    channel_id = IntegerField()
    message_id = IntegerField()

    class Meta:
        table_name = 'async_race_messages'
        database = db

class AsyncRaceCategory(Model):
    id          = IntegerField(primary_key=True)
    server_id   = ForeignKeyField(AsyncRaceServer, backref='categories')
    name        = CharField()
    description = CharField()

    class Meta:
        table_name = 'async_race_categories'
        database = db

class AsyncRace(Model):
    id                      = IntegerField(primary_key= True)
    server_id               = ForeignKeyField(AsyncRaceServer, backref='races')
    start_datetime          = DateField(null=True)
    seed                    = CharField()
    hash                    = CharField(null=True)
    description             = CharField(null=True)
    additional_instructions = CharField(null=True)
    category_id             = ForeignKeyField(AsyncRaceCategory, backref='races')
    state                   = CharField(constraints=[Check('state in ("INACTIVE", "ACTIVE", "CLOSED")')])
    leaderboard_message     = ForeignKeyField(AsyncRaceMessage, backref='races', null=True)
    race_info_message       = ForeignKeyField(AsyncRaceMessage, backref='races', null=True)
    submission_role         = IntegerField(null=True)

    class Meta:
        table_name = 'async_races'
        database = db

####################################################################################################################
# Checks the database for the required tables, creating them if they don't exist.
def check_add_db_tables():
    tables = db.get_tables()

    if 'async_race_servers' not in tables:
        AsyncRaceServer.create_table()

    if 'async_race_messages' not in tables:
        AsyncRaceMessage.create_table()

    if 'async_race_categories' not in tables:
        AsyncRaceCategory.create_table()

    if 'async_races' not in tables:
        AsyncRace.create_table()
