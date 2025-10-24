# -*- coding: utf-8 -*-
"""
Unit tests for show_race_details() function in ui/menus.py.
Tests the race details display functionality including seed confirmation and view creation.
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

from ui.menus import show_race_details, zConfirmMenu, zRaceInfoButtonView
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild
from test.test_utils.db_fixtures import create_mock_race, create_mock_category
from db.db_util import RaceState


@pytest.mark.unit
class TestShowRaceDetails:
    """Tests for show_race_details() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_race_not_found_error(self):
        """Test error handling when race data cannot be found."""
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_race', return_value=None) as mock_get_race, \
             patch('ui.menus.send_message') as mock_send_message:
            
            await show_race_details(interaction, race_id=999)
            
            mock_get_race.assert_called_once_with(999)
            mock_send_message.assert_called_once_with(
                interaction, 
                "**ERROR** Could not find race data. Please notify a bot admin"
            )

    @pytest.mark.asyncio
    async def test_non_assigned_race_direct_display(self):
        """Test that non-assigned races display directly without confirmation."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the race info message and embed
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # get_race is called twice: once in show_race_details and once in zRaceInfoButtonView constructor
            assert mock_get_race.call_count == 2
            assert mock_get_race.call_args_list[0] == ((1,),)
            assert mock_get_race.call_args_list[1] == ((1,),)
            mock_is_assigned.assert_called_once_with(1)
            mock_get_race_info.assert_called_once_with(race)
            mock_send_message.assert_called_once()
            
            # Verify the call to send_message includes the view and embed
            call_args = mock_send_message.call_args
            assert call_args[0][0] == interaction  # interaction
            assert 'view' in call_args[1]  # view parameter
            assert 'embed' in call_args[1]  # embed parameter
            assert isinstance(call_args[1]['view'], zRaceInfoButtonView)

    @pytest.mark.asyncio
    async def test_assigned_race_no_assignment_direct_display(self):
        """Test assigned race where user has no assignment displays directly."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=True) as mock_is_assigned, \
             patch('ui.menus.get_race_assignment', return_value=None) as mock_get_assignment, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.send_message') as mock_send_message:
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # get_race is called twice: once in show_race_details and once in zRaceInfoButtonView constructor
            assert mock_get_race.call_count == 2
            assert mock_get_race.call_args_list[0] == ((1,),)
            assert mock_get_race.call_args_list[1] == ((1,),)
            mock_is_assigned.assert_called_once_with(1)
            mock_get_assignment.assert_called_once_with(interaction.user.id, 1)
            mock_get_race_info.assert_called_once_with(race)
            mock_send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_assigned_race_with_seed_time_direct_display(self):
        """Test assigned race where user already has seed_time displays directly."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock assignment with existing seed_time
        mock_assignment = MagicMock()
        mock_assignment.seed_time = datetime.now().isoformat()
        mock_assignment.save = MagicMock()
        
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=True) as mock_is_assigned, \
             patch('ui.menus.get_race_assignment', return_value=mock_assignment) as mock_get_assignment, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.send_message') as mock_send_message:
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # get_race is called twice: once in show_race_details and once in zRaceInfoButtonView constructor
            assert mock_get_race.call_count == 2
            assert mock_get_race.call_args_list[0] == ((1,),)
            assert mock_get_race.call_args_list[1] == ((1,),)
            mock_is_assigned.assert_called_once_with(1)
            mock_get_assignment.assert_called_once_with(interaction.user.id, 1)
            mock_get_race_info.assert_called_once_with(race)
            mock_send_message.assert_called_once()
            
            # Verify seed_time was not modified
            mock_assignment.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_assigned_race_seed_confirmation_accepted(self):
        """Test assigned race seed confirmation when user accepts."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock assignment without seed_time
        mock_assignment = MagicMock()
        mock_assignment.seed_time = None
        mock_assignment.save = MagicMock()
        
        # Mock the confirmation menu to return True (accepted)
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=True) as mock_is_assigned, \
             patch('ui.menus.get_race_assignment', return_value=mock_assignment) as mock_get_assignment, \
             patch('ui.menus.zConfirmMenu') as mock_confirm_menu_class, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the confirmation menu instance
            mock_confirm_menu = MagicMock()
            mock_confirm_menu.prompt = AsyncMock(return_value=True)
            mock_confirm_menu_class.return_value = mock_confirm_menu
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # Verify confirmation menu was created and prompted
            mock_confirm_menu_class.assert_called_once()
            mock_confirm_menu.prompt.assert_called_once_with(interaction)
            
            # Verify seed_time was set and saved
            assert mock_assignment.seed_time is not None
            mock_assignment.save.assert_called_once()
            
            # Verify race info was displayed
            mock_get_race_info.assert_called_once_with(race)
            mock_send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_assigned_race_seed_confirmation_cancelled(self):
        """Test assigned race seed confirmation when user cancels."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock assignment without seed_time
        mock_assignment = MagicMock()
        mock_assignment.seed_time = None
        mock_assignment.save = MagicMock()
        
        # Mock the confirmation menu to return False (cancelled)
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=True) as mock_is_assigned, \
             patch('ui.menus.get_race_assignment', return_value=mock_assignment) as mock_get_assignment, \
             patch('ui.menus.zConfirmMenu') as mock_confirm_menu_class, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the confirmation menu instance
            mock_confirm_menu = MagicMock()
            mock_confirm_menu.prompt = AsyncMock(return_value=False)
            mock_confirm_menu_class.return_value = mock_confirm_menu
            
            await show_race_details(interaction, race_id=1)
            
            # Verify confirmation menu was created and prompted
            mock_confirm_menu_class.assert_called_once()
            mock_confirm_menu.prompt.assert_called_once_with(interaction)
            
            # Verify seed_time was not set
            assert mock_assignment.seed_time is None
            mock_assignment.save.assert_not_called()
            
            # Verify cancellation message was sent
            mock_send_message.assert_called_once_with(interaction, "Cancelled")

    @pytest.mark.asyncio
    async def test_race_info_button_view_creation(self):
        """Test that zRaceInfoButtonView is created with correct race_id."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.send_message') as mock_send_message:
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # Verify the view was created with correct race_id
            call_args = mock_send_message.call_args
            view = call_args[1]['view']
            assert isinstance(view, zRaceInfoButtonView)
            assert view.race_id == 1

    @pytest.mark.asyncio
    async def test_embed_field_addition(self):
        """Test that embed fields are added to the race info embed."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active, is_team_race=True)
        
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.zRaceInfoButtonView.add_static_embed_fields') as mock_add_fields, \
             patch('ui.menus.send_message') as mock_send_message:
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # Verify add_static_embed_fields was called with correct parameters
            mock_add_fields.assert_called_once_with(mock_embed, True)  # is_team_race=True

    @pytest.mark.asyncio
    async def test_team_race_vs_individual_race(self):
        """Test that team race status is correctly passed to embed field addition."""
        interaction = create_mock_interaction()
        
        # Test individual race
        individual_race = create_mock_race(race_id=1, state=RaceState.Active, is_team_race=False)
        
        with patch('ui.menus.get_race', return_value=individual_race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.zRaceInfoButtonView.add_static_embed_fields') as mock_add_fields, \
             patch('ui.menus.send_message') as mock_send_message:
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            mock_add_fields.assert_called_once_with(mock_embed, False)  # is_team_race=False

    @pytest.mark.asyncio
    async def test_seed_time_datetime_handling(self):
        """Test that seed_time is properly set as datetime object."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock assignment without seed_time
        mock_assignment = MagicMock()
        mock_assignment.seed_time = None
        mock_assignment.save = MagicMock()
        
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=True) as mock_is_assigned, \
             patch('ui.menus.get_race_assignment', return_value=mock_assignment) as mock_get_assignment, \
             patch('ui.menus.zConfirmMenu') as mock_confirm_menu_class, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the confirmation menu instance
            mock_confirm_menu = MagicMock()
            mock_confirm_menu.prompt = AsyncMock(return_value=True)
            mock_confirm_menu_class.return_value = mock_confirm_menu
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # Verify seed_time was set to a datetime object
            assert isinstance(mock_assignment.seed_time, datetime)
            mock_assignment.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_interaction_flow_mocking(self):
        """Test the complete interaction flow with all mocks in place."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active, is_team_race=False)
        
        # Mock assignment without seed_time
        mock_assignment = MagicMock()
        mock_assignment.seed_time = None
        mock_assignment.save = MagicMock()
        
        with patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.is_assigned_race', return_value=True) as mock_is_assigned, \
             patch('ui.menus.get_race_assignment', return_value=mock_assignment) as mock_get_assignment, \
             patch('ui.menus.zConfirmMenu') as mock_confirm_menu_class, \
             patch('ui.menus.get_race_info_message') as mock_get_race_info, \
             patch('ui.menus.zRaceInfoButtonView.add_static_embed_fields') as mock_add_fields, \
             patch('ui.menus.send_message') as mock_send_message:
            
            # Mock the confirmation menu instance
            mock_confirm_menu = MagicMock()
            mock_confirm_menu.prompt = AsyncMock(return_value=True)
            mock_confirm_menu_class.return_value = mock_confirm_menu
            
            mock_embed = MagicMock()
            mock_get_race_info.return_value = mock_embed
            
            await show_race_details(interaction, race_id=1)
            
            # Verify all expected calls were made
            # get_race is called twice: once in show_race_details and once in zRaceInfoButtonView constructor
            assert mock_get_race.call_count == 2
            assert mock_get_race.call_args_list[0] == ((1,),)
            assert mock_get_race.call_args_list[1] == ((1,),)
            mock_is_assigned.assert_called_once_with(1)
            mock_get_assignment.assert_called_once_with(interaction.user.id, 1)
            mock_confirm_menu_class.assert_called_once()
            mock_confirm_menu.prompt.assert_called_once_with(interaction)
            mock_get_race_info.assert_called_once_with(race)
            mock_add_fields.assert_called_once_with(mock_embed, False)
            mock_send_message.assert_called_once()
            
            # Verify seed_time was set and saved
            assert isinstance(mock_assignment.seed_time, datetime)
            mock_assignment.save.assert_called_once()
