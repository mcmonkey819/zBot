# -*- coding: utf-8 -*-
"""
Integration tests for pinned race state UI functions.
Tests UI functions with mocked Discord interactions and database operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# Mock the menus import before importing UI modules
import sys
import test.mock_menus
sys.modules['nextcord.ext.menus'] = test.mock_menus.menus

from ui.ui_util import (
    handle_missing_channel_restoration,
    send_startup_restoration_summary,
    restore_pinned_race_states
)
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category
from db.db_util import PinType, RaceMessageType


@pytest.mark.integration
class TestHandleMissingChannelRestoration:
    """Tests for handle_missing_channel_restoration() function"""

    @pytest.mark.asyncio
    @patch('ui.menus.prompt_for_channel')
    @patch('ui.ui_util.update_pinned_state_channel')
    async def test_individual_race_channel_restoration_success(self, mock_update_channel, mock_prompt):
        """Test successful channel restoration for individual race."""
        # Setup
        interaction = create_mock_interaction()
        mock_channel = create_mock_text_channel(channel_id=999)
        mock_prompt.return_value = mock_channel
        mock_update_channel.return_value = True
        
        # Test
        result = await handle_missing_channel_restoration(
            interaction, race_id=123, category_id=None, pin_type=PinType.Individual
        )
        
        # Verify
        assert result == mock_channel
        mock_prompt.assert_called_once_with(
            interaction, 
            "Channel not found when restoring pinned info for race 123. Choose a new channel or dismiss to skip"
        )
        mock_update_channel.assert_called_once_with(interaction.guild_id, 123, None, 999)

    @pytest.mark.asyncio
    @patch('ui.menus.prompt_for_channel')
    @patch('ui.ui_util.update_pinned_state_channel')
    async def test_category_channel_restoration_success(self, mock_update_channel, mock_prompt):
        """Test successful channel restoration for category pin."""
        # Setup
        interaction = create_mock_interaction()
        mock_channel = create_mock_text_channel(channel_id=999)
        mock_prompt.return_value = mock_channel
        mock_update_channel.return_value = True
        
        # Test
        result = await handle_missing_channel_restoration(
            interaction, race_id=None, category_id=456, pin_type=PinType.Category
        )
        
        # Verify
        assert result == mock_channel
        mock_prompt.assert_called_once_with(
            interaction, 
            "Channel not found when restoring pinned info for category 456. Choose a new channel or dismiss to skip"
        )
        mock_update_channel.assert_called_once_with(interaction.guild_id, None, 456, 999)

    @pytest.mark.asyncio
    @patch('ui.menus.prompt_for_channel')
    async def test_channel_restoration_user_dismisses(self, mock_prompt):
        """Test when user dismisses channel selection."""
        # Setup
        interaction = create_mock_interaction()
        mock_prompt.return_value = None  # User dismissed
        
        # Test
        result = await handle_missing_channel_restoration(
            interaction, race_id=123, category_id=None, pin_type=PinType.Individual
        )
        
        # Verify
        assert result is None


@pytest.mark.integration
class TestSendStartupRestorationSummary:
    """Tests for send_startup_restoration_summary() function"""

    @pytest.mark.asyncio
    @patch('ui.ui_util.send_message')
    async def test_summary_with_restored_and_skipped(self, mock_send_message):
        """Test summary message with both restored and skipped items."""
        # Setup
        interaction = create_mock_interaction()
        restored_count = 2
        skipped_races = [123, 456]
        skipped_categories = [789]
        
        # Test
        await send_startup_restoration_summary(
            interaction, restored_count, skipped_races, skipped_categories
        )
        
        # Verify
        expected_message = (
            "**Pinned Race Restoration Summary:**\n"
            "✅ Successfully restored 2 pinned race(s)\n"
            "⚠️ Skipped 2 race(s) (no longer exist): 123, 456\n"
            "⚠️ Skipped 1 category/category pin(s) (no longer exist): 789"
        )
        mock_send_message.assert_called_once_with(
            interaction, expected_message, ephemeral=True
        )

    @pytest.mark.asyncio
    @patch('ui.ui_util.send_message')
    async def test_summary_only_restored(self, mock_send_message):
        """Test summary message with only restored items."""
        # Setup
        interaction = create_mock_interaction()
        restored_count = 3
        skipped_races = []
        skipped_categories = []
        
        # Test
        await send_startup_restoration_summary(
            interaction, restored_count, skipped_races, skipped_categories
        )
        
        # Verify
        expected_message = "**Pinned Race Restoration Summary:**\n✅ Successfully restored 3 pinned race(s)"
        mock_send_message.assert_called_once_with(
            interaction, expected_message, ephemeral=True
        )

    @pytest.mark.asyncio
    @patch('ui.ui_util.send_message')
    async def test_summary_no_restoration(self, mock_send_message):
        """Test summary message with no restoration activity."""
        # Setup
        interaction = create_mock_interaction()
        restored_count = 0
        skipped_races = []
        skipped_categories = []
        
        # Test
        await send_startup_restoration_summary(
            interaction, restored_count, skipped_races, skipped_categories
        )
        
        # Verify - should not send message when nothing to report
        mock_send_message.assert_not_called()


@pytest.mark.integration
class TestRestorePinnedRaceStates:
    """Tests for restore_pinned_race_states() function"""


    @pytest.mark.asyncio
    @patch('ui.ui_util.get_pinned_race_states')
    @patch('ui.ui_util.get_race')
    @patch('ui.ui_util.get_category')
    @patch('ui.ui_util.send_startup_restoration_summary')
    async def test_restore_skips_missing_race(self, mock_summary, mock_get_category, 
                                              mock_get_race, mock_get_states):
        """Test that missing races are skipped."""
        # Setup
        interaction = create_mock_interaction()
        
        mock_state = Mock()
        mock_state.race_id = 123
        mock_state.category_id = None
        mock_state.channel_id = 999
        mock_state.pin_type = PinType.Individual
        mock_state.id = 1
        
        mock_get_states.return_value = [mock_state]
        mock_get_race.return_value = None  # Race doesn't exist
        
        # Test
        await restore_pinned_race_states(interaction.guild_id, interaction)
        
        # Verify
        mock_summary.assert_called_once_with(interaction, 0, [123], [])

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_pinned_race_states')
    @patch('ui.ui_util.get_race')
    @patch('ui.ui_util.get_category')
    @patch('ui.ui_util.send_startup_restoration_summary')
    async def test_restore_skips_missing_category(self, mock_summary, mock_get_category, 
                                                  mock_get_race, mock_get_states):
        """Test that missing categories are skipped."""
        # Setup
        interaction = create_mock_interaction()
        
        mock_state = Mock()
        mock_state.race_id = None
        mock_state.category_id = 456
        mock_state.channel_id = 999
        mock_state.pin_type = PinType.Category
        mock_state.id = 1
        
        mock_get_states.return_value = [mock_state]
        mock_get_category.return_value = None  # Category doesn't exist
        
        # Test
        await restore_pinned_race_states(interaction.guild_id, interaction)
        
        # Verify
        mock_summary.assert_called_once_with(interaction, 0, [], [456])

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_pinned_race_states')
    @patch('ui.ui_util.get_race')
    @patch('ui.ui_util.get_category')
    @patch('ui.ui_util.handle_missing_channel_restoration')
    @patch('ui.menus.pin_race_info')
    @patch('ui.ui_util.send_startup_restoration_summary')
    async def test_restore_handles_missing_channel(self, mock_summary, mock_pin_race,
                                                   mock_handle_channel, mock_get_category,
                                                   mock_get_race, mock_get_states):
        """Test handling of missing channels with user selection."""
        # Setup
        interaction = create_mock_interaction()
        mock_race = create_mock_race(race_id=123)
        mock_channel = create_mock_text_channel(channel_id=999)
        
        mock_state = Mock()
        mock_state.race_id = 123
        mock_state.category_id = None
        mock_state.channel_id = 888  # Original channel
        mock_state.pin_type = PinType.Individual
        mock_state.id = 1
        
        mock_get_states.return_value = [mock_state]
        mock_get_race.return_value = mock_race
        interaction.guild.get_channel.return_value = None  # Channel missing
        mock_handle_channel.return_value = mock_channel  # User selects new channel
        
        # Test
        await restore_pinned_race_states(interaction.guild_id, interaction)
        
        # Verify
        mock_handle_channel.assert_called_once_with(
            interaction, 123, None, PinType.Individual
        )
        mock_pin_race.assert_called_once_with(999, mock_race, interaction)
        mock_summary.assert_called_once_with(interaction, 1, [], [])

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_pinned_race_states')
    @patch('ui.ui_util.get_race')
    @patch('ui.ui_util.get_category')
    @patch('ui.ui_util.handle_missing_channel_restoration')
    @patch('ui.ui_util.send_startup_restoration_summary')
    async def test_restore_user_dismisses_channel_selection(self, mock_summary,
                                                           mock_handle_channel,
                                                           mock_get_category,
                                                           mock_get_race, mock_get_states):
        """Test when user dismisses channel selection."""
        # Setup
        interaction = create_mock_interaction()
        mock_race = create_mock_race(race_id=123)
        
        mock_state = Mock()
        mock_state.race_id = 123
        mock_state.category_id = None
        mock_state.channel_id = 888
        mock_state.pin_type = PinType.Individual
        mock_state.id = 1
        
        mock_get_states.return_value = [mock_state]
        mock_get_race.return_value = mock_race
        interaction.guild.get_channel.return_value = None  # Channel missing
        mock_handle_channel.return_value = None  # User dismisses
        
        # Test
        await restore_pinned_race_states(interaction.guild_id, interaction)
        
        # Verify
        mock_handle_channel.assert_called_once_with(
            interaction, 123, None, PinType.Individual
        )
        mock_summary.assert_called_once_with(interaction, 0, [123], [])

    @pytest.mark.asyncio
    @patch('ui.ui_util.get_pinned_race_states')
    @patch('ui.ui_util.send_startup_restoration_summary')
    async def test_restore_handles_exception(self, mock_summary, mock_get_states):
        """Test exception handling during restoration."""
        # Setup
        interaction = create_mock_interaction()
        
        mock_state = Mock()
        mock_state.race_id = 123
        mock_state.category_id = None
        mock_state.channel_id = 999
        mock_state.pin_type = PinType.Individual
        mock_state.id = 1
        
        mock_get_states.return_value = [mock_state]
        # Simulate an exception during processing
        with patch('ui.ui_util.get_race', side_effect=Exception("Test error")):
            # Test
            await restore_pinned_race_states(interaction.guild_id, interaction)
        
        # Verify - should still call summary with 0 restored
        mock_summary.assert_called_once_with(interaction, 0, [], [])
