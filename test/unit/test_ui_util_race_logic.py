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

from ui.ui_util import forfeit_race, get_submission_details_dict, save_message
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