# -*- coding: utf-8 -*-
"""
Unit tests for update_race_leaderboard() function in ui/menus.py.
Tests the race leaderboard update functionality including message deletion and recreation.
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

from ui.menus import update_race_leaderboard
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState, RaceLeaderboardType, RaceMessageType


@pytest.mark.unit
class TestUpdateRaceLeaderboard:
    """Tests for update_race_leaderboard() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_no_submissions_early_return(self):
        """Test that function returns early when race has no submissions."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.race_has_submissions', return_value=False) as mock_has_submissions, \
             patch('ui.menus.get_messages_by_race_id') as mock_get_messages, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_leaderboard, \
             patch('ui.menus.update_category_leaderboard') as mock_update_category:
            
            await update_race_leaderboard(interaction, race)
            
            # Verify race_has_submissions was called
            mock_has_submissions.assert_called_once_with(race.id)
            
            # Verify no other functions were called (early return)
            mock_get_messages.assert_not_called()
            mock_post_leaderboard.assert_not_called()
            mock_update_category.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_existing_messages_logging(self):
        """Test logging when no existing messages are found."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.race_has_submissions', return_value=True) as mock_has_submissions, \
             patch('ui.menus.get_messages_by_race_id', return_value=[]) as mock_get_messages, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_leaderboard, \
             patch('ui.menus.update_category_leaderboard') as mock_update_category, \
             patch('ui.menus.logging') as mock_logging:
            
            await update_race_leaderboard(interaction, race)
            
            # Verify race_has_submissions was called
            mock_has_submissions.assert_called_once_with(race.id)
            
            # Verify get_messages_by_race_id was called with correct parameters
            mock_get_messages.assert_called_once_with(race.id, message_type=RaceMessageType.Leaderboard)
            
            # Verify logging was called
            mock_logging.info.assert_called_once_with("No race messages found in update_race_leaderboard")
            
            # Verify no posting or category update was called
            mock_post_leaderboard.assert_not_called()
            mock_update_category.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_deletion_and_recreation(self):
        """Test message deletion and recreation when messages exist."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock existing messages
        mock_message1 = MagicMock()
        mock_message1.channel_id = 12345
        mock_message1.id = 11111
        mock_message2 = MagicMock()
        mock_message2.channel_id = 12345
        mock_message2.id = 22222
        existing_messages = [mock_message1, mock_message2]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.race_has_submissions', return_value=True) as mock_has_submissions, \
             patch('ui.menus.get_messages_by_race_id', return_value=existing_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_leaderboard, \
             patch('ui.menus.get_emoji_list') as mock_get_emojis, \
             patch('ui.menus.update_category_leaderboard') as mock_update_category:
            
            mock_get_emojis.return_value = ["🏆", "🥇", "🥈", "🥉"]
            
            await update_race_leaderboard(interaction, race)
            
            # Verify race_has_submissions was called
            mock_has_submissions.assert_called_once_with(race.id)
            
            # Verify get_messages_by_race_id was called
            mock_get_messages.assert_called_once_with(race.id, message_type=RaceMessageType.Leaderboard)
            
            # Verify channel was fetched
            interaction.guild.get_channel.assert_called_once_with(12345)
            
            # Verify messages were deleted
            assert mock_delete_message.call_count == 2
            mock_delete_message.assert_any_call(interaction.guild, 11111)
            mock_delete_message.assert_any_call(interaction.guild, 22222)
            
            # Verify new leaderboard was posted
            mock_post_leaderboard.assert_called_once_with(
                interaction, 
                mock_channel, 
                race.id, 
                interaction.client, 
                ["🏆", "🥇", "🥈", "🥉"]
            )
            
            # Verify category update was not called (not RecentRace type)
            mock_update_category.assert_not_called()

    @pytest.mark.asyncio
    async def test_category_leaderboard_cascade_update_recent_race(self):
        """Test category leaderboard cascade update for RecentRace type."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        race = create_mock_race(race_id=1, state=RaceState.Active, category_id=category)
        
        # Mock existing messages
        mock_message = MagicMock()
        mock_message.channel_id = 12345
        mock_message.id = 11111
        existing_messages = [mock_message]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.race_has_submissions', return_value=True) as mock_has_submissions, \
             patch('ui.menus.get_messages_by_race_id', return_value=existing_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_leaderboard, \
             patch('ui.menus.get_emoji_list') as mock_get_emojis, \
             patch('ui.menus.get_most_recent_race', return_value=race) as mock_get_recent_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_category:
            
            mock_get_emojis.return_value = ["🏆", "🥇", "🥈", "🥉"]
            
            await update_race_leaderboard(interaction, race)
            
            # Verify race_has_submissions was called
            mock_has_submissions.assert_called_once_with(race.id)
            
            # Verify get_messages_by_race_id was called
            mock_get_messages.assert_called_once_with(race.id, message_type=RaceMessageType.Leaderboard)
            
            # Verify messages were deleted
            mock_delete_message.assert_called_once_with(interaction.guild, 11111)
            
            # Verify new leaderboard was posted
            mock_post_leaderboard.assert_called_once_with(
                interaction, 
                mock_channel, 
                race.id, 
                interaction.client, 
                ["🏆", "🥇", "🥈", "🥉"]
            )
            
            # Verify recent race check was performed
            mock_get_recent_race.assert_called_once_with(race.category_id.id)
            
            # Verify category leaderboard was updated
            mock_update_category.assert_called_once_with(interaction, race)

    @pytest.mark.asyncio
    async def test_category_leaderboard_cascade_update_not_recent_race(self):
        """Test that category leaderboard is not updated when race is not the most recent."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        race = create_mock_race(race_id=1, state=RaceState.Active, category_id=category)
        recent_race = create_mock_race(race_id=2, state=RaceState.Active, category_id=category)
        
        # Mock existing messages
        mock_message = MagicMock()
        mock_message.channel_id = 12345
        mock_message.id = 11111
        existing_messages = [mock_message]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.race_has_submissions', return_value=True) as mock_has_submissions, \
             patch('ui.menus.get_messages_by_race_id', return_value=existing_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_leaderboard, \
             patch('ui.menus.get_emoji_list') as mock_get_emojis, \
             patch('ui.menus.get_most_recent_race', return_value=recent_race) as mock_get_recent_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_category:
            
            mock_get_emojis.return_value = ["🏆", "🥇", "🥈", "🥉"]
            
            await update_race_leaderboard(interaction, race)
            
            # Verify race_has_submissions was called
            mock_has_submissions.assert_called_once_with(race.id)
            
            # Verify get_messages_by_race_id was called
            mock_get_messages.assert_called_once_with(race.id, message_type=RaceMessageType.Leaderboard)
            
            # Verify messages were deleted
            mock_delete_message.assert_called_once_with(interaction.guild, 11111)
            
            # Verify new leaderboard was posted
            mock_post_leaderboard.assert_called_once_with(
                interaction, 
                mock_channel, 
                race.id, 
                interaction.client, 
                ["🏆", "🥇", "🥈", "🥉"]
            )
            
            # Verify recent race check was performed
            mock_get_recent_race.assert_called_once_with(race.category_id.id)
            
            # Verify category leaderboard was NOT updated (race is not the most recent)
            mock_update_category.assert_not_called()

    @pytest.mark.asyncio
    async def test_points_leaderboard_type_no_cascade(self):
        """Test that category leaderboard is not updated for Points leaderboard type."""
        interaction = create_mock_interaction()
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        race = create_mock_race(race_id=1, state=RaceState.Active, category_id=category)
        
        # Mock existing messages
        mock_message = MagicMock()
        mock_message.channel_id = 12345
        mock_message.id = 11111
        existing_messages = [mock_message]
        
        # Mock channel
        mock_channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        interaction.guild.get_channel = MagicMock(return_value=mock_channel)
        
        with patch('ui.menus.race_has_submissions', return_value=True) as mock_has_submissions, \
             patch('ui.menus.get_messages_by_race_id', return_value=existing_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_leaderboard, \
             patch('ui.menus.get_emoji_list') as mock_get_emojis, \
             patch('ui.menus.get_most_recent_race') as mock_get_recent_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_category:
            
            mock_get_emojis.return_value = ["🏆", "🥇", "🥈", "🥉"]
            
            await update_race_leaderboard(interaction, race)
            
            # Verify race_has_submissions was called
            mock_has_submissions.assert_called_once_with(race.id)
            
            # Verify get_messages_by_race_id was called
            mock_get_messages.assert_called_once_with(race.id, message_type=RaceMessageType.Leaderboard)
            
            # Verify messages were deleted
            mock_delete_message.assert_called_once_with(interaction.guild, 11111)
            
            # Verify new leaderboard was posted
            mock_post_leaderboard.assert_called_once_with(
                interaction, 
                mock_channel, 
                race.id, 
                interaction.client, 
                ["🏆", "🥇", "🥈", "🥉"]
            )
            
            # Verify recent race check was NOT performed (Points type)
            mock_get_recent_race.assert_not_called()
            
            # Verify category leaderboard was NOT updated (Points type)
            mock_update_category.assert_not_called()

    @pytest.mark.asyncio
    async def test_channel_not_found_handling(self):
        """Test handling when channel is not found."""
        interaction = create_mock_interaction()
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Mock existing messages
        mock_message = MagicMock()
        mock_message.channel_id = 12345
        mock_message.id = 11111
        existing_messages = [mock_message]
        
        # Mock channel not found
        interaction.guild.get_channel = MagicMock(return_value=None)
        
        with patch('ui.menus.race_has_submissions', return_value=True) as mock_has_submissions, \
             patch('ui.menus.get_messages_by_race_id', return_value=existing_messages) as mock_get_messages, \
             patch('ui.menus.delete_message') as mock_delete_message, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_leaderboard, \
             patch('ui.menus.get_emoji_list') as mock_get_emojis, \
             patch('ui.menus.update_category_leaderboard') as mock_update_category:
            
            mock_get_emojis.return_value = ["🏆", "🥇", "🥈", "🥉"]
            
            # This should not raise an error, but should handle the None channel gracefully
            await update_race_leaderboard(interaction, race)
            
            # Verify race_has_submissions was called
            mock_has_submissions.assert_called_once_with(race.id)
            
            # Verify get_messages_by_race_id was called
            mock_get_messages.assert_called_once_with(race.id, message_type=RaceMessageType.Leaderboard)
            
            # Verify channel was fetched
            interaction.guild.get_channel.assert_called_once_with(12345)
            
            # Verify messages were still deleted
            mock_delete_message.assert_called_once_with(interaction.guild, 11111)
            
            # Verify post_channel_race_leaderboard was called with None channel
            mock_post_leaderboard.assert_called_once_with(
                interaction, 
                None, 
                race.id, 
                interaction.client, 
                ["🏆", "🥇", "🥈", "🥉"]
            )