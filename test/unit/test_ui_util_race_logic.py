# -*- coding: utf-8 -*-
"""
Unit tests for UI utility race management and submission functions.
Tests race and submission logic from ui/ui_util.py with mocked database operations.
"""
import pytest
import sys
from unittest.mock import patch, Mock, MagicMock, call, AsyncMock
from datetime import datetime

# Mock nextcord.ext.menus before importing ui.menus to avoid import errors
sys.modules['nextcord.ext.menus'] = MagicMock()

from ui.ui_util import forfeit_race, get_submission_details_dict, save_message, get_race_leaderboard_table, get_sorted_team_submissions, export_race, get_race_info_message, get_race_leaderboard_embed, get_category_leaderboard_embed
from ui.menus import do_post_submit_actions
from test.test_utils.db_fixtures import (
    create_mock_race, 
    create_mock_submission, 
    create_mock_extra_info,
    create_mock_extra_info_type,
    create_mock_extra_info_assignment,
    ForfeitFinishTime,
    RaceMessageType
)
from db.db_util import RaceState, PointsType, VarType


@pytest.mark.unit
class TestForfeitRace:
    """Tests for forfeit_race() function in ui/ui_util.py"""

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_creates_submission_with_forfeit_time(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test that forfeit creates a submission with ForfeitFinishTime."""
        # Setup
        race_id = 1
        user_id = 123456789
        timestamp = "2024-10-12 14:30"
        
        race = create_mock_race(race_id=race_id)
        mock_get_race.return_value = race
        mock_zbot_now.return_value = timestamp
        
        # Create a mock submission instance
        mock_submission = Mock()
        mock_submission_class.return_value = mock_submission
        
        # Execute
        forfeit_race(user_id, race_id)
        
        # Verify submission was created and configured correctly
        mock_submission_class.assert_called_once()
        assert mock_submission.race_id == race_id
        assert mock_submission.user_id == user_id
        assert mock_submission.submit_datetime == timestamp
        assert mock_submission.finish_time == ForfeitFinishTime
        mock_submission.save.assert_called_once()

    @patch('ui.ui_util.get_race')
    def test_forfeit_with_nonexistent_race(self, mock_get_race):
        """Test forfeit with race that doesn't exist does nothing."""
        # Setup
        race_id = 999
        user_id = 123456789
        mock_get_race.return_value = None  # Race doesn't exist
        
        # Execute - should not raise exception
        forfeit_race(user_id, race_id)
        
        # Verify get_race was called but nothing else happened
        mock_get_race.assert_called_once_with(race_id)

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_uses_current_timestamp(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test that forfeit uses zBot_now() for timestamp."""
        # Setup
        race_id = 2
        user_id = 987654321
        expected_timestamp = "2024-10-12 16:45"
        
        race = create_mock_race(race_id=race_id)
        mock_get_race.return_value = race
        mock_zbot_now.return_value = expected_timestamp
        
        mock_submission = Mock()
        mock_submission_class.return_value = mock_submission
        
        # Execute
        forfeit_race(user_id, race_id)
        
        # Verify
        mock_zbot_now.assert_called_once()
        assert mock_submission.submit_datetime == expected_timestamp

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_saves_to_database(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test that forfeit calls save() on the submission."""
        # Setup
        race_id = 3
        user_id = 111222333
        
        race = create_mock_race(race_id=race_id)
        mock_get_race.return_value = race
        mock_zbot_now.return_value = "2024-10-12 10:00"
        
        mock_submission = Mock()
        mock_submission_class.return_value = mock_submission
        
        # Execute
        forfeit_race(user_id, race_id)
        
        # Verify save was called
        mock_submission.save.assert_called_once()

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_with_different_user_ids(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test forfeit works with various user IDs."""
        # Setup
        race_id = 4
        mock_zbot_now.return_value = "2024-10-12 12:00"
        race = create_mock_race(race_id=race_id)
        mock_get_race.return_value = race
        
        test_user_ids = [1, 42, 123456789, 999999999999]
        
        for user_id in test_user_ids:
            mock_submission = Mock()
            mock_submission_class.return_value = mock_submission
            
            # Execute
            forfeit_race(user_id, race_id)
            
            # Verify
            assert mock_submission.user_id == user_id
            assert mock_submission.finish_time == ForfeitFinishTime

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_submission_fields_complete(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test that all required submission fields are set."""
        # Setup
        race_id = 5
        user_id = 555666777
        timestamp = "2024-10-12 18:20"
        
        race = create_mock_race(race_id=race_id)
        mock_get_race.return_value = race
        mock_zbot_now.return_value = timestamp
        
        mock_submission = Mock()
        mock_submission_class.return_value = mock_submission
        
        # Execute
        forfeit_race(user_id, race_id)
        
        # Verify all fields are set
        assert hasattr(mock_submission, 'race_id')
        assert hasattr(mock_submission, 'user_id')
        assert hasattr(mock_submission, 'submit_datetime')
        assert hasattr(mock_submission, 'finish_time')
        assert mock_submission.race_id == race_id
        assert mock_submission.user_id == user_id
        assert mock_submission.submit_datetime == timestamp
        assert mock_submission.finish_time == ForfeitFinishTime

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_multiple_users_same_race(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test multiple users can forfeit the same race."""
        # Setup
        race_id = 6
        mock_zbot_now.return_value = "2024-10-12 14:00"
        race = create_mock_race(race_id=race_id)
        mock_get_race.return_value = race
        
        user_ids = [111, 222, 333]
        submissions = []
        
        for user_id in user_ids:
            mock_submission = Mock()
            mock_submission_class.return_value = mock_submission
            submissions.append(mock_submission)
            
            # Execute
            forfeit_race(user_id, race_id)
            
            # Verify
            assert mock_submission.user_id == user_id
            assert mock_submission.race_id == race_id
            assert mock_submission.finish_time == ForfeitFinishTime
            mock_submission.save.assert_called_once()

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_different_races(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test same user can forfeit different races."""
        # Setup
        user_id = 123456789
        mock_zbot_now.return_value = "2024-10-12 15:30"
        
        race_ids = [1, 2, 3, 4, 5]
        
        for race_id in race_ids:
            race = create_mock_race(race_id=race_id)
            mock_get_race.return_value = race
            
            mock_submission = Mock()
            mock_submission_class.return_value = mock_submission
            
            # Execute
            forfeit_race(user_id, race_id)
            
            # Verify
            assert mock_submission.race_id == race_id
            assert mock_submission.user_id == user_id
            assert mock_submission.finish_time == ForfeitFinishTime

    @patch('ui.ui_util.get_race')
    def test_forfeit_checks_race_exists_first(self, mock_get_race):
        """Test that forfeit checks if race exists before attempting to create submission."""
        # Setup
        race_id = 999
        user_id = 123456789
        mock_get_race.return_value = None  # Race doesn't exist
        
        # Execute - should complete without error
        try:
            forfeit_race(user_id, race_id)
        except Exception as e:
            pytest.fail(f"forfeit_race raised exception when race not found: {e}")
        
        # Verify
        mock_get_race.assert_called_once_with(race_id)

    @patch('ui.ui_util.zBot_now')
    @patch('ui.ui_util.AsyncRaceSubmission')
    @patch('ui.ui_util.get_race')
    def test_forfeit_time_format(self, mock_get_race, mock_submission_class, mock_zbot_now):
        """Test that forfeit time is exactly 23:59:59."""
        # Setup
        race_id = 7
        user_id = 123456789
        mock_zbot_now.return_value = "2024-10-12 12:00"
        
        race = create_mock_race(race_id=race_id)
        mock_get_race.return_value = race
        
        mock_submission = Mock()
        mock_submission_class.return_value = mock_submission
        
        # Execute
        forfeit_race(user_id, race_id)
        
        # Verify the forfeit time is exactly as expected
        assert mock_submission.finish_time == "23:59:59"
        assert mock_submission.finish_time == ForfeitFinishTime


@pytest.mark.unit
class TestGetSubmissionDetailsDict:
    """Tests for get_submission_details_dict() function in ui/ui_util.py"""

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_basic_submission_with_finish_time(self, mock_assignment_class):
        """Test basic submission returns finish time."""
        # Setup
        submission = create_mock_submission(
            submission_id=1,
            race_id=1,
            finish_time="1:23:45",
            comment=None,
            points=None
        )
        
        # Mock empty extra info assignments
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert result["Finish Time"] == "1:23:45"
        assert "Comment" not in result  # No comment
        assert "Points" not in result  # No points

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_forfeit_time_shows_as_dnf(self, mock_assignment_class):
        """Test that ForfeitFinishTime is displayed as 'DNF'."""
        # Setup
        submission = create_mock_submission(
            submission_id=2,
            finish_time=ForfeitFinishTime,  # 23:59:59
            comment=None,
            points=None
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert result["Finish Time"] == "DNF"
        assert result["Finish Time"] != "23:59:59"

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_comment(self, mock_assignment_class):
        """Test submission with comment includes it in details."""
        # Setup
        submission = create_mock_submission(
            submission_id=3,
            finish_time="2:15:30",
            comment="Great run!",
            points=None
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert "Comment" in result
        assert result["Comment"] == "Great run!"

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_empty_comment(self, mock_assignment_class):
        """Test submission with empty comment doesn't include it."""
        # Setup
        submission = create_mock_submission(
            submission_id=4,
            finish_time="1:45:20",
            comment="",  # Empty comment
            points=None
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert "Comment" not in result  # Empty comment excluded

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_points(self, mock_assignment_class):
        """Test submission with points includes formatted points."""
        # Setup
        submission = create_mock_submission(
            submission_id=5,
            finish_time="1:30:00",
            comment=None,
            points=95.750
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Points" in result
        assert result["Points"] == "95.750"  # Formatted via format_points_str

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_integer_points(self, mock_assignment_class):
        """Test submission with integer points formats without decimals."""
        # Setup
        submission = create_mock_submission(
            submission_id=6,
            finish_time="1:30:00",
            comment=None,
            points=100.000
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Points" in result
        assert result["Points"] == "100"  # format_points_str removes .000

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_zero_points(self, mock_assignment_class):
        """Test submission with zero points is excluded (is_value_empty check)."""
        # Setup  
        submission = create_mock_submission(
            submission_id=7,
            finish_time="1:30:00",
            comment=None,
            points=0
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify - zero is not empty, so should be included
        assert "Points" in result
        assert result["Points"] == "0"

    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_extra_info(self, mock_assignment_class, mock_get_extra_info, mock_get_extra_info_type):
        """Test submission with extra info includes it in details."""
        # Setup
        submission = create_mock_submission(
            submission_id=8,
            race_id=1,
            finish_time="1:25:30",
            comment=None,
            points=None
        )
        
        # Create extra info assignment and type
        info_type = create_mock_extra_info_type(info_type_id=10, name="Collection Rate")
        assignment = create_mock_extra_info_assignment(info_type_id=info_type, race_id=1)
        extra_info = create_mock_extra_info(submission_id=8, info_type_id=10, data="75")
        
        mock_assignment_class.select.return_value.where.return_value = [assignment]
        mock_get_extra_info.return_value = extra_info
        mock_get_extra_info_type.return_value = info_type
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert "Collection Rate" in result
        assert result["Collection Rate"] == "75"

    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_empty_extra_info(self, mock_assignment_class, mock_get_extra_info, mock_get_extra_info_type):
        """Test extra info with empty data is excluded."""
        # Setup
        submission = create_mock_submission(
            submission_id=9,
            race_id=1,
            finish_time="1:25:30"
        )
        
        info_type = create_mock_extra_info_type(info_type_id=10, name="VoD Link")
        assignment = create_mock_extra_info_assignment(info_type_id=info_type, race_id=1)
        extra_info = create_mock_extra_info(submission_id=9, info_type_id=10, data="")  # Empty
        
        mock_assignment_class.select.return_value.where.return_value = [assignment]
        mock_get_extra_info.return_value = extra_info
        mock_get_extra_info_type.return_value = info_type
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert "VoD Link" not in result  # Empty data excluded

    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_multiple_extra_infos(self, mock_assignment_class, mock_get_extra_info, mock_get_extra_info_type):
        """Test submission with multiple extra info fields."""
        # Setup
        submission = create_mock_submission(
            submission_id=10,
            race_id=1,
            finish_time="1:35:45",
            comment="Good race"
        )
        
        # Create multiple extra info types
        info_type_cr = create_mock_extra_info_type(info_type_id=10, name="Collection Rate")
        info_type_vod = create_mock_extra_info_type(info_type_id=11, name="VoD Link")
        
        # Assignments need info_type_id as integer (for get_extra_info lookup)
        assignment_cr = create_mock_extra_info_assignment(info_type_id=10, race_id=1)
        assignment_vod = create_mock_extra_info_assignment(info_type_id=11, race_id=1)
        
        extra_info_cr = create_mock_extra_info(submission_id=10, info_type_id=10, data="80")
        extra_info_vod = create_mock_extra_info(submission_id=10, info_type_id=11, data="https://youtube.com/watch?v=...")
        
        mock_assignment_class.select.return_value.where.return_value = [assignment_cr, assignment_vod]
        
        def get_extra_info_side_effect(submission_id, info_type_id):
            if info_type_id == 10:
                return extra_info_cr
            elif info_type_id == 11:
                return extra_info_vod
            return None
        
        def get_extra_info_type_side_effect(info_type_id):
            if info_type_id == 10:
                return info_type_cr
            elif info_type_id == 11:
                return info_type_vod
            return None
        
        mock_get_extra_info.side_effect = get_extra_info_side_effect
        mock_get_extra_info_type.side_effect = get_extra_info_type_side_effect
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert "Comment" in result
        assert "Collection Rate" in result
        assert "VoD Link" in result
        assert result["Collection Rate"] == "80"
        assert result["VoD Link"] == "https://youtube.com/watch?v=..."

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_submission_with_no_extra_info_for_assignment(self, mock_assignment_class, mock_get_extra_info):
        """Test when assignment exists but no extra info is saved."""
        # Setup
        submission = create_mock_submission(submission_id=11, race_id=1, finish_time="1:20:00")
        
        info_type = create_mock_extra_info_type(info_type_id=10, name="Optional Field")
        assignment = create_mock_extra_info_assignment(info_type_id=info_type, race_id=1)
        
        mock_assignment_class.select.return_value.where.return_value = [assignment]
        mock_get_extra_info.return_value = None  # No extra info saved
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Finish Time" in result
        assert "Optional Field" not in result  # No data saved

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_complete_submission_all_fields(self, mock_assignment_class):
        """Test submission with all possible fields populated."""
        # Setup
        submission = create_mock_submission(
            submission_id=12,
            race_id=1,
            finish_time="1:15:20",
            comment="Perfect run!",
            points=98.500
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify all fields present
        assert "Finish Time" in result
        assert result["Finish Time"] == "1:15:20"
        assert "Comment" in result
        assert result["Comment"] == "Perfect run!"
        assert "Points" in result
        assert result["Points"] == "98.500"

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_minimal_submission(self, mock_assignment_class):
        """Test minimal submission with only finish time."""
        # Setup
        submission = create_mock_submission(
            submission_id=13,
            race_id=1,
            finish_time="2:00:00",
            comment=None,
            points=None
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify only finish time present
        assert len(result) == 1
        assert "Finish Time" in result
        assert result["Finish Time"] == "2:00:00"

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_dict_is_new_instance(self, mock_assignment_class):
        """Test that each call returns a new dictionary instance."""
        # Setup
        submission = create_mock_submission(submission_id=14, finish_time="1:00:00")
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result1 = get_submission_details_dict(submission)
        result2 = get_submission_details_dict(submission)
        
        # Verify they're different instances
        assert result1 is not result2
        # But have same content
        assert result1 == result2

    @patch('ui.ui_util.AsyncRaceExtraInfoAssignment')
    def test_comment_with_unicode_emoji(self, mock_assignment_class):
        """Test comment with emoji is preserved."""
        # Setup
        submission = create_mock_submission(
            submission_id=15,
            finish_time="1:30:00",
            comment="Amazing run! 🎉🏆 Personal best! 🎮"
        )
        
        mock_assignment_class.select.return_value.where.return_value = []
        
        # Execute
        result = get_submission_details_dict(submission)
        
        # Verify
        assert "Comment" in result
        assert "🎉" in result["Comment"]
        assert "🏆" in result["Comment"]
        assert "🎮" in result["Comment"]


@pytest.mark.unit
class TestSaveMessage:
    """Tests for save_message() function in ui/ui_util.py"""

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_default_type(self, mock_message_class):
        """Test save_message with default message type (Leaderboard)."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id)
        
        # Verify message was created with correct values
        mock_message_class.assert_called_once_with(
            server_id=server_id,
            channel_id=channel_id,
            message_id=message_id,
            message_type=RaceMessageType.Leaderboard,
            category_id=None,
            race_id=None
        )
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_race_id(self, mock_message_class):
        """Test save_message with race_id specified."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        race_id = 42
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id, race_id=race_id)
        
        # Verify
        mock_message_class.assert_called_once_with(
            server_id=server_id,
            channel_id=channel_id,
            message_id=message_id,
            message_type=RaceMessageType.Leaderboard,
            category_id=None,
            race_id=race_id
        )
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_category_id(self, mock_message_class):
        """Test save_message with category_id specified."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        category_id = 10
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id, category_id=category_id)
        
        # Verify
        mock_message_class.assert_called_once_with(
            server_id=server_id,
            channel_id=channel_id,
            message_id=message_id,
            message_type=RaceMessageType.Leaderboard,
            category_id=category_id,
            race_id=None
        )
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_menu_type(self, mock_message_class):
        """Test save_message with Menu message type."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id, message_type=RaceMessageType.Menu)
        
        # Verify
        mock_message_class.assert_called_once_with(
            server_id=server_id,
            channel_id=channel_id,
            message_id=message_id,
            message_type=RaceMessageType.Menu,
            category_id=None,
            race_id=None
        )
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_race_info_type(self, mock_message_class):
        """Test save_message with RaceInfo message type."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        race_id = 5
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id, message_type=RaceMessageType.RaceInfo, race_id=race_id)
        
        # Verify
        mock_message_class.assert_called_once_with(
            server_id=server_id,
            channel_id=channel_id,
            message_id=message_id,
            message_type=RaceMessageType.RaceInfo,
            category_id=None,
            race_id=race_id
        )
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_announcement_type(self, mock_message_class):
        """Test save_message with Announcement message type."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        category_id = 3
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id, 
                    message_type=RaceMessageType.Announcement, 
                    category_id=category_id)
        
        # Verify
        mock_message_class.assert_called_once_with(
            server_id=server_id,
            channel_id=channel_id,
            message_id=message_id,
            message_type=RaceMessageType.Announcement,
            category_id=category_id,
            race_id=None
        )
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_both_race_and_category(self, mock_message_class):
        """Test save_message with both race_id and category_id."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        race_id = 15
        category_id = 8
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id, race_id=race_id, category_id=category_id)
        
        # Verify both IDs are saved
        mock_message_class.assert_called_once_with(
            server_id=server_id,
            channel_id=channel_id,
            message_id=message_id,
            message_type=RaceMessageType.Leaderboard,
            category_id=category_id,
            race_id=race_id
        )
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_handles_save_exception(self, mock_message_class):
        """Test save_message handles exceptions during save gracefully."""
        # Setup
        server_id = 111222333
        channel_id = 444555666
        message_id = 777888999
        
        mock_message = Mock()
        mock_message.save.side_effect = Exception("Database error")
        mock_message_class.return_value = mock_message
        
        # Execute - should not raise exception
        try:
            save_message(server_id, channel_id, message_id)
        except Exception as e:
            pytest.fail(f"save_message raised exception: {e}")
        
        # Verify save was attempted
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    @pytest.mark.parametrize("message_type", [
        RaceMessageType.Leaderboard,
        RaceMessageType.RaceInfo,
        RaceMessageType.Menu,
        RaceMessageType.Announcement,
    ])
    def test_save_message_all_message_types(self, mock_message_class, message_type):
        """Parametrized test for all message types."""
        # Setup
        server_id = 111
        channel_id = 222
        message_id = 333
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id, message_type=message_type)
        
        # Verify
        assert mock_message_class.call_args[1]['message_type'] == message_type
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_with_large_ids(self, mock_message_class):
        """Test save_message handles large Discord ID values."""
        # Setup - Discord IDs can be very large
        server_id = 999999999999999999
        channel_id = 888888888888888888
        message_id = 777777777777777777
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute
        save_message(server_id, channel_id, message_id)
        
        # Verify
        assert mock_message_class.call_args[1]['server_id'] == server_id
        assert mock_message_class.call_args[1]['channel_id'] == channel_id
        assert mock_message_class.call_args[1]['message_id'] == message_id
        mock_message.save.assert_called_once()

    @patch('ui.ui_util.AsyncRaceMessage')
    def test_save_message_keyword_only_arguments(self, mock_message_class):
        """Test that message_type, category_id, and race_id are keyword-only."""
        # Setup
        server_id = 111
        channel_id = 222
        message_id = 333
        
        mock_message = Mock()
        mock_message_class.return_value = mock_message
        
        # Execute with keyword arguments
        save_message(server_id, channel_id, message_id, 
                    message_type=RaceMessageType.RaceInfo,
                    category_id=5,
                    race_id=10)
        
        # Verify all parameters passed correctly
        call_kwargs = mock_message_class.call_args[1]
        assert call_kwargs['message_type'] == RaceMessageType.RaceInfo
        assert call_kwargs['category_id'] == 5
        assert call_kwargs['race_id'] == 10


@pytest.mark.unit
class TestDoPostSubmitActions:
    """Tests for do_post_submit_actions() function in ui/menus.py"""

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_with_category_submit_role(self, mock_get_user, mock_update_leaderboard):
        """Test role application when category has submit_role."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = 123456789  # Category submit role
        race.submission_role = 987654321  # Race-specific submit role
        
        user_id = 555666777
        mock_user = Mock()
        mock_user.add_roles = AsyncMock()
        mock_get_user.return_value = mock_user
        
        mock_guild = Mock()
        mock_cat_role = Mock()
        mock_race_role = Mock()
        mock_guild.get_role.side_effect = lambda role_id: mock_cat_role if role_id == 123456789 else mock_race_role
        
        mock_interaction = Mock()
        mock_interaction.guild = mock_guild
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify
        mock_get_user.assert_called_once_with(mock_interaction, user_id)
        mock_guild.get_role.assert_any_call(123456789)  # Category role
        mock_guild.get_role.assert_any_call(987654321)  # Race role
        mock_user.add_roles.assert_any_call(mock_cat_role)
        mock_user.add_roles.assert_any_call(mock_race_role)
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_no_submit_roles(self, mock_get_user, mock_update_leaderboard):
        """Test behavior when category has no submit_role."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = None  # No submit role
        race.submission_role = None
        
        user_id = 555666777
        mock_interaction = Mock()
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify
        mock_get_user.assert_not_called()  # Should not try to get user
        mock_interaction.guild.get_role.assert_not_called()  # Should not try to get roles
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_only_category_role(self, mock_get_user, mock_update_leaderboard):
        """Test behavior when only category has submit_role."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = 123456789  # Category submit role
        race.submission_role = None  # No race-specific role
        
        user_id = 555666777
        mock_user = Mock()
        mock_user.add_roles = AsyncMock()
        mock_get_user.return_value = mock_user
        
        mock_guild = Mock()
        mock_cat_role = Mock()
        mock_guild.get_role.side_effect = lambda role_id: mock_cat_role if role_id == 123456789 else None
        
        mock_interaction = Mock()
        mock_interaction.guild = mock_guild
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify
        mock_get_user.assert_called_once_with(mock_interaction, user_id)
        mock_guild.get_role.assert_any_call(123456789)  # Category role
        mock_guild.get_role.assert_any_call(None)  # Race role (None)
        assert mock_guild.get_role.call_count == 2  # Called twice
        mock_user.add_roles.assert_called_once_with(mock_cat_role)  # Only category role added
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_only_race_role(self, mock_get_user, mock_update_leaderboard):
        """Test behavior when only race has submission_role but category has no submit_role."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = None  # No category role
        race.submission_role = 987654321  # Race-specific submit role
        
        user_id = 555666777
        mock_interaction = Mock()
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify - since category.submit_role is None, no role logic should execute
        mock_get_user.assert_not_called()  # Should not try to get user
        mock_interaction.guild.get_role.assert_not_called()  # Should not try to get roles
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_user_not_found(self, mock_get_user, mock_update_leaderboard):
        """Test behavior when user cannot be found."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = 123456789
        race.submission_role = 987654321
        
        user_id = 555666777
        mock_get_user.return_value = None  # User not found
        
        mock_guild = Mock()
        mock_interaction = Mock()
        mock_interaction.guild = mock_guild
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify
        mock_get_user.assert_called_once_with(mock_interaction, user_id)
        mock_guild.get_role.assert_not_called()  # Should not try to get roles
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_role_not_found(self, mock_get_user, mock_update_leaderboard):
        """Test behavior when roles don't exist on server."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = 123456789  # Role doesn't exist
        race.submission_role = 987654321  # Role doesn't exist
        
        user_id = 555666777
        mock_user = Mock()
        mock_user.add_roles = AsyncMock()
        mock_get_user.return_value = mock_user
        
        mock_guild = Mock()
        mock_guild.get_role.return_value = None  # Role not found
        
        mock_interaction = Mock()
        mock_interaction.guild = mock_guild
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify
        mock_get_user.assert_called_once_with(mock_interaction, user_id)
        mock_guild.get_role.assert_any_call(123456789)  # Should try to get category role
        mock_guild.get_role.assert_any_call(987654321)  # Should try to get race role
        mock_user.add_roles.assert_not_called()  # Should not try to add None roles
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_mixed_role_availability(self, mock_get_user, mock_update_leaderboard):
        """Test behavior when one role exists and one doesn't."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = 123456789  # Exists
        race.submission_role = 987654321  # Doesn't exist
        
        user_id = 555666777
        mock_user = Mock()
        mock_user.add_roles = AsyncMock()
        mock_get_user.return_value = mock_user
        
        mock_guild = Mock()
        mock_cat_role = Mock()
        mock_guild.get_role.side_effect = lambda role_id: mock_cat_role if role_id == 123456789 else None
        
        mock_interaction = Mock()
        mock_interaction.guild = mock_guild
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify
        mock_get_user.assert_called_once_with(mock_interaction, user_id)
        mock_guild.get_role.assert_any_call(123456789)  # Category role
        mock_guild.get_role.assert_any_call(987654321)  # Race role
        mock_user.add_roles.assert_called_once_with(mock_cat_role)  # Only category role added
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_always_updates_leaderboard(self, mock_get_user, mock_update_leaderboard):
        """Test that leaderboard is always updated regardless of role application."""
        # Setup
        race = create_mock_race(race_id=1, category_id=1)
        race.category_id.submit_role = None  # No roles to apply
        
        user_id = 555666777
        mock_interaction = Mock()
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify
        mock_update_leaderboard.assert_called_once_with(mock_interaction, race)

    @pytest.mark.asyncio
    @patch('ui.menus.update_race_leaderboard')
    @patch('ui.menus.get_user_from_interaction')
    async def test_do_post_submit_actions_with_none_race(self, mock_get_user, mock_update_leaderboard):
        """Test behavior when race is None."""
        # Setup
        race = None
        user_id = 555666777
        mock_interaction = Mock()
        
        # Execute
        await do_post_submit_actions(mock_interaction, race, user_id)
        
        # Verify - should return early and not do anything
        mock_get_user.assert_not_called()
        mock_interaction.guild.get_role.assert_not_called()
        mock_update_leaderboard.assert_not_called()


@pytest.mark.unit
class TestGetRaceLeaderboardTable:
    """Tests for get_race_leaderboard_table() function in ui/ui_util.py"""

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_basic_submissions(self, mock_get_user_name, mock_get_sorted_submissions, 
                                                         mock_get_extra_info_type, mock_get_extra_info):
        """Test basic leaderboard table generation with submissions."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        
        # Create mock submissions
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", comment="Great run!"
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:45:12", comment="Could be better"
        )
        submission3 = create_mock_submission(
            submission_id=3, race_id=race_id, user_id=333, finish_time="2:01:33", comment="First attempt"
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2, submission3]
        mock_get_user_name.side_effect = lambda user_id, user: f"User{user_id}"
        
        # Mock extra info assignments (none for this test)
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = []
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify
            assert "1st" in result
            assert "2nd" in result  
            assert "3rd" in result
            assert "User111" in result
            assert "User222" in result
            assert "User333" in result
            assert "1:23:45" in result
            assert "1:45:12" in result
            assert "2:01:33" in result
            assert "Great run!" in result
            assert "Could be better" in result
            assert "First attempt" in result
            assert "Name" in result
            assert "Finish Time" in result
            assert "Comment" in result
            
            mock_get_sorted_submissions.assert_called_once_with(race_id)
            assert mock_get_user_name.call_count == 3

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_with_extra_info(self, mock_get_user_name, mock_get_sorted_submissions,
                                                       mock_get_extra_info_type, mock_get_extra_info):
        """Test leaderboard table with extra info assignments."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        
        # Create mock submissions
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", comment="Great run!"
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:45:12", comment="Could be better"
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2]
        mock_get_user_name.side_effect = lambda user_id, user: f"User{user_id}"
        
        # Create mock extra info assignments
        mock_assignment1 = Mock()
        mock_assignment1.info_type_id = 1
        mock_assignment2 = Mock()
        mock_assignment2.info_type_id = 2
        
        # Create mock extra info types
        mock_extra_info_type1 = create_mock_extra_info_type(info_type_id=1, name="Collection Rate")
        mock_extra_info_type2 = create_mock_extra_info_type(info_type_id=2, name="VoD Link")
        
        # Create mock extra info data
        mock_extra_info1 = create_mock_extra_info(submission_id=1, info_type_id=1, data="95.5%")
        mock_extra_info2 = create_mock_extra_info(submission_id=2, info_type_id=1, data="87.2%")
        mock_extra_info3 = create_mock_extra_info(submission_id=1, info_type_id=2, data="https://youtube.com/watch?v=abc123")
        
        mock_get_extra_info_type.side_effect = lambda info_type_id: mock_extra_info_type1 if info_type_id == 1 else mock_extra_info_type2
        mock_get_extra_info.side_effect = lambda submission_id, info_type_id: {
            (1, 1): mock_extra_info1,
            (2, 1): mock_extra_info2,
            (1, 2): mock_extra_info3,
            (2, 2): None  # No VoD link for submission 2
        }.get((submission_id, info_type_id))
        
        # Mock extra info assignments
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = [mock_assignment1, mock_assignment2]
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify
            assert "Collection Rate" in result
            assert "VoD Link" in result
            assert "95.5%" in result
            assert "87.2%" in result
            assert "https://youtube.com/watch?v=abc123" in result
            assert "Name" in result
            assert "Finish Time" in result
            assert "Comment" in result
            
            # Verify extra info lookups
            assert mock_get_extra_info_type.call_count == 2
            assert mock_get_extra_info.call_count == 4  # 2 submissions × 2 extra info types

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_no_submissions(self, mock_get_user_name, mock_get_sorted_submissions,
                                                      mock_get_extra_info_type, mock_get_extra_info):
        """Test leaderboard table with no submissions."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        
        mock_get_sorted_submissions.return_value = None
        
        # Mock extra info assignments (none for this test)
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = []
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify
            assert "Name" in result
            assert "Finish Time" in result
            assert "Comment" in result
            # Should not contain any user data
            assert "User" not in result
            assert "1st" not in result
            assert "2nd" not in result
            
            mock_get_sorted_submissions.assert_called_once_with(race_id)
            mock_get_user_name.assert_not_called()

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_empty_submissions_list(self, mock_get_user_name, mock_get_sorted_submissions,
                                                              mock_get_extra_info_type, mock_get_extra_info):
        """Test leaderboard table with empty submissions list."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        
        mock_get_sorted_submissions.return_value = []
        
        # Mock extra info assignments (none for this test)
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = []
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify
            assert "Name" in result
            assert "Finish Time" in result
            assert "Comment" in result
            # Should not contain any user data
            assert "User" not in result
            assert "1st" not in result
            assert "2nd" not in result
            
            mock_get_sorted_submissions.assert_called_once_with(race_id)
            mock_get_user_name.assert_not_called()

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_missing_extra_info_type(self, mock_get_user_name, mock_get_sorted_submissions,
                                                               mock_get_extra_info_type, mock_get_extra_info):
        """Test leaderboard table when extra info type is not found."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        
        # Create mock submissions
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", comment="Great run!"
        )
        
        mock_get_sorted_submissions.return_value = [submission1]
        mock_get_user_name.return_value = "User111"
        
        # Create mock extra info assignments with missing type
        mock_assignment1 = Mock()
        mock_assignment1.info_type_id = 999  # Non-existent type
        
        mock_get_extra_info_type.return_value = None  # Type not found
        mock_get_extra_info.return_value = None
        
        # Mock extra info assignments
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = [mock_assignment1]
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify
            assert "User111" in result
            assert "1:23:45" in result
            assert "Great run!" in result
            # Should not include the missing extra info type
            assert "Name" in result
            assert "Finish Time" in result
            assert "Comment" in result
            
            mock_get_extra_info_type.assert_called_once_with(999)

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_user_not_found(self, mock_get_user_name, mock_get_sorted_submissions,
                                                      mock_get_extra_info_type, mock_get_extra_info):
        """Test leaderboard table when user is not found by client."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        mock_interaction.client.get_user.return_value = None  # User not found
        
        # Create mock submissions
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", comment="Great run!"
        )
        
        mock_get_sorted_submissions.return_value = [submission1]
        mock_get_user_name.return_value = "111"  # Fallback to user_id
        
        # Mock extra info assignments (none for this test)
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = []
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify
            assert "111" in result  # Should show user_id as fallback
            assert "1:23:45" in result
            assert "Great run!" in result
            assert "1st" in result
            
            mock_interaction.client.get_user.assert_called_once_with(111)
            mock_get_user_name.assert_called_once_with(111, None)

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_sorting_verification(self, mock_get_user_name, mock_get_sorted_submissions,
                                                            mock_get_extra_info_type, mock_get_extra_info):
        """Test that leaderboard respects the sorting from get_sorted_race_submissions."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        
        # Create mock submissions in reverse order (slowest first)
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="2:01:33", comment="Slowest"
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:45:12", comment="Middle"
        )
        submission3 = create_mock_submission(
            submission_id=3, race_id=race_id, user_id=333, finish_time="1:23:45", comment="Fastest"
        )
        
        # Return submissions in reverse order (slowest first)
        mock_get_sorted_submissions.return_value = [submission1, submission2, submission3]
        mock_get_user_name.side_effect = lambda user_id, user: f"User{user_id}"
        
        # Mock extra info assignments (none for this test)
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = []
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify the order in the table matches the submission order
            # Find the positions of each user in the result
            lines = result.split('\n')
            user111_line = next((line for line in lines if "User111" in line), None)
            user222_line = next((line for line in lines if "User222" in line), None)
            user333_line = next((line for line in lines if "User333" in line), None)
            
            assert user111_line is not None
            assert user222_line is not None
            assert user333_line is not None
            
            # Find line numbers
            user111_idx = lines.index(user111_line)
            user222_idx = lines.index(user222_line)
            user333_idx = lines.index(user333_line)
            
            # User111 should come first (slowest), then User222, then User333 (fastest)
            assert user111_idx < user222_idx < user333_idx
            
            mock_get_sorted_submissions.assert_called_once_with(race_id)

    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_user_name_str')
    def test_get_race_leaderboard_table_comment_handling(self, mock_get_user_name, mock_get_sorted_submissions,
                                                        mock_get_extra_info_type, mock_get_extra_info):
        """Test leaderboard table with various comment scenarios."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.client = Mock()
        
        # Create mock submissions with different comment scenarios
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", comment="Great run!"
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:45:12", comment=""  # Empty comment
        )
        submission3 = create_mock_submission(
            submission_id=3, race_id=race_id, user_id=333, finish_time="2:01:33", comment=None  # None comment
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2, submission3]
        mock_get_user_name.side_effect = lambda user_id, user: f"User{user_id}"
        
        # Mock extra info assignments (none for this test)
        with patch('ui.ui_util.AsyncRaceExtraInfoAssignment') as mock_assignment_class:
            mock_assignment_class.select.return_value.where.return_value = []
            
            # Execute
            result = get_race_leaderboard_table(mock_interaction, race_id)
            
            # Verify
            assert "Great run!" in result
            assert "User111" in result
            assert "User222" in result
            assert "User333" in result
            # Empty and None comments should be handled gracefully
            assert "Comment" in result  # Column header should be present
            
            mock_get_sorted_submissions.assert_called_once_with(race_id)
            assert mock_get_user_name.call_count == 3


@pytest.mark.unit
class TestGetSortedTeamSubmissions:
    """Tests for get_sorted_team_submissions() function in ui/ui_util.py"""

    @patch('ui.ui_util.finish_time_seconds_to_str')
    @patch('ui.ui_util.finish_time_to_seconds')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_get_sorted_team_submissions_not_team_race(self, mock_get_race, mock_get_sorted_submissions, 
                                                      mock_get_user_name, mock_get_extra_info, 
                                                      mock_finish_time_to_seconds, mock_finish_time_seconds_to_str):
        """Test that function returns None for non-team races."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=False)
        mock_get_race.return_value = race
        
        # Execute
        result = get_sorted_team_submissions(mock_interaction, race_id)
        
        # Verify
        assert result is None
        mock_get_race.assert_called_once_with(race_id)
        mock_get_sorted_submissions.assert_not_called()

    @patch('ui.ui_util.finish_time_seconds_to_str')
    @patch('ui.ui_util.finish_time_to_seconds')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_get_sorted_team_submissions_single_submission(self, mock_get_race, mock_get_sorted_submissions, 
                                                          mock_get_user_name, mock_get_extra_info, 
                                                          mock_finish_time_to_seconds, mock_finish_time_seconds_to_str):
        """Test team submissions with single submission (no teammate)."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=True, team_name_info_id=1)
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Solo run", teammate_id=None
        )
        
        mock_get_sorted_submissions.return_value = [submission1]
        mock_get_user_name.return_value = "Player1"
        mock_get_extra_info.return_value = None  # No team name
        mock_finish_time_to_seconds.return_value = 5025  # 1:23:45 in seconds
        mock_finish_time_seconds_to_str.return_value = "1:23:45"
        
        # Execute
        result = get_sorted_team_submissions(mock_interaction, race_id)
        
        # Verify
        assert result is not None
        assert len(result) == 1
        
        team_sub = result[0]
        assert team_sub.team_name == "Team Player1"
        assert team_sub.user_ids == [111]
        assert team_sub.user_names == ["Player1"]
        assert team_sub.team_finish_time == "1:23:45"
        assert team_sub.finish_times == ["1:23:45", None]
        
        mock_get_race.assert_called_once_with(race_id)
        mock_get_sorted_submissions.assert_called_once_with(race_id)
        mock_get_user_name.assert_called_once_with(111, mock_interaction.guild.get_member(111))

    @patch('ui.ui_util.finish_time_seconds_to_str')
    @patch('ui.ui_util.finish_time_to_seconds')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_get_sorted_team_submissions_matched_teammates(self, mock_get_race, mock_get_sorted_submissions, 
                                                         mock_get_user_name, mock_get_extra_info, 
                                                         mock_finish_time_to_seconds, mock_finish_time_seconds_to_str):
        """Test team submissions with matched teammates."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=True, team_name_info_id=1)
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Team run", teammate_id=222
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:25:30", 
            comment="Team run", teammate_id=111
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2]
        mock_get_user_name.side_effect = lambda user_id, user: f"Player{user_id}"
        mock_get_extra_info.return_value = None  # No team name
        mock_finish_time_to_seconds.side_effect = lambda time: 5025 if time == "1:23:45" else 5130  # 1:25:30
        mock_finish_time_seconds_to_str.return_value = "1:24:37"  # Average time
        
        # Execute
        result = get_sorted_team_submissions(mock_interaction, race_id)
        
        # Verify
        assert result is not None
        assert len(result) == 1
        
        team_sub = result[0]
        assert team_sub.team_name == "Team Player111 & Player222"
        assert team_sub.user_ids == [111, 222]
        assert team_sub.user_names == ["Player111", "Player222"]
        assert team_sub.team_finish_time == "1:24:37"
        assert team_sub.finish_times == ["1:23:45", "1:25:30"]
        
        # Verify finish_time_to_seconds was called for both times plus sorting
        assert mock_finish_time_to_seconds.call_count == 3  # 2 for calculation + 1 for sorting
        mock_finish_time_to_seconds.assert_any_call("1:23:45")
        mock_finish_time_to_seconds.assert_any_call("1:25:30")
        mock_finish_time_to_seconds.assert_any_call("1:24:37")  # For sorting

    @patch('ui.ui_util.finish_time_seconds_to_str')
    @patch('ui.ui_util.finish_time_to_seconds')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_get_sorted_team_submissions_with_team_name(self, mock_get_race, mock_get_sorted_submissions, 
                                                      mock_get_user_name, mock_get_extra_info, 
                                                      mock_finish_time_to_seconds, mock_finish_time_seconds_to_str):
        """Test team submissions with custom team name."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=True, team_name_info_id=1)
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Team run", teammate_id=222
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:25:30", 
            comment="Team run", teammate_id=111
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2]
        mock_get_user_name.side_effect = lambda user_id, user: f"Player{user_id}"
        
        # Mock team name extra info
        team_name_info = create_mock_extra_info(submission_id=1, info_type_id=1, data="Awesome Team")
        mock_get_extra_info.return_value = team_name_info
        
        mock_finish_time_to_seconds.side_effect = lambda time: 5025 if time == "1:23:45" else 5130
        mock_finish_time_seconds_to_str.return_value = "1:24:37"
        
        # Execute
        result = get_sorted_team_submissions(mock_interaction, race_id)
        
        # Verify
        assert result is not None
        assert len(result) == 1
        
        team_sub = result[0]
        assert team_sub.team_name == "Awesome Team"
        assert team_sub.user_ids == [111, 222]
        assert team_sub.user_names == ["Player111", "Player222"]
        assert team_sub.team_finish_time == "1:24:37"
        assert team_sub.finish_times == ["1:23:45", "1:25:30"]

    @patch('ui.ui_util.finish_time_seconds_to_str')
    @patch('ui.ui_util.finish_time_to_seconds')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_get_sorted_team_submissions_teammate_id_mismatch(self, mock_get_race, mock_get_sorted_submissions, 
                                                            mock_get_user_name, mock_get_extra_info, 
                                                            mock_finish_time_to_seconds, mock_finish_time_seconds_to_str):
        """Test team submissions with teammate ID mismatch."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=True, team_name_info_id=1)
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Team run", teammate_id=222
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:25:30", 
            comment="Team run", teammate_id=333  # Mismatch - should be 111
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2]
        mock_get_user_name.return_value = "Player111"
        mock_get_extra_info.return_value = None
        mock_finish_time_to_seconds.return_value = 5025
        mock_finish_time_seconds_to_str.return_value = "1:23:45"
        
        # Execute
        result = get_sorted_team_submissions(mock_interaction, race_id)
        
        # Verify - should treat as solo submission due to mismatch
        assert result is not None
        assert len(result) == 2  # Both submissions treated as solo
        
        # First submission (solo due to mismatch)
        team_sub1 = result[0]
        assert team_sub1.team_name == "Team Player111"
        assert team_sub1.user_ids == [111]
        assert team_sub1.user_names == ["Player111"]
        assert team_sub1.team_finish_time == "1:23:45"
        assert team_sub1.finish_times == ["1:23:45", None]

    @patch('ui.ui_util.finish_time_seconds_to_str')
    @patch('ui.ui_util.finish_time_to_seconds')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_get_sorted_team_submissions_multiple_teams(self, mock_get_race, mock_get_sorted_submissions, 
                                                       mock_get_user_name, mock_get_extra_info, 
                                                       mock_finish_time_to_seconds, mock_finish_time_seconds_to_str):
        """Test team submissions with multiple teams."""
        # Setup
        race_id = 123
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=True, team_name_info_id=1)
        mock_get_race.return_value = race
        
        # Team 1: Users 111 & 222
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Team 1", teammate_id=222
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:25:30", 
            comment="Team 1", teammate_id=111
        )
        
        # Team 2: Users 333 & 444
        submission3 = create_mock_submission(
            submission_id=3, race_id=race_id, user_id=333, finish_time="1:30:00", 
            comment="Team 2", teammate_id=444
        )
        submission4 = create_mock_submission(
            submission_id=4, race_id=race_id, user_id=444, finish_time="1:32:15", 
            comment="Team 2", teammate_id=333
        )
        
        # Solo submission: User 555
        submission5 = create_mock_submission(
            submission_id=5, race_id=race_id, user_id=555, finish_time="1:35:00", 
            comment="Solo", teammate_id=None
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2, submission3, submission4, submission5]
        mock_get_user_name.side_effect = lambda user_id, user: f"Player{user_id}"
        mock_get_extra_info.return_value = None
        mock_finish_time_to_seconds.side_effect = lambda time: {
            "1:23:45": 5025, "1:25:30": 5130, "1:30:00": 5400, "1:32:15": 5535, "1:35:00": 5700,
            "1:24:37": 5077, "1:31:07": 5467  # Average times for sorting
        }[time]
        mock_finish_time_seconds_to_str.side_effect = lambda sec: {
            5077: "1:24:37", 5467: "1:31:07", 5700: "1:35:00"
        }[sec]
        
        # Execute
        result = get_sorted_team_submissions(mock_interaction, race_id)
        
        # Verify
        assert result is not None
        assert len(result) == 3  # 2 teams + 1 solo
        
        # Results should be sorted by team finish time
        team1 = result[0]  # Fastest team
        team2 = result[1]  # Second team
        solo = result[2]   # Solo submission
        
        assert team1.team_name == "Team Player111 & Player222"
        assert team1.user_ids == [111, 222]
        assert team1.team_finish_time == "1:24:37"
        
        assert team2.team_name == "Team Player333 & Player444"
        assert team2.user_ids == [333, 444]
        assert team2.team_finish_time == "1:31:07"
        
        assert solo.team_name == "Team Player555"
        assert solo.user_ids == [555]
        assert solo.team_finish_time == "1:35:00"


@pytest.mark.unit
class TestExportRace:
    """Tests for export_race() function in ui/ui_util.py"""

    @patch('ui.ui_util.csv.writer')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('ui.ui_util.get_sorted_team_submissions')
    @patch('ui.ui_util.get_race_extra_info_assignments')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_export_race_basic_individual_race(self, mock_get_race, mock_get_sorted_submissions, 
                                             mock_get_user_name, mock_get_extra_info, 
                                             mock_get_extra_info_type, mock_get_race_extra_info_assignments,
                                             mock_get_sorted_team_submissions, mock_open, mock_csv_writer):
        """Test basic individual race export."""
        # Setup
        race_id = 123
        filepath = "test_export.csv"
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=False, state=RaceState.Completed)
        race.category_id.points_type = PointsType.NoScoring
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Great run!", points=None
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:25:30", 
            comment="Good run", points=None
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2]
        mock_get_user_name.side_effect = lambda user_id, user: f"Player{user_id}"
        mock_get_race_extra_info_assignments.return_value = []
        mock_get_sorted_team_submissions.return_value = None
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_csv_writer.return_value = mock_file
        
        # Execute
        result = export_race(mock_interaction, race_id, filepath)
        
        # Verify
        assert result is True
        mock_open.assert_called_once_with(filepath, 'w', newline='')
        
        # Verify CSV writer calls
        assert mock_file.writerow.call_count == 3  # Header + 2 data rows
        
        # Check header row
        header_call = mock_file.writerow.call_args_list[0][0][0]
        assert "User ID" in header_call
        assert "Username" in header_call
        assert "Finish Time" in header_call
        assert "Comment" in header_call
        assert "Points" not in header_call  # No scoring race

    @patch('ui.ui_util.csv.writer')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('ui.ui_util.get_sorted_team_submissions')
    @patch('ui.ui_util.get_race_extra_info_assignments')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_export_race_with_points(self, mock_get_race, mock_get_sorted_submissions, 
                                   mock_get_user_name, mock_get_extra_info, 
                                   mock_get_extra_info_type, mock_get_race_extra_info_assignments,
                                   mock_get_sorted_team_submissions, mock_open, mock_csv_writer):
        """Test race export with points scoring."""
        # Setup
        race_id = 123
        filepath = "test_export.csv"
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=False, state=RaceState.Completed)
        race.category_id.points_type = PointsType.MarioKart
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Great run!", points=100.0
        )
        
        mock_get_sorted_submissions.return_value = [submission1]
        mock_get_user_name.return_value = "Player111"
        mock_get_race_extra_info_assignments.return_value = []
        mock_get_sorted_team_submissions.return_value = None
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_csv_writer.return_value = mock_file
        
        # Execute
        result = export_race(mock_interaction, race_id, filepath)
        
        # Verify
        assert result is True
        
        # Check header includes Points
        header_call = mock_file.writerow.call_args_list[0][0][0]
        assert "Points" in header_call
        
        # Check data row includes points
        data_call = mock_file.writerow.call_args_list[1][0][0]
        assert 100.0 in data_call

    @patch('ui.ui_util.get_race')
    def test_export_race_race_not_found(self, mock_get_race):
        """Test export when race is not found."""
        # Setup
        race_id = 123
        filepath = "test_export.csv"
        mock_interaction = Mock()
        
        mock_get_race.return_value = None
        
        # Execute
        result = export_race(mock_interaction, race_id, filepath)
        
        # Verify
        assert result is False
        mock_get_race.assert_called_once_with(race_id)

    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_export_race_no_submissions(self, mock_get_race, mock_get_sorted_submissions):
        """Test export when race has no submissions."""
        # Setup
        race_id = 123
        filepath = "test_export.csv"
        mock_interaction = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=False)
        mock_get_race.return_value = race
        mock_get_sorted_submissions.return_value = None
        
        # Execute
        result = export_race(mock_interaction, race_id, filepath)
        
        # Verify
        assert result is False
        mock_get_race.assert_called_once_with(race_id)
        mock_get_sorted_submissions.assert_called_once_with(race_id)

    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_export_race_empty_submissions(self, mock_get_race, mock_get_sorted_submissions):
        """Test export when race has empty submissions list."""
        # Setup
        race_id = 123
        filepath = "test_export.csv"
        mock_interaction = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=False)
        mock_get_race.return_value = race
        mock_get_sorted_submissions.return_value = []
        
        # Execute
        result = export_race(mock_interaction, race_id, filepath)
        
        # Verify
        assert result is False
        mock_get_race.assert_called_once_with(race_id)
        mock_get_sorted_submissions.assert_called_once_with(race_id)

    @patch('ui.ui_util.csv.writer')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('ui.ui_util.get_sorted_team_submissions')
    @patch('ui.ui_util.get_race_extra_info_assignments')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_export_race_with_extra_info(self, mock_get_race, mock_get_sorted_submissions, 
                                       mock_get_user_name, mock_get_extra_info, 
                                       mock_get_extra_info_type, mock_get_race_extra_info_assignments,
                                       mock_get_sorted_team_submissions, mock_open, mock_csv_writer):
        """Test race export with extra info columns."""
        # Setup
        race_id = 123
        filepath = "test_export.csv"
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=False, state=RaceState.Completed)
        race.category_id.points_type = PointsType.NoScoring
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Great run!"
        )
        
        mock_get_sorted_submissions.return_value = [submission1]
        mock_get_user_name.return_value = "Player111"
        
        # Mock extra info assignments
        mock_assignment1 = Mock()
        mock_assignment1.info_type_id = 1
        mock_assignment2 = Mock()
        mock_assignment2.info_type_id = 2
        
        mock_extra_info_type1 = create_mock_extra_info_type(info_type_id=1, name="Collection Rate", var_type=0)  # String
        mock_extra_info_type2 = create_mock_extra_info_type(info_type_id=2, name="Score", var_type=1)  # Int
        
        mock_get_race_extra_info_assignments.return_value = [mock_assignment1, mock_assignment2]
        mock_get_extra_info_type.side_effect = lambda info_type_id: mock_extra_info_type1 if info_type_id == 1 else mock_extra_info_type2
        
        # Mock extra info data
        mock_extra_info1 = create_mock_extra_info(submission_id=1, info_type_id=1, data="95.5%")
        mock_extra_info2 = create_mock_extra_info(submission_id=1, info_type_id=2, data="1500")
        
        mock_get_extra_info.side_effect = lambda submission_id, info_type_id: {
            (1, 1): mock_extra_info1,
            (1, 2): mock_extra_info2
        }.get((submission_id, info_type_id))
        
        mock_get_sorted_team_submissions.return_value = None
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_csv_writer.return_value = mock_file
        
        # Execute
        result = export_race(mock_interaction, race_id, filepath)
        
        # Verify
        assert result is True
        
        # Check header includes extra info columns
        header_call = mock_file.writerow.call_args_list[0][0][0]
        assert "Collection Rate" in header_call
        assert "Score" in header_call
        
        # Check data row includes extra info data
        data_call = mock_file.writerow.call_args_list[1][0][0]
        assert "95.5%" in data_call
        assert 1500 in data_call  # Int type should be converted

    @patch('ui.ui_util.csv.writer')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('ui.ui_util.get_sorted_team_submissions')
    @patch('ui.ui_util.get_race_extra_info_assignments')
    @patch('ui.ui_util.get_extra_info_type')
    @patch('ui.ui_util.get_extra_info')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_sorted_race_submissions')
    @patch('ui.ui_util.get_race')
    def test_export_race_team_race(self, mock_get_race, mock_get_sorted_submissions, 
                                  mock_get_user_name, mock_get_extra_info, 
                                  mock_get_extra_info_type, mock_get_race_extra_info_assignments,
                                  mock_get_sorted_team_submissions, mock_open, mock_csv_writer):
        """Test team race export with team data."""
        # Setup
        race_id = 123
        filepath = "test_export.csv"
        mock_interaction = Mock()
        mock_interaction.guild = Mock()
        
        race = create_mock_race(race_id=race_id, is_team_race=True, state=RaceState.Completed)
        race.category_id.points_type = PointsType.NoScoring
        mock_get_race.return_value = race
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=race_id, user_id=111, finish_time="1:23:45", 
            comment="Team run", teammate_id=222
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=race_id, user_id=222, finish_time="1:25:30", 
            comment="Team run", teammate_id=111
        )
        
        mock_get_sorted_submissions.return_value = [submission1, submission2]
        mock_get_user_name.side_effect = lambda user_id, user: f"Player{user_id}"
        mock_get_race_extra_info_assignments.return_value = []
        
        # Mock team submissions
        from ui.ui_util import TeamSubmissionData
        team_sub = TeamSubmissionData(
            team_name="Test Team",
            user_ids=[111, 222],
            user_names=["Player111", "Player222"],
            team_finish_time="1:24:37",
            finish_times=["1:23:45", "1:25:30"]
        )
        mock_get_sorted_team_submissions.return_value = [team_sub]
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_csv_writer.return_value = mock_file
        
        # Execute
        result = export_race(mock_interaction, race_id, filepath)
        
        # Verify
        assert result is True
        
        # Check header includes team columns
        header_call = mock_file.writerow.call_args_list[0][0][0]
        assert "Teammate ID" in header_call
        assert "Teammate Username" in header_call
        assert "Team Finish Time (Avg)" in header_call
        
        # Check data rows include team data
        data_calls = [call[0][0] for call in mock_file.writerow.call_args_list[1:]]
        assert len(data_calls) == 2  # Two data rows
        
        # Verify team data is included in both rows
        for data_call in data_calls:
            assert 222 in data_call or 111 in data_call  # Teammate ID
            assert "Player222" in data_call or "Player111" in data_call  # Teammate username
            assert "1:24:37" in data_call  # Team finish time


@pytest.mark.unit
class TestGetRaceInfoMessage:
    """Tests for get_race_info_message() function in ui/ui_util.py"""

    @patch('ui.ui_util.validators.url')
    def test_get_race_info_message_basic(self, mock_validators_url):
        """Test basic race info message creation."""
        # Setup
        race = create_mock_race(
            race_id=123,
            description="Test Race",
            seed="ABC123DEF456",
            hash="1234567890abcdef",
            additional_instructions="Test instructions"
        )
        race.create_datetime = "2024-01-15 10:30:00"
        race.category_id.thumbnail_url = "https://example.com/thumb.jpg"
        
        mock_validators_url.return_value = False  # No URL in seed
        
        # Execute
        result = get_race_info_message(race)
        
        # Verify
        assert result.title == "Test Race"
        assert "Use the buttons below for Race ID 123" in result.description
        assert "*Created On:* 2024-01-15 10:30:00" in result.description
        assert "Test instructions" in result.description
        assert result.url is None  # No URL found in seed
        assert result.thumbnail.url == "https://example.com/thumb.jpg"
        
        # Check fields
        seed_field = next((field for field in result.fields if field.name == "Seed"), None)
        assert seed_field is not None
        assert seed_field.value == "ABC123DEF456"
        assert seed_field.inline is False
        
        hash_field = next((field for field in result.fields if field.name == "Hash"), None)
        assert hash_field is not None
        assert hash_field.value == "1234567890abcdef"
        assert hash_field.inline is False

    @patch('ui.ui_util.validators.url')
    def test_get_race_info_message_with_seed_url(self, mock_validators_url):
        """Test race info message with URL in seed."""
        # Setup
        race = create_mock_race(
            race_id=456,
            description="URL Race",
            seed="https://example.com/seed ABC123DEF456",
            hash=None,
            additional_instructions=None
        )
        race.create_datetime = "2024-01-20 15:45:00"
        race.category_id.thumbnail_url = None
        
        # Mock URL validation - first part is URL, second is not
        mock_validators_url.side_effect = lambda url: url == "https://example.com/seed"
        
        # Execute
        result = get_race_info_message(race)
        
        # Verify
        assert result.title == "URL Race"
        assert "Use the buttons below for Race ID 456" in result.description
        assert "*Created On:* 2024-01-20 15:45:00" in result.description
        assert result.url == "https://example.com/seed"
        assert result.thumbnail.url is None  # No thumbnail
        
        # Check fields
        seed_field = next((field for field in result.fields if field.name == "Seed"), None)
        assert seed_field is not None
        assert seed_field.value == "https://example.com/seed ABC123DEF456"
        
        # No hash field should be present
        hash_field = next((field for field in result.fields if field.name == "Hash"), None)
        assert hash_field is None

    @patch('ui.ui_util.validators.url')
    def test_get_race_info_message_empty_hash(self, mock_validators_url):
        """Test race info message with empty hash."""
        # Setup
        race = create_mock_race(
            race_id=789,
            description="Empty Hash Race",
            seed="DEF456GHI789",
            hash="",  # Empty hash
            additional_instructions=None
        )
        race.create_datetime = "2024-01-25 08:15:00"
        race.category_id.thumbnail_url = None
        
        mock_validators_url.return_value = False
        
        # Execute
        result = get_race_info_message(race)
        
        # Verify
        assert result.title == "Empty Hash Race"
        
        # No hash field should be present for empty hash
        hash_field = next((field for field in result.fields if field.name == "Hash"), None)
        assert hash_field is None

    @patch('ui.ui_util.validators.url')
    def test_get_race_info_message_thumbnail_error(self, mock_validators_url):
        """Test race info message with thumbnail URL that causes error."""
        # Setup
        race = create_mock_race(
            race_id=999,
            description="Thumbnail Error Race",
            seed="GHI789JKL012",
            hash="abcdef123456",
            additional_instructions=None
        )
        race.create_datetime = "2024-01-30 12:00:00"
        race.category_id.thumbnail_url = "invalid-url"
        
        mock_validators_url.return_value = False
        
        # Execute - should not raise exception even if thumbnail fails
        result = get_race_info_message(race)
        
        # Verify
        assert result.title == "Thumbnail Error Race"
        # Function should handle thumbnail error gracefully - thumbnail is still set but may be invalid
        # The try-except just logs the error but doesn't prevent setting the thumbnail


@pytest.mark.unit
class TestGetRaceLeaderboardEmbed:
    """Tests for get_race_leaderboard_embed() function in ui/ui_util.py"""

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_submission_details_dict')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_place_str')
    async def test_get_race_leaderboard_embed_with_details(self, mock_get_place_str, mock_get_user_name_str, mock_get_submission_details_dict):
        """Test race leaderboard embed with show_details=True."""
        # Setup
        title = "Test Race Leaderboard"
        body_text = "Test race results"
        current_page = 0
        per_page = 5
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=123, user_id=111, finish_time="1:23:45", 
            comment="Great run!", points=100.0
        )
        submission2 = create_mock_submission(
            submission_id=2, race_id=123, user_id=222, finish_time="1:25:30", 
            comment="Good run", points=80.0
        )
        submissions = [submission1, submission2]
        
        mock_bot_client = Mock()
        mock_user1 = Mock()
        mock_user1.id = 111
        mock_user2 = Mock()
        mock_user2.id = 222
        
        mock_bot_client.fetch_user = AsyncMock(side_effect=lambda user_id: mock_user1 if user_id == 111 else mock_user2)
        mock_get_user_name_str.side_effect = lambda user_id, user: f"Player{user_id}"
        mock_get_place_str.side_effect = lambda place: f"{place}st" if place == 1 else f"{place}nd"
        
        # Mock submission details
        def mock_submission_details(sub):
            if sub.submission_id == 1:
                return {
                    "Collection Rate": "95.5%",
                    "Score": "1500",
                    "Points": "100.0"
                }
            else:
                return {
                    "Collection Rate": "92.0%", 
                    "Points": "80.0"
                }
        
        mock_get_submission_details_dict.side_effect = mock_submission_details
        
        # Execute
        result = await get_race_leaderboard_embed(title, body_text, submissions, current_page, per_page, mock_bot_client, show_details=True)
        
        # Verify
        assert result.title == title
        assert result.description == body_text
        assert len(result.fields) == 2
        
        # Check first field
        field1 = result.fields[0]
        assert field1.name == "1st"
        assert "**Player111**" in field1.value
        # The function processes submissions in order, so first submission should have its details
        assert "--: Collection Rate: 95.5%" in field1.value or "--: Collection Rate: 92.0%" in field1.value
        assert field1.inline is False
        
        # Check second field
        field2 = result.fields[1]
        assert field2.name == "2nd"
        assert "**Player222**" in field2.value
        # The function processes submissions in order, so second submission should have its details
        assert "--: Collection Rate: 95.5%" in field2.value or "--: Collection Rate: 92.0%" in field2.value
        assert field2.inline is False

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_place_str')
    async def test_get_race_leaderboard_embed_without_details(self, mock_get_place_str, mock_get_user_name_str):
        """Test race leaderboard embed with show_details=False."""
        # Setup
        title = "Simple Leaderboard"
        body_text = "Simple results"
        current_page = 1  # Second page
        per_page = 3
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=123, user_id=111, finish_time="1:23:45", 
            comment="Great run!"
        )
        submissions = [submission1]
        
        mock_bot_client = Mock()
        mock_user1 = Mock()
        mock_user1.id = 111
        
        mock_bot_client.fetch_user = AsyncMock(return_value=mock_user1)
        mock_get_user_name_str.return_value = "Player111"
        mock_get_place_str.return_value = "4th"  # Page 1, position 1 = 4th overall
        
        # Execute
        result = await get_race_leaderboard_embed(title, body_text, submissions, current_page, per_page, mock_bot_client, show_details=False)
        
        # Verify
        assert result.title == title
        assert result.description == body_text
        assert len(result.fields) == 1
        
        field1 = result.fields[0]
        assert field1.name == "4th"
        assert field1.value == "1:23:45 - Player111"
        assert field1.inline is False

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_submission_details_dict')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_place_str')
    async def test_get_race_leaderboard_embed_points_last(self, mock_get_place_str, mock_get_user_name_str, mock_get_submission_details_dict):
        """Test that points field is added last in details."""
        # Setup
        title = "Points Last Test"
        body_text = "Testing points order"
        current_page = 0
        per_page = 5
        
        submission1 = create_mock_submission(
            submission_id=1, race_id=123, user_id=111, finish_time="1:23:45", 
            comment="Test run"
        )
        submissions = [submission1]
        
        mock_bot_client = Mock()
        mock_user1 = Mock()
        mock_user1.id = 111
        
        mock_bot_client.fetch_user = AsyncMock(return_value=mock_user1)
        mock_get_user_name_str.return_value = "Player111"
        mock_get_place_str.return_value = "1st"
        
        # Mock submission details with points
        mock_get_submission_details_dict.return_value = {
            "Collection Rate": "95.5%",
            "Score": "1500",
            "Points": "100.0",
            "Other Field": "test"
        }
        
        # Execute
        result = await get_race_leaderboard_embed(title, body_text, submissions, current_page, per_page, mock_bot_client, show_details=True)
        
        # Verify
        field1 = result.fields[0]
        value_lines = field1.value.split('\n')
        
        # Points should be last
        assert value_lines[-1] == "--: Points: 100.0"
        # Other fields should come before points
        assert "--: Collection Rate: 95.5%" in field1.value
        assert "--: Score: 1500" in field1.value
        assert "--: Other Field: test" in field1.value


@pytest.mark.unit
class TestGetCategoryLeaderboardEmbed:
    """Tests for get_category_leaderboard_embed() function in ui/ui_util.py"""

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_num_category_submissions')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_place_str')
    @patch('ui.ui_util.format_points_str')
    async def test_get_category_leaderboard_embed_basic(self, mock_format_points_str, mock_get_place_str, mock_get_user_name_str, mock_get_num_category_submissions):
        """Test basic category leaderboard embed creation."""
        # Setup
        title = "Category Leaderboard"
        body_text = "Category results"
        current_page = 0
        per_page = 5
        
        # Mock points objects
        point1 = Mock()
        point1.user_id = 111
        point1.category_id = 1
        point1.points = 150.5
        
        point2 = Mock()
        point2.user_id = 222
        point2.category_id = 1
        point2.points = 120.0
        
        points_list = [point1, point2]
        
        mock_bot_client = Mock()
        mock_user1 = Mock()
        mock_user1.id = 111
        mock_user2 = Mock()
        mock_user2.id = 222
        
        mock_bot_client.fetch_user = AsyncMock(side_effect=lambda user_id: mock_user1 if user_id == 111 else mock_user2)
        mock_get_user_name_str.side_effect = lambda user_id, user: f"Player{user_id}"
        mock_get_place_str.side_effect = lambda place: f"{place}st" if place == 1 else f"{place}nd"
        mock_format_points_str.side_effect = lambda points: f"{points:.1f}"
        mock_get_num_category_submissions.side_effect = lambda user_id, cat_id: 5 if user_id == 111 else 3
        
        # Execute
        result = await get_category_leaderboard_embed(title, body_text, points_list, current_page, per_page, mock_bot_client)
        
        # Verify
        assert result.title == title
        assert result.description == body_text
        assert len(result.fields) == 2
        
        # Check first field
        field1 = result.fields[0]
        assert field1.name == "1st - 150.5"
        assert field1.value == "Player111 (5)"
        assert field1.inline is False
        
        # Check second field
        field2 = result.fields[1]
        assert field2.name == "2nd - 120.0"
        assert field2.value == "Player222 (3)"
        assert field2.inline is False

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_num_category_submissions')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_place_str')
    @patch('ui.ui_util.format_points_str')
    async def test_get_category_leaderboard_embed_pagination(self, mock_format_points_str, mock_get_place_str, mock_get_user_name_str, mock_get_num_category_submissions):
        """Test category leaderboard embed with pagination."""
        # Setup
        title = "Paginated Leaderboard"
        body_text = "Page 2 results"
        current_page = 1  # Second page
        per_page = 3
        
        # Mock points objects
        point1 = Mock()
        point1.user_id = 333
        point1.category_id = 1
        point1.points = 100.0
        
        points_list = [point1]
        
        mock_bot_client = Mock()
        mock_user1 = Mock()
        mock_user1.id = 333
        
        mock_bot_client.fetch_user = AsyncMock(return_value=mock_user1)
        mock_get_user_name_str.return_value = "Player333"
        mock_get_place_str.return_value = "4th"  # Page 1, position 1 = 4th overall
        mock_format_points_str.return_value = "100.0"
        mock_get_num_category_submissions.return_value = 7
        
        # Execute
        result = await get_category_leaderboard_embed(title, body_text, points_list, current_page, per_page, mock_bot_client)
        
        # Verify
        assert result.title == title
        assert result.description == body_text
        assert len(result.fields) == 1
        
        field1 = result.fields[0]
        assert field1.name == "4th - 100.0"
        assert field1.value == "Player333 (7)"
        assert field1.inline is False

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_num_category_submissions')
    @patch('ui.ui_util.get_user_name_str')
    @patch('ui.ui_util.get_place_str')
    @patch('ui.ui_util.format_points_str')
    async def test_get_category_leaderboard_embed_empty_list(self, mock_format_points_str, mock_get_place_str, mock_get_user_name_str, mock_get_num_category_submissions):
        """Test category leaderboard embed with empty points list."""
        # Setup
        title = "Empty Leaderboard"
        body_text = "No results"
        current_page = 0
        per_page = 5
        points_list = []
        
        mock_bot_client = Mock()
        
        # Execute
        result = await get_category_leaderboard_embed(title, body_text, points_list, current_page, per_page, mock_bot_client)
        
        # Verify
        assert result.title == title
        assert result.description == body_text
        assert len(result.fields) == 0  # No fields for empty list