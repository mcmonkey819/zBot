# -*- coding: utf-8 -*-
"""
Unit tests for update_category_leaderboard() function in ui/menus.py.
Tests the category leaderboard update functionality including message lookup and deletion.
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

from ui.menus import update_category_leaderboard
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState, RaceLeaderboardType, RaceMessageType


@pytest.mark.unit
class TestUpdateCategoryLeaderboard:
    """Tests for update_category_leaderboard() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_no_messages_early_return(self):
        """Test that function returns early when no messages are found."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_messages_by_category_id', return_value=[]) as mock_get_messages, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            await update_category_leaderboard(interaction, race)
            
            # Verify get_messages_by_category_id was called
            mock_get_messages.assert_called_once_with(race.category_id.id)
            
            # Verify no posting was called (early return)
            mock_post_leaderboard.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_leaderboard_messages_early_return(self):
        """Test that function returns early when no leaderboard messages are found."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock messages that are not leaderboard type
        mock_message1 = MagicMock()
        mock_message1.message_type = RaceMessageType.Announcement
        mock_message2 = MagicMock()
        mock_message2.message_type = RaceMessageType.RaceInfo
        non_leaderboard_messages = [mock_message1, mock_message2]
        
        with patch('ui.menus.get_messages_by_category_id', return_value=non_leaderboard_messages) as mock_get_messages, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            await update_category_leaderboard(interaction, race)
            
            # Verify get_messages_by_category_id was called
            mock_get_messages.assert_called_once_with(race.category_id.id)
            
            # Verify no posting was called (no leaderboard messages)
            mock_post_leaderboard.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_lookup_by_category(self):
        """Test message lookup by category ID."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock leaderboard messages
        mock_message1 = MagicMock()
        mock_message1.message_type = RaceMessageType.Leaderboard
        mock_message1.channel_id = 12345
        mock_message1.id = 11111
        mock_message2 = MagicMock()
        mock_message2.message_type = RaceMessageType.Leaderboard
        mock_message2.channel_id = 12345
        mock_message2.id = 22222
        leaderboard_messages = [mock_message1, mock_message2]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.get_messages_by_category_id', return_value=leaderboard_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            await update_category_leaderboard(interaction, race)
            
            # Verify get_messages_by_category_id was called with correct category ID
            mock_get_messages.assert_called_once_with(race.category_id.id)
            
            # Verify channel was fetched
            interaction.guild.get_channel.assert_called_once_with(12345)
            
            # Verify messages were deleted
            assert mock_delete_message.call_count == 2
            mock_delete_message.assert_any_call(interaction.guild, 11111)
            mock_delete_message.assert_any_call(interaction.guild, 22222)
            
            # Verify new leaderboard was posted
            mock_post_leaderboard.assert_called_once_with(interaction, mock_channel, race.category_id.id, interaction.client)

    @pytest.mark.asyncio
    async def test_message_deletion(self):
        """Test that existing messages are properly deleted."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock leaderboard messages
        mock_message1 = MagicMock()
        mock_message1.message_type = RaceMessageType.Leaderboard
        mock_message1.channel_id = 12345
        mock_message1.id = 11111
        mock_message2 = MagicMock()
        mock_message2.message_type = RaceMessageType.Leaderboard
        mock_message2.channel_id = 12345
        mock_message2.id = 22222
        mock_message3 = MagicMock()
        mock_message3.message_type = RaceMessageType.Leaderboard
        mock_message3.channel_id = 12345
        mock_message3.id = 33333
        leaderboard_messages = [mock_message1, mock_message2, mock_message3]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.get_messages_by_category_id', return_value=leaderboard_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            await update_category_leaderboard(interaction, race)
            
            # Verify all messages were deleted
            assert mock_delete_message.call_count == 3
            mock_delete_message.assert_any_call(interaction.guild, 11111)
            mock_delete_message.assert_any_call(interaction.guild, 22222)
            mock_delete_message.assert_any_call(interaction.guild, 33333)

    @pytest.mark.asyncio
    async def test_new_leaderboard_posting(self):
        """Test that new leaderboard is posted after message deletion."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock leaderboard messages
        mock_message = MagicMock()
        mock_message.message_type = RaceMessageType.Leaderboard
        mock_message.channel_id = 12345
        mock_message.id = 11111
        leaderboard_messages = [mock_message]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.get_messages_by_category_id', return_value=leaderboard_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            await update_category_leaderboard(interaction, race)
            
            # Verify new leaderboard was posted with correct parameters
            mock_post_leaderboard.assert_called_once_with(interaction, mock_channel, race.category_id.id, interaction.client)

    @pytest.mark.asyncio
    async def test_mixed_message_types_filtering(self):
        """Test that only leaderboard messages are processed when mixed message types exist."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock mixed message types
        mock_leaderboard1 = MagicMock()
        mock_leaderboard1.message_type = RaceMessageType.Leaderboard
        mock_leaderboard1.channel_id = 12345
        mock_leaderboard1.id = 11111
        mock_announcement = MagicMock()
        mock_announcement.message_type = RaceMessageType.Announcement
        mock_announcement.channel_id = 12345
        mock_announcement.id = 22222
        mock_leaderboard2 = MagicMock()
        mock_leaderboard2.message_type = RaceMessageType.Leaderboard
        mock_leaderboard2.channel_id = 12345
        mock_leaderboard2.id = 33333
        mixed_messages = [mock_leaderboard1, mock_announcement, mock_leaderboard2]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.get_messages_by_category_id', return_value=mixed_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            await update_category_leaderboard(interaction, race)
            
            # Verify only leaderboard messages were deleted (2 out of 3)
            assert mock_delete_message.call_count == 2
            mock_delete_message.assert_any_call(interaction.guild, 11111)
            mock_delete_message.assert_any_call(interaction.guild, 33333)
            
            # Verify new leaderboard was posted
            mock_post_leaderboard.assert_called_once_with(interaction, mock_channel, race.category_id.id, interaction.client)

    @pytest.mark.asyncio
    async def test_channel_not_found_handling(self):
        """Test handling when channel is not found."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock leaderboard messages
        mock_message = MagicMock()
        mock_message.message_type = RaceMessageType.Leaderboard
        mock_message.channel_id = 12345
        mock_message.id = 11111
        leaderboard_messages = [mock_message]
        
        # Mock channel not found
        interaction.guild.get_channel = MagicMock(return_value=None)
        
        with patch('ui.menus.get_messages_by_category_id', return_value=leaderboard_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            # This should not raise an error, but should handle the None channel gracefully
            await update_category_leaderboard(interaction, race)
            
            # Verify get_messages_by_category_id was called
            mock_get_messages.assert_called_once_with(race.category_id.id)
            
            # Verify channel was fetched
            interaction.guild.get_channel.assert_called_once_with(12345)
            
            # Verify messages were still deleted
            mock_delete_message.assert_called_once_with(interaction.guild, 11111)
            
            # Verify post_channel_category_leaderboard was called with None channel
            mock_post_leaderboard.assert_called_once_with(interaction, None, race.category_id.id, interaction.client)

    @pytest.mark.asyncio
    async def test_none_messages_handling(self):
        """Test handling when get_messages_by_category_id returns None."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_messages_by_category_id', return_value=None) as mock_get_messages, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            # This should handle None gracefully by treating it as empty list
            await update_category_leaderboard(interaction, race)
            
            # Verify get_messages_by_category_id was called
            mock_get_messages.assert_called_once_with(race.category_id.id)
            
            # Verify no posting was called (None messages treated as empty)
            mock_post_leaderboard.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_leaderboard_messages_after_filtering(self):
        """Test handling when no leaderboard messages remain after filtering."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock only non-leaderboard messages
        mock_announcement = MagicMock()
        mock_announcement.message_type = RaceMessageType.Announcement
        mock_race_info = MagicMock()
        mock_race_info.message_type = RaceMessageType.RaceInfo
        non_leaderboard_messages = [mock_announcement, mock_race_info]
        
        with patch('ui.menus.get_messages_by_category_id', return_value=non_leaderboard_messages) as mock_get_messages, \
             patch('ui.menus.post_channel_category_leaderboard') as mock_post_leaderboard:
            
            await update_category_leaderboard(interaction, race)
            
            # Verify get_messages_by_category_id was called
            mock_get_messages.assert_called_once_with(race.category_id.id)
            
            # Verify no posting was called (no leaderboard messages after filtering)
            mock_post_leaderboard.assert_not_called()