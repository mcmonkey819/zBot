# -*- coding: utf-8 -*-
"""
Unit tests for toggle_required_extra_info() function in ui/menus.py.
Tests the required extra info toggle functionality including database persistence and UI updates.
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

from ui.menus import toggle_required_extra_info
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState, RaceLeaderboardType, RaceMessageType


@pytest.mark.unit
class TestToggleRequiredExtraInfo:
    """Tests for toggle_required_extra_info() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_required_to_optional_toggle(self):
        """Test toggling from required to optional extra info."""
        interaction = create_mock_interaction()
        
        # Create assignment with required=True
        assignment = MagicMock()
        assignment.required = True
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.grey
            mock_to_str.return_value = "Optional"
            
            await toggle_required_extra_info(interaction, payload)
            
            # Verify assignment was updated to optional
            assert assignment.required == False
            
            # Verify assignment was saved
            assignment.save.assert_called_once()
            
            # Verify button style was updated
            mock_get_button_style.assert_called_once_with(False)
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.grey
            
            # Verify embed field value was updated
            mock_to_str.assert_called_once_with(False)
            assert mock_toggle_field.embed_field.value == "Optional"
            
            # Verify menu was updated
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)

    @pytest.mark.asyncio
    async def test_optional_to_required_toggle(self):
        """Test toggling from optional to required extra info."""
        interaction = create_mock_interaction()
        
        # Create assignment with required=False
        assignment = MagicMock()
        assignment.required = False
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Required"
            
            await toggle_required_extra_info(interaction, payload)
            
            # Verify assignment was updated to required
            assert assignment.required == True
            
            # Verify assignment was saved
            assignment.save.assert_called_once()
            
            # Verify button style was updated
            mock_get_button_style.assert_called_once_with(True)
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.green
            
            # Verify embed field value was updated
            mock_to_str.assert_called_once_with(True)
            assert mock_toggle_field.embed_field.value == "Required"
            
            # Verify menu was updated
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)

    @pytest.mark.asyncio
    async def test_button_style_update(self):
        """Test that button style is updated correctly."""
        interaction = create_mock_interaction()
        
        # Create assignment
        assignment = MagicMock()
        assignment.required = True
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.grey
            mock_to_str.return_value = "Optional"
            
            await toggle_required_extra_info(interaction, payload)
            
            # Verify required_field_button_style was called with new value
            mock_get_button_style.assert_called_once_with(False)
            
            # Verify button style was set on toggle field
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.grey

    @pytest.mark.asyncio
    async def test_menu_embed_update(self):
        """Test that menu embed is properly updated after toggle."""
        interaction = create_mock_interaction()
        
        # Create assignment
        assignment = MagicMock()
        assignment.required = True
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.grey
            mock_to_str.return_value = "Optional"
            
            await toggle_required_extra_info(interaction, payload)
            
            # Verify update_menu_embed_field was called with correct parameters
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)

    @pytest.mark.asyncio
    async def test_database_persistence(self):
        """Test that database changes are persisted."""
        interaction = create_mock_interaction()
        
        # Create assignment
        assignment = MagicMock()
        assignment.required = True
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.grey
            mock_to_str.return_value = "Optional"
            
            await toggle_required_extra_info(interaction, payload)
            
            # Verify assignment.save() was called to persist changes
            assignment.save.assert_called_once()
            
            # Verify the assignment object was modified
            assert assignment.required == False

    @pytest.mark.asyncio
    async def test_embed_field_value_update(self):
        """Test that embed field value is updated correctly."""
        interaction = create_mock_interaction()
        
        # Create assignment
        assignment = MagicMock()
        assignment.required = True
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.grey
            mock_to_str.return_value = "Optional"
            
            await toggle_required_extra_info(interaction, payload)
            
            # Verify required_field_to_str was called with new value
            mock_to_str.assert_called_once_with(False)
            
            # Verify embed field value was set
            assert mock_toggle_field.embed_field.value == "Optional"

    @pytest.mark.asyncio
    async def test_payload_structure(self):
        """Test that function correctly extracts menu and toggle field from payload."""
        interaction = create_mock_interaction()
        
        # Create assignment
        assignment = MagicMock()
        assignment.required = True
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            mock_get_button_style.return_value = nextcord.ButtonStyle.grey
            mock_to_str.return_value = "Optional"
            
            await toggle_required_extra_info(interaction, payload)
            
            # Verify that the function correctly extracted menu and toggle_field from payload
            # This is implicit in the successful execution and the calls to update_menu_embed_field
            mock_update_menu.assert_called_once_with(mock_menu, mock_toggle_field)

    @pytest.mark.asyncio
    async def test_multiple_toggles_consistency(self):
        """Test that multiple toggles work consistently."""
        interaction = create_mock_interaction()
        
        # Create assignment
        assignment = MagicMock()
        assignment.required = True
        assignment.save = MagicMock()
        
        # Mock menu and toggle field
        mock_menu = MagicMock()
        mock_toggle_field = MagicMock()
        mock_toggle_field.payload = assignment
        mock_toggle_field.button_style = None
        mock_toggle_field.embed_field = MagicMock()
        mock_toggle_field.embed_field.value = None
        
        payload = (mock_menu, mock_toggle_field)
        
        with patch('ui.menus.required_field_button_style') as mock_get_button_style, \
             patch('ui.menus.required_field_to_str') as mock_to_str, \
             patch('ui.menus.update_menu_embed_field') as mock_update_menu:
            
            # First toggle: True -> False
            mock_get_button_style.return_value = nextcord.ButtonStyle.grey
            mock_to_str.return_value = "Optional"
            
            await toggle_required_extra_info(interaction, payload)
            
            assert assignment.required == False
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.grey
            assert mock_toggle_field.embed_field.value == "Optional"
            
            # Reset for second toggle
            mock_toggle_field.button_style = None
            mock_toggle_field.embed_field.value = None
            
            # Second toggle: False -> True
            mock_get_button_style.return_value = nextcord.ButtonStyle.green
            mock_to_str.return_value = "Required"
            
            await toggle_required_extra_info(interaction, payload)
            
            assert assignment.required == True
            assert mock_toggle_field.button_style == nextcord.ButtonStyle.green
            assert mock_toggle_field.embed_field.value == "Required"
