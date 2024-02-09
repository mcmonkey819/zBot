from datetime import datetime, date
import logging
import nextcord
import trueskill

from db.zBot_db_orm import *

class VarType:
    Int      = 1
    Str      = 2
    GameTime = 3
    DateTime = 4

    SelectOptionList = [
        nextcord.SelectOption(label="Integer",             value=Int,      description="Integer Value"),
        nextcord.SelectOption(label="String",              value=Str,      description="String text up to 255 characters in length"),
        nextcord.SelectOption(label="Game Time (H:MM:SS)", value=GameTime, description="Game time expressed in 'H:MM:SS' format"),
        nextcord.SelectOption(label="Date/Time",           value=DateTime, description="Date & Time string, typically something like 'YYYY-MM-DD HH:MM:SS'"),
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
def get_assigned_racers(race_id):
    racers = AsyncRaceRoster.select().where(AsyncRaceRoster.race_id == race_id)
    return racers

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
    races = AsyncRace.select().where(AsyncRace.category_id == category_id)
    return races

########################################################################################################################
def get_category_points(category_id):
    points = AsyncRaceCategoryPoints.select().where(AsyncRaceCategoryPoints.category_id == category_id)
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
    races = AsyncRace.select().where(AsyncRace.server_id == server_id).order_by(AsyncRace.create_datetime.desc())

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

########################################################################################################################
def finish_time_to_seconds(finish_time_str):
    parts = finish_time_str.split(':')
    hours = 0
    if len(parts) == 3:
        hours = int(parts[0])
        mins = int(parts[1])
        seconds = int(parts[2])
    else:
        mins = int(parts[0])
        seconds = int(parts[1])
    return (3600 * hours) + (60 * mins) + seconds

########################################################################################################################
# Used to sort submissions by finish time
def finish_time_sort_key(submission):
    # Convert the time to seconds for sorting
    time_in_seconds = 0
    if submission.finish_time is not None and submission.finish_time != '':
        time_in_seconds = finish_time_to_seconds(submission.finish_time)
    return time_in_seconds

########################################################################################################################
# Used to sort submissions by score
def score_sort_key(submission):
    return s.score

########################################################################################################################
def get_sorted_race_submissions(race_id, reverse=False):
    # Get all of the submissions for this race
    submissions = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == race_id)

    if len(submissions) == 0:
        return None

    # Return the list, sorted by finish time
    return sorted(submissions, key=finish_time_sort_key, reverse=reverse)

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

########################################################################################################################
def get_draw_threshold_seconds(category_id):
    # The default cutoff for a tie is within 2 seconds if there is not one  specified by the category
    draw_threshold_seconds = 2
    draw_threshold = get_race_draw_threshold(race.category_id.id)
    if draw_threshold is None:
        draw_threshold_seconds = draw_threshold.draw_threshold_seconds

########################################################################################################################
def score_race(race):
    match race.category_id.points_type:
        case PointsType.NoScoring:
            pass
        case PointsType.MarioKart:
            score_mario_kart_race(race)
        case PointsType.Elo:
            pass
        case PointsType.ParTime:
            pass
        case PointsType.Fixed:
            pass
        case _:
            pass

########################################################################################################################
def delete_race_points(race):
    submissions = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == race.id)
    for s in submissions:
        s.points = None
        s.save()

########################################################################################################################
def score_mario_kart_race(race):
    # Get the submissions for this race, sorted from highest time to lowest
    submissions = get_sorted_race_submissions(race.id, reverse=True)

    # If there are no submissions, there's nothing to do here
    if submissions == None:
        return

    # If there are more than 15 submissions, any outside the top 15 get zero points
    if len(submissions) > 15:
        num_zeroes = len(submissions)-15
        zero_list = submissions[:num_zeroes]
        for z in zero_list:
            # If there's a tie at the cutoff, make sure all tied players are in points list
            if is_tie(z.finish_time, submissions[num_zeroes]):
                num_zeroes -= 1
            else:
                z.points = 0
                z.save()
        # Then save the top 15 for scoring below
        submissions = submissions[num_zeroes:]

    # The top 15 get points according to the lookup table
    mk_points_lookup = [ 25, 21, 18, 15, 12, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1 ]
    last_points_idx = 0
    for i, s in enumerate(submissions.reverse()):
        points_idx = i
        # Check for a tie with the previous time
        if i > 0 and is_tie(s.finish_time, submissions.reverse[i-1]):
            # If this submission is tied with the previous then it gets the same points
            # the previous one did
            points_idx = last_points_idx

        # Lookup the point value to assign
        if idx > len(mk_points_lookup):
            points = 0
        else:
            points = mk_points_lookup[idx]

        s.points = points
        s.save()
        last_points_idx = idx

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
        env = Trueskill(mu=trueskill_params.mu,
                        sigma=trueskill_params.sigma,
                        draw_probability=trueskill_params.draw_chance)

        # Create a list of rating objects matching the submissions
        rating_dict = {}
        for s in submissions:
            player_rating = None

            # Lookup this racer's category data
            player_params = get_racer_trueskill_params(race.category_id.id, s.user_id)
            if player_params is not None:
                player_rating = env.create_rating(mu=player_params.mu, sigma=player_params.sigma)
            else:
                # If the player doesn't exist in this category yet, create a new player rating
                player_rating = env.create_rating()

            rating_dict[s.user_id] = player_rating

        # Rate the race
        new_rates = env.rate(rating_dict)

        # Now walk the submission list again and update the ratings.
        for s in submissions:
            # The points for this race represents a snapshot of the rating at this point in time. 
            s.points = new_rates[s.user_id].mu
            s.save()

            # The category points is the most up to date rating
            cat_points = get_create_category_points(race.category_id.id, s.user_id)
            cat_points.points = new_rates[s.user_id].mu
            cat_points.save()

            # Finally save the updated, underlying trueskill params
            update_create_trueskill_racer_params(race.category_id.id,
                                                 s.user_id,
                                                 new_rates[s.user_id].mu,
                                                 new_rates[s.user_id].sigma)

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
def score_par_time_race(race):
    submissions = get_sorted_race_submissions(race.id)

    # Calculate the par time in seconds
    par_time_seconds = calculate_par_time(submissions)

    # For each submission
    for s in submissions:
        # Score is calculated as (2 - (time_in_seconds / par_time)) * 100
        s.points = (2 - (finish_time_to_seconds(s.finish_time) / par_time_seconds)) * 100
        s.save()

        # Category points is the average of all scores, dropping the bottom score if there
        # are more than 2 and dropping top and bottom if there are more than 3
        cat_submissions = get_category_submissions(s.user_id, race.category_id.id)
        num_scores = 0
        total_score = 0
        num_subs = len(cat_submissions)
        for i, c in enumerate(sorted(cat_submission, key=score_points_key, reverse=True)):
            if i == 0 and num_subs > 3:
                # Drop top score
                continue
            if i == (num_subs - 1) and num_subs > 2:
                # Drop bottom score
                continue
            total_score += c.points
            num_scores += 1
        new_category_score = total_score / num_scores
        cat_points = get_create_category_points(race.category_id.id, s.user_id)
        cat_points.points = new_category_score
        cat_points.save()

########################################################################################################################
def score_fixed_points_race(race):
    submissions = get_sorted_race_submissions(race.id)

    draw_threshold_seconds = get_draw_threshold_seconds(race.category_id.id)

    # Fixed points is designed for 1v1 races only, so we'll just check for a tie
    # and then assign points
    if len(submissions) > 1:
        if is_tie(submissions[0].finish_time, submissions, draw_threshold_seconds):
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

