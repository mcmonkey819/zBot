# -*- coding: utf-8 -*-
from peewee import *
import config.bot_config as bot_config
import logging

db_path = bot_config.PRODUCTION_DB
if bot_config.TEST_MODE:
    db_path = bot_config.TEST_DB
db = SqliteDatabase(db_path)

#####################################################################################################################
# Checks a race submission time string, returns True if it is properly formatted as H:MM:SS, False otherwise
def game_time_is_valid(self, time_str):
        valid_time_str = False
        parts = time_str.split(':')
        # Hours can be left off for short seeds
        if len(parts) >= 2 and len(parts) <= 3:
            hours = 0
            minutes = -1
            seconds = -1
            try:
                seconds = int(parts[-1])
                minutes = int(parts[-2])
                hours = 0
                if len(parts) == 3:
                    hours = int(parts[0])
            except ValueError:
                valid_time_str = False
            if hours >= 0 and hours <= 24 and minutes >= 0 and minutes <= 59 and seconds >= 0 and seconds <= 59:
               valid_time_str = True
        return valid_time_str

class AsyncRaceMessage(Model):
    id                      = IntegerField(primary_key= True)
    server_id               = IntegerField()
    channel_id              = IntegerField()
    message_id              = IntegerField(null=True)

    class Meta:
        table_name = 'async_race_messages'
        database = db

class AsyncRaceServer(Model):
    id                      = IntegerField(primary_key=True)
    name                    = CharField()
    mod_role_id             = IntegerField()
    admin_role_id           = IntegerField()
    category_mod_message    = IntegerField(null=True)
    race_mod_message        = IntegerField(null=True)
    racer_info_message      = IntegerField(null=True)

    class Meta:
        table_name = 'async_race_servers'
        database = db

class AsyncRaceCategory(Model):
    id                      = IntegerField(primary_key=True)
    server_id               = ForeignKeyField(AsyncRaceServer, backref='categories')
    name                    = CharField()
    description             = CharField()
    #extra_info_fields       = 

    class Meta:
        table_name = 'async_race_categories'
        database = db

class AsyncRace(Model):
    id                      = IntegerField(primary_key= True)
    server_id               = ForeignKeyField(AsyncRaceServer, backref='races')
    create_datetime         = DateField(null=True)
    seed                    = CharField()
    hash                    = CharField(null=True)
    description             = CharField(null=True)
    additional_instructions = CharField(null=True)
    submit_instructions     = CharField(null=True)
    category_id             = ForeignKeyField(AsyncRaceCategory, backref='races')
    active                  = BooleanField(default=False)
    leaderboard_message     = ForeignKeyField(AsyncRaceMessage, backref='races', null=True)
    race_info_message       = ForeignKeyField(AsyncRaceMessage, backref='races', null=True)
    submission_role         = IntegerField(null=True)

    class Meta:
        table_name = 'async_races'
        database = db

class AsyncRaceRoster(Model):
    id                      = IntegerField(primary_key= True)
    race_id                 = ForeignKeyField(AsyncRace, backref='rosters')
    user_id                 = IntegerField()
    seed_time               = DateField(null=True)

    class Meta:
        table_name = 'async_race_rosters'
        database = db

class AsyncRaceSubmission(Model):
    id                      = IntegerField(primary_key= True)
    race_id                 = ForeignKeyField(AsyncRace, backref='submissions')
    user_id                 = IntegerField()
    submit_datetime         = DateField(null=True)
    finish_time             = CharField()
    comment                 = CharField(null=True)

    class Meta:
        table_name = 'async_submissions'
        database = db

AsyncRaceExtraInfoServerAny = 0
class AsyncRaceExtraInfoType(Model):
    id                      = IntegerField(primary_key= True)
    # If server_id is None, info type can be used anywhere
    server_id               = IntegerField(null=True)
    name                    = CharField()
    description             = CharField()
    var_type                = IntegerField()
    default_value           = CharField()

    class Meta:
        table_name = 'async_race_extra_info_types'
        database = db

class AsyncRaceExtraInfo(Model):
    id                      = IntegerField(primary_key= True)
    submission_id           = ForeignKeyField(AsyncRaceSubmission, backref='extra_info')
    info_type_id            = ForeignKeyField(AsyncRaceExtraInfoType, backref='extra_info')
    data                    = CharField()

    class Meta:
        table_name = 'async_race_extra_info'
        database = db

class AsyncRaceExtraInfoAssignment(Model):
    id                      = IntegerField(primary_key= True)
    info_type_id            = ForeignKeyField(AsyncRaceExtraInfoType, backref='extra_info_assignments')
    server_id               = IntegerField(null=True)
    category_id             = ForeignKeyField(AsyncRaceCategory, backref='extra_info_assignments', null=True)
    race_id                 = ForeignKeyField(AsyncRace, backref='extra_info_assignments', null=True)
    required                = BooleanField(default=False)

    class Meta:
        table_name = 'async_race_extra_info_assignments'
        database = db

####################################################################################################################
# Deletes all existing tables, then recreates them.
def drop_add_db_tables():
    db.drop_tables([
        AsyncRaceServer,
        AsyncRaceMessage,
        AsyncRaceCategory,
        AsyncRace,
        AsyncRaceRoster,
        AsyncRaceSubmission,
        AsyncRaceExtraInfoType,
        AsyncRaceExtraInfo,
        AsyncRaceExtraInfoAssignment])
    add_db_tables()

####################################################################################################################
# Creates required tables.
def add_db_tables():
    db.create_tables([
        AsyncRaceServer,
        AsyncRaceMessage,
        AsyncRaceCategory,
        AsyncRace,
        AsyncRaceRoster,
        AsyncRaceSubmission,
        AsyncRaceExtraInfoType,
        AsyncRaceExtraInfo,
        AsyncRaceExtraInfoAssignment])

####################################################################################################################
# Recreates the indicated table
def recreate_table(table_name):
    logging.info(f"Attempting to recreate DB Table: {table_name}")
    match table_name:
        case "AsyncRaceServer":
            db.drop_tables([AsyncRaceServer])
            db.create_tables([AsyncRaceServer])
        case "AsyncRaceMessage":
            db.drop_tables([AsyncRaceMessage])
            db.create_tables([AsyncRaceMessage])
        case "AsyncRaceCategory":
            db.drop_tables([AsyncRaceCategory])
            db.create_tables([AsyncRaceCategory])
        case "AsyncRace":
            db.drop_tables([AsyncRace])
            db.create_tables([AsyncRace])
        case "AsyncRaceRoster":
            db.drop_tables([AsyncRaceRoster])
            db.create_tables([AsyncRaceRoster])
        case "AsyncRaceSubmission":
            db.drop_tables([AsyncRaceSubmission])
            db.create_tables([AsyncRaceSubmission])
        case "AsyncRaceExtraInfoType":
            db.drop_tables([AsyncRaceExtraInfoType])
            db.create_tables([AsyncRaceExtraInfoType])
        case "AsyncRaceExtraInfo":
            db.drop_tables([AsyncRaceExtraInfo])
            db.create_tables([AsyncRaceExtraInfo])
        case "AsyncRaceExtraInfoAssignment":
            db.drop_tables([AsyncRaceExtraInfoAssignment])
            db.create_tables([AsyncRaceExtraInfoAssignment])
        case _:
            logging.info(f"Unrecognized table name {table_name}")