# -*- coding: utf-8 -*-
"""
Integration tests for race state transition logic.
Tests complex state change workflows from ui/menus.py with mocked dependencies.

Note: These tests import and execute race_change_state() directly, which requires
heavy mocking of database and UI functions. We mock nextcord.ext.menus to avoid import errors.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Mock nextcord.ext.menus before importing ui.menus to avoid import errors
sys.modules['nextcord.ext.menus'] = MagicMock()

from test.test_utils.discord_mocks import create_mock_interaction, create_mock_guild
from test.test_utils.db_fixtures import create_mock_race, create_mock_category, RaceState, PointsType

# Now we can import the functions
from ui.menus import race_change_state, handle_activate_race


@pytest.fixture
def sample_interaction():
    """Create a sample interaction for testing"""
    interaction = create_mock_interaction()
    # Make guild.get_role a proper mock
    interaction.guild.get_role = MagicMock()
    return interaction


@pytest.fixture
def sample_race():
    """Create a sample race for testing"""
    category = create_mock_category()
    return create_mock_race(race_id=1, category_id=category, state=RaceState.Inactive)


@pytest.mark.integration
@pytest.mark.asyncio
class TestRaceChangeState:
    """Tests for race_change_state() function in ui/menus.py"""

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.handle_activate_race', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_inactive_to_active_valid(self, mock_has_subs, mock_handle_activate, mock_send_message):
        """Test valid transition from Inactive to Active."""
        # Setup
        category = create_mock_category(points_type=PointsType.NoScoring)
        race = create_mock_race(race_id=1, category_id=category, state=RaceState.Inactive)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = False
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Active)
        
        # Verify
        assert race.state == RaceState.Active
        race.save.assert_called_once()
        mock_handle_activate.assert_called_once_with(interaction, race)
        mock_send_message.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_active_to_inactive_invalid_with_submissions(self, mock_has_subs, mock_send_message):
        """Test invalid transition from Active to Inactive when submissions exist."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=2, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = True  # Has submissions
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Inactive)
        
        # Verify state did NOT change
        assert race.state == RaceState.Active  # Still active
        race.save.assert_not_called()
        # Should send error message
        mock_send_message.assert_called_once()
        assert "Cannot change state to Inactive" in mock_send_message.call_args[0][1]

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_active_to_inactive_valid_no_submissions(self, mock_has_subs, mock_send_message):
        """Test valid transition from Active to Inactive when no submissions."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=3, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = False  # No submissions
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Inactive)
        
        # Verify
        assert race.state == RaceState.Inactive
        race.save.assert_called_once()
        # Should send success message
        assert "state changed to" in mock_send_message.call_args[0][1]

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.update_race_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.update_category_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.score_race')
    @patch('ui.menus.get_assigned_racers')
    @patch('ui.menus.race_has_submissions')
    async def test_active_to_completed_valid(self, mock_has_subs, mock_get_assigned, mock_score_race, 
                                             mock_update_cat, mock_update_race, mock_send_message):
        """Test valid transition from Active to Completed."""
        # Setup
        category = create_mock_category(points_type=PointsType.MarioKart)
        race = create_mock_race(race_id=4, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = True
        mock_get_assigned.return_value = []  # No assigned racers
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Completed)
        
        # Verify
        assert race.state == RaceState.Completed
        race.save.assert_called_once()
        mock_score_race.assert_called_once_with(race)
        mock_update_cat.assert_called_once_with(interaction, race)
        mock_update_race.assert_called_once_with(interaction, race)

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_completed_to_active_invalid_with_scoring(self, mock_has_subs, mock_send_message):
        """Test invalid transition from Completed to Active when category has scoring."""
        # Setup
        category = create_mock_category(points_type=PointsType.MarioKart)
        race = create_mock_race(race_id=5, category_id=category, state=RaceState.Completed)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Active)
        
        # Verify state did NOT change
        assert race.state == RaceState.Completed
        race.save.assert_not_called()
        # Should send error message
        mock_send_message.assert_called_once()
        assert "already been scored" in mock_send_message.call_args[0][1]

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.handle_activate_race', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_completed_to_active_valid_no_scoring(self, mock_has_subs, mock_handle_activate, mock_send_message):
        """Test valid transition from Completed to Active when category has no scoring."""
        # Setup
        category = create_mock_category(points_type=PointsType.NoScoring)
        race = create_mock_race(race_id=6, category_id=category, state=RaceState.Completed)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Active)
        
        # Verify state DID change
        assert race.state == RaceState.Active
        race.save.assert_called_once()
        mock_handle_activate.assert_called_once_with(interaction, race)

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_completed_to_inactive_invalid(self, mock_has_subs, mock_send_message):
        """Test invalid transition from Completed to Inactive (has submissions)."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=7, category_id=category, state=RaceState.Completed)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = True  # Completed races have submissions
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Inactive)
        
        # Verify
        assert race.state == RaceState.Completed  # Did not change
        race.save.assert_not_called()
        mock_send_message.assert_called_once()
        assert "Cannot change state to Inactive" in mock_send_message.call_args[0][1]

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.zConfirmMenu')
    @patch('ui.menus.race_has_submissions')
    async def test_to_completed_no_subs_confirms_inactive(self, mock_has_subs, mock_confirm_menu, mock_send_message):
        """Test changing to Completed with no submissions prompts to use Inactive instead."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=8, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = False  # No submissions
        
        # Mock confirmation menu to return True (user confirms to use Inactive)
        mock_menu_instance = AsyncMock()
        mock_menu_instance.prompt.return_value = True
        mock_confirm_menu.return_value = mock_menu_instance
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Completed)
        
        # Verify state changed to Inactive instead
        assert race.state == RaceState.Inactive
        race.save.assert_called_once()
        mock_confirm_menu.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.update_race_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.update_category_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.score_race')
    @patch('ui.menus.zConfirmMenu')
    @patch('ui.menus.race_has_submissions')
    async def test_to_completed_no_subs_user_rejects_confirmation(self, mock_has_subs, mock_confirm_menu,
                                                                  mock_score, mock_update_cat, mock_update_race,
                                                                  mock_send_message):
        """Test changing to Completed with no subs when user rejects Inactive suggestion."""
        # Setup
        category = create_mock_category(points_type=PointsType.ParTime)
        race = create_mock_race(race_id=9, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = False
        
        # Mock confirmation to return False (user wants Completed anyway)
        mock_menu_instance = AsyncMock()
        mock_menu_instance.prompt.return_value = False
        mock_confirm_menu.return_value = mock_menu_instance
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Completed)
        
        # Verify state changed to Completed (user's original choice)
        assert race.state == RaceState.Completed
        race.save.assert_called_once()
        mock_score.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.get_race_submission')
    @patch('ui.menus.get_assigned_racers')
    @patch('ui.menus.race_has_submissions')
    async def test_to_completed_not_all_assigned_submitted_cancelled(self, mock_has_subs, mock_get_assigned,
                                                                      mock_get_submission, mock_send_message):
        """Test completing race with assigned racers missing, user cancels."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=10, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = True
        
        # Create mock assigned racers
        racer1 = Mock()
        racer1.user_id = 111
        racer2 = Mock()
        racer2.user_id = 222
        mock_get_assigned.return_value = [racer1, racer2]
        
        # Only racer1 has submitted
        def get_submission_side_effect(user_id, race_id):
            if user_id == 111:
                return Mock()  # Has submission
            return None  # No submission
        
        mock_get_submission.side_effect = get_submission_side_effect
        
        # Mock confirmation menu - user cancels
        with patch('ui.menus.zConfirmMenu') as mock_confirm_menu:
            mock_menu_instance = AsyncMock()
            mock_menu_instance.prompt.return_value = False  # User cancels
            mock_confirm_menu.return_value = mock_menu_instance
            
            # Execute
            await race_change_state(interaction, race, new_state=RaceState.Completed)
        
        # Verify state did NOT change
        assert race.state == RaceState.Active
        race.save.assert_not_called()
        # Should send cancelled message
        assert "Cancelled" in mock_send_message.call_args[0][1]

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.update_race_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.update_category_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.score_race')
    @patch('ui.menus.get_race_submission')
    @patch('ui.menus.get_assigned_racers')
    @patch('ui.menus.race_has_submissions')
    async def test_to_completed_not_all_assigned_submitted_confirmed(self, mock_has_subs, mock_get_assigned,
                                                                      mock_get_submission, mock_score,
                                                                      mock_update_cat, mock_update_race,
                                                                      mock_send_message):
        """Test completing race with assigned racers missing, user confirms."""
        # Setup
        category = create_mock_category(points_type=PointsType.ParTime)
        race = create_mock_race(race_id=11, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = True
        
        # Create mock assigned racers  
        racer1 = Mock()
        racer1.user_id = 111
        racer2 = Mock()
        racer2.user_id = 222
        mock_get_assigned.return_value = [racer1, racer2]
        
        # Only racer1 has submitted
        def get_submission_side_effect(user_id, race_id):
            if user_id == 111:
                return Mock()
            return None
        
        mock_get_submission.side_effect = get_submission_side_effect
        
        # Mock confirmation menu - user confirms
        with patch('ui.menus.zConfirmMenu') as mock_confirm_menu:
            mock_menu_instance = AsyncMock()
            mock_menu_instance.prompt.return_value = True  # User confirms
            mock_confirm_menu.return_value = mock_menu_instance
            
            # Execute
            await race_change_state(interaction, race, new_state=RaceState.Completed)
        
        # Verify state DID change
        assert race.state == RaceState.Completed
        race.save.assert_called_once()
        mock_score.assert_called_once_with(race)
        mock_update_cat.assert_called_once()
        mock_update_race.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.update_race_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.update_category_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.score_race')
    @patch('ui.menus.get_assigned_racers')
    @patch('ui.menus.race_has_submissions')
    async def test_to_completed_all_assigned_submitted(self, mock_has_subs, mock_get_assigned, mock_score,
                                                       mock_update_cat, mock_update_race, mock_send_message):
        """Test completing race when all assigned racers have submitted."""
        # Setup
        category = create_mock_category(points_type=PointsType.MarioKart)
        race = create_mock_race(race_id=12, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = True
        
        # Create mock assigned racers who all submitted
        racer1 = Mock()
        racer1.user_id = 111
        racer2 = Mock()
        racer2.user_id = 222
        mock_get_assigned.return_value = [racer1, racer2]
        
        # Mock both racers have submitted
        with patch('ui.menus.get_race_submission') as mock_get_submission:
            mock_get_submission.return_value = Mock()  # Always returns submission
            
            # Execute
            await race_change_state(interaction, race, new_state=RaceState.Completed)
        
        # Verify state changed without confirmation prompt
        assert race.state == RaceState.Completed
        race.save.assert_called_once()
        mock_score.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_inactive_to_completed_with_confirmation(self, mock_has_subs, mock_send_message):
        """Test transition from Inactive to Completed with no submissions."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=13, category_id=category, state=RaceState.Inactive)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = False
        
        # Pre-confirmed (user already said yes to using Inactive)
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Completed, confirmed=True)
        
        # Verify it changed to Inactive instead (per confirmation logic)
        assert race.state == RaceState.Inactive
        race.save.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.handle_activate_race', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_inactive_to_active_with_submissions(self, mock_has_subs, mock_handle_activate, mock_send_message):
        """Test Inactive to Active even with submissions (valid transition)."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=14, category_id=category, state=RaceState.Inactive)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        # Note: Inactive → Active doesn't check for submissions
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Active)
        
        # Verify
        assert race.state == RaceState.Active
        race.save.assert_called_once()
        mock_handle_activate.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_same_state_transition(self, mock_has_subs, mock_send_message):
        """Test 'changing' to the same state (Active → Active)."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=15, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        
        # Execute - change to same state
        await race_change_state(interaction, race, new_state=RaceState.Active)
        
        # Verify - should still save and trigger actions
        assert race.state == RaceState.Active
        race.save.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    async def test_state_transition_saves_race(self, mock_has_subs, mock_send_message):
        """Test that race.save() is called for valid state transitions."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=16, category_id=category, state=RaceState.Inactive)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = False
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Active)
        
        # Verify
        race.save.assert_called_once()

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.update_race_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.update_category_leaderboard', new_callable=AsyncMock)
    @patch('ui.menus.score_race')
    @patch('ui.menus.get_assigned_racers')
    @patch('ui.menus.race_has_submissions')
    async def test_to_completed_sends_success_message(self, mock_has_subs, mock_get_assigned, mock_score,
                                                      mock_update_cat, mock_update_race, mock_send_message):
        """Test that success message is sent after state change."""
        # Setup
        category = create_mock_category()
        race = create_mock_race(race_id=17, category_id=category, state=RaceState.Active)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        mock_has_subs.return_value = True
        mock_get_assigned.return_value = []
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Completed)
        
        # Verify success message sent
        assert mock_send_message.call_count >= 1
        last_call = mock_send_message.call_args_list[-1]
        assert "state changed to" in last_call[0][1]
        assert "Completed" in last_call[0][1]

    @patch('ui.menus.send_message', new_callable=AsyncMock)
    @patch('ui.menus.handle_activate_race', new_callable=AsyncMock)
    @patch('ui.menus.race_has_submissions')
    @pytest.mark.parametrize("points_type", [
        PointsType.NoScoring,
        PointsType.MarioKart,
        PointsType.Trueskill,
        PointsType.ParTime,
        PointsType.Fixed,
    ])
    async def test_completed_to_active_various_scoring_types(self, mock_has_subs, mock_handle_activate,
                                                             mock_send_message, points_type):
        """Test Completed → Active with various scoring types."""
        # Setup
        category = create_mock_category(points_type=points_type)
        race = create_mock_race(race_id=18, category_id=category, state=RaceState.Completed)
        race.save = Mock()
        
        interaction = create_mock_interaction()
        
        # Execute
        await race_change_state(interaction, race, new_state=RaceState.Active)
        
        # Verify
        if points_type == PointsType.NoScoring:
            # Should succeed
            assert race.state == RaceState.Active
            race.save.assert_called_once()
        else:
            # Should fail for all other scoring types
            assert race.state == RaceState.Completed
            race.save.assert_not_called()


########################################################################################################################
# Tests for handle_activate_race()
########################################################################################################################

class TestHandleActivateRace:
    """Test handle_activate_race() function - handles race activation actions"""

    @pytest.mark.asyncio
    async def test_handle_activate_race_open_race_with_submit_role(self, sample_interaction, sample_race):
        """Test handle_activate_race for open race with submit role"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            sample_interaction.guild.members = [MagicMock(roles=[mock_role])]
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            mock_is_assigned.assert_called_once_with(sample_race.id)
            mock_send_announcement.assert_called_once_with(sample_interaction, sample_race)
            sample_interaction.guild.get_role.assert_called_once_with(12345)
            assert mock_remove_role.call_count == 2  # Called twice due to retry logic
            mock_pin_race.assert_called_once_with(sample_interaction, sample_race)
            mock_update_leaderboard.assert_called_once_with(sample_interaction, sample_race)

    @pytest.mark.asyncio
    async def test_handle_activate_race_assigned_race_with_submit_role(self, sample_interaction, sample_race):
        """Test handle_activate_race for assigned race with submit role"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=True) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            sample_interaction.guild.members = [MagicMock(roles=[mock_role])]
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            mock_is_assigned.assert_called_once_with(sample_race.id)
            mock_send_announcement.assert_not_called()  # Should not be called for assigned races
            sample_interaction.guild.get_role.assert_called_once_with(12345)
            assert mock_remove_role.call_count == 2  # Called twice due to retry logic
            mock_pin_race.assert_called_once_with(sample_interaction, sample_race)
            mock_update_leaderboard.assert_called_once_with(sample_interaction, sample_race)

    @pytest.mark.asyncio
    async def test_handle_activate_race_open_race_no_submit_role(self, sample_interaction, sample_race):
        """Test handle_activate_race for open race without submit role"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race without submit role
            sample_race.category_id.submit_role = None
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            mock_is_assigned.assert_called_once_with(sample_race.id)
            mock_send_announcement.assert_called_once_with(sample_interaction, sample_race)
            sample_interaction.guild.get_role.assert_not_called()
            mock_remove_role.assert_not_called()
            mock_pin_race.assert_called_once_with(sample_interaction, sample_race)
            mock_update_leaderboard.assert_called_once_with(sample_interaction, sample_race)

    @pytest.mark.asyncio
    async def test_handle_activate_race_submit_role_removal_success_first_attempt(self, sample_interaction, sample_race):
        """Test handle_activate_race when role removal succeeds on first attempt"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            # No members have the role after first removal
            sample_interaction.guild.members = [MagicMock(roles=[])]
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls - only called once since no members have the role after first call
            mock_remove_role.assert_called_once_with(sample_interaction.guild, mock_role)

    @pytest.mark.asyncio
    async def test_handle_activate_race_submit_role_removal_retry_success(self, sample_interaction, sample_race):
        """Test handle_activate_race when role removal succeeds on retry"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            
            # Member still has role after first removal (simulating retry scenario)
            member_with_role = MagicMock(roles=[mock_role])
            sample_interaction.guild.members = [member_with_role]
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls - called once initially, then once more for the member that still had the role
            assert mock_remove_role.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_activate_race_submit_role_removal_retry_fails(self, sample_interaction, sample_race):
        """Test handle_activate_race when role removal fails even after retry"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            
            # Member always has role (removal always fails)
            member_with_role = MagicMock(roles=[mock_role])
            sample_interaction.guild.members = [member_with_role]
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            assert mock_remove_role.call_count == 2  # Called twice due to retry logic
            # Other functions should still be called
            mock_send_announcement.assert_called_once_with(sample_interaction, sample_race)
            mock_pin_race.assert_called_once_with(sample_interaction, sample_race)
            mock_update_leaderboard.assert_called_once_with(sample_interaction, sample_race)

    @pytest.mark.asyncio
    async def test_handle_activate_race_submit_role_not_found(self, sample_interaction, sample_race):
        """Test handle_activate_race when submit role is not found in guild"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            sample_interaction.guild.get_role.return_value = None  # Role not found
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            mock_is_assigned.assert_called_once_with(sample_race.id)
            mock_send_announcement.assert_called_once_with(sample_interaction, sample_race)
            sample_interaction.guild.get_role.assert_called_once_with(12345)
            mock_remove_role.assert_called_once_with(sample_interaction.guild, None)  # Called with None role
            mock_pin_race.assert_called_once_with(sample_interaction, sample_race)
            mock_update_leaderboard.assert_called_once_with(sample_interaction, sample_race)

    @pytest.mark.asyncio
    async def test_handle_activate_race_all_functions_called_in_order(self, sample_interaction, sample_race):
        """Test handle_activate_race calls all functions in correct order"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            sample_interaction.guild.members = [MagicMock(roles=[])]
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify call order
            call_args_list = [
                (mock_is_assigned, [(sample_race.id,)]),
                (mock_send_announcement, [(sample_interaction, sample_race)]),
                (sample_interaction.guild.get_role, [(12345,)]),
                (mock_remove_role, [(sample_interaction.guild, mock_role)]),
                (mock_pin_race, [(sample_interaction, sample_race)]),
                (mock_update_leaderboard, [(sample_interaction, sample_race)])
            ]
            
            for mock_func, expected_args in call_args_list:
                mock_func.assert_called_once_with(*expected_args[0])

    @pytest.mark.asyncio
    async def test_handle_activate_race_exception_propagation(self, sample_interaction, sample_race):
        """Test handle_activate_race propagates exceptions from dependencies"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement', side_effect=Exception("Test error")) as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race without submit role to avoid role removal logic
            sample_race.category_id.submit_role = None
            
            # Call function - should raise exception
            with pytest.raises(Exception, match="Test error"):
                await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            mock_is_assigned.assert_called_once_with(sample_race.id)
            mock_send_announcement.assert_called_once_with(sample_interaction, sample_race)
            # Other functions should not be called due to exception
            mock_pin_race.assert_not_called()
            mock_update_leaderboard.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_activate_race_multiple_members_with_role(self, sample_interaction, sample_race):
        """Test handle_activate_race with multiple members having the submit role"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            
            # Multiple members with role - they still have role after first removal
            member1 = MagicMock(roles=[mock_role])
            member2 = MagicMock(roles=[mock_role])
            member3 = MagicMock(roles=[])  # No role
            sample_interaction.guild.members = [member1, member2, member3]
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            mock_is_assigned.assert_called_once_with(sample_race.id)
            mock_send_announcement.assert_called_once_with(sample_interaction, sample_race)
            sample_interaction.guild.get_role.assert_called_once_with(12345)
            # Called once initially, then once for each member that still has the role (2 members)
            assert mock_remove_role.call_count == 3  # 1 initial + 2 retries
            mock_pin_race.assert_called_once_with(sample_interaction, sample_race)
            mock_update_leaderboard.assert_called_once_with(sample_interaction, sample_race)

    @pytest.mark.asyncio
    async def test_handle_activate_race_empty_guild_members(self, sample_interaction, sample_race):
        """Test handle_activate_race with empty guild members list"""
        # Mock dependencies
        with patch('ui.menus.is_assigned_race', return_value=False) as mock_is_assigned, \
             patch('ui.menus.send_race_announcement') as mock_send_announcement, \
             patch('ui.menus.remove_role_from_members') as mock_remove_role, \
             patch('ui.menus.pin_race_for_category') as mock_pin_race, \
             patch('ui.menus.update_category_leaderboard') as mock_update_leaderboard:
            
            # Setup race with submit role
            sample_race.category_id.submit_role = 12345
            mock_role = MagicMock()
            sample_interaction.guild.get_role.return_value = mock_role
            sample_interaction.guild.members = []  # Empty members list
            
            # Call function
            await handle_activate_race(sample_interaction, sample_race)
            
            # Verify calls
            mock_is_assigned.assert_called_once_with(sample_race.id)
            mock_send_announcement.assert_called_once_with(sample_interaction, sample_race)
            sample_interaction.guild.get_role.assert_called_once_with(12345)
            mock_remove_role.assert_called_once_with(sample_interaction.guild, mock_role)  # Called once, no retry needed
            mock_pin_race.assert_called_once_with(sample_interaction, sample_race)
            mock_update_leaderboard.assert_called_once_with(sample_interaction, sample_race)

