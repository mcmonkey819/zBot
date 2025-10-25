# -*- coding: utf-8 -*-
"""
Unit tests for pinned race state helper functions.
Tests database operations and utility functions with mocked dependencies.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from db.db_util import (
    save_pinned_race_state, 
    get_pinned_race_states, 
    clear_pinned_race_states,
    update_pinned_state_channel,
    PinType
)
from test.test_utils.db_fixtures import create_mock_race, create_mock_category


@pytest.mark.unit
class TestSavePinnedRaceState:
    """Tests for save_pinned_race_state() function"""

    @patch('db.db_util.AsyncRacePinnedState')
    def test_save_individual_race_pin(self, mock_pinned_state_class):
        """Test saving an individual race pin state."""
        mock_pinned_state = Mock()
        mock_pinned_state_class.return_value = mock_pinned_state
        
        result = save_pinned_race_state(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        
        assert result is True
        mock_pinned_state_class.assert_called_once_with(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        mock_pinned_state.save.assert_called_once()

    @patch('db.db_util.AsyncRacePinnedState')
    def test_save_category_pin(self, mock_pinned_state_class):
        """Test saving a category pin state."""
        mock_pinned_state = Mock()
        mock_pinned_state_class.return_value = mock_pinned_state
        
        result = save_pinned_race_state(
            server_id=123,
            race_id=None,
            category_id=456,
            channel_id=789,
            pin_type=PinType.Category
        )
        
        assert result is True
        mock_pinned_state_class.assert_called_once_with(
            server_id=123,
            race_id=None,
            category_id=456,
            channel_id=789,
            pin_type=PinType.Category
        )
        mock_pinned_state.save.assert_called_once()

    @patch('db.db_util.AsyncRacePinnedState')
    def test_save_pin_state_error_handling(self, mock_pinned_state_class):
        """Test error handling when saving fails."""
        mock_pinned_state = Mock()
        mock_pinned_state.save.side_effect = Exception("Database error")
        mock_pinned_state_class.return_value = mock_pinned_state
        
        result = save_pinned_race_state(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        
        assert result is False


@pytest.mark.unit
class TestGetPinnedRaceStates:
    """Tests for get_pinned_race_states() function"""

    @patch('db.db_util.AsyncRacePinnedState')
    def test_get_pinned_states_success(self, mock_pinned_state_class):
        """Test successfully getting pinned states."""
        mock_states = [Mock(), Mock()]
        mock_pinned_state_class.select.return_value.where.return_value = mock_states
        
        result = get_pinned_race_states(123)
        
        assert result == mock_states
        mock_pinned_state_class.select.assert_called_once()
        mock_pinned_state_class.select.return_value.where.assert_called_once()

    @patch('db.db_util.AsyncRacePinnedState')
    def test_get_pinned_states_error_handling(self, mock_pinned_state_class):
        """Test error handling when getting states fails."""
        mock_pinned_state_class.select.side_effect = Exception("Database error")
        
        result = get_pinned_race_states(123)
        
        assert result == []


@pytest.mark.unit
class TestClearPinnedRaceStates:
    """Tests for clear_pinned_race_states() function"""

    @patch('db.db_util.AsyncRacePinnedState')
    def test_clear_pinned_states_success(self, mock_pinned_state_class):
        """Test successfully clearing pinned states."""
        mock_query = Mock()
        mock_query.execute.return_value = 3  # 3 states deleted
        mock_pinned_state_class.delete.return_value.where.return_value = mock_query
        
        result = clear_pinned_race_states(123)
        
        assert result is True
        mock_pinned_state_class.delete.assert_called_once()
        mock_query.execute.assert_called_once()

    @patch('db.db_util.AsyncRacePinnedState')
    def test_clear_pinned_states_error_handling(self, mock_pinned_state_class):
        """Test error handling when clearing states fails."""
        mock_pinned_state_class.delete.side_effect = Exception("Database error")
        
        result = clear_pinned_race_states(123)
        
        assert result is False


@pytest.mark.unit
class TestUpdatePinnedStateChannel:
    """Tests for update_pinned_state_channel() function"""

    @patch('db.db_util.AsyncRacePinnedState')
    def test_update_channel_success(self, mock_pinned_state_class):
        """Test successfully updating channel for pinned state."""
        mock_query = Mock()
        mock_query.execute.return_value = 1  # 1 state updated
        mock_pinned_state_class.update.return_value.where.return_value = mock_query
        
        result = update_pinned_state_channel(123, 456, 789, 999)
        
        assert result is True
        mock_pinned_state_class.update.assert_called_once_with(channel_id=999)
        mock_query.execute.assert_called_once()

    @patch('db.db_util.AsyncRacePinnedState')
    def test_update_channel_no_match(self, mock_pinned_state_class):
        """Test updating channel when no matching state found."""
        mock_query = Mock()
        mock_query.execute.return_value = 0  # No states updated
        mock_pinned_state_class.update.return_value.where.return_value = mock_query
        
        result = update_pinned_state_channel(123, 456, 789, 999)
        
        assert result is False

    @patch('db.db_util.AsyncRacePinnedState')
    def test_update_channel_error_handling(self, mock_pinned_state_class):
        """Test error handling when updating channel fails."""
        mock_pinned_state_class.update.side_effect = Exception("Database error")
        
        result = update_pinned_state_channel(123, 456, 789, 999)
        
        assert result is False


@pytest.mark.unit
class TestPinTypeConstants:
    """Tests for PinType constants"""

    def test_pin_type_values(self):
        """Test that PinType constants have expected values."""
        assert PinType.Individual == 0
        assert PinType.Category == 1
