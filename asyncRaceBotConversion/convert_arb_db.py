import traceback
from datetime import datetime, date

from db.zBot_db_orm import *
from db.db_util import *

from asyncRaceBotConversion.async_db_orm import *

def convert_database(clear_first=False):
    print("Starting database conversion")
    rta = None
    collection_rate = None
    next_mode = None
    vod_link = None

    # Clear the database
    if clear_first:
        print("--: Clearing the database")
        races = AsyncRace.select().where(AsyncRace.server_id == arb_server_id)
        for r in races:
            # Get the rosters for this race
            rosters = AsyncRaceRoster.select().where(AsyncRaceRoster.race_id == r.id)
            for ro in rosters:
                ro.delete_instance()

            # And the submissions
            subs = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == r.id)
            for s in subs:
                s.delete_instance()

            # Finally delete the race
            r.delete_instance()

        assigns = AsyncRaceExtraInfoAssignment.select().where(AsyncRaceExtraInfoAssignment.server_id == arb_server_id)
        for a in assigns:
            a.delete_instance()

        types = AsyncRaceExtraInfoType.select().where(AsyncRaceExtraInfoType.server_id == arb_server_id)
        for t in types:
            # Get the info entries for this type
            infos = AsyncRaceExtraInfo.select().where(AsyncRaceExtraInfo.info_type_id == t.id)
            for i in infos:
                i.delete_instance()
            # Then delete the type
            t.delete_instance()

        cats = AsyncRaceCategory.select().where(AsyncRaceCategory.server_id == arb_server_id)
        for c in cats:
            c.delete_instance()

    # Create Extra Info
    print("--: Creating Extra Info Types")
    collection_rate = AsyncRaceExtraInfoType()
    collection_rate.server_id = arb_server_id
    collection_rate.name = "Collection Rate"
    collection_rate.description = "Collection Rate as displayed at the end credits"
    collection_rate.var_type = VarTypeInt
    collection_rate.default_value = "216"
    collection_rate.save()

    if arb_server_id == forty_bonks_server_id:
        # 40 Bonks Weekly collects IGT, Collection Rate and the Next Mode suggestion for the wheel spin
        rta = AsyncRaceExtraInfoType()
        rta.server_id = arb_server_id
        rta.name = "Real Time"
        rta.description = "Real Time - i.e. LiveSplit time"
        rta.var_type = VarTypeGameTime
        rta.default_value = "23:59:59"
        rta.save()

        next_mode = AsyncRaceExtraInfoType()
        next_mode.server_id = arb_server_id
        next_mode.name = "Next Mode Suggestion"
        next_mode.description = "Suggestion for the next weekly mode for the biweekly wheel spin"
        next_mode.var_type = VarTypeStr
        next_mode.default_value = None
        next_mode.save()
    elif arb_server_id == forty_bonks_tourney_server_id:
        vod_link = AsyncRaceExtraInfoType()
        vod_link.server_id = arb_server_id
        vod_link.name = "VoD Link"
        vod_link.description = "Link to a video of race completion"
        vod_link.var_type = VarTypeStr
        vod_link.default_value = None
        vod_link.save()

    # Convert Categories
    cat_lookup = {}
    print("--: Converting categories")
    arb_cats = ArbRaceCategory.select()
    for c in arb_cats:
        zbot_cat = AsyncRaceCategory()
        zbot_cat.server_id = arb_server_id
        zbot_cat.name = c.name
        zbot_cat.description = c.description
        zbot_cat.save()
        cat_lookup[c.id] = zbot_cat.id

        # Assign Extra Info
        print("--: Assigning Extra Info")
        a = AsyncRaceExtraInfoAssignment()
        a.info_type_id = collection_rate.id
        a.server_id = arb_server_id
        a.category_id = zbot_cat.id
        a.required = True
        a.save()

        if arb_server_id == forty_bonks_server_id:
            a1 = AsyncRaceExtraInfoAssignment()
            a1.info_type_id = rta.id
            a1.server_id = arb_server_id
            a1.category_id = zbot_cat.id
            a1.save()

            a2 = AsyncRaceExtraInfoAssignment()
            a2.info_type_id = next_mode.id
            a2.server_id = arb_server_id
            a2.category_id = zbot_cat.id
            a2.save()
        elif arb_server_id == forty_bonks_tourney_server_id:
            a2 = AsyncRaceExtraInfoAssignment()
            a2.info_type_id = vod_link.id
            a2.server_id = arb_server_id
            a2.category_id = zbot_cat.id
            a2.save()

    # Convert Races
    race_lookup = {}
    print("--: Converting Races")
    arb_races = ArbAsyncRace.select()
    for r in arb_races:
        try:
            zbot_race = AsyncRace()
            zbot_race.server_id = arb_server_id
            zbot_race.create_datetime = r.start
            zbot_race.seed = r.seed
            zbot_race.description = r.description
            zbot_race.additional_instructions = r.additional_instructions
            zbot_race.category_id = cat_lookup[r.category_id]
            zbot_race.active = r.active
            zbot_race.save()
        except:
            print(f"Error converting race ID {r.id}. Category ID: {r.category_id}")
            traceback.print_exc()
            return

        race_lookup[r.id] = zbot_race.id

    # Convert Rosters
    print("--: Converting Rosters")
    arb_tables = arb_db.get_tables()
    if 'async_race_rosters' in arb_tables:
        arb_rosters = ArbRaceRoster.select()
        for r in arb_rosters:
            zbot_roster = AsyncRaceRoster()
            zbot_roster.race_id = race_lookup[r.race_id]
            zbot_roster.user_id = r.user_id
            zbot_roster.seed_time = r.race_info_time
            zbot_roster.save()

    # Convert Submissions
    print("--: Converting Submissions")
    arb_submissions = ArbAsyncSubmission.select()
    for s in arb_submissions:
        # Base Submission Data
        zbot_submission = AsyncRaceSubmission()
        zbot_submission.race_id = race_lookup[s.race_id]
        zbot_submission.user_id = s.user_id
        zbot_submission.submit_datetime = s.submit_date
        # Forty Bonks tourney server uses RTA as primary time
        if arb_server_id == forty_bonks_tourney_server_id:
            zbot_submission.finish_time = s.finish_time_rta
        else:
            # The other servers use IGT as primary
            zbot_submission.finish_time = s.finish_time_igt
        zbot_submission.save()

        # Extra Info
        if s.collection_rate is None:
            s.collection_rate = 216
        collection_rate_data = AsyncRaceExtraInfo()
        collection_rate_data.submission_id = zbot_submission.id
        collection_rate_data.info_type_id = collection_rate.id
        collection_rate_data.data = s.collection_rate
        collection_rate_data.save()

        if arb_server_id == forty_bonks_server_id:
            if s.finish_time_rta is not None:
                rta_data = AsyncRaceExtraInfo()
                rta_data.submission_id = zbot_submission.id
                rta_data.info_type_id = rta.id
                rta_data.data = s.finish_time_rta
                rta_data.save()

            if s.next_mode is not None:
                next_mode_data = AsyncRaceExtraInfo()
                next_mode_data.submission_id = zbot_submission.id
                next_mode_data.info_type_id = next_mode.id
                next_mode_data.data = s.next_mode
                next_mode_data.save()
        elif arb_server_id == forty_bonks_tourney_server_id:
            if s.vod_link is not None:
                vod_link_data = AsyncRaceExtraInfo()
                vod_link_data.submission_id = zbot_submission.id
                vod_link_data.info_type_id = vod_link.id
                vod_link_data.data = s.vod_link
                vod_link_data.save()

    print("Done!")

