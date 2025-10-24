# -*- coding: utf-8 -*-
"""
Unit tests for show_race_leaderboard() function in ui/menus.py.
Tests the race leaderboard display functionality including pagination and title generation.
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

from ui.menus import show_race_leaderboard
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState


@pytest.mark.unit
class TestShowRaceLeaderboard:
    """Tests for show_race_leaderboard() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_paginated_menu_creation(self):
        """Test that paginated menu is created with correct parameters."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Completed)
        submissions = [
            create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45"),
            create_mock_submission(submission_id=2, race_id=1, user_id=101, finish_time="1:24:30"),
            create_mock_submission(submission_id=3, race_id=1, user_id=102, finish_time="1:25:15")
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.zRaceLeaderboardMenuPages') as mock_menu_class, \
             patch('ui.menus.zRaceLeaderboardPageSource') as mock_source_class:
            
            # Mock the menu instance
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            # Mock the source instance
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            # Mock title and description functions
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            await show_race_leaderboard(interaction, race_id=1)
            
            # Verify submissions were fetched
            mock_get_submissions.assert_called_once_with(1)
            
            # Verify race was fetched
            mock_get_race.assert_called_once_with(1)
            
            # Verify title and description were generated
            mock_get_title.assert_called_once_with(1)
            mock_get_description.assert_called_once_with(1)
            
            # Verify page source was created with correct parameters
            mock_source_class.assert_called_once_with(
                submissions,
                interaction.guild_id,
                interaction.client,
                title="Test Race Leaderboard",
                body_text="Test race description"
            )
            
            # Verify menu was created with correct source
            mock_menu_class.assert_called_once_with(source=mock_source)
            
            # Verify menu was started
            mock_menu.start.assert_called_once_with(interaction=interaction, ephemeral=True)

    @pytest.mark.asyncio
    async def test_with_various_submission_counts(self):
        """Test leaderboard creation with different numbers of submissions."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Completed)
        
        # Test with no submissions
        with patch('ui.menus.get_sorted_race_submissions', return_value=[]) as mock_get_submissions, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.zRaceLeaderboardMenuPages') as mock_menu_class, \
             patch('ui.menus.zRaceLeaderboardPageSource') as mock_source_class:
            
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            await show_race_leaderboard(interaction, race_id=1)
            
            # Verify source was created with empty submissions list
            mock_source_class.assert_called_once_with(
                [],
                interaction.guild_id,
                interaction.client,
                title="Test Race Leaderboard",
                body_text="Test race description"
            )
        
        # Test with many submissions
        many_submissions = [
            create_mock_submission(submission_id=i, race_id=1, user_id=100+i, finish_time=f"1:{20+i:02d}:30")
            for i in range(1, 26)  # 25 submissions
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=many_submissions) as mock_get_submissions, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.zRaceLeaderboardMenuPages') as mock_menu_class, \
             patch('ui.menus.zRaceLeaderboardPageSource') as mock_source_class:
            
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            await show_race_leaderboard(interaction, race_id=1)
            
            # Verify source was created with many submissions
            mock_source_class.assert_called_once_with(
                many_submissions,
                interaction.guild_id,
                interaction.client,
                title="Test Race Leaderboard",
                body_text="Test race description"
            )

    @pytest.mark.asyncio
    async def test_title_and_description_generation(self):
        """Test that title and description are properly generated and passed to the menu."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Completed)
        submissions = [create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45")]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.zRaceLeaderboardMenuPages') as mock_menu_class, \
             patch('ui.menus.zRaceLeaderboardPageSource') as mock_source_class:
            
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            # Test with specific title and description
            expected_title = "Race #1 Leaderboard - Test Race"
            expected_description = "Race completed on 2024-01-01"
            mock_get_title.return_value = expected_title
            mock_get_description.return_value = expected_description
            
            await show_race_leaderboard(interaction, race_id=1)
            
            # Verify title and description functions were called with correct race_id
            mock_get_title.assert_called_once_with(1)
            mock_get_description.assert_called_once_with(1)
            
            # Verify the generated title and description were passed to the source
            mock_source_class.assert_called_once_with(
                submissions,
                interaction.guild_id,
                interaction.client,
                title=expected_title,
                body_text=expected_description
            )

    @pytest.mark.asyncio
    async def test_menu_start_parameters(self):
        """Test that the menu is started with correct parameters."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Completed)
        submissions = [create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45")]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.zRaceLeaderboardMenuPages') as mock_menu_class, \
             patch('ui.menus.zRaceLeaderboardPageSource') as mock_source_class:
            
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            mock_get_title.return_value = "Test Title"
            mock_get_description.return_value = "Test Description"
            
            await show_race_leaderboard(interaction, race_id=1)
            
            # Verify menu.start was called with correct parameters
            mock_menu.start.assert_called_once_with(interaction=interaction, ephemeral=True)

    @pytest.mark.asyncio
    async def test_different_race_states(self):
        """Test leaderboard creation for races in different states."""
        interaction = create_mock_interaction()
        submissions = [create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45")]
        
        # Test with Active race
        active_race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race', return_value=active_race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.zRaceLeaderboardMenuPages') as mock_menu_class, \
             patch('ui.menus.zRaceLeaderboardPageSource') as mock_source_class:
            
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            mock_get_title.return_value = "Active Race Leaderboard"
            mock_get_description.return_value = "Active race description"
            
            await show_race_leaderboard(interaction, race_id=1)
            
            # Verify the race was fetched and used
            mock_get_race.assert_called_once_with(1)
            mock_source_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_guild_id_and_client_passing(self):
        """Test that guild_id and client are properly passed to the page source."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Completed)
        submissions = [create_mock_submission(submission_id=1, race_id=1, user_id=100, finish_time="1:23:45")]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.zRaceLeaderboardMenuPages') as mock_menu_class, \
             patch('ui.menus.zRaceLeaderboardPageSource') as mock_source_class:
            
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            mock_get_title.return_value = "Test Title"
            mock_get_description.return_value = "Test Description"
            
            await show_race_leaderboard(interaction, race_id=1)
            
            # Verify guild_id and client were passed correctly
            call_args = mock_source_class.call_args
            assert call_args[0][1] == interaction.guild_id  # guild_id
            assert call_args[0][2] == interaction.client    # client
