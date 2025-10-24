# -*- coding: utf-8 -*-
"""
Unit tests for race_edit_submission() function in ui/menus.py.
Tests the race submission editing functionality including validation and user interactions.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import nextcord

# Mock the menus module since it's not available in the current nextcord version
import sys
from unittest.mock import MagicMock

# Create a mock menus module
mock_menus = MagicMock()
mock_menus.ButtonMenu = MagicMock
sys.modules['nextcord.ext.menus'] = mock_menus

from ui.menus import race_edit_submission, on_select_edit_submission, on_select_user_edit_submission
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState


@pytest.mark.unit
class TestRaceEditSubmission:
    """Tests for race_edit_submission() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_inactive_race_rejection(self):
        """Test that inactive races are rejected with appropriate message."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Inactive)
        
        with patch('ui.menus.defer') as mock_defer, \
             patch('ui.menus.send_message') as mock_send_message:
            
            await race_edit_submission(interaction, race)
            
            mock_defer.assert_called_once_with(interaction)
            mock_send_message.assert_called_once_with(
                interaction, 
                "Cannot create submissions for an Inactive race."
            )

    @pytest.mark.asyncio
    async def test_submission_list_generation_with_submissions(self):
        """Test submission list generation when submissions exist."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        submissions = [
            create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45"),
            create_mock_submission(submission_id=2, race_id=1, user_id=101, finish_time="1:24:30"),
            create_mock_submission(submission_id=3, race_id=1, user_id=102, finish_time="1:25:15")
        ]
        
        with patch('ui.menus.defer') as mock_defer, \
             patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_user_from_interaction') as mock_get_user, \
             patch('ui.menus.get_user_name_str') as mock_get_user_name, \
             patch('ui.menus.zSingleSelectView') as mock_view_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock user fetching
            mock_user1 = create_mock_user(user_id=100, username="User1")
            mock_user2 = create_mock_user(user_id=101, username="User2")
            mock_user3 = create_mock_user(user_id=102, username="User3")
            
            mock_get_user.side_effect = [mock_user1, mock_user2, mock_user3]
            mock_get_user_name.side_effect = ["User1", "User2", "User3"]
            
            # Mock the view
            mock_view = MagicMock()
            mock_view_class.return_value = mock_view
            
            await race_edit_submission(interaction, race)
            
            mock_defer.assert_called_once_with(interaction)
            mock_get_submissions.assert_called_once_with(race.id)
            
            # Verify user fetching was called for each submission
            assert mock_get_user.call_count == 3
            assert mock_get_user_name.call_count == 3
            
            # Verify view was created with correct parameters
            mock_view_class.assert_called_once()
            call_args = mock_view_class.call_args
            
            # Check that the select list contains the expected options
            select_list = call_args[0][0]  # First argument is the select_list
            assert len(select_list) == 5  # 3 submissions + "Create New..." + "Cancel..."
            
            # Check "Create New..." option
            create_new_option = select_list[0]
            assert create_new_option.label == "Create New..."
            assert create_new_option.value == -1
            assert create_new_option.description == "Create a new submission"
            
            # Check "Cancel..." option
            cancel_option = select_list[1]
            assert cancel_option.label == "Cancel..."
            assert cancel_option.value == 0
            assert cancel_option.description == "Cancel the operation"
            
            # Check submission options
            for i, submission in enumerate(submissions):
                option = select_list[i + 2]  # +2 because of Create New and Cancel options
                assert option.value == submission.id
                assert f"User{i+1} - {submission.finish_time}" in option.label
                assert f"User{i+1} - {submission.finish_time}" in option.description
            
            # Verify view was sent
            mock_send_message.assert_called_once_with(interaction, view=mock_view)

    @pytest.mark.asyncio
    async def test_submission_list_generation_no_submissions(self):
        """Test submission list generation when no submissions exist."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.defer') as mock_defer, \
             patch('ui.menus.get_sorted_race_submissions', return_value=None) as mock_get_submissions, \
             patch('ui.menus.zSingleSelectView') as mock_view_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the view
            mock_view = MagicMock()
            mock_view_class.return_value = mock_view
            
            await race_edit_submission(interaction, race)
            
            mock_defer.assert_called_once_with(interaction)
            mock_get_submissions.assert_called_once_with(race.id)
            
            # Verify view was created with only default options
            mock_view_class.assert_called_once()
            call_args = mock_view_class.call_args
            select_list = call_args[0][0]
            
            # Should only have "Create New..." and "Cancel..." options
            assert len(select_list) == 2
            assert select_list[0].label == "Create New..."
            assert select_list[1].label == "Cancel..."
            
            mock_send_message.assert_called_once_with(interaction, view=mock_view)

    @pytest.mark.asyncio
    async def test_submission_list_generation_empty_submissions(self):
        """Test submission list generation when submissions list is empty."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.defer') as mock_defer, \
             patch('ui.menus.get_sorted_race_submissions', return_value=[]) as mock_get_submissions, \
             patch('ui.menus.zSingleSelectView') as mock_view_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the view
            mock_view = MagicMock()
            mock_view_class.return_value = mock_view
            
            await race_edit_submission(interaction, race)
            
            mock_defer.assert_called_once_with(interaction)
            mock_get_submissions.assert_called_once_with(race.id)
            
            # Verify view was created with only default options
            mock_view_class.assert_called_once()
            call_args = mock_view_class.call_args
            select_list = call_args[0][0]
            
            # Should only have "Create New..." and "Cancel..." options
            assert len(select_list) == 2
            assert select_list[0].label == "Create New..."
            assert select_list[1].label == "Cancel..."
            
            mock_send_message.assert_called_once_with(interaction, view=mock_view)

    @pytest.mark.asyncio
    async def test_user_fetch_error_handling(self):
        """Test handling of errors when fetching user information."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        submissions = [
            create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45"),
            create_mock_submission(submission_id=2, race_id=1, user_id=101, finish_time="1:24:30")
        ]
        
        with patch('ui.menus.defer') as mock_defer, \
             patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_user_from_interaction') as mock_get_user, \
             patch('ui.menus.zSingleSelectView') as mock_view_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock user fetching to raise exception for first user, succeed for second
            mock_get_user.side_effect = [Exception("User not found"), create_mock_user(user_id=101, username="User2")]
            
            # Mock the view
            mock_view = MagicMock()
            mock_view_class.return_value = mock_view
            
            await race_edit_submission(interaction, race)
            
            mock_defer.assert_called_once_with(interaction)
            mock_get_submissions.assert_called_once_with(race.id)
            
            # Verify view was created
            mock_view_class.assert_called_once()
            call_args = mock_view_class.call_args
            select_list = call_args[0][0]
            
            # Should have 4 options: Create New, Cancel, Unknown (from error), User2
            assert len(select_list) == 4
            
            # Check that first submission shows as "Unknown"
            unknown_option = select_list[2]
            assert "Unknown" in unknown_option.label
            assert unknown_option.value == 1
            
            # Check that second submission shows user name (it uses the user's display name from the mock)
            user2_option = select_list[3]
            assert "User101" in user2_option.label  # The mock user has username "User101"
            assert user2_option.value == 2
            
            mock_send_message.assert_called_once_with(interaction, view=mock_view)

    @pytest.mark.asyncio
    async def test_on_select_edit_submission_cancel(self):
        """Test on_select_edit_submission when user cancels (value 0)."""
        interaction = create_mock_interaction()
        
        with patch('ui.menus.send_message') as mock_send_message:
            await on_select_edit_submission([0, 1], interaction)
            
            mock_send_message.assert_called_once_with(interaction, "Cancelled")

    @pytest.mark.asyncio
    async def test_on_select_edit_submission_create_new(self):
        """Test on_select_edit_submission when user selects create new (value -1)."""
        interaction = create_mock_interaction()
        
        with patch('ui.menus.zUserSelectView') as mock_user_select_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the user select view
            mock_user_select = MagicMock()
            mock_user_select_class.return_value = mock_user_select
            
            await on_select_edit_submission([-1, 1], interaction)
            
            # Verify user select view was created and sent
            mock_user_select_class.assert_called_once_with(
                on_select_user_edit_submission, 
                placeholder="Choose racer to submit for...", 
                payload=1
            )
            mock_send_message.assert_called_once_with(interaction, view=mock_user_select)

    @pytest.mark.asyncio
    async def test_on_select_edit_submission_edit_existing(self):
        """Test on_select_edit_submission when user selects existing submission."""
        interaction = create_mock_interaction()
        submission = create_mock_submission(submission_id=123, race_id=1, user_id=100, finish_time="1:23:45")
        
        with patch('ui.menus.get_race_submission_by_id', return_value=submission) as mock_get_submission, \
             patch('ui.menus.zRaceSubmitHandler') as mock_handler_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the submit handler
            mock_handler = MagicMock()
            mock_handler.send_submit_modal = AsyncMock()
            mock_handler_class.return_value = mock_handler
            
            await on_select_edit_submission([123, 1], interaction)
            
            # Verify submission was fetched
            mock_get_submission.assert_called_once_with(123)
            
            # Verify submit handler was created with correct parameters
            mock_handler_class.assert_called_once_with(submission.race_id, submission, include_points=True)
            
            # Verify modal was sent
            mock_handler.send_submit_modal.assert_called_once_with(interaction)

    @pytest.mark.asyncio
    async def test_on_select_edit_submission_submission_not_found(self):
        """Test on_select_edit_submission when submission is not found."""
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race_submission_by_id', return_value=None) as mock_get_submission, \
             patch('ui.menus.zRaceSubmitHandler') as mock_handler_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            await on_select_edit_submission([999, 1], interaction)
            
            # Verify submission was fetched
            mock_get_submission.assert_called_once_with(999)
            
            # Should not create submit handler or send modal
            mock_handler_class.assert_not_called()
            mock_send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_select_user_edit_submission_cancel(self):
        """Test on_select_user_edit_submission when user cancels (None user)."""
        interaction = create_mock_interaction()
        
        with patch('ui.menus.send_message') as mock_send_message:
            await on_select_user_edit_submission([None, 1], interaction)
            
            mock_send_message.assert_called_once_with(interaction, "Cancelled")

    @pytest.mark.asyncio
    async def test_on_select_user_edit_submission_user_selected(self):
        """Test on_select_user_edit_submission when user selects a user."""
        interaction = create_mock_interaction()
        user = create_mock_user(user_id=100, username="TestUser")
        
        with patch('ui.menus.zRaceSubmitHandler') as mock_handler_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the submit handler
            mock_handler = MagicMock()
            mock_handler.send_submit_modal = AsyncMock()
            mock_handler_class.return_value = mock_handler
            
            await on_select_user_edit_submission([user, 1], interaction)
            
            # Verify submit handler was created with correct parameters
            mock_handler_class.assert_called_once_with(1, None, include_points=True, user_id=user.id)
            
            # Verify modal was sent
            mock_handler.send_submit_modal.assert_called_once_with(interaction)

    @pytest.mark.asyncio
    async def test_view_creation_parameters(self):
        """Test that zSingleSelectView is created with correct parameters."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        submissions = [create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45")]
        
        with patch('ui.menus.defer') as mock_defer, \
             patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_user_from_interaction') as mock_get_user, \
             patch('ui.menus.get_user_name_str') as mock_get_user_name, \
             patch('ui.menus.zSingleSelectView') as mock_view_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            mock_get_user.return_value = create_mock_user(user_id=100, username="User1")
            mock_get_user_name.return_value = "User1"
            
            mock_view = MagicMock()
            mock_view_class.return_value = mock_view
            
            await race_edit_submission(interaction, race)
            
            # Verify view was created with correct parameters
            mock_view_class.assert_called_once()
            call_args = mock_view_class.call_args
            
            # Check parameters
            select_list = call_args[0][0]
            handler_func = call_args[0][1]
            placeholder = call_args[0][2]
            payload = call_args[1]['payload']
            
            assert len(select_list) == 3  # 1 submission + Create New + Cancel
            assert handler_func == on_select_edit_submission
            assert placeholder == "Choose Submission To Edit.."
            assert payload == race.id
