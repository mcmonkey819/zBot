# -*- coding: utf-8 -*-
"""
Mock factories and fixtures for database models used in testing.
"""
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Import constants and simple utility functions directly from the actual code (no side effects)
from db.db_util import RaceState, ForfeitFinishTime, ForfeitFinishTimeSeconds, is_value_empty, RaceMessageType, PointsType

def create_mock_category(
    category_id=1,
    name="Test Category",
    description="Test category description",
    server_id=111222333,
    active=True,
    points_type=None,
    submit_role=None,
    create_role=None,
    leaderboard_type=None,
    pin_recent_race=False,
    allow_completed_submit=False,
    activate_new_races=False,
    mod_can_view_leaderboard=True,
    thumbnail_url=None,
    submit_time_limit_hours=None
):
    """
    Creates a mock AsyncRaceCategory object.
    
    Args:
        category_id: Category ID
        name: Category name
        description: Category description
        server_id: Discord server ID
        active: Whether category is active
        points_type: Scoring type (PointsType enum value)
        submit_role: Role ID for submit role
        create_role: Role ID for create role
        leaderboard_type: Leaderboard type enum
        pin_recent_race: Whether to pin recent race
        allow_completed_submit: Allow submitting to completed races
        activate_new_races: Auto-activate new races
        mod_can_view_leaderboard: Mods can view leaderboard
        thumbnail_url: URL for category thumbnail
        submit_time_limit_hours: Time limit for submissions in hours
    
    Returns:
        Mock AsyncRaceCategory object
    """
    category = Mock()
    category.id = category_id
    category.name = name
    category.description = description
    category.server_id = server_id
    category.active = active
    category.points_type = points_type
    category.submit_role = submit_role
    category.create_role = create_role
    category.leaderboard_type = leaderboard_type
    category.pin_recent_race = pin_recent_race
    category.allow_completed_submit = allow_completed_submit
    category.activate_new_races = activate_new_races
    category.mod_can_view_leaderboard = mod_can_view_leaderboard
    category.thumbnail_url = thumbnail_url
    category.submit_time_limit_hours = submit_time_limit_hours
    return category


def create_mock_race(
    race_id=1,
    category_id=None,
    server_id=111222333,
    seed="Test Seed",
    hash="ABCD1234",
    description="Test Race",
    additional_instructions=None,
    create_datetime=None,
    state=None,
    is_team_race=False,
    team_name_info_id=None,
    submission_role=None
):
    """
    Creates a mock AsyncRace object.
    
    Args:
        race_id: Race ID
        category_id: Category object or ID (will create mock if None)
        server_id: Discord server ID
        seed: Race seed string
        hash: Race hash string
        description: Race description
        additional_instructions: Additional instructions text
        create_datetime: Creation datetime (defaults to now)
        state: Race state (RaceState enum value)
        is_team_race: Whether this is a team race
        team_name_info_id: Extra info ID for team names
        submission_role: Role ID for submission role
    
    Returns:
        Mock AsyncRace object
    """
    race = Mock()
    race.id = race_id
    
    # Create a mock category if not provided
    if category_id is None:
        race.category_id = create_mock_category()
    elif isinstance(category_id, int):
        race.category_id = create_mock_category(category_id=category_id)
    else:
        race.category_id = category_id
    
    race.server_id = server_id
    race.seed = seed
    race.hash = hash
    race.description = description
    race.additional_instructions = additional_instructions
    race.create_datetime = create_datetime if create_datetime is not None else datetime.now().isoformat()
    race.state = state
    race.is_team_race = is_team_race
    race.team_name_info_id = team_name_info_id
    race.submission_role = submission_role
    
    # Add commonly accessed attributes
    race.extra_info_assignments = []
    
    return race


def create_mock_submission(
    submission_id=1,
    race_id=1,
    user_id=123456789,
    finish_time="1:23:45",
    comment="Test comment",
    submit_datetime=None,
    points=None,
    teammate_id=None
):
    """
    Creates a mock AsyncRaceSubmission object.
    
    Args:
        submission_id: Submission ID
        race_id: Race ID this submission is for
        user_id: Discord user ID who submitted
        finish_time: Finish time string (H:MM:SS format)
        comment: Submission comment
        submit_datetime: Submission datetime
        points: Points awarded (float or None)
        teammate_id: Teammate user ID for team races
    
    Returns:
        Mock AsyncRaceSubmission object
    """
    submission = Mock()
    submission.id = submission_id
    submission.race_id = race_id
    submission.user_id = user_id
    submission.finish_time = finish_time
    submission.comment = comment
    submission.submit_datetime = submit_datetime if submit_datetime is not None else datetime.now().isoformat()
    submission.points = points
    submission.teammate_id = teammate_id
    return submission


def create_mock_extra_info_type(
    info_type_id=1,
    name="Extra Info",
    description="Extra info description",
    var_type=0,
    server_id=None
):
    """
    Creates a mock AsyncRaceExtraInfoType object.
    
    Args:
        info_type_id: Info type ID
        name: Info type name
        description: Info type description
        var_type: Variable type (VarType enum value)
        server_id: Discord server ID (None for global)
    
    Returns:
        Mock AsyncRaceExtraInfoType object
    """
    info_type = Mock()
    info_type.id = info_type_id
    info_type.name = name
    info_type.description = description
    info_type.var_type = var_type
    info_type.server_id = server_id
    return info_type


def create_mock_extra_info(
    info_id=1,
    submission_id=1,
    info_type_id=1,
    data="Test data"
):
    """
    Creates a mock AsyncRaceExtraInfo object.
    
    Args:
        info_id: Extra info ID
        submission_id: Submission ID this info belongs to
        info_type_id: Extra info type ID
        data: The actual data value
    
    Returns:
        Mock AsyncRaceExtraInfo object
    """
    info = Mock()
    info.id = info_id
    info.submission_id = submission_id
    info.info_type_id = info_type_id
    info.data = data
    return info


def create_mock_extra_info_assignment(
    assignment_id=1,
    race_id=1,
    info_type_id=1,
    category_id=None,
    required=False
):
    """
    Creates a mock AsyncRaceExtraInfoAssignment object.
    
    Args:
        assignment_id: Assignment ID
        race_id: Race ID (None for category assignment)
        info_type_id: Info type ID or object
        category_id: Category ID (None for race assignment)
        required: Whether this field is required
    
    Returns:
        Mock AsyncRaceExtraInfoAssignment object
    """
    assignment = Mock()
    assignment.id = assignment_id
    assignment.race_id = race_id
    assignment.category_id = category_id
    assignment.required = required
    
    # Handle info_type_id being either an ID or an object
    if isinstance(info_type_id, int):
        assignment.info_type_id = info_type_id
    else:
        assignment.info_type_id = info_type_id
    
    return assignment


def create_race_with_submissions(race_id=1, num_submissions=3, category_name="Test Category"):
    """
    Creates a mock race with the specified number of submissions.
    
    Args:
        race_id: Race ID
        num_submissions: Number of submissions to create
        category_name: Name for the race's category
    
    Returns:
        Tuple of (race, submissions_list)
    """
    category = create_mock_category(category_id=1, name=category_name)
    race = create_mock_race(race_id=race_id, category_id=category, description=f"Race {race_id}")
    
    submissions = []
    for i in range(num_submissions):
        submission = create_mock_submission(
            submission_id=i+1,
            race_id=race_id,
            user_id=100000 + i,
            finish_time=f"1:{20+i:02d}:30",
            comment=f"Submission {i+1}"
        )
        submissions.append(submission)
    
    return race, submissions

