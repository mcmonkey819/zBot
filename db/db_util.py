from datetime import datetime, date
import csv
import logging
import nextcord
import trueskill

from db.zBot_db_orm import *

class VarType:
    Int      = 1
    Str      = 2
    GameTime = 3
    DateTime = 4
    Float    = 5

    SelectOptionList = [
        nextcord.SelectOption(label="Integer",             value=Int,      description="Integer Value"),
        nextcord.SelectOption(label="String",              value=Str,      description="String text up to 255 characters in length"),
        nextcord.SelectOption(label="Game Time (H:MM:SS)", value=GameTime, description="Game time expressed in 'H:MM:SS' format"),
        nextcord.SelectOption(label="Date/Time",           value=DateTime, description="Date & Time string, typically something like 'YYYY-MM-DD HH:MM:SS'"),
        nextcord.SelectOption(label="Float",               value=Float,    description="Floating point number (e.g. 3.14)"),
]

class RaceState:
    Inactive  = 0
    Active    = 1
    Completed = 2

    SelectOptionList = [
        nextcord.SelectOption(label="Inactive",  value=Inactive,  description="Mark the race as inactive"),
        nextcord.SelectOption(label="Active",    value=Active,    description="Mark the race as active (accepting submissions)"),
        nextcord.SelectOption(label="Completed", value=Completed, description="Close the race to further submissions (and calculate score, if applicable)"),
    ]

    def to_str(state: int):
        if state == RaceState.Inactive:
            return "Inactive"
        elif state == RaceState.Active:
            return "Active"
        elif state == RaceState.Completed:
            return "Completed"
        else:
            return "Unknown State"

class PointsType:
    NoScoring = 0
    MarioKart = 1
    Trueskill = 2
    ParTime   = 3
    Fixed     = 4

    SelectOptionList = [
        nextcord.SelectOption(label="No Scoring", value=NoScoring, description="Do not assign points for races in this category"),
        nextcord.SelectOption(label="MarioKart",  value=MarioKart, description="Mario Kart style scoring"),
        nextcord.SelectOption(label="Trueskill",  value=Trueskill, description="Trueskill scoring"),
        nextcord.SelectOption(label="Par Time",   value=ParTime,   description="Scoring based on par time calculated from top finishers"),
        nextcord.SelectOption(label="Fixed",      value=Fixed,     description="3 points for a win, 1 point for a tie or close loss (configurable)"),
    ]

    def to_str(points_type: int):
        if points_type >= 0 and points_type < len(PointsType.SelectOptionList):
            return PointsType.SelectOptionList[points_type].label
        else:
            return "Unknown"

class RaceLeaderboardType:
    Points = 0
    RecentRace = 1

    def to_str(leaderboard_type: int):
        if leaderboard_type == RaceLeaderboardType.Points:
            return "Points"
        elif leaderboard_type == RaceLeaderboardType.RecentRace:
            return "Most Recent Race"
        else:
            return "Unknown Leaderboard Type"

class RaceMessageType:
    Leaderboard  = 0
    RaceInfo     = 1
    Menu         = 2
    Announcement = 3

class VcChannelType:
    Ignore        = 0  # Ignore this channel for dynamic VC creation
    Permanent     = 1  # Permanent VC that should not be deleted
    OnDemand      = 2  # VC created by the bot that can be deleted when empty

    def to_str(channel_type: int):
        if channel_type == VcChannelType.Ignore:
            return "Ignore"
        elif channel_type == VcChannelType.Permanent:
            return "Permanent"
        elif channel_type == VcChannelType.OnDemand:
            return "On Demand"
        else:
            return "Unknown"
        
class ValidationStatus:
    Unverified = 0
    Verified   = 1
    Rejected   = 2

    def to_str(validation_type: int):
        if validation_type == ValidationStatus.Unverified:
            return "Unverified"
        elif validation_type == ValidationStatus.Verified:
            return "Verified"
        elif validation_type == ValidationStatus.Rejected:
            return "Rejected"
        else:
            return "Unknown"

ForfeitFinishTime = "23:59:59"
ForfeitFinishTimeSeconds = (3600 * 23) + (60 * 59) + 59

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
def get_extra_info(submission_id, info_type_id):
    info = None
    try:
        info = AsyncRaceExtraInfo.select().where(
            (AsyncRaceExtraInfo.submission_id == submission_id) &
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
def get_race_submission_by_id(submission_id):
    try:
        submission = AsyncRaceSubmission.select().where(AsyncRaceSubmission.id == submission_id).get()
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
def get_category_race_info_messages(race):
    return AsyncRaceMessage.select().where(
        (AsyncRaceMessage.category_id == race.category_id.id) &
        (AsyncRaceMessage.message_type == RaceMessageType.RaceInfo))

########################################################################################################################
def get_assigned_racers(race_id):
    racers = AsyncRaceRoster.select().where(AsyncRaceRoster.race_id == race_id)
    return racers

########################################################################################################################
def is_assigned_race(race_id):
    racers = get_assigned_racers(race_id)
    if racers is None or len(racers) == 0:
        return False
    return True

########################################################################################################################
def get_open_races(server_id):
    races = AsyncRace.select().where(AsyncRace.server_id == server_id).order_by(AsyncRace.create_datetime.desc())
    ret_list = []
    for r in races:
        # An open race is a race that does NOT have assignments
        if AsyncRaceRoster.select().where(AsyncRaceRoster.race_id == r.id).count() == 0:
            ret_list.append(r)
    
    # Filter out inactive races
    ret_list = list(filter(lambda r: r.state != RaceState.Inactive, ret_list))
    return ret_list

########################################################################################################################
def get_available_open_races(server_id):
    # Start with all open races
    races = get_open_races(server_id)

    # Filter out completed races if the category does not allow submissions after a race is completed
    ret_list = []
    for r in races:
        if r.category_id.allow_submissions_after_completed or r.state != RaceState.Completed:
            ret_list.append(r)
    
    return ret_list

########################################################################################################################
def get_assigned_races(user_id, server_id, states=[RaceState.Active, RaceState.Completed]):
    races = AsyncRace.select().join(AsyncRaceRoster).where(
        (AsyncRaceRoster.user_id == user_id) &
        (AsyncRace.server_id == server_id)).order_by(AsyncRace.create_datetime.desc())
    
    if RaceState.Inactive not in states:
        races = list(filter(lambda r: r.state != RaceState.Inactive, races))

    if RaceState.Active not in states:
        races = list(filter(lambda r: r.state != RaceState.Active, races))

    if RaceState.Completed not in states:
        races = list(filter(lambda r: r.state != RaceState.Completed, races))

    return races

########################################################################################################################
def get_completed_races(user_id, server_id):
    open_races = get_open_races(server_id)
    open_races = list(filter(lambda r: r.state == RaceState.Completed, open_races))
    assigned_races = get_assigned_races(user_id, server_id, states=[RaceState.Completed])
    
    races = open_races + assigned_races
    
    return races

########################################################################################################################
def get_most_recent_race(category_id, include_completed=True):
    # This list will come sorted by create_datetime, so we can just walk through the list to find the most recent
    # active or completed race
    races = get_category_races(category_id)

    for r in races:
        if r.state == RaceState.Active:
            return r
        if include_completed and r.state == RaceState.Completed:
            return r

    return None

########################################################################################################################
def get_completed_races_by_category(category_id):
    races = get_category_races(category_id)
    races = list(filter(lambda r: r.state == RaceState.Completed, races))
    
    return races

########################################################################################################################
def get_create_category_points(category_id, user_id):
    try:
        cat_points_row = AsyncRaceCategoryPoints.select().where(
            (AsyncRaceCategoryPoints.user_id == user_id) & (AsyncRaceCategoryPoints.category_id == category_id)).get()
    except:
        cat_points_row = AsyncRaceCategoryPoints()
        cat_points_row.user_id = user_id
        cat_points_row.category_id = category_id
        cat_points_row.points = 0
        cat_points_row.save()
    return cat_points_row

########################################################################################################################
def get_category_submissions(user_id, category_id):
    cat_submissions = AsyncRaceSubmission.select().join(AsyncRace).where(
        (AsyncRaceSubmission.user_id == user_id) & (AsyncRace.category_id == category_id))
    return cat_submissions

########################################################################################################################
def get_category_races(category_id):
    races = AsyncRace.select().where(AsyncRace.category_id == category_id).order_by(AsyncRace.create_datetime.desc())
    return races

########################################################################################################################
def get_active_category_assignments(category_id):
    assignments = AsyncRaceRoster.select().join(AsyncRace).where(
        (AsyncRace.category_id == category_id) & (AsyncRace.state == RaceState.Active))
    return assignments

########################################################################################################################
def get_category_points(category_id):
    points = AsyncRaceCategoryPoints.select().where(
        AsyncRaceCategoryPoints.category_id == category_id).order_by(AsyncRaceCategoryPoints.points.desc())

    return points

########################################################################################################################
def get_category_points_by_id(points_id):
    try:
        points = AsyncRaceCategoryPoints.select().where(AsyncRaceCategoryPoints.id == points_id).get()
    except:
        points = None
    return points

########################################################################################################################
def get_category_trueskill_params(category_id):
    try:
        trueskill_params = AsyncRaceTrueSkillParams.select().where(
            AsyncRaceTrueSkillParams.category_id == category_id).get()
    except:
        trueskill_params = None
    return trueskill_params

########################################################################################################################
def create_default_trueskill_params(category_id):
    trueskill_params = AsyncRaceTrueSkillParams()
    trueskill_params.category_id = category_id
    trueskill_params.mu = 25.0
    trueskill_params.sigma = 8.333
    trueskill_params.draw_chance = 0.01
    trueskill_params.save()

########################################################################################################################
def get_racer_trueskill_params(category_id, user_id):
    try:
        trueskill_params = AsyncRaceTrueSkillRacerParams.select().where(
            (AsyncRaceTrueSkillRacerParams.category_id == category_id) &
            (AsyncRaceTrueSkillRacerParams.user_id == user_id)).get()
    except:
        trueskill_params = None
    return trueskill_params

########################################################################################################################
def get_race_draw_threshold(category_id):
    try:
        draw_threshold = AsyncRaceCategoryDrawThreshold.select().where(
            AsyncRaceCategoryDrawThreshold.category_id == category_id).get()
    except:
        draw_threshold = None
    return draw_threshold

########################################################################################################################
def get_vc_ignore_list(server_id):
    ignore_list = []
    try:
        ignore_list = ServerUtilsVcList.select().where(
            (ServerUtilsVcList.server_id == server_id) &
            (ServerUtilsVcList.channel_type == VcChannelType.Ignore))
    except:
        ignore_list = []
    return ignore_list

########################################################################################################################
def get_vc_channel(server_id, channel_id):
    try:
        ignore_channel = ServerUtilsVcList.select().where(
            (ServerUtilsVcList.server_id == server_id) &
            (ServerUtilsVcList.channel_id == channel_id)).get()
    except:
        ignore_channel = None
    return ignore_channel

########################################################################################################################
def get_vc_permanent_list(server_id):
    permanent_list = []
    try:
        permanent_list = ServerUtilsVcList.select().where(
            (ServerUtilsVcList.server_id == server_id) &
            (ServerUtilsVcList.channel_type == VcChannelType.Permanent))
    except:
        permanent_list = []
    return permanent_list

########################################################################################################################
def get_vc_on_demand_list(server_id):
    on_demand_list = []
    try:
        on_demand_list = ServerUtilsVcList.select().where(
            (ServerUtilsVcList.server_id == server_id) &
            (ServerUtilsVcList.channel_type == VcChannelType.OnDemand))
    except:
        on_demand_list = []
    return on_demand_list

########################################################################################################################
# Other Utility Functions
#####################################################################################################################
# Returns the current date/time in the format used in the database
def zBot_now():
    return datetime.now().isoformat(timespec='minutes').replace('T', ' ')

#####################################################################################################################
def get_server_assignment(info_type_id, server_id):
    try:
        a = AsyncRaceExtraInfoAssignment.select().where(
                (AsyncRaceExtraInfoAssignment.info_type_id == info_type_id) &
                (AsyncRaceExtraInfoAssignment.server_id == server_id)).get()
    except:
        a = None
    return a

#####################################################################################################################
def get_category_assignment(info_type_id, category_id):
    try:
        a = AsyncRaceExtraInfoAssignment.select().where(
                (AsyncRaceExtraInfoAssignment.info_type_id == info_type_id) &
                (AsyncRaceExtraInfoAssignment.category_id == category_id)).get()
    except:
        a = None
    return a

#####################################################################################################################
def get_race_info_assignment(info_type_id, race_id):
    try:
        a = AsyncRaceExtraInfoAssignment.select().where(
                (AsyncRaceExtraInfoAssignment.info_type_id == info_type_id) &
                (AsyncRaceExtraInfoAssignment.category_id == race_id)).get()
    except:
        a = None
    return a

#####################################################################################################################
def get_category_extra_info_assignments(category_id):
    assignments = AsyncRaceExtraInfoAssignment.select().where(
        AsyncRaceExtraInfoAssignment.category_id == category_id)
    return assignments

#####################################################################################################################
def get_race_extra_info_assignments(race_id):
    assignments = AsyncRaceExtraInfoAssignment.select().where(
        AsyncRaceExtraInfoAssignment.race_id == race_id)
    return assignments

#####################################################################################################################
def check_category_assignment_exists(info_type_id, category_id):
    a = get_category_assignment(info_type_id, category_id)
    return a is not None

#####################################################################################################################
def check_race_assignment_exists(info_type_id, race_id):
    a = get_race_info_assignment(info_type_id, race_id)
    return a is not None

#####################################################################################################################
def delete_category_assignment(info_type_id, category_id):
    a = get_category_assignment(info_type_id, category_id)
    if a is not None:
        a.delete_instance()

#####################################################################################################################
def delete_race_assignment(info_type_id, race_id):
    a = get_race_assignment(info_type_id, race_id)
    if a is not None:
        a.delete_instance()

#####################################################################################################################
def get_categories(server_id):
    return AsyncRaceCategory.select().where(AsyncRaceCategory.server_id == server_id)

#####################################################################################################################
def get_category_select_list(server_id):
    # Get the list of categories for this server
    categories = get_categories(server_id)

    # Populate the SelectOption list with the category information
    select_list = []
    for c in categories:
        select_list.append(nextcord.SelectOption(label=c.name, value=c.id, description=c.description))
    return select_list

#####################################################################################################################
def get_race_select_list(server_id: int, include_completed: bool=True):
    # If a list of races wasn't already provided, get the list of races for this server
    if include_completed:
        races = AsyncRace.select().where(AsyncRace.server_id == server_id).order_by(AsyncRace.create_datetime.desc())
    else:
        # Get the list of races for this server, ignoring completed races
        races = AsyncRace.select().where(
            (AsyncRace.server_id == server_id) &
            (AsyncRace.state != RaceState.Completed)).order_by(AsyncRace.create_datetime.desc())

    # Return the SelectOption list
    return create_race_select_list(races)

#####################################################################################################################
def create_race_select_list(races: list):
    # Populate a SelectOption list with the race information
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
        return True
    else:
        return False

########################################################################################################################
def datetime_is_valid(datetime_str):
    date_time_format = "%Y-%m-%d %H:%M:%S"
    date_only_format = "%Y-%m-%d"
    time_only_format = "%H:%M:%S"

    # We'll try to parse the string as a date/time, date only, and time only
    success = True
    try:
        datetime.strptime(datetime_str, date_time_format)
        return True
    except:
        success = False

    try:
        datetime.strptime(datetime_str, date_only_format)
        return True
    except:
        success = False

    try:
        datetime.strptime(datetime_str, time_only_format)
        return True
    except:
        success = False

    return success
        
    
########################################################################################################################
def game_time_is_valid(time_str):
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

########################################################################################################################
def finish_time_to_seconds(finish_time_str):
    try:
        parts = finish_time_str.split(':')
        hours = 0
        if len(parts) == 3:
            hours = int(parts[0])
            mins = int(parts[1])
            seconds = int(parts[2])
        else:
            mins = int(parts[0])
            seconds = int(parts[1])
    except:
        return ForfeitFinishTimeSeconds
    return (3600 * hours) + (60 * mins) + seconds

########################################################################################################################
def finish_time_seconds_to_str(finish_time_seconds):
    hours = finish_time_seconds // 3600
    minutes = (finish_time_seconds % 3600) // 60
    seconds = finish_time_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

########################################################################################################################
# Used to sort submissions by finish time
def finish_time_sort_key(submission):
    try:
        return finish_time_to_seconds(submission.finish_time)
    except:
        return ForfeitFinishTimeSeconds

########################################################################################################################
def get_sorted_race_submissions(race_id, reverse=False):
    # Get all of the submissions for this race
    submissions = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == race_id)

    if len(submissions) == 0:
        return submissions

    # Return the list, sorted by finish time
    return sorted(submissions, key=finish_time_sort_key, reverse=reverse)

########################################################################################################################
def get_num_submissions(race_id):
    return AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == race_id).count()

########################################################################################################################
def get_num_category_submissions(user_id, category_id):
    return AsyncRaceSubmission.select().join(AsyncRace).where(
        (AsyncRaceSubmission.user_id == user_id) &
        (AsyncRace.state == RaceState.Completed) &
        (AsyncRace.category_id == category_id)).count()

########################################################################################################################
def is_tie(finish_time_a, finish_time_b, tie_threshold_seconds=2):
    time_a_seconds = finish_time_to_seconds(finish_time_a)
    time_b_seconds = finish_time_to_seconds(finish_time_b)
    delta = abs(time_a_seconds - time_b_seconds)
    is_tie = False
    if delta <= tie_threshold_seconds:
        is_tie = True
    return is_tie

########################################################################################################################
def calculate_par_time(submissions):
    # Par time is the average of the top times. The number of times being averaged depends
    # on the total number of submissions
    times_to_average = 5
    if len(submissions) <= 3:
        times_to_average = 1
    elif len(submissions) <= 5:
        times_to_average = 2
    elif len(submissions) <= 9:
        times_to_average = 3
    elif len(submissions) <= 12:
        times_to_average = 4
    
    total_seconds = 0
    for i, s in enumerate(submissions[:times_to_average]):
        total_seconds += finish_time_to_seconds(s.finish_time)
    par_time = float(total_seconds / times_to_average)

    return par_time

########################################################################################################################
def get_draw_threshold_seconds(category_id):
    # The default cutoff for a tie is within 2 seconds if there is not one  specified by the category
    draw_threshold_seconds = 2
    draw_threshold = get_race_draw_threshold(category_id)
    if draw_threshold is not None:
        draw_threshold_seconds = draw_threshold.draw_threshold_seconds
    return draw_threshold_seconds

########################################################################################################################
def score_race(race):
    match race.category_id.points_type:
        case PointsType.NoScoring:
            pass
        case PointsType.MarioKart:
            score_mario_kart_race(race)
        case PointsType.Trueskill:
            score_trueskill_race(race)
        case PointsType.ParTime:
            score_par_time_race(race)
        case PointsType.Fixed:
            score_fixed_points_race(race)
        case _:
            logging.info(f"**ERROR** Unknown scoring type for race {race.id}")
            pass

########################################################################################################################
def score_mario_kart_race(race):
    # Get the submissions for this race, sorted from highest time to lowest
    reverse_submissions = get_sorted_race_submissions(race.id, reverse=True)
    submissions = get_sorted_race_submissions(race.id, reverse=False)

    # If there are no submissions, there's nothing to do here
    if submissions == None:
        return

    # If there are more submissions than scores, the rest get zero points
    mk_points_lookup = [ 25, 21, 18, 15, 12, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1 ]
    scoring_places = len(mk_points_lookup)
    num_zeroes = 0
    if len(reverse_submissions) > scoring_places:
        num_zeroes = len(reverse_submissions)-scoring_places
        zero_list = reverse_submissions[:num_zeroes]
        for z in zero_list:
            # If there's a tie at the cutoff, make sure all tied players are in points list
            if is_tie(z.finish_time, reverse_submissions[num_zeroes].finish_time):
                num_zeroes -= 1
        
        logging.info(f"Saving slice [{num_zeroes}:]")

    # The top times get points according to the lookup table
    last_points_idx = 0
    
    for i, s in enumerate(submissions):
        points_idx = i
        # Check for a tie with the previous time
        if i > 0 and is_tie(s.finish_time, submissions[i-1].finish_time):
            # If this submission is tied with the previous then it gets the same points
            # the previous one did
            points_idx = last_points_idx

        # Lookup the point value to assign
        if i >= len(submissions) - num_zeroes:
            points = 0
        else:
            points = mk_points_lookup[points_idx]

        s.points = points
        s.save()
        last_points_idx = points_idx

        # Now update the category totals for the racer
        cat_points = get_create_category_points(race.category_id.id, s.user_id)
        cat_points.points += s.points
        cat_points.save()

########################################################################################################################
def score_trueskill_race(race):
    # Get the submissions for this race
    submissions = get_sorted_race_submissions(race.id)

    # Setup Trueskill environment
    # Get this category's trueskill params from DB
    trueskill_params = get_category_trueskill_params(race.category_id.id)
    if trueskill_params is not None:
        env = trueskill.TrueSkill(mu=trueskill_params.mu,
                        sigma=trueskill_params.sigma,
                        draw_probability=trueskill_params.draw_chance)

        # Create a list of rating objects matching the submissions
        rating_list = []
        for s in submissions:
            player_rating = None

            # Lookup this racer's category data
            player_params = get_racer_trueskill_params(race.category_id.id, s.user_id)
            if player_params is not None:
                player_rating = env.create_rating(mu=player_params.mu, sigma=player_params.sigma)
            else:
                # If the player doesn't exist in this category yet, create a new player rating
                player_rating = env.create_rating()

            rating_list.append({s.user_id: player_rating})

        # Rate the race
        new_rates = env.rate(rating_list)

        # Now walk the submission list again and update the ratings.
        for i, s in enumerate(submissions):
            # The points for this race represents a snapshot of the rating at this point in time. 
            s.points = new_rates[i][s.user_id].mu
            s.save()

            # The category points is the most up to date rating
            cat_points = get_create_category_points(race.category_id.id, s.user_id)
            cat_points.points = new_rates[i][s.user_id].mu
            cat_points.save()

            # Finally save the updated, underlying trueskill params
            update_create_trueskill_racer_params(race.category_id.id,
                                                 s.user_id,
                                                 new_rates[i][s.user_id].mu,
                                                 new_rates[i][s.user_id].sigma)

########################################################################################################################
def update_create_trueskill_racer_params(category_id, user_id, mu, sigma):
    player_params = get_racer_trueskill_params(category_id, user_id)
    if player_params is None:
        player_params = AsyncRaceTrueSkillRacerParams()
        player_params.category_id = category_id
        player_params.user_id = user_id
    player_params.mu = mu
    player_params.sigma = sigma
    player_params.save()

########################################################################################################################
def score_points_key(submission):
    return submission.points

########################################################################################################################
def score_par_time_race(race):
    submissions = get_sorted_race_submissions(race.id)

    last_finish_idx = 0
    for i, s in enumerate(submissions):
        # Anything longer than 4 hours we treat as the same as a DNF
        if finish_time_to_seconds(s.finish_time) > (4*60*60):
            last_finish_idx = i - 1
            break
    
    if last_finish_idx != 0:
        # DNFs get a time equal to the slowest non-DNF time + 15 minutes
        dnf_time_seconds = finish_time_to_seconds(submissions[last_finish_idx].finish_time) + (15 * 60)
        dnf_time = finish_time_seconds_to_str(dnf_time_seconds)
        for i in range(last_finish_idx+1, len(submissions)):
            submissions[i].finish_time = dnf_time
            submissions[i].save()
    
    # Calculate the par time in seconds
    par_time_seconds = calculate_par_time(submissions)
    logging.info(f"Par time: {finish_time_seconds_to_str(int(par_time_seconds))}({par_time_seconds} seconds)")

    # For each submission
    for s in submissions:
        # Score is calculated as (2 - (time_in_seconds / par_time)) * 100
        s.points = (2.0 - (float(finish_time_to_seconds(s.finish_time) / par_time_seconds))) * 100.0
        if s.points > 105:
            s.points = 105
        s.save()

        logging.info(f"Points for {s.finish_time}: {s.points}")

        # Category points is the average of all scores, dropping the bottom score if there
        # are more than 2 and dropping top and bottom if there are more than 3
        cat_submissions = get_category_submissions(s.user_id, race.category_id.id)
        
        # Filter for only races that have been scored
        cat_submissions = list(filter(lambda x: x.points is not None, cat_submissions))
        num_scores = 0
        total_score = 0.0
        num_subs = len(cat_submissions)
        for i, c in enumerate(sorted(cat_submissions, key=score_points_key, reverse=True)):
            if i == 0 and num_subs > 3:
                # Drop top score
                continue
            if i == (num_subs - 1) and num_subs > 2:
                # Drop bottom score
                continue
            total_score += c.points
            num_scores += 1
        new_category_score = float(total_score / num_scores)
        cat_points = get_create_category_points(race.category_id.id, s.user_id)
        cat_points.points = new_category_score
        cat_points.save()

########################################################################################################################
def score_fixed_points_race(race):
    submissions = get_sorted_race_submissions(race.id)

    draw_threshold_seconds = get_draw_threshold_seconds(race.category_id.id)

    # Fixed points is designed for 1v1 races only, so we'll just check for a tie between
    # the first two items and then assign points
    if len(submissions) > 1:
        if is_tie(submissions[0].finish_time, submissions[1].finish_time, draw_threshold_seconds):
            submissions[0].points = 1
            submissions[0].save()
            cat_points = get_create_category_points(race.category_id.id, submissions[0].user_id)
            cat_points.points += submissions[0].points
            cat_points.save()

            submissions[1].points = 1
            submissions[1].save()
            cat_points = get_create_category_points(race.category_id.id, submissions[1].user_id)
            cat_points.points += submissions[1].points
            cat_points.save()
        else:
            submissions[0].points = 3
            submissions[0].save()
            cat_points = get_create_category_points(race.category_id.id, submissions[0].user_id)
            cat_points.points += submissions[0].points
            cat_points.save()

            for s in submissions[1:]:
                s.points = 0
                s.save()
                cat_points = get_create_category_points(race.category_id.id, s.user_id)
                if cat_points.points is None:
                    cat_points.points = 0
                    cat_points.save()

########################################################################################################################
def get_user_place(race_id, user_id):
    submissions = get_sorted_race_submissions(race_id)
    for i, s in enumerate(submissions):
        if s.user_id == user_id:
            return i+1

########################################################################################################################
def is_race_one_v_one(race_id):
    race = get_race(race_id)
    ret = False
    if race is not None and race.state == RaceState.Completed:
        if get_num_submissions(race_id) == 2:
            ret = True
    return ret

########################################################################################################################
def get_one_v_one_record(user_id, server_id, *, opponent_id=None, category_id=None):
    wins = 0
    losses = 0
    ties = 0
    categories = []
    if category_id is not None:
        categories.append(get_category(category_id))
    else:
        categories = get_categories(server_id)

    for c in categories:
        # Get the races for this category that the user submitted to
        user_submissions = get_category_submissions(user_id, c.id)
        for s in user_submissions:
            # If comparing against a specific opponent, skip if the opponent didn't submit
            if opponent_id is not None and get_race_submission(opponent_id, s.race_id) is None:
                continue

            # Only count 1v1 races
            if is_race_one_v_one(s.race_id):
                submissions = get_sorted_race_submissions(s.race_id)
                draw_threshold_seconds = get_draw_threshold_seconds(c.id)
                if is_tie(submissions[0].finish_time, submissions[1].finish_time, draw_threshold_seconds):
                    ties += 1
                elif submissions[0].user_id == user_id:
                    wins += 1
                elif submissions[1].user_id == user_id:
                    losses += 1
                else:
                    logging.info(f"**ERROR** Something went wrong in get_one_v_one_record")
    return wins, losses, ties
                
########################################################################################################################
def is_value_empty(value):
    if value is None or value == "":
        return True
    return False

########################################################################################################################
def get_server_messages(server_id):
    return AsyncRaceMessage.select().where(AsyncRaceMessage.server_id == server_id)

########################################################################################################################
def get_messages_by_race_id(race_id, message_type=RaceMessageType.Leaderboard):
    return AsyncRaceMessage.select().where(
        (AsyncRaceMessage.race_id == race_id) & (AsyncRaceMessage.message_type == message_type))

########################################################################################################################
def get_messages_by_category_id(category_id):
    return AsyncRaceMessage.select().where(AsyncRaceMessage.category_id == category_id)
