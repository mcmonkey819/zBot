# -*- coding: utf-8 -*-
"""
Unit tests for UI utility race management and submission functions.
Tests race and submission logic from ui/ui_util.py with mocked database operations.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock, call
from datetime import datetime
from ui.ui_util import forfeit_race
from test.test_utils.db_fixtures import create_mock_race, ForfeitFinishTime


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

