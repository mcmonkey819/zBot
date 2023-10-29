from datetime import datetime, date
import logging
import nextcord

from db.zBot_db_orm import *

VarTypeInt      = 1
VarTypeStr      = 2
VarTypeGameTime = 3
VarTypeDateTime = 4

VartypeStrDict = {
    VarTypeInt:       "Integer",
    VarTypeStr:       "String",
    VarTypeGameTime:  "Game Time (H:MM:SS)",
    VarTypeDateTime:  "Date/Time",
}

VartypeSelectOptionList = [
    nextcord.SelectOption(label="Integer", value=VarTypeInt, description="Integer Value"),
    nextcord.SelectOption(label="String", value=VarTypeStr, description="String text up to 255 characters in length"),
    nextcord.SelectOption(label="Game Time (H:MM:SS)", value=VarTypeGameTime, description="Game time expressed in 'H:MM:SS' format"),
    nextcord.SelectOption(label="Date/Time", value=VarTypeDateTime, description="Date & Time string, typically something like 'YYYY-MM-DD HH:MM:SS'"),
]

ForfeitFinishTime = "23:59:59"

########################################################################################################################
# DB Getters
#####################################################################################################################
def get_server(server_id):
    server = None
    if server_id is not None:
        try:
            server = AsyncRaceServer.select().where(AsyncRaceServer.id == server_id).get()
        except:
            logging.info(f"Could not find server ID {server_id}")
    return server

#####################################################################################################################
def get_race(race_id):
    race = None
    if race_id is not None:
        try:
            race = AsyncRace.select().where(AsyncRace.id == race_id).get()
        except:
            logging.info(f"Could not find race ID {race_id}")
    return race

#####################################################################################################################
def get_category(category_id):
    category = None
    if category_id is not None:
        try:
            category = AsyncRaceCategory.select().where(AsyncRaceCategory.id == category_id).get()
        except:
            logging.info(f"Could not find category ID {category_id}")
    return category

#####################################################################################################################
def get_extra_info_type(info_type_id):
    info_type = None
    if info_type_id is not None:
        try:
            info_type = AsyncRaceExtraInfoType.select().where(AsyncRaceExtraInfoType.id == info_type_id).get()
        except:
            logging.info(f"Could not find Info Type ID {info_type_id}")
    return info_type

########################################################################################################################
def get_extra_info(submission, info_type_id):
    info = None
    if submission is not None:
        try:
            info = AsyncRaceExtraInfo.select().where(
                (AsyncRaceExtraInfo.submission_id == submission.id) &
                (AsyncRaceExtraInfo.info_type_id == info_type_id)).get()
        except:
            info = None
    return info

########################################################################################################################
def get_race_submission(user_id, race_id):
    try:
        submission = AsyncRaceSubmission.select().where(
            (AsyncRaceSubmission.user_id == user_id) &
            (AsyncRaceSubmission.race_id == race_id)).get()
    except:
        submission = None
    return submission

########################################################################################################################
def get_race_message(message_id):
    try:
        msg = AsyncRaceMessage().select().where(
            AsyncRaceMessage.id == message_id).get()
    except:
        msg = None
    return msg

########################################################################################################################
def get_race_assignment(user_id, race_id):
    try:
        a = AsyncRaceRoster().select().where(
                (AsyncRaceRoster.user_id == user_id) &
                (AsyncRaceRoster.race_id == race_id)).get()
    except:
        a = None
    return a

########################################################################################################################
def get_open_races(server_id):
    races = AsyncRace.select().where(AsyncRace.server_id == server_id)
    ret_list = []
    for r in races:
        # An open race is a race that does NOT have assignments
        if AsyncRaceRoster.select().where(AsyncRaceRoster.race_id == r.id).count() == 0:
            ret_list.append(r)
    return ret_list

########################################################################################################################
def get_assigned_races(user_id, server_id):
    return AsyncRace.select().join(AsyncRaceRoster).where(
        (AsyncRaceRoster.user_id == user_id) &
        (AsyncRace.server_id == server_id))

########################################################################################################################
# Other Utility Functions
#####################################################################################################################
# Returns the current date/time in the format used in the database
def zBot_now():
    return datetime.now().isoformat(timespec='minutes').replace('T', ' ')

#####################################################################################################################
def check_server_assignment_exists(info_type_id, server_id):
    try:
        a = AsyncRaceExtraInfoAssignment.select().where(
            (AsyncRaceExtraInfoAssignment.info_type_id == info_type_id) &
            (AsyncRaceExtraInfoAssignment.server_id == server_id)).get()
    except:
        a = None
    return a is not None

#####################################################################################################################
def check_category_assignment_exists(info_type_id, category_id):
    try:
        a = AsyncRaceExtraInfoAssignment.select().where(
                (AsyncRaceExtraInfoAssignment.info_type_id == info_type_id) &
                (AsyncRaceExtraInfoAssignment.category_id == category_id)).get()
    except:
        a = None
    return a is not None

#####################################################################################################################
def get_category_select_list(server_id):
    # Get the list of categories for this server
    categories = AsyncRaceCategory.select().where(AsyncRaceCategory.server_id == server_id)

    # Populate the SelectOption list with the category information
    select_list = []
    for c in categories:
        select_list.append(nextcord.SelectOption(label=c.name, value=c.id, description=c.description))
    return select_list

#####################################################################################################################
def get_race_select_list(server_id):
    # Get the list of race for this server
    races = AsyncRace.select().where(AsyncRace.server_id == server_id)

    # Populate the SelectOption list with the race information
    select_list = []
    for r in races:
        select_list.append(nextcord.SelectOption(label=f"{r.id} - {r.description[:15]}", value=r.id, description=r.description))
    return select_list

#####################################################################################################################
def get_extra_info_type_select_list(server_id, race =None):
    # Get the list of extra info types for this server
    types = AsyncRaceExtraInfoType.select().where(AsyncRaceExtraInfoType.server_id == server_id)
    default_list = []
    if race is not None:
        for r in race.extra_info_assignments:
            default_list.append(r.info_type_id.id)

    # Populate the SelectOption list with the race information
    select_list = []
    for t in types:
        select_list.append(nextcord.SelectOption(label=f"{t.name}", value=t.id, description=t.description, default=t.id in default_list))
    return select_list

########################################################################################################################
def race_has_submissions(race_id):
    submissions = AsyncRaceSubmission.select().where(
        AsyncRaceSubmission.race_id == race_id)

    if submissions is None or len(submissions) == 0:
        return False
    else:
        return True

########################################################################################################################
def assign_racer(user_id, race_id):
    # We only want to create a new row if one doesn't already exist
    if get_race_assignment(user_id, race_id) is None:
        assignment = AsyncRaceRoster()
        assignment.user_id = user_id
        assignment.race_id = race_id
        assignment.save()