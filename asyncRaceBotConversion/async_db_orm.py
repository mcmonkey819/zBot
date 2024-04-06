# -*- coding: utf-8 -*-
from peewee import *

forty_bonks_server_id = 485284146063736832
forty_bonks_tourney_server_id = 828666862798635049
gmp_server_id = 473911155924926490
bot_testing_things_server_id = 853060981528723468

# Note uncomment vod_link when switching from forty-bonks
arb_server_id = forty_bonks_tourney_server_id

arb_db_path = "asyncRaceBotConversion/testDbUtil.db"
if arb_server_id == forty_bonks_server_id:
    arb_db_path = "asyncRaceBotConversion/fortyBonksRaceInfo.db"
elif arb_server_id == forty_bonks_tourney_server_id:
    arb_db_path = "asyncRaceBotConversion/FortyBonksTourneyRaceInfo.db"
elif arb_server_id == gmp_server_id:
    arb_db_path = "asyncRaceBotConversion/GmpRaceInfo.db"
arb_db = SqliteDatabase(arb_db_path)

class ArbRaceCategory(Model):
    id = IntegerField(primary_key=True)
    name = CharField()
    description = CharField()

    class Meta:
        table_name = 'race_categories'
        database = arb_db

class ArbAsyncRace(Model):
    id = IntegerField(primary_key= True)
    start = DateField()
    seed = CharField()
    description = CharField()
    additional_instructions = CharField()
    category_id = IntegerField()
    active = BooleanField(default=False)

    class Meta:
        table_name = 'async_races'
        database = arb_db

class ArbAsyncRacer(Model):
    user_id = IntegerField(primary_key=True)
    username = CharField()
    wheel_weight = IntegerField()

    class Meta:
        table_name = 'async_racers'
        database = arb_db

class ArbAsyncSubmission(Model):
    id = IntegerField(primary_key=True)
    submit_date = DateTimeField()
    race_id = IntegerField()
    user_id = IntegerField()
    username = CharField()
    finish_time_rta = CharField()
    finish_time_igt = CharField()
    collection_rate = IntegerField()
    next_mode = CharField(null=True)
    comment = CharField(null=True)
    vod_link = CharField(null=True)

    class Meta:
        table_name = 'async_submissions'
        database = arb_db

class ArbRaceRoster(Model):
    id = IntegerField(primary_key=True)
    race_id = IntegerField()
    user_id = IntegerField()
    race_info_time = DateTimeField(null=True)

    class Meta:
        table_name = 'async_race_rosters'
        database = arb_db
