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

# Now we can import the function
from ui.menus import race_change_state


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

