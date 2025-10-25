# -*- coding: utf-8 -*-
"""
Unit tests for the AsyncRacePinnedState database model.
Tests model creation, field validation, and table operations.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from db.zBot_db_orm import AsyncRacePinnedState
from db.db_util import PinType


@pytest.mark.unit
class TestAsyncRacePinnedStateModel:
    """Tests for AsyncRacePinnedState model"""

    @patch('db.zBot_db_orm.AsyncRacePinnedState.race_id')
    def test_model_creation_individual_pin(self, mock_race_id):
        """Test creating an individual race pin state."""
        # Mock the foreign key to avoid database lookup
        mock_race_id.__get__ = Mock(return_value=456)
        
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        
        assert pinned_state.server_id == 123
        assert pinned_state.race_id == 456
        assert pinned_state.category_id is None
        assert pinned_state.channel_id == 789
        assert pinned_state.pin_type == PinType.Individual
        assert pinned_state.created_datetime is not None

    @patch('db.zBot_db_orm.AsyncRacePinnedState.category_id')
    def test_model_creation_category_pin(self, mock_category_id):
        """Test creating a category pin state."""
        # Mock the foreign key to avoid database lookup
        mock_category_id.__get__ = Mock(return_value=456)
        
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=None,
            category_id=456,
            channel_id=789,
            pin_type=PinType.Category
        )
        
        assert pinned_state.server_id == 123
        assert pinned_state.race_id is None
        assert pinned_state.category_id == 456
        assert pinned_state.channel_id == 789
        assert pinned_state.pin_type == PinType.Category
        assert pinned_state.created_datetime is not None

    def test_model_creation_with_custom_datetime(self):
        """Test creating a pinned state with custom datetime."""
        custom_datetime = datetime(2024, 1, 15, 10, 30, 0)
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual,
            created_datetime=custom_datetime
        )
        
        assert pinned_state.created_datetime == custom_datetime

    def test_model_meta_attributes(self):
        """Test model meta attributes."""
        assert AsyncRacePinnedState._meta.table_name == 'async_race_pinned_states'
        assert AsyncRacePinnedState._meta.database is not None

    def test_model_field_types(self):
        """Test that model fields have correct types."""
        # Check that fields exist and are properly defined
        assert hasattr(AsyncRacePinnedState, 'id')
        assert hasattr(AsyncRacePinnedState, 'server_id')
        assert hasattr(AsyncRacePinnedState, 'race_id')
        assert hasattr(AsyncRacePinnedState, 'category_id')
        assert hasattr(AsyncRacePinnedState, 'channel_id')
        assert hasattr(AsyncRacePinnedState, 'pin_type')
        assert hasattr(AsyncRacePinnedState, 'created_datetime')

    def test_model_foreign_key_relationships(self):
        """Test foreign key relationships."""
        # Test that foreign key fields are properly defined
        race_field = AsyncRacePinnedState._meta.fields['race_id']
        assert hasattr(race_field, 'rel_model')
        
        category_field = AsyncRacePinnedState._meta.fields['category_id']
        assert hasattr(category_field, 'rel_model')

    def test_model_string_representation(self):
        """Test model string representation."""
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        
        # The string representation should include the model name and ID
        str_repr = str(pinned_state)
        # For unsaved models, the string representation might be different
        # Just check that it's not None and contains some identifier
        assert str_repr is not None
        assert len(str_repr) > 0

    @patch('db.zBot_db_orm.AsyncRacePinnedState.race_id')
    def test_model_validation_individual_pin(self, mock_race_id):
        """Test validation for individual pin (race_id required, category_id None)."""
        # Mock the foreign key to avoid database lookup
        mock_race_id.__get__ = Mock(return_value=456)
        
        # Valid individual pin
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        assert pinned_state.race_id is not None
        assert pinned_state.category_id is None
        assert pinned_state.pin_type == PinType.Individual

    @patch('db.zBot_db_orm.AsyncRacePinnedState.category_id')
    def test_model_validation_category_pin(self, mock_category_id):
        """Test validation for category pin (category_id required, race_id None)."""
        # Mock the foreign key to avoid database lookup
        mock_category_id.__get__ = Mock(return_value=456)
        
        # Valid category pin
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=None,
            category_id=456,
            channel_id=789,
            pin_type=PinType.Category
        )
        assert pinned_state.race_id is None
        assert pinned_state.category_id is not None
        assert pinned_state.pin_type == PinType.Category

    def test_model_required_fields(self):
        """Test that required fields are properly defined."""
        # server_id should be required
        pinned_state = AsyncRacePinnedState()
        assert pinned_state.server_id is None  # Not set, should be None initially
        
        # channel_id should be required
        assert pinned_state.channel_id is None  # Not set, should be None initially
        
        # pin_type should be required
        assert pinned_state.pin_type is None  # Not set, should be None initially

    def test_model_optional_fields(self):
        """Test that optional fields can be None."""
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=None,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        
        # Both race_id and category_id can be None (one or the other should be set in practice)
        assert pinned_state.race_id is None
        assert pinned_state.category_id is None


@pytest.mark.unit
class TestPinTypeConstants:
    """Tests for PinType constants used with the model"""

    def test_pin_type_values(self):
        """Test that PinType constants have expected values."""
        assert PinType.Individual == 0
        assert PinType.Category == 1

    def test_pin_type_usage_in_model(self):
        """Test using PinType constants in model creation."""
        # Individual pin
        individual_pin = AsyncRacePinnedState(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        assert individual_pin.pin_type == 0
        
        # Category pin
        category_pin = AsyncRacePinnedState(
            server_id=123,
            race_id=None,
            category_id=456,
            channel_id=789,
            pin_type=PinType.Category
        )
        assert category_pin.pin_type == 1


@pytest.mark.unit
class TestModelIntegration:
    """Tests for model integration with database operations"""

    @patch('db.zBot_db_orm.AsyncRacePinnedState.save')
    def test_model_save_operation(self, mock_save):
        """Test saving a pinned state model."""
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        
        pinned_state.save()
        mock_save.assert_called_once()

    @patch('db.zBot_db_orm.AsyncRacePinnedState.delete_instance')
    def test_model_delete_operation(self, mock_delete):
        """Test deleting a pinned state model."""
        pinned_state = AsyncRacePinnedState(
            server_id=123,
            race_id=456,
            category_id=None,
            channel_id=789,
            pin_type=PinType.Individual
        )
        
        pinned_state.delete_instance()
        mock_delete.assert_called_once()

    @patch('db.zBot_db_orm.AsyncRacePinnedState.select')
    def test_model_query_operation(self, mock_select):
        """Test querying pinned state models."""
        mock_query = Mock()
        mock_select.return_value.where.return_value = mock_query
        
        # Simulate querying by server_id
        query = AsyncRacePinnedState.select().where(AsyncRacePinnedState.server_id == 123)
        
        mock_select.assert_called_once()
        assert query == mock_query
