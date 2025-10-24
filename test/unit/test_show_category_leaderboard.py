# -*- coding: utf-8 -*-
"""
Unit tests for show_category_leaderboard() function in ui/menus.py.
Tests the category leaderboard display functionality including different leaderboard types.
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

from ui.menus import show_category_leaderboard
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState, RaceLeaderboardType


@pytest.mark.unit
class TestShowCategoryLeaderboard:
    """Tests for show_category_leaderboard() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_category_not_found_error(self):
        """Test error handling when category cannot be found."""
        interaction = create_mock_interaction()
        
        with patch('ui.menus.get_category', return_value=None) as mock_get_category, \
             patch('ui.menus.send_message') as mock_send_message:
            
            await show_category_leaderboard(interaction, category_id=999)
            
            mock_get_category.assert_called_once_with(999)
            mock_send_message.assert_called_once_with(
                interaction, 
                "**ERROR** Fetching category with ID 999. Please contact a bot admin."
            )

    @pytest.mark.asyncio
    async def test_recent_race_leaderboard_type(self):
        """Test RecentRace leaderboard type shows race leaderboard."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        race = create_mock_race(race_id=1, state=RaceState.Completed)
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_completed_races_by_category', return_value=[race]) as mock_get_races, \
             patch('ui.menus.show_race_leaderboard') as mock_show_race_leaderboard:
            
            await show_category_leaderboard(interaction, category_id=1)
            
            mock_get_category.assert_called_once_with(1)
            mock_get_races.assert_called_once_with(1)
            mock_show_race_leaderboard.assert_called_once_with(interaction, race.id)

    @pytest.mark.asyncio
    async def test_recent_race_no_completed_races(self):
        """Test RecentRace leaderboard type with no completed races."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_completed_races_by_category', return_value=[]) as mock_get_races, \
             patch('ui.menus.show_race_leaderboard') as mock_show_race_leaderboard:
            
            # The actual function will raise an IndexError when trying to access races[0]
            # This test verifies the current behavior (which may need to be fixed in the actual code)
            with pytest.raises(IndexError):
                await show_category_leaderboard(interaction, category_id=1)
            
            mock_get_category.assert_called_once_with(1)
            mock_get_races.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_points_leaderboard_type_with_points(self):
        """Test Points leaderboard type with existing points."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        points_list = [
            {"user_id": 100, "points": 150.5, "username": "User1"},
            {"user_id": 101, "points": 120.0, "username": "User2"},
            {"user_id": 102, "points": 90.5, "username": "User3"}
        ]
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_points', return_value=points_list) as mock_get_points, \
             patch('ui.menus.menus.ButtonMenuPages') as mock_menu_class, \
             patch('ui.menus.zCategoryPointsLeaderboardPageSource') as mock_source_class:
            
            # Mock the menu instance
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            # Mock the source instance
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            await show_category_leaderboard(interaction, category_id=1)
            
            mock_get_category.assert_called_once_with(1)
            mock_get_points.assert_called_once_with(1)
            
            # Verify page source was created with correct parameters
            mock_source_class.assert_called_once_with(points_list, interaction.client)
            
            # Verify menu was created with correct source
            mock_menu_class.assert_called_once_with(source=mock_source)
            
            # Verify menu was started
            mock_menu.start.assert_called_once_with(interaction=interaction, ephemeral=True)

    @pytest.mark.asyncio
    async def test_points_leaderboard_type_no_points(self):
        """Test Points leaderboard type with no points scenario."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_points', return_value=[]) as mock_get_points, \
             patch('ui.menus.get_category_no_points_message') as mock_get_no_points_msg, \
             patch('ui.menus.send_message') as mock_send_message:
            
            expected_message = "No points scored yet for Test Category. This is likely due to no completed races."
            mock_get_no_points_msg.return_value = expected_message
            
            await show_category_leaderboard(interaction, category_id=1)
            
            mock_get_category.assert_called_once_with(1)
            mock_get_points.assert_called_once_with(1)
            mock_get_no_points_msg.assert_called_once_with(category.name)
            mock_send_message.assert_called_once_with(interaction, expected_message)

    @pytest.mark.asyncio
    async def test_points_leaderboard_type_none_points(self):
        """Test Points leaderboard type when get_category_points returns None."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_points', return_value=None) as mock_get_points, \
             patch('ui.menus.get_category_no_points_message') as mock_get_no_points_msg, \
             patch('ui.menus.send_message') as mock_send_message:
            
            expected_message = "No points scored yet for Test Category. This is likely due to no completed races."
            mock_get_no_points_msg.return_value = expected_message
            
            await show_category_leaderboard(interaction, category_id=1)
            
            mock_get_category.assert_called_once_with(1)
            mock_get_points.assert_called_once_with(1)
            mock_get_no_points_msg.assert_called_once_with(category.name)
            mock_send_message.assert_called_once_with(interaction, expected_message)

    @pytest.mark.asyncio
    async def test_different_leaderboard_types(self):
        """Test handling of different leaderboard types."""
        interaction = create_mock_interaction()
        
        # Test RecentRace type
        recent_category = create_mock_category(
            category_id=1, 
            name="Recent Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        with patch('ui.menus.get_category', return_value=recent_category) as mock_get_category, \
             patch('ui.menus.get_completed_races_by_category', return_value=[]) as mock_get_races, \
             patch('ui.menus.show_race_leaderboard') as mock_show_race_leaderboard:
            
            # The actual function will raise an IndexError when trying to access races[0]
            with pytest.raises(IndexError):
                await show_category_leaderboard(interaction, category_id=1)
            
            # Should call get_completed_races_by_category for RecentRace type
            mock_get_races.assert_called_once_with(1)
        
        # Test Points type
        points_category = create_mock_category(
            category_id=2, 
            name="Points Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        with patch('ui.menus.get_category', return_value=points_category) as mock_get_category, \
             patch('ui.menus.get_category_points', return_value=[]) as mock_get_points, \
             patch('ui.menus.get_category_no_points_message') as mock_get_no_points_msg, \
             patch('ui.menus.send_message') as mock_send_message:
            
            mock_get_no_points_msg.return_value = "No points message"
            
            await show_category_leaderboard(interaction, category_id=2)
            
            # Should call get_category_points for Points type
            mock_get_points.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_menu_creation_parameters(self):
        """Test that menu is created with correct parameters for Points leaderboard."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        points_list = [{"user_id": 100, "points": 150.5, "username": "User1"}]
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_points', return_value=points_list) as mock_get_points, \
             patch('ui.menus.menus.ButtonMenuPages') as mock_menu_class, \
             patch('ui.menus.zCategoryPointsLeaderboardPageSource') as mock_source_class:
            
            mock_menu = MagicMock()
            mock_menu.start = AsyncMock()
            mock_menu_class.return_value = mock_menu
            
            mock_source = MagicMock()
            mock_source_class.return_value = mock_source
            
            await show_category_leaderboard(interaction, category_id=1)
            
            # Verify page source was created with correct parameters
            mock_source_class.assert_called_once_with(points_list, interaction.client)
            
            # Verify menu was created with correct source
            mock_menu_class.assert_called_once_with(source=mock_source)
            
            # Verify menu was started with correct parameters
            mock_menu.start.assert_called_once_with(interaction=interaction, ephemeral=True)

    @pytest.mark.asyncio
    async def test_recent_race_multiple_races(self):
        """Test RecentRace leaderboard type with multiple completed races (should use first one)."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        race1 = create_mock_race(race_id=1, state=RaceState.Completed)
        race2 = create_mock_race(race_id=2, state=RaceState.Completed)
        races = [race1, race2]  # race1 should be used (first in list)
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_completed_races_by_category', return_value=races) as mock_get_races, \
             patch('ui.menus.show_race_leaderboard') as mock_show_race_leaderboard:
            
            await show_category_leaderboard(interaction, category_id=1)
            
            mock_get_category.assert_called_once_with(1)
            mock_get_races.assert_called_once_with(1)
            # Should use the first race (race1.id = 1)
            mock_show_race_leaderboard.assert_called_once_with(interaction, race1.id)
