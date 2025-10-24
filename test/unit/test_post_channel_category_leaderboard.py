# -*- coding: utf-8 -*-
"""
Unit tests for post_channel_category_leaderboard() function in ui/menus.py.
Tests the channel category leaderboard posting functionality including different leaderboard types.
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

from ui.menus import post_channel_category_leaderboard
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState, RaceLeaderboardType, RaceMessageType


@pytest.mark.unit
class TestPostChannelCategoryLeaderboard:
    """Tests for post_channel_category_leaderboard() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_category_not_found_error(self):
        """Test error handling when category cannot be found."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        
        with patch('ui.menus.get_category', return_value=None) as mock_get_category, \
             patch('ui.menus.send_message') as mock_send_message:
            
            await post_channel_category_leaderboard(interaction, channel, 999, interaction.client)
            
            mock_get_category.assert_called_once_with(999)
            mock_send_message.assert_called_once_with(
                interaction, 
                "**ERROR** Fetching category with ID 999. Please contact a bot admin."
            )

    @pytest.mark.asyncio
    async def test_recent_race_type_posting(self):
        """Test RecentRace type posting."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        race = create_mock_race(race_id=1, state=RaceState.Completed, category_id=category)
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_most_recent_race', return_value=race) as mock_get_recent_race, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_race_leaderboard, \
             patch('ui.menus.get_emoji_list') as mock_get_emojis:
            
            mock_get_emojis.return_value = ["🏆", "🥇", "🥈", "🥉"]
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify category was fetched
            mock_get_category.assert_called_once_with(1)
            
            # Verify most recent race was fetched
            mock_get_recent_race.assert_called_once_with(1)
            
            # Verify race leaderboard was posted with correct parameters
            mock_post_race_leaderboard.assert_called_once_with(
                interaction, 
                channel, 
                race.id, 
                interaction.client, 
                ["🏆", "🥇", "🥈", "🥉"], 
                save_as_category_message=True
            )

    @pytest.mark.asyncio
    async def test_recent_race_type_no_races(self):
        """Test RecentRace type posting when no races exist."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_most_recent_race', return_value=None) as mock_get_recent_race, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_race_leaderboard, \
             patch('ui.menus.send_message') as mock_send_message:
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify category was fetched
            mock_get_category.assert_called_once_with(1)
            
            # Verify most recent race was fetched
            mock_get_recent_race.assert_called_once_with(1)
            
            # Verify error message was sent
            mock_send_message.assert_called_once_with(
                interaction, 
                "No active or completed races yet for category Test Category"
            )
            
            # Verify race leaderboard was not posted
            mock_post_race_leaderboard.assert_not_called()

    @pytest.mark.asyncio
    async def test_points_type_posting_with_points(self):
        """Test Points type posting when points exist."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        # Mock channel.send
        mock_message1 = MagicMock()
        mock_message1.id = 11111
        mock_message2 = MagicMock()
        mock_message2.id = 22222
        channel.send = AsyncMock(side_effect=[mock_message1, mock_message2])
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_leaderboard_embed_list') as mock_get_embed_list, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock embed list
            mock_embed1 = MagicMock()
            mock_embed2 = MagicMock()
            mock_embed_list = [mock_embed1, mock_embed2]
            mock_get_embed_list.return_value = mock_embed_list
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify category was fetched
            mock_get_category.assert_called_once_with(1)
            
            # Verify embed list was generated
            mock_get_embed_list.assert_called_once_with(1, 8, interaction.client)
            
            # Verify 2 messages were sent
            assert channel.send.call_count == 2
            channel.send.assert_any_call(embed=mock_embed1)
            channel.send.assert_any_call(embed=mock_embed2)
            
            # Verify messages were saved to DB
            assert mock_save_message.call_count == 2
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 11111, category_id=1)
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 22222, category_id=1)

    @pytest.mark.asyncio
    async def test_points_type_posting_no_points(self):
        """Test Points type posting when no points exist."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        # Mock channel.send
        mock_message = MagicMock()
        mock_message.id = 11111
        channel.send = AsyncMock(return_value=mock_message)
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_leaderboard_embed_list', return_value=[]) as mock_get_embed_list, \
             patch('ui.menus.save_message') as mock_save_message:
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify category was fetched
            mock_get_category.assert_called_once_with(1)
            
            # Verify embed list was generated
            mock_get_embed_list.assert_called_once_with(1, 8, interaction.client)
            
            # Verify no points message was sent
            expected_text = "No points scored yet for category Test Category. This is likely due to no completed races."
            channel.send.assert_called_once_with(expected_text)
            
            # Verify message was saved to DB
            mock_save_message.assert_called_once_with(interaction.guild_id, channel.id, 11111, category_id=1)

    @pytest.mark.asyncio
    async def test_points_type_posting_none_embed_list(self):
        """Test Points type posting when embed list is None."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        # Mock channel.send
        mock_message = MagicMock()
        mock_message.id = 11111
        channel.send = AsyncMock(return_value=mock_message)
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_leaderboard_embed_list', return_value=None) as mock_get_embed_list, \
             patch('ui.menus.save_message') as mock_save_message:
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify category was fetched
            mock_get_category.assert_called_once_with(1)
            
            # Verify embed list was generated
            mock_get_embed_list.assert_called_once_with(1, 8, interaction.client)
            
            # Verify no points message was sent
            expected_text = "No points scored yet for category Test Category. This is likely due to no completed races."
            channel.send.assert_called_once_with(expected_text)
            
            # Verify message was saved to DB
            mock_save_message.assert_called_once_with(interaction.guild_id, channel.id, 11111, category_id=1)

    @pytest.mark.asyncio
    async def test_per_page_setting(self):
        """Test that per_page is correctly set to 8."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_leaderboard_embed_list') as mock_get_embed_list, \
             patch('ui.menus.save_message') as mock_save_message:
            
            mock_get_embed_list.return_value = []
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify embed list was generated with per_page=8
            mock_get_embed_list.assert_called_once_with(1, 8, interaction.client)

    @pytest.mark.asyncio
    async def test_different_leaderboard_types(self):
        """Test handling of different leaderboard types."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        
        # Test RecentRace type
        recent_category = create_mock_category(
            category_id=1, 
            name="Recent Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        
        with patch('ui.menus.get_category', return_value=recent_category) as mock_get_category, \
             patch('ui.menus.get_most_recent_race', return_value=None) as mock_get_recent_race, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_race_leaderboard, \
             patch('ui.menus.get_category_leaderboard_embed_list') as mock_get_embed_list, \
             patch('ui.menus.send_message') as mock_send_message:
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Should call get_most_recent_race for RecentRace type
            mock_get_recent_race.assert_called_once_with(1)
            mock_get_embed_list.assert_not_called()
        
        # Test Points type
        points_category = create_mock_category(
            category_id=2, 
            name="Points Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        with patch('ui.menus.get_category', return_value=points_category) as mock_get_category, \
             patch('ui.menus.get_most_recent_race') as mock_get_recent_race, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_race_leaderboard, \
             patch('ui.menus.get_category_leaderboard_embed_list', return_value=[]) as mock_get_embed_list, \
             patch('ui.menus.save_message') as mock_save_message:
            
            mock_message = MagicMock()
            mock_message.id = 11111
            channel.send = AsyncMock(return_value=mock_message)
            
            await post_channel_category_leaderboard(interaction, channel, 2, interaction.client)
            
            # Should call get_category_leaderboard_embed_list for Points type
            mock_get_embed_list.assert_called_once_with(2, 8, interaction.client)
            mock_get_recent_race.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_saving_parameters(self):
        """Test that messages are saved with correct parameters."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.Points
        )
        
        # Mock channel.send
        mock_message1 = MagicMock()
        mock_message1.id = 11111
        mock_message2 = MagicMock()
        mock_message2.id = 22222
        channel.send = AsyncMock(side_effect=[mock_message1, mock_message2])
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_category_leaderboard_embed_list') as mock_get_embed_list, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock embed list
            mock_embed1 = MagicMock()
            mock_embed2 = MagicMock()
            mock_embed_list = [mock_embed1, mock_embed2]
            mock_get_embed_list.return_value = mock_embed_list
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify messages were saved with correct parameters
            assert mock_save_message.call_count == 2
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 11111, category_id=1)
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 22222, category_id=1)

    @pytest.mark.asyncio
    async def test_recent_race_save_as_category_message_flag(self):
        """Test that RecentRace type uses save_as_category_message=True flag."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        category = create_mock_category(
            category_id=1, 
            name="Test Category", 
            leaderboard_type=RaceLeaderboardType.RecentRace
        )
        race = create_mock_race(race_id=1, state=RaceState.Completed, category_id=category)
        
        with patch('ui.menus.get_category', return_value=category) as mock_get_category, \
             patch('ui.menus.get_most_recent_race', return_value=race) as mock_get_recent_race, \
             patch('ui.menus.post_channel_race_leaderboard') as mock_post_race_leaderboard, \
             patch('ui.menus.get_emoji_list') as mock_get_emojis:
            
            mock_get_emojis.return_value = ["🏆", "🥇", "🥈", "🥉"]
            
            await post_channel_category_leaderboard(interaction, channel, 1, interaction.client)
            
            # Verify post_channel_race_leaderboard was called with save_as_category_message=True
            mock_post_race_leaderboard.assert_called_once()
            call_args = mock_post_race_leaderboard.call_args
            assert call_args[1]['save_as_category_message'] == True
