# -*- coding: utf-8 -*-
"""
Unit tests for UI utility view classes.
Tests zSingleSelectView and zMultiPageModalSender classes from ui/ui_util.py.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import nextcord

from ui.ui_util import zSingleSelectView, zMultiPageModalSender, zField, zModal, zContinueCancelButtonView, safe_zSingleSelectView
from test.test_utils.discord_mocks import create_mock_interaction, create_mock_user


@pytest.mark.unit
class TestZSingleSelectView:
    """Tests for zSingleSelectView class in ui/ui_util.py"""

    @pytest.mark.asyncio
    async def test_init_with_small_list(self):
        """Test initialization with a small list (<=25 items)."""
        select_list = [
            nextcord.SelectOption(label="Option 1", value="1", description="First option"),
            nextcord.SelectOption(label="Option 2", value="2", description="Second option"),
            nextcord.SelectOption(label="Option 3", value="3", description="Third option")
        ]
        
        def mock_handler(value, interaction):
            pass
        
        view = zSingleSelectView(select_list, mock_handler, "Choose an option")
        
        assert view.submit_handler == mock_handler
        assert view.selected_value is None
        assert len(view.children) == 1
        assert isinstance(view.children[0], nextcord.ui.Select)
        assert view.children[0].placeholder == "Choose an option"
        assert len(view.children[0].options) == 3

    @pytest.mark.asyncio
    async def test_init_with_large_list(self):
        """Test initialization with a large list (>25 items) shows pagination."""
        select_list = [nextcord.SelectOption(label=f"Option {i}", value=str(i), description=f"Option {i}") for i in range(30)]
        
        def mock_handler(value, interaction):
            pass
        
        view = zSingleSelectView(select_list, mock_handler, "Choose an option")
        
        assert view.submit_handler == mock_handler
        assert view.selected_value is None
        assert len(view.children) == 1
        assert isinstance(view.children[0], nextcord.ui.Select)
        assert view.children[0].placeholder == "Choose an option"
        # Should show first 24 options + "Show More..." option
        assert len(view.children[0].options) == 25
        assert view.children[0].options[-1].label == "Show More..."

    @pytest.mark.asyncio
    async def test_init_with_empty_list_raises_error(self):
        """Test initialization with an empty list (0 items) raises ValueError."""
        select_list = []
        
        def mock_handler(value, interaction):
            pass
        
        # Should raise ValueError when trying to create view with empty list
        with pytest.raises(ValueError, match="zSingleSelectView requires at least one option"):
            zSingleSelectView(select_list, mock_handler, "Choose an option")

    @pytest.mark.asyncio
    async def test_save_selected_value_with_payload(self):
        """Test save_selected_value method with payload."""
        select_list = [nextcord.SelectOption(label="Option 1", value="1", description="First option")]
        mock_interaction = create_mock_interaction()
        captured_value = None
        captured_interaction = None
        
        async def mock_handler(value, interaction):
            nonlocal captured_value, captured_interaction
            captured_value = value
            captured_interaction = interaction
        
        view = zSingleSelectView(select_list, mock_handler, "Choose an option", payload="test_payload")
        
        await view.save_selected_value((1, "test_payload"), mock_interaction)
        
        assert view.selected_value == (1, "test_payload")
        assert view.interaction == mock_interaction
        assert captured_value == (1, "test_payload")
        assert captured_interaction == mock_interaction

    @pytest.mark.asyncio
    async def test_save_selected_value_without_payload(self):
        """Test save_selected_value method without payload."""
        select_list = [nextcord.SelectOption(label="Option 1", value="1", description="First option")]
        mock_interaction = create_mock_interaction()
        captured_value = None
        captured_interaction = None
        
        async def mock_handler(value, interaction):
            nonlocal captured_value, captured_interaction
            captured_value = value
            captured_interaction = interaction
        
        view = zSingleSelectView(select_list, mock_handler, "Choose an option")
        
        await view.save_selected_value(1, mock_interaction)
        
        assert view.selected_value == 1
        assert view.interaction == mock_interaction
        assert captured_value == 1
        assert captured_interaction == mock_interaction

    @pytest.mark.asyncio
    async def test_get_selected_value(self):
        """Test get_selected_value method."""
        select_list = [nextcord.SelectOption(label="Option 1", value="1", description="First option")]
        view = zSingleSelectView(select_list, None, "Choose an option")
        
        # Initially None
        assert view.get_selected_value() is None
        
        # After setting a value
        view.selected_value = "test_value"
        assert view.get_selected_value() == "test_value"

    @pytest.mark.asyncio
    async def test_prompt_method(self):
        """Test prompt method flow."""
        select_list = [nextcord.SelectOption(label="Option 1", value="1", description="First option")]
        mock_interaction = create_mock_interaction()
        
        async def mock_handler(value, interaction):
            pass
        
        view = zSingleSelectView(select_list, mock_handler, "Choose an option")
        
        # Mock the wait method to simulate user selection
        with patch.object(view, 'wait', new_callable=AsyncMock) as mock_wait:
            with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
                result = await view.prompt(mock_interaction, "Test message")
                
                mock_send.assert_called_once_with(mock_interaction, "", view=view)
                mock_wait.assert_called_once()
                assert result is None  # No value selected yet

    @pytest.mark.asyncio
    async def test_prompt_method_with_selected_value(self):
        """Test prompt method returns selected value."""
        select_list = [nextcord.SelectOption(label="Option 1", value="1", description="First option")]
        mock_interaction = create_mock_interaction()
        
        async def mock_handler(value, interaction):
            pass
        
        view = zSingleSelectView(select_list, mock_handler, "Choose an option")
        view.selected_value = "test_selection"
        
        with patch.object(view, 'wait', new_callable=AsyncMock) as mock_wait:
            with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
                result = await view.prompt(mock_interaction, "Test message")
                
                mock_send.assert_called_once_with(mock_interaction, "", view=view)
                mock_wait.assert_called_once()
                assert result == "test_selection"

    @pytest.mark.asyncio
    async def test_init_with_none_submit_handler(self):
        """Test initialization with None submit handler."""
        select_list = [nextcord.SelectOption(label="Option 1", value="1", description="First option")]
        
        view = zSingleSelectView(select_list, None, "Choose an option")
        
        assert view.submit_handler is None
        assert view.selected_value is None
        assert len(view.children) == 1

    @pytest.mark.asyncio
    async def test_save_selected_value_with_none_handler(self):
        """Test save_selected_value with None submit handler doesn't crash."""
        select_list = [nextcord.SelectOption(label="Option 1", value="1", description="First option")]
        mock_interaction = create_mock_interaction()
        
        view = zSingleSelectView(select_list, None, "Choose an option")
        
        # Should not raise an exception
        await view.save_selected_value(1, mock_interaction)
        
        assert view.selected_value == 1
        assert view.interaction == mock_interaction


@pytest.mark.unit
class TestSafeZSingleSelectView:
    """Tests for safe_zSingleSelectView helper function in ui/ui_util.py"""

    @pytest.mark.asyncio
    async def test_safe_view_with_non_empty_list(self):
        """Test safe_zSingleSelectView with a non-empty list returns view."""
        select_list = [
            nextcord.SelectOption(label="Option 1", value="1", description="First option"),
            nextcord.SelectOption(label="Option 2", value="2", description="Second option")
        ]
        
        def mock_handler(value, interaction):
            pass
        
        mock_interaction = create_mock_interaction()
        
        with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
            result = await safe_zSingleSelectView(mock_interaction, select_list, mock_handler, "Choose an option")
            
            # Should return a zSingleSelectView instance
            assert result is not None
            assert isinstance(result, zSingleSelectView)
            assert result.submit_handler == mock_handler
            
            # Should not call send_message since list is not empty
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_safe_view_with_empty_list_default_message(self):
        """Test safe_zSingleSelectView with empty list shows default message and returns None."""
        select_list = []
        
        def mock_handler(value, interaction):
            pass
        
        mock_interaction = create_mock_interaction()
        
        with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
            result = await safe_zSingleSelectView(mock_interaction, select_list, mock_handler, "Choose an option")
            
            # Should return None
            assert result is None
            
            # Should call send_message with default empty message
            mock_send.assert_called_once_with(mock_interaction, "No options available")

    @pytest.mark.asyncio
    async def test_safe_view_with_empty_list_custom_message(self):
        """Test safe_zSingleSelectView with empty list shows custom message and returns None."""
        select_list = []
        
        def mock_handler(value, interaction):
            pass
        
        mock_interaction = create_mock_interaction()
        custom_message = "No categories available. Create a category first."
        
        with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
            result = await safe_zSingleSelectView(mock_interaction, select_list, mock_handler, "Choose an option", empty_message=custom_message)
            
            # Should return None
            assert result is None
            
            # Should call send_message with custom message
            mock_send.assert_called_once_with(mock_interaction, custom_message)

    @pytest.mark.asyncio
    async def test_safe_view_with_payload(self):
        """Test safe_zSingleSelectView with payload parameter."""
        select_list = [
            nextcord.SelectOption(label="Option 1", value="1", description="First option")
        ]
        
        def mock_handler(value, interaction):
            pass
        
        mock_interaction = create_mock_interaction()
        
        with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
            result = await safe_zSingleSelectView(mock_interaction, select_list, mock_handler, "Choose an option", payload="test_payload")
            
            # Should return a zSingleSelectView instance
            assert result is not None
            assert isinstance(result, zSingleSelectView)
            assert result.submit_handler == mock_handler
            
            # Should not call send_message since list is not empty
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_safe_view_with_empty_list_and_payload(self):
        """Test safe_zSingleSelectView with empty list and payload parameter."""
        select_list = []
        
        def mock_handler(value, interaction):
            pass
        
        mock_interaction = create_mock_interaction()
        
        with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
            result = await safe_zSingleSelectView(mock_interaction, select_list, mock_handler, "Choose an option", payload="test_payload")
            
            # Should return None
            assert result is None
            
            # Should call send_message with default empty message
            mock_send.assert_called_once_with(mock_interaction, "No options available")


@pytest.mark.unit
class TestZMultiPageModalSender:
    """Tests for zMultiPageModalSender class in ui/ui_util.py"""

    def test_init(self):
        """Test initialization."""
        sender = zMultiPageModalSender()
        assert sender is not None

    @pytest.mark.asyncio
    async def test_send_modal_single_page(self):
        """Test sending a modal with a single page (<=4 fields)."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3")
        ]
        
        mock_interaction = create_mock_interaction()
        captured_values = None
        captured_interaction = None
        
        async def mock_handler(interaction, values):
            nonlocal captured_values, captured_interaction
            captured_values = values
            captured_interaction = interaction
        
        sender = zMultiPageModalSender()
        
        with patch.object(sender, 'send_modal_page', new_callable=AsyncMock) as mock_send_page:
            await sender.send_modal(mock_interaction, fields, mock_handler, "Test Modal")
            
            mock_send_page.assert_called_once_with(mock_interaction)
            assert sender.fields == fields
            assert sender.submit_handler == mock_handler
            assert sender.title == "Test Modal"
            assert sender.field_idx == 0
            assert sender.submit_values == [None, None, None]

    @pytest.mark.asyncio
    async def test_send_modal_multi_page(self):
        """Test sending a modal with multiple pages (>4 fields)."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3"),
            zField("field4", "Field 4", "default4", True, "placeholder4"),
            zField("field5", "Field 5", "default5", False, "placeholder5"),
            zField("field6", "Field 6", "default6", True, "placeholder6")
        ]
        
        mock_interaction = create_mock_interaction()
        captured_values = None
        captured_interaction = None
        
        async def mock_handler(interaction, values):
            nonlocal captured_values, captured_interaction
            captured_values = values
            captured_interaction = interaction
        
        sender = zMultiPageModalSender()
        
        with patch.object(sender, 'send_modal_page', new_callable=AsyncMock) as mock_send_page:
            await sender.send_modal(mock_interaction, fields, mock_handler, "Test Modal")
            
            mock_send_page.assert_called_once_with(mock_interaction)
            assert sender.fields == fields
            assert sender.submit_handler == mock_handler
            assert sender.title == "Test Modal"
            assert sender.field_idx == 0
            assert sender.submit_values == [None] * 6

    def test_get_field_index(self):
        """Test get_field_index method."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3")
        ]
        
        sender = zMultiPageModalSender()
        sender.fields = fields
        
        assert sender.get_field_index("field1") == 0
        assert sender.get_field_index("field2") == 1
        assert sender.get_field_index("field3") == 2
        assert sender.get_field_index("nonexistent") is None

    @pytest.mark.asyncio
    async def test_send_modal_page_single_page(self):
        """Test send_modal_page with single page (<=4 fields)."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3")
        ]
        
        mock_interaction = create_mock_interaction()
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.title = "Test Modal"
        sender.field_idx = 0
        
        with patch('ui.ui_util.zModal') as mock_modal_class:
            mock_modal = MagicMock()
            mock_modal_class.return_value = mock_modal
            
            with patch.object(mock_interaction, 'response') as mock_response:
                mock_response.send_modal = AsyncMock()
                await sender.send_modal_page(mock_interaction)
                
                # Should create a modal with 3 fields
                mock_modal_class.assert_called_once()
                call_args = mock_modal_class.call_args
                field_dict = call_args[0][0]  # First positional argument
                assert len(field_dict) == 3
                assert "field1" in field_dict
                assert "field2" in field_dict
                assert "field3" in field_dict
                
                # Should call send_modal on the interaction
                mock_response.send_modal.assert_called_once_with(mock_modal)
                
                # Should update field_idx
                assert sender.field_idx == 3

    @pytest.mark.asyncio
    async def test_send_modal_page_multi_page_first(self):
        """Test send_modal_page with first page of multi-page modal."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3"),
            zField("field4", "Field 4", "default4", True, "placeholder4"),
            zField("field5", "Field 5", "default5", False, "placeholder5")
        ]
        
        mock_interaction = create_mock_interaction()
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.title = "Test Modal"
        sender.field_idx = 0
        
        with patch('ui.ui_util.zModal') as mock_modal_class:
            mock_modal = MagicMock()
            mock_modal_class.return_value = mock_modal
            
            with patch.object(mock_interaction, 'response') as mock_response:
                mock_response.send_modal = AsyncMock()
                await sender.send_modal_page(mock_interaction)
                
                # Should create a modal with 4 fields (first page)
                mock_modal_class.assert_called_once()
                call_args = mock_modal_class.call_args
                field_dict = call_args[0][0]  # First positional argument
                assert len(field_dict) == 4
                assert "field1" in field_dict
                assert "field2" in field_dict
                assert "field3" in field_dict
                assert "field4" in field_dict
                
                # Should call send_modal on the interaction
                mock_response.send_modal.assert_called_once_with(mock_modal)
                
                # Should update field_idx
                assert sender.field_idx == 4

    @pytest.mark.asyncio
    async def test_send_modal_page_multi_page_second(self):
        """Test send_modal_page with second page of multi-page modal."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3"),
            zField("field4", "Field 4", "default4", True, "placeholder4"),
            zField("field5", "Field 5", "default5", False, "placeholder5")
        ]
        
        mock_interaction = create_mock_interaction()
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.title = "Test Modal"
        sender.field_idx = 4  # Start from second page
        
        with patch('ui.ui_util.zModal') as mock_modal_class:
            mock_modal = MagicMock()
            mock_modal_class.return_value = mock_modal
            
            with patch.object(mock_interaction, 'response') as mock_response:
                mock_response.send_modal = AsyncMock()
                await sender.send_modal_page(mock_interaction)
                
                # Should create a modal with 1 field (remaining field)
                mock_modal_class.assert_called_once()
                call_args = mock_modal_class.call_args
                field_dict = call_args[0][0]  # First positional argument
                assert len(field_dict) == 1
                assert "field5" in field_dict
                
                # Should call send_modal on the interaction
                mock_response.send_modal.assert_called_once_with(mock_modal)
                
                # Should update field_idx
                assert sender.field_idx == 5

    @pytest.mark.asyncio
    async def test_on_page_submit_with_more_fields(self):
        """Test on_page_submit when there are more fields to process."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3"),
            zField("field4", "Field 4", "default4", True, "placeholder4"),
            zField("field5", "Field 5", "default5", False, "placeholder5")
        ]
        
        mock_interaction = create_mock_interaction()
        captured_values = None
        captured_interaction = None
        
        async def mock_handler(interaction, values):
            nonlocal captured_values, captured_interaction
            captured_values = values
            captured_interaction = interaction
        
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.submit_handler = mock_handler
        sender.field_idx = 4  # After first page
        sender.submit_values = [None] * 5
        
        # Mock modal with children
        mock_modal = MagicMock()
        mock_field1 = MagicMock()
        mock_field1.custom_id = "field1"
        mock_field1.value = "value1"
        mock_field2 = MagicMock()
        mock_field2.custom_id = "field2"
        mock_field2.value = "value2"
        mock_field3 = MagicMock()
        mock_field3.custom_id = "field3"
        mock_field3.value = "value3"
        mock_field4 = MagicMock()
        mock_field4.custom_id = "field4"
        mock_field4.value = "value4"
        mock_modal.children = [mock_field1, mock_field2, mock_field3, mock_field4]
        
        with patch('ui.ui_util.send_message', new_callable=AsyncMock) as mock_send:
            with patch('ui.ui_util.zContinueCancelButtonView') as mock_button_view:
                await sender.on_page_submit(mock_interaction, mock_modal)
                
                # Should save the values from the modal
                assert sender.submit_values[0] == "value1"
                assert sender.submit_values[1] == "value2"
                assert sender.submit_values[2] == "value3"
                assert sender.submit_values[3] == "value4"
                assert sender.submit_values[4] is None  # Not processed yet
                
                # Should send continue/cancel message
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == mock_interaction
                assert call_args[0][1] == "Continue to next page or cancel?"
                assert call_args[1]['view'] is not None

    @pytest.mark.asyncio
    async def test_on_page_submit_final_page(self):
        """Test on_page_submit when this is the final page."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3")
        ]
        
        mock_interaction = create_mock_interaction()
        captured_values = None
        captured_interaction = None
        
        async def mock_handler(interaction, values):
            nonlocal captured_values, captured_interaction
            captured_values = values
            captured_interaction = interaction
        
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.submit_handler = mock_handler
        sender.field_idx = 3  # All fields processed
        sender.submit_values = [None] * 3
        
        # Mock modal with children
        mock_modal = MagicMock()
        mock_field1 = MagicMock()
        mock_field1.custom_id = "field1"
        mock_field1.value = "value1"
        mock_field2 = MagicMock()
        mock_field2.custom_id = "field2"
        mock_field2.value = "value2"
        mock_field3 = MagicMock()
        mock_field3.custom_id = "field3"
        mock_field3.value = "value3"
        mock_modal.children = [mock_field1, mock_field2, mock_field3]
        
        await sender.on_page_submit(mock_interaction, mock_modal)
        
        # Should save the values from the modal
        assert sender.submit_values[0] == "value1"
        assert sender.submit_values[1] == "value2"
        assert sender.submit_values[2] == "value3"
        
        # Should call the submit handler with all values
        assert captured_values == ["value1", "value2", "value3"]
        assert captured_interaction == mock_interaction

    @pytest.mark.asyncio
    async def test_on_page_submit_with_unknown_field(self):
        """Test on_page_submit with a field that doesn't exist in the field list."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2")
        ]
        
        mock_interaction = create_mock_interaction()
        
        async def mock_handler(interaction, values):
            pass
        
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.submit_handler = mock_handler
        sender.field_idx = 2
        sender.submit_values = [None] * 2
        
        # Mock modal with unknown field
        mock_modal = MagicMock()
        mock_field = MagicMock()
        mock_field.custom_id = "unknown_field"
        mock_field.value = "value"
        mock_modal.children = [mock_field]
        
        with patch('ui.ui_util.logging') as mock_logging:
            await sender.on_page_submit(mock_interaction, mock_modal)
            
            # Should log an error about the unknown field
            mock_logging.info.assert_called()
            error_call = mock_logging.info.call_args[0][0]
            assert "Index not found for modal field unknown_field" in error_call

    @pytest.mark.asyncio
    async def test_cancel_submit(self):
        """Test cancel_submit method."""
        mock_interaction = create_mock_interaction()
        captured_values = None
        captured_interaction = None
        
        async def mock_handler(interaction, values):
            nonlocal captured_values, captured_interaction
            captured_values = values
            captured_interaction = interaction
        
        sender = zMultiPageModalSender()
        sender.submit_handler = mock_handler
        
        await sender.cancel_submit(mock_interaction)
        
        # Should call submit handler with None values
        assert captured_values is None
        assert captured_interaction == mock_interaction

    @pytest.mark.asyncio
    async def test_send_modal_page_field_row_assignment(self):
        """Test that fields are assigned correct row numbers in modal."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3"),
            zField("field4", "Field 4", "default4", True, "placeholder4")
        ]
        
        mock_interaction = create_mock_interaction()
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.title = "Test Modal"
        sender.field_idx = 0
        
        with patch('ui.ui_util.zModal') as mock_modal_class:
            mock_modal = MagicMock()
            mock_modal_class.return_value = mock_modal
            
            with patch.object(mock_interaction, 'response') as mock_response:
                mock_response.send_modal = AsyncMock()
                await sender.send_modal_page(mock_interaction)
                
                # Should create TextInput objects with correct row assignments
                call_args = mock_modal_class.call_args
                field_dict = call_args[0][0]  # First positional argument
                
                # Check that TextInput objects were created with correct row numbers
                for i, (field_id, text_input) in enumerate(field_dict.items()):
                    assert text_input.row == i + 1  # Rows start at 1

    @pytest.mark.asyncio
    async def test_send_modal_page_title_with_page_number(self):
        """Test that modal title includes page number for multi-page modals."""
        fields = [
            zField("field1", "Field 1", "default1", True, "placeholder1"),
            zField("field2", "Field 2", "default2", False, "placeholder2"),
            zField("field3", "Field 3", "default3", True, "placeholder3"),
            zField("field4", "Field 4", "default4", True, "placeholder4"),
            zField("field5", "Field 5", "default5", False, "placeholder5")
        ]
        
        mock_interaction = create_mock_interaction()
        sender = zMultiPageModalSender()
        sender.fields = fields
        sender.title = "Test Modal"
        sender.field_idx = 0
        
        with patch('ui.ui_util.zModal') as mock_modal_class:
            mock_modal = MagicMock()
            mock_modal_class.return_value = mock_modal
            
            with patch.object(mock_interaction, 'response') as mock_response:
                mock_response.send_modal = AsyncMock()
                await sender.send_modal_page(mock_interaction)
                
                # Should create modal with page number in title
                call_args = mock_modal_class.call_args
                title = call_args[0][2]  # Third positional argument (title)
                assert title == "Test Modal [pg. 2]"
