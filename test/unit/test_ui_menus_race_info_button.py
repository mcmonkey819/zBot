# -*- coding: utf-8 -*-
"""
Tests for zRaceInfoButtonView class from ui/menus.py

Tests the Discord UI view that provides race information and action buttons.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import nextcord
from nextcord.partial_emoji import PartialEmoji

# Import the class under test
from ui.menus import zRaceInfoButtonView
from db.zBot_db_orm import RaceState
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission


class TestZRaceInfoButtonView:
    """Test suite for zRaceInfoButtonView class."""

    def test_initialization_regular_race(self):
        """Test initialization with a regular (non-team) race."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id, is_team_race=False)
        
        with patch('ui.menus.get_race', return_value=mock_race):
            # Execute
            view = zRaceInfoButtonView(race_id)
            
            # Verify
            assert view.race_id == race_id
            assert view.is_team_race is False
            assert not hasattr(view, 'team_leaderboard_button')
            # Should have 3 buttons: submit_time, forfeit, leaderboard
            assert len(view.children) == 3

    def test_initialization_team_race(self):
        """Test initialization with a team race."""
        # Setup
        race_id = 456
        mock_race = create_mock_race(race_id=race_id, is_team_race=True)
        
        with patch('ui.menus.get_race', return_value=mock_race):
            # Execute
            view = zRaceInfoButtonView(race_id)
            
            # Verify
            assert view.race_id == race_id
            assert view.is_team_race is True
            assert hasattr(view, 'team_leaderboard_button')
            # Should have 4 buttons: submit_time, forfeit, leaderboard, team_leaderboard
            assert len(view.children) == 4

    def test_initialization_race_not_found(self):
        """Test initialization when race is not found."""
        # Setup
        race_id = 999
        
        with patch('ui.menus.get_race', return_value=None):
            # Execute
            view = zRaceInfoButtonView(race_id)
            
            # Verify
            assert view.race_id == race_id
            assert view.is_team_race is False
            assert not hasattr(view, 'team_leaderboard_button')
            # Should still have 3 buttons even if race not found
            assert len(view.children) == 3

    @pytest.mark.asyncio
    async def test_check_can_submit_inactive_race(self):
        """Test check_can_submit with inactive race."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id, state=RaceState.Inactive)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            result = await view.check_can_submit(interaction)
            
            # Verify
            assert result is False
            mock_send.assert_called_once_with(interaction, "Cannot create a submission, this race is Inactive")

    @pytest.mark.asyncio
    async def test_check_can_submit_completed_race_no_allow(self):
        """Test check_can_submit with completed race that doesn't allow submissions."""
        # Setup
        race_id = 123
        mock_category = create_mock_category(allow_completed_submit=False)
        mock_race = create_mock_race(race_id=race_id, state=RaceState.Completed, category_id=mock_category)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            result = await view.check_can_submit(interaction)
            
            # Verify
            assert result is False
            mock_send.assert_called_once_with(interaction, "The category for this race does not permit submitting to a completed race.")

    @pytest.mark.asyncio
    async def test_check_can_submit_completed_race_allow(self):
        """Test check_can_submit with completed race that allows submissions."""
        # Setup
        race_id = 123
        mock_category = create_mock_category(allow_completed_submit=True)
        mock_race = create_mock_race(race_id=race_id, state=RaceState.Completed, category_id=mock_category)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.get_race_submission', return_value=None), \
             patch('ui.menus.is_assigned_race', return_value=False):
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            result = await view.check_can_submit(interaction)
            
            # Verify
            assert result is True

    @pytest.mark.asyncio
    async def test_check_can_submit_edit_window_expired(self):
        """Test check_can_submit when edit window has expired."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id, state=RaceState.Open)
        interaction = create_mock_interaction()
        
        # Create submission with old timestamp (outside edit window)
        old_time = datetime.now() - timedelta(hours=5)  # Past 4-hour limit
        mock_submission = create_mock_submission(
            user_id=interaction.user.id,
            race_id=race_id,
            submit_datetime=old_time
        )
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.get_race_submission', return_value=mock_submission), \
             patch('ui.menus.is_assigned_race', return_value=False), \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            result = await view.check_can_submit(interaction)
            
            # Verify
            assert result is False
            mock_send.assert_called_once_with(interaction, "It is past the window to edit your submission. Please contact a moderator if you need to make changes.")

    @pytest.mark.asyncio
    async def test_check_can_submit_assigned_race_not_assigned(self):
        """Test check_can_submit for assigned race when user is not assigned."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id, state=RaceState.Open)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.get_race_submission', return_value=None), \
             patch('ui.menus.is_assigned_race', return_value=True), \
             patch('ui.menus.get_race_assignment', return_value=None), \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            result = await view.check_can_submit(interaction)
            
            # Verify
            assert result is False
            mock_send.assert_called_once_with(interaction, "Can't submit: This is an assigned race and you are not assigned to it")

    @pytest.mark.asyncio
    async def test_check_can_submit_assigned_race_seed_time_expired(self):
        """Test check_can_submit for assigned race when seed time window has expired."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id, state=RaceState.Open)
        interaction = create_mock_interaction()
        
        # Create assignment with old seed time
        old_seed_time = datetime.now() - timedelta(hours=5)  # Past 4-hour limit
        mock_assignment = Mock()
        mock_assignment.seed_time = old_seed_time
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.get_race_submission', return_value=None), \
             patch('ui.menus.is_assigned_race', return_value=True), \
             patch('ui.menus.get_race_assignment', return_value=mock_assignment), \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            result = await view.check_can_submit(interaction)
            
            # Verify
            assert result is False
            mock_send.assert_called_once_with(interaction, "It is past the window to submit a time for this assigned race. Please contact a moderator if you need to make changes.")

    @pytest.mark.asyncio
    async def test_check_can_submit_success(self):
        """Test check_can_submit when all conditions are met."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id, state=RaceState.Open)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.get_race_submission', return_value=None), \
             patch('ui.menus.is_assigned_race', return_value=False):
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            result = await view.check_can_submit(interaction)
            
            # Verify
            assert result is True

    @pytest.mark.asyncio
    async def test_submit_time_button_success(self):
        """Test submit_time_button when check_can_submit passes."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        mock_submission = create_mock_submission(user_id=interaction.user.id, race_id=race_id)
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch.object(zRaceInfoButtonView, 'check_can_submit', new_callable=AsyncMock, return_value=True), \
             patch('ui.menus.get_race_submission', return_value=mock_submission), \
             patch('ui.menus.zRaceSubmitHandler') as mock_handler_class:
            
            view = zRaceInfoButtonView(race_id)
            mock_handler = Mock()
            mock_handler.send_submit_modal = AsyncMock()
            mock_handler_class.return_value = mock_handler
            
            # Execute
            await view.submit_time_button(Mock(), interaction)
            
            # Verify
            mock_handler_class.assert_called_once_with(race_id, mock_submission)
            mock_handler.send_submit_modal.assert_called_once_with(interaction)

    @pytest.mark.asyncio
    async def test_submit_time_button_cannot_submit(self):
        """Test submit_time_button when check_can_submit fails."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch.object(zRaceInfoButtonView, 'check_can_submit', new_callable=AsyncMock, return_value=False), \
             patch('ui.menus.zRaceSubmitHandler') as mock_handler_class:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            await view.submit_time_button(Mock(), interaction)
            
            # Verify
            mock_handler_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_forfeit_button_already_submitted(self):
        """Test forfeit_button when user already has a submission."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        mock_submission = create_mock_submission(user_id=interaction.user.id, race_id=race_id)
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch.object(zRaceInfoButtonView, 'check_can_submit', new_callable=AsyncMock, return_value=True), \
             patch('ui.menus.get_race_submission', return_value=mock_submission), \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            await view.forfeit_button(Mock(), interaction)
            
            # Verify
            mock_send.assert_called_once_with(interaction, "Time already submitted for this race, use `Submit/Edit` button to edit")

    @pytest.mark.asyncio
    async def test_forfeit_button_success(self):
        """Test forfeit_button when user can forfeit."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch.object(zRaceInfoButtonView, 'check_can_submit', new_callable=AsyncMock, return_value=True), \
             patch('ui.menus.get_race_submission', return_value=None), \
             patch('ui.menus.forfeit_race') as mock_forfeit, \
             patch('ui.menus.do_post_submit_actions', new_callable=AsyncMock) as mock_post_actions, \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            await view.forfeit_button(Mock(), interaction)
            
            # Verify
            mock_forfeit.assert_called_once_with(interaction.user.id, race_id)
            mock_post_actions.assert_called_once_with(interaction, mock_race, interaction.user.id)
            mock_send.assert_called_once_with(interaction, "Forfeit submitted")

    @pytest.mark.asyncio
    async def test_leaderboard_button_can_view(self):
        """Test leaderboard_button when user can view leaderboard."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.can_view_race_leaderboard', return_value=True), \
             patch('ui.menus.show_race_leaderboard', new_callable=AsyncMock) as mock_show_leaderboard:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            await view.leaderboard_button(Mock(), interaction)
            
            # Verify
            mock_show_leaderboard.assert_called_once_with(interaction, race_id)

    @pytest.mark.asyncio
    async def test_leaderboard_button_cannot_view(self):
        """Test leaderboard_button when user cannot view leaderboard."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.can_view_race_leaderboard', return_value=False), \
             patch('ui.menus.send_message', new_callable=AsyncMock) as mock_send:
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute
            await view.leaderboard_button(Mock(), interaction)
            
            # Verify
            mock_send.assert_called_once_with(interaction, "You must submit a time, forfeit or wait for the race to be completed to view the leaderboard")

    def test_add_static_embed_fields_regular_race(self):
        """Test add_static_embed_fields for regular race."""
        # Setup
        embed = Mock()
        
        # Execute
        zRaceInfoButtonView.add_static_embed_fields(embed, is_team_race=False)
        
        # Verify
        assert embed.add_field.call_count == 3  # submit, forfeit, leaderboard
        calls = embed.add_field.call_args_list
        
        # Check that all expected fields are added
        field_names = [call[1]['name'] for call in calls]
        assert any('Submit/Edit Time' in name for name in field_names)
        assert any('Forfeit' in name for name in field_names)
        assert any('View Leaderboard' in name for name in field_names)

    def test_add_static_embed_fields_team_race(self):
        """Test add_static_embed_fields for team race."""
        # Setup
        embed = Mock()
        
        # Execute
        zRaceInfoButtonView.add_static_embed_fields(embed, is_team_race=True)
        
        # Verify
        assert embed.add_field.call_count == 4  # submit, forfeit, leaderboard, team_leaderboard
        calls = embed.add_field.call_args_list
        
        # Check that all expected fields are added
        field_names = [call[1]['name'] for call in calls]
        assert any('Submit/Edit Time' in name for name in field_names)
        assert any('Forfeit' in name for name in field_names)
        assert any('View Leaderboard' in name for name in field_names)
        assert any('Show Team Leaderboard' in name for name in field_names)

    @pytest.mark.asyncio
    async def test_discord_api_error_handling_submit_button(self):
        """Test Discord API error handling in submit_time_button."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        
        # Mock Discord API error
        discord_error = nextcord.errors.HTTPException(Mock(), {"message": "Rate limited"})
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch.object(zRaceInfoButtonView, 'check_can_submit', new_callable=AsyncMock, return_value=True), \
             patch('ui.menus.get_race_submission', return_value=None), \
             patch('ui.menus.zRaceSubmitHandler') as mock_handler_class:
            
            view = zRaceInfoButtonView(race_id)
            mock_handler = Mock()
            mock_handler.send_submit_modal = AsyncMock(side_effect=discord_error)
            mock_handler_class.return_value = mock_handler
            
            # Execute - should not raise exception
            try:
                await view.submit_time_button(Mock(), interaction)
                # If we get here, the error was handled gracefully
                assert True
            except nextcord.errors.HTTPException:
                pytest.fail("Discord API error was not handled gracefully")

    @pytest.mark.asyncio
    async def test_discord_api_error_handling_forfeit_button(self):
        """Test Discord API error handling in forfeit_button."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        
        # Mock Discord API error
        discord_error = nextcord.errors.ConnectionClosed(Mock(), Mock())
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch.object(zRaceInfoButtonView, 'check_can_submit', new_callable=AsyncMock, return_value=True), \
             patch('ui.menus.get_race_submission', return_value=None), \
             patch('ui.menus.forfeit_race'), \
             patch('ui.menus.do_post_submit_actions', new_callable=AsyncMock, side_effect=discord_error), \
             patch('ui.menus.send_message', new_callable=AsyncMock, side_effect=discord_error):
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute - should not raise exception
            try:
                await view.forfeit_button(Mock(), interaction)
                # If we get here, the error was handled gracefully
                assert True
            except nextcord.errors.ConnectionClosed:
                pytest.fail("Discord API error was not handled gracefully")

    @pytest.mark.asyncio
    async def test_discord_api_error_handling_leaderboard_button(self):
        """Test Discord API error handling in leaderboard_button."""
        # Setup
        race_id = 123
        mock_race = create_mock_race(race_id=race_id)
        interaction = create_mock_interaction()
        
        # Mock Discord API error
        discord_error = nextcord.errors.HTTPException(Mock(), {"message": "Unauthorized"})
        
        with patch('ui.menus.get_race', return_value=mock_race), \
             patch('ui.menus.can_view_race_leaderboard', return_value=True), \
             patch('ui.menus.show_race_leaderboard', new_callable=AsyncMock, side_effect=discord_error):
            
            view = zRaceInfoButtonView(race_id)
            
            # Execute - should not raise exception
            try:
                await view.leaderboard_button(Mock(), interaction)
                # If we get here, the error was handled gracefully
                assert True
            except nextcord.errors.HTTPException:
                pytest.fail("Discord API error was not handled gracefully")
