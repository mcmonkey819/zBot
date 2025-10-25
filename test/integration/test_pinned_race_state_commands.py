# -*- coding: utf-8 -*-
"""
Integration tests for pinned race state commands (shutdown/startup).
Tests the complete workflow with mocked Discord interactions and database operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# Mock the menus import before importing AsyncRaces
import sys
import test.mock_menus
sys.modules['nextcord.ext.menus'] = test.mock_menus.menus
from cogs.async_races import AsyncRaces
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_guild, create_mock_text_channel
from test.test_utils.db_fixtures import create_mock_race, create_mock_category
from db.db_util import PinType, RaceMessageType


@pytest.mark.integration
class TestShutdownCommand:
    """Tests for the shutdown command with pinned state saving"""

    @pytest.fixture
    def async_races_cog(self):
        """Create AsyncRaces cog instance for testing."""
        bot = Mock()
        return AsyncRaces(bot)

    @pytest.mark.asyncio
    @patch('cogs.async_races.get_server_messages')
    @patch('cogs.async_races.delete_message')
    @patch('cogs.async_races.send_message')
    @patch('cogs.async_races.AsyncRaces.save_pinned_race_states')
    async def test_shutdown_saves_pinned_states(self, mock_save_states, mock_send_message, 
                                                mock_delete_message, mock_get_messages, 
                                                async_races_cog):
        """Test that shutdown command saves pinned states before cleanup."""
        # Setup
        interaction = create_mock_interaction()
        mock_messages = [Mock(), Mock()]
        mock_get_messages.return_value = mock_messages
        
        # Test
        await async_races_cog.shutdown(interaction)
        
        # Verify
        mock_save_states.assert_called_once_with(interaction)
        mock_get_messages.assert_called_once_with(interaction.guild_id)
        assert mock_delete_message.call_count == 2
        mock_send_message.assert_called_once_with(interaction, "Done!", ephemeral=True)

    @pytest.mark.asyncio
    @patch('cogs.async_races.get_server_messages')
    @patch('cogs.async_races.AsyncRaceMessage')
    @patch('db.db_util.save_pinned_race_state')
    @patch('db.db_util.clear_pinned_race_states')
    async def test_save_pinned_race_states_individual_pins(self, mock_clear, mock_save_state,
                                                          mock_message_class, mock_get_messages,
                                                          async_races_cog):
        """Test saving individual race pins during shutdown."""
        # Setup
        interaction = create_mock_interaction()
        
        # Create mock messages - one individual race pin, one category pin, one other message
        mock_race_message = Mock()
        mock_race_message.message_type = RaceMessageType.RaceInfo
        mock_race_message.race_id = 123
        mock_race_message.category_id = None
        mock_race_message.channel_id = 999
        
        mock_category_message = Mock()
        mock_category_message.message_type = RaceMessageType.RaceInfo
        mock_category_message.race_id = None
        mock_category_message.category_id = 456
        mock_category_message.channel_id = 888
        
        mock_other_message = Mock()
        mock_other_message.message_type = RaceMessageType.Leaderboard
        mock_other_message.race_id = 789
        mock_other_message.category_id = None
        mock_other_message.channel_id = 777
        
        mock_get_messages.return_value = [mock_race_message, mock_category_message, mock_other_message]
        
        # Test
        await async_races_cog.save_pinned_race_states(interaction)
        
        # Verify
        mock_clear.assert_called_once_with(interaction.guild_id)
        assert mock_save_state.call_count == 2
        
        # Check individual race pin save
        individual_call = mock_save_state.call_args_list[0]
        assert individual_call[1]['server_id'] == interaction.guild_id
        assert individual_call[1]['race_id'] == 123
        assert individual_call[1]['category_id'] is None
        assert individual_call[1]['channel_id'] == 999
        assert individual_call[1]['pin_type'] == PinType.Individual
        
        # Check category pin save
        category_call = mock_save_state.call_args_list[1]
        assert category_call[1]['server_id'] == interaction.guild_id
        assert category_call[1]['race_id'] is None
        assert category_call[1]['category_id'] == 456
        assert category_call[1]['channel_id'] == 888
        assert category_call[1]['pin_type'] == PinType.Category

    @pytest.mark.asyncio
    @patch('cogs.async_races.get_server_messages')
    @patch('db.db_util.save_pinned_race_state')
    @patch('db.db_util.clear_pinned_race_states')
    async def test_save_pinned_race_states_no_pins(self, mock_clear, mock_save_state,
                                                   mock_get_messages, async_races_cog):
        """Test saving when no pinned states exist."""
        # Setup
        interaction = create_mock_interaction()
        mock_get_messages.return_value = []  # No messages
        
        # Test
        await async_races_cog.save_pinned_race_states(interaction)
        
        # Verify
        mock_clear.assert_called_once_with(interaction.guild_id)
        mock_save_state.assert_not_called()


@pytest.mark.integration
class TestStartupCommand:
    """Tests for the startup command with pinned state restoration"""

    @pytest.fixture
    def async_races_cog(self):
        """Create AsyncRaces cog instance for testing."""
        bot = Mock()
        return AsyncRaces(bot)

    @pytest.mark.asyncio
    @patch('cogs.async_races.send_moderator_menu')
    @patch('cogs.async_races.send_racer_menu')
    @patch('cogs.async_races.save_message')
    @patch('cogs.async_races.send_message')
    @patch('cogs.async_races.AsyncRaces.restore_pinned_race_states')
    async def test_startup_restores_pinned_states(self, mock_restore, mock_send_message, 
                                                  mock_save_message, mock_send_racer, 
                                                  mock_send_mod, async_races_cog):
        """Test that startup command restores pinned states after creating menus."""
        # Setup
        interaction = create_mock_interaction()
        mod_channel = create_mock_text_channel(channel_id=111)
        racer_channel = create_mock_text_channel(channel_id=222)
        
        mock_mod_message = Mock()
        mock_mod_message.id = 333
        mock_send_mod.return_value = mock_mod_message
        
        mock_racer_message = Mock()
        mock_racer_message.id = 444
        mock_send_racer.return_value = mock_racer_message
        
        # Mock server exists and user is admin
        with patch('cogs.async_races.AsyncRaces.get_server', return_value=Mock()), \
             patch('cogs.async_races.user_is_admin', return_value=True):
            
            # Test
            await async_races_cog.startup(interaction, mod_channel, racer_channel)
        
        # Verify
        mock_send_mod.assert_called_once_with(interaction, mod_channel)
        mock_send_racer.assert_called_once_with(interaction, racer_channel)
        assert mock_save_message.call_count == 2
        mock_restore.assert_called_once_with(interaction)
        mock_send_message.assert_called_once_with(interaction, "Done!", ephemeral=True)

    @pytest.mark.asyncio
    @patch('ui.ui_util.restore_pinned_race_states', new_callable=AsyncMock)
    async def test_restore_pinned_race_states_calls_ui_function(self, mock_restore_ui, 
                                                               async_races_cog):
        """Test that the cog method calls the UI function."""
        # Setup
        interaction = create_mock_interaction()
        
        # Test
        await async_races_cog.restore_pinned_race_states(interaction)
        
        # Verify
        mock_restore_ui.assert_called_once_with(interaction.guild_id, interaction)


@pytest.mark.integration
class TestPinnedRaceStateWorkflow:
    """Tests for the complete pinned race state workflow"""

    @pytest.fixture
    def async_races_cog(self):
        """Create AsyncRaces cog instance for testing."""
        bot = Mock()
        return AsyncRaces(bot)

    @pytest.mark.asyncio
    @patch('cogs.async_races.get_server_messages')
    @patch('db.db_util.save_pinned_race_state')
    @patch('db.db_util.clear_pinned_race_states')
    @patch('db.db_util.get_pinned_race_states')
    @patch('db.db_util.get_race')
    @patch('ui.menus.pin_race_info', new_callable=AsyncMock)
    @patch('ui.ui_util.send_startup_restoration_summary', new_callable=AsyncMock)
    async def test_complete_workflow_individual_race(self, mock_summary, mock_pin_race,
                                                     mock_get_race, mock_get_states,
                                                     mock_clear, mock_save_state,
                                                     mock_get_messages, async_races_cog):
        """Test complete workflow: save during shutdown, restore during startup."""
        # Setup
        interaction = create_mock_interaction()
        mock_race = create_mock_race(race_id=123)
        mock_channel = create_mock_text_channel(channel_id=999)
        
        # Mock shutdown: save pinned state
        mock_race_message = Mock()
        mock_race_message.message_type = RaceMessageType.RaceInfo
        mock_race_message.race_id = 123
        mock_race_message.category_id = None
        mock_race_message.channel_id = 999
        mock_get_messages.return_value = [mock_race_message]
        
        # Mock startup: restore pinned state
        mock_pinned_state = Mock()
        mock_pinned_state.race_id = 123
        mock_pinned_state.category_id = None
        mock_pinned_state.channel_id = 999
        mock_pinned_state.pin_type = PinType.Individual
        mock_pinned_state.id = 1
        mock_get_states.return_value = [mock_pinned_state]
        mock_get_race.return_value = mock_race
        interaction.guild.get_channel.return_value = mock_channel
        
        # Test shutdown
        await async_races_cog.save_pinned_race_states(interaction)
        
        # Verify shutdown
        mock_clear.assert_called_once_with(interaction.guild_id)
        mock_save_state.assert_called_once_with(
            server_id=interaction.guild_id,
            race_id=123,
            category_id=None,
            channel_id=999,
            pin_type=PinType.Individual
        )
        
        # Reset mocks for startup
        mock_clear.reset_mock()
        mock_save_state.reset_mock()
        
        # Test startup restoration
        with patch('ui.ui_util.restore_pinned_race_states') as mock_restore_ui:
            await async_races_cog.restore_pinned_race_states(interaction)
            mock_restore_ui.assert_called_once_with(interaction.guild_id, interaction)

    @pytest.mark.asyncio
    @patch('cogs.async_races.get_server_messages')
    @patch('db.db_util.save_pinned_race_state')
    @patch('db.db_util.clear_pinned_race_states')
    async def test_workflow_no_pinned_states(self, mock_clear, mock_save_state, 
                                             mock_get_messages, async_races_cog):
        """Test workflow when no pinned states exist."""
        # Setup
        interaction = create_mock_interaction()
        mock_get_messages.return_value = []  # No pinned messages
        
        # Test
        await async_races_cog.save_pinned_race_states(interaction)
        
        # Verify
        mock_clear.assert_called_once_with(interaction.guild_id)
        mock_save_state.assert_not_called()

    @pytest.mark.asyncio
    @patch('cogs.async_races.get_server_messages')
    @patch('db.db_util.save_pinned_race_state')
    @patch('db.db_util.clear_pinned_race_states')
    async def test_workflow_mixed_message_types(self, mock_clear, mock_save_state,
                                               mock_get_messages, async_races_cog):
        """Test workflow with mixed message types (only RaceInfo should be saved)."""
        # Setup
        interaction = create_mock_interaction()
        
        # Create various message types
        mock_race_info = Mock()
        mock_race_info.message_type = RaceMessageType.RaceInfo
        mock_race_info.race_id = 123
        mock_race_info.category_id = None
        mock_race_info.channel_id = 999
        
        mock_leaderboard = Mock()
        mock_leaderboard.message_type = RaceMessageType.Leaderboard
        mock_leaderboard.race_id = 456
        mock_leaderboard.category_id = None
        mock_leaderboard.channel_id = 888
        
        mock_menu = Mock()
        mock_menu.message_type = RaceMessageType.Menu
        mock_menu.race_id = None
        mock_menu.category_id = None
        mock_menu.channel_id = 777
        
        mock_get_messages.return_value = [mock_race_info, mock_leaderboard, mock_menu]
        
        # Test
        await async_races_cog.save_pinned_race_states(interaction)
        
        # Verify - only RaceInfo message should be saved
        mock_clear.assert_called_once_with(interaction.guild_id)
        mock_save_state.assert_called_once_with(
            server_id=interaction.guild_id,
            race_id=123,
            category_id=None,
            channel_id=999,
            pin_type=PinType.Individual
        )
