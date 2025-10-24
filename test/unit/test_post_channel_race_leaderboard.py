# -*- coding: utf-8 -*-
"""
Unit tests for post_channel_race_leaderboard() function in ui/menus.py.
Tests the channel race leaderboard posting functionality including multi-page posting and message saving.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import nextcord
import math

# Mock the menus module since it's not available in the current nextcord version
import sys
from unittest.mock import MagicMock

# Create a mock menus module
mock_menus = MagicMock()
mock_menus.ButtonMenu = MagicMock
sys.modules['nextcord.ext.menus'] = mock_menus

from ui.menus import post_channel_race_leaderboard
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, create_mock_submission
from db.db_util import RaceState, RaceLeaderboardType, RaceMessageType


@pytest.mark.unit
class TestPostChannelRaceLeaderboard:
    """Tests for post_channel_race_leaderboard() function in ui/menus.py"""

    @pytest.mark.asyncio
    async def test_empty_submissions_case(self):
        """Test handling when there are no submissions."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=[]) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock channel.send
            mock_message = MagicMock()
            mock_message.id = 11111
            channel.send = AsyncMock(return_value=mock_message)
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=False)
            
            # Verify submissions were fetched
            mock_get_submissions.assert_called_once_with(1)
            
            # Verify title and description were generated
            mock_get_title.assert_called_once_with(1)
            mock_get_description.assert_called_once_with(1)
            
            # Verify race was fetched
            mock_get_race.assert_called_once_with(1)
            
            # Verify message was sent with correct text
            expected_text = "**Test Race Leaderboard**\n\nTest race description\n\nNo submissions yet"
            channel.send.assert_called_once_with(expected_text)
            
            # Verify message was saved to DB
            mock_save_message.assert_called_once_with(interaction.guild_id, channel.id, 11111, race_id=1)

    @pytest.mark.asyncio
    async def test_empty_submissions_save_as_category_message(self):
        """Test empty submissions case with save_as_category_message flag."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=[]) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock channel.send
            mock_message = MagicMock()
            mock_message.id = 11111
            channel.send = AsyncMock(return_value=mock_message)
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=True)
            
            # Verify message was sent
            expected_text = "**Test Race Leaderboard**\n\nTest race description\n\nNo submissions yet"
            channel.send.assert_called_once_with(expected_text)
            
            # Verify message was saved as category message
            mock_save_message.assert_called_once_with(interaction.guild_id, channel.id, 11111, category_id=race.category_id.id)

    @pytest.mark.asyncio
    async def test_multi_page_leaderboard_posting(self):
        """Test multi-page leaderboard posting with multiple submissions."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Create 25 submissions (3 pages with per_page=10)
        submissions = [
            create_mock_submission(submission_id=i, race_id=1, user_id=100+i, finish_time=f"1:{20+i:02d}:30")
            for i in range(1, 26)
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_embed') as mock_get_embed, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock channel.send
            mock_message1 = MagicMock()
            mock_message1.id = 11111
            mock_message2 = MagicMock()
            mock_message2.id = 22222
            mock_message3 = MagicMock()
            mock_message3.id = 33333
            channel.send = AsyncMock(side_effect=[mock_message1, mock_message2, mock_message3])
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            # Mock embed creation
            mock_embed1 = MagicMock()
            mock_embed2 = MagicMock()
            mock_embed3 = MagicMock()
            mock_get_embed.side_effect = [mock_embed1, mock_embed2, mock_embed3]
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=False)
            
            # Verify submissions were fetched
            mock_get_submissions.assert_called_once_with(1)
            
            # Verify title and description were generated
            mock_get_title.assert_called_once_with(1)
            mock_get_description.assert_called_once_with(1)
            
            # Verify race was fetched
            mock_get_race.assert_called_once_with(1)
            
            # Verify 3 pages were created (25 submissions / 10 per page = 3 pages)
            assert mock_get_embed.call_count == 3
            
            # Verify each page was called with correct parameters
            expected_calls = [
                (("Test Race Leaderboard", "Test race description", submissions[0:10], 0, 10, interaction.client),),
                (("Test Race Leaderboard", "Test race description", submissions[10:20], 1, 10, interaction.client),),
                (("Test Race Leaderboard", "Test race description", submissions[20:25], 2, 10, interaction.client),)
            ]
            
            for i, call in enumerate(mock_get_embed.call_args_list):
                assert call[0] == expected_calls[i][0]
            
            # Verify 3 messages were sent
            assert channel.send.call_count == 3
            channel.send.assert_any_call(embed=mock_embed1)
            channel.send.assert_any_call(embed=mock_embed2)
            channel.send.assert_any_call(embed=mock_embed3)
            
            # Verify all messages were saved to DB
            assert mock_save_message.call_count == 3
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 11111, race_id=1)
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 22222, race_id=1)
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 33333, race_id=1)

    @pytest.mark.asyncio
    async def test_single_page_leaderboard_posting(self):
        """Test single page leaderboard posting with few submissions."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Create 5 submissions (1 page with per_page=10)
        submissions = [
            create_mock_submission(submission_id=i, race_id=1, user_id=100+i, finish_time=f"1:{20+i:02d}:30")
            for i in range(1, 6)
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_embed') as mock_get_embed, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock channel.send
            mock_message = MagicMock()
            mock_message.id = 11111
            channel.send = AsyncMock(return_value=mock_message)
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            # Mock embed creation
            mock_embed = MagicMock()
            mock_get_embed.return_value = mock_embed
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=False)
            
            # Verify 1 page was created
            mock_get_embed.assert_called_once_with("Test Race Leaderboard", "Test race description", submissions, 0, 10, interaction.client)
            
            # Verify 1 message was sent
            channel.send.assert_called_once_with(embed=mock_embed)
            
            # Verify message was saved to DB
            mock_save_message.assert_called_once_with(interaction.guild_id, channel.id, 11111, race_id=1)

    @pytest.mark.asyncio
    async def test_save_as_category_message_flag(self):
        """Test save_as_category_message flag for multi-page posting."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Create 15 submissions (2 pages with per_page=10)
        submissions = [
            create_mock_submission(submission_id=i, race_id=1, user_id=100+i, finish_time=f"1:{20+i:02d}:30")
            for i in range(1, 16)
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_embed') as mock_get_embed, \
             patch('ui.menus.save_message') as mock_save_message, \
             patch('ui.menus.logging') as mock_logging:
            
            # Mock channel.send
            mock_message1 = MagicMock()
            mock_message1.id = 11111
            mock_message2 = MagicMock()
            mock_message2.id = 22222
            channel.send = AsyncMock(side_effect=[mock_message1, mock_message2])
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            # Mock embed creation
            mock_embed1 = MagicMock()
            mock_embed2 = MagicMock()
            mock_get_embed.side_effect = [mock_embed1, mock_embed2]
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=True)
            
            # Verify 2 pages were created
            assert mock_get_embed.call_count == 2
            
            # Verify 2 messages were sent
            assert channel.send.call_count == 2
            
            # Verify all messages were saved as category messages
            assert mock_save_message.call_count == 2
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 11111, category_id=race.category_id.id)
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 22222, category_id=race.category_id.id)
            
            # Verify logging was called
            assert mock_logging.info.call_count == 2
            mock_logging.info.assert_any_call("Saving race leaderboard 1 as a category message")

    @pytest.mark.asyncio
    async def test_message_saving_to_db(self):
        """Test that messages are properly saved to the database."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Create 12 submissions (2 pages with per_page=10)
        submissions = [
            create_mock_submission(submission_id=i, race_id=1, user_id=100+i, finish_time=f"1:{20+i:02d}:30")
            for i in range(1, 13)
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_embed') as mock_get_embed, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock channel.send
            mock_message1 = MagicMock()
            mock_message1.id = 11111
            mock_message2 = MagicMock()
            mock_message2.id = 22222
            channel.send = AsyncMock(side_effect=[mock_message1, mock_message2])
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            # Mock embed creation
            mock_embed1 = MagicMock()
            mock_embed2 = MagicMock()
            mock_get_embed.side_effect = [mock_embed1, mock_embed2]
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=False)
            
            # Verify messages were saved with correct parameters
            assert mock_save_message.call_count == 2
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 11111, race_id=1)
            mock_save_message.assert_any_call(interaction.guild_id, channel.id, 22222, race_id=1)

    @pytest.mark.asyncio
    async def test_per_page_calculation(self):
        """Test that per_page is correctly set to 10."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Create 25 submissions to test pagination
        submissions = [
            create_mock_submission(submission_id=i, race_id=1, user_id=100+i, finish_time=f"1:{20+i:02d}:30")
            for i in range(1, 26)
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_embed') as mock_get_embed, \
             patch('ui.menus.save_message') as mock_save_message:
            
            # Mock channel.send
            mock_messages = [MagicMock(id=10000+i) for i in range(3)]
            channel.send = AsyncMock(side_effect=mock_messages)
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            # Mock embed creation
            mock_embeds = [MagicMock() for _ in range(3)]
            mock_get_embed.side_effect = mock_embeds
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=False)
            
            # Verify 3 pages were created (25 submissions / 10 per page = 3 pages)
            assert mock_get_embed.call_count == 3
            
            # Verify each page was called with per_page=10
            for call in mock_get_embed.call_args_list:
                assert call[0][4] == 10  # per_page parameter

    @pytest.mark.asyncio
    async def test_race_id_from_submissions(self):
        """Test that race_id is correctly extracted from submissions."""
        interaction = create_mock_interaction()
        channel = create_mock_text_channel(channel_id=12345, name="leaderboard-channel")
        race = create_mock_race(race_id=1, state=RaceState.Active)
        
        # Create submissions with specific race_id
        submissions = [
            create_mock_submission(submission_id=i, race_id=999, user_id=100+i, finish_time=f"1:{20+i:02d}:30")
            for i in range(1, 6)
        ]
        
        with patch('ui.menus.get_sorted_race_submissions', return_value=submissions) as mock_get_submissions, \
             patch('ui.menus.get_race_leaderboard_title') as mock_get_title, \
             patch('ui.menus.get_race_leaderboard_description') as mock_get_description, \
             patch('ui.menus.get_race', return_value=race) as mock_get_race, \
             patch('ui.menus.get_race_leaderboard_embed') as mock_get_embed, \
             patch('ui.menus.save_message') as mock_save_message, \
             patch('ui.menus.logging') as mock_logging:
            
            # Mock channel.send
            mock_message = MagicMock()
            mock_message.id = 11111
            channel.send = AsyncMock(return_value=mock_message)
            
            mock_get_title.return_value = "Test Race Leaderboard"
            mock_get_description.return_value = "Test race description"
            
            # Mock embed creation
            mock_embed = MagicMock()
            mock_get_embed.return_value = mock_embed
            
            await post_channel_race_leaderboard(interaction, channel, 1, interaction.client, ["🏆", "🥇"], save_as_category_message=False)
            
            # Verify logging shows the race_id from submissions (999), not the parameter (1)
            mock_logging.info.assert_called_with("Saving race leaderboard 999 as a race message")
