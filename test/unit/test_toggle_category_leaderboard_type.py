# -*- coding: utf-8 -*-
"""
Unit tests for toggle_category_leaderboard_type() function in ui/menus.py.
Tests the category leaderboard type toggle functionality including database persistence and UI updates.
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

from ui.menus import toggle_category_leaderboard_type
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState, RaceLeaderboardType, RaceMessageType


@pytest.mark.unit
class TestToggleCategoryLeaderboardType:
    """Tests for toggle_category_leaderboard_type() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_recent_race_to_points_toggle(self):
        """Test toggling from RecentRace to Points leaderboard type."""
        interaction = create_mock_interaction()
        
        # Create category with RecentRace type
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Points"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify category was updated to Points
            assert category.leaderboard_type == RaceLeaderboardType.Points
            
            # Verify category was saved
            category.save.assert_called_once()
            
            # Verify button style was updated
            mock_get_button_style.assert_called_once_with(RaceLeaderboardType.Points)
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.green
            
            # Verify embed field value was updated
            mock_to_str.assert_called_once_with(RaceLeaderboardType.Points)
            assert mock_toggle_field.embed_field.value == "Points"
            
            # Verify logging was called
            mock_logging.info.assert_called_once_with("Category Test Category leaderboard type toggled to Points")
            
            # Verify menu was updated
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)

    @pytest.mark.asyncio
    async def test_points_to_recent_race_toggle(self):
        """Test toggling from Points to RecentRace leaderboard type."""
        interaction = create_mock_interaction()
        
        # Create category with Points type
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.primary
            mock_to_str.return_value = "Recent Race"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify category was updated to RecentRace
            assert category.leaderboard_type == RaceLeaderboardType.RecentRace
            
            # Verify category was saved
            category.save.assert_called_once()
            
            # Verify button style was updated
            mock_get_button_style.assert_called_once_with(RaceLeaderboardType.RecentRace)
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.primary
            
            # Verify embed field value was updated
            mock_to_str.assert_called_once_with(RaceLeaderboardType.RecentRace)
            assert mock_toggle_field.embed_field.value == "Recent Race"
            
            # Verify logging was called
            mock_logging.info.assert_called_once_with("Category Test Category leaderboard type toggled to Recent Race")
            
            # Verify menu was updated
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)

    @pytest.mark.asyncio
    async def test_menu_embed_update(self):
        """Test that menu embed is properly updated after toggle."""
        interaction = create_mock_interaction()
        
        # Create category
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Points"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify update_menu_embed_field was called with correct parameters
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)

    @pytest.mark.asyncio
    async def test_database_persistence(self):
        """Test that database changes are persisted."""
        interaction = create_mock_interaction()
        
        # Create category
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Points"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify category.save() was called to persist changes
            category.save.assert_called_once()
            
            # Verify the category object was modified
            assert category.leaderboard_type == RaceLeaderboardType.Points

    @pytest.mark.asyncio
    async def test_button_style_update(self):
        """Test that button style is updated correctly."""
        interaction = create_mock_interaction()
        
        # Create category
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Points"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify get_leaderboard_type_button_style was called with new type
            mock_get_button_style.assert_called_once_with(RaceLeaderboardType.Points)
            
            # Verify button style was set on toggle field
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.green

    @pytest.mark.asyncio
    async def test_embed_field_value_update(self):
        """Test that embed field value is updated correctly."""
        interaction = create_mock_interaction()
        
        # Create category
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Points"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify RaceLeaderboardType.to_str was called with new type
            mock_to_str.assert_called_once_with(RaceLeaderboardType.Points)
            
            # Verify embed field value was set
            assert mock_toggle_field.embed_field.value == "Points"

    @pytest.mark.asyncio
    async def test_logging_output(self):
        """Test that appropriate logging occurs."""
        interaction = create_mock_interaction()
        
        # Create category
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Points"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify logging was called with correct message
            mock_logging.info.assert_called_once_with("Category Test Category leaderboard type toggled to Points")

    @pytest.mark.asyncio
    async def test_payload_structure(self):
        """Test that function correctly extracts menu and toggle field from payload."""
        interaction = create_mock_interaction()
        
        # Create category
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = category
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.get_leaderboard_type_button_style') as mock_get_button_style, \
             patch('ui.menus.RaceLeaderboardType.to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu, \
             patch('ui.menus.logging') as mock_logging:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Points"
            
            await toggle_category_leaderboard_type(interaction, payload)
            
            # Verify that the function correctly extracted menu and toggle_field from payload
            # This is implicit in the successful execution and the calls to update_menu_embed_field
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)
