# -*- coding: utf-8 -*-
"""
Unit tests for UI utility formatting functions.
Tests pure functions from ui/ui_util.py with no external dependencies.
"""
import pytest
from unittest.mock import patch, MagicMock
from ui.ui_util import get_place_str, format_points_str, build_response_message_list, get_user_name_str, get_race_embed_field_value
from test.test_utils.discord_mocks import create_mock_user
from test.test_utils.db_fixtures import create_mock_race, create_mock_category


@pytest.mark.unit
class TestGetPlaceStr:
    """Tests for get_place_str() function - ui/ui_util.py:145"""

    def test_first_place(self):
        """Test 1st place formatting."""
        assert get_place_str(1) == "1st"

    def test_second_place(self):
        """Test 2nd place formatting."""
        assert get_place_str(2) == "2nd"

    def test_third_place(self):
        """Test 3rd place formatting."""
        assert get_place_str(3) == "3rd"

    def test_fourth_through_tenth(self):
        """Test 4th through 10th place formatting."""
        assert get_place_str(4) == "4th"
        assert get_place_str(5) == "5th"
        assert get_place_str(6) == "6th"
        assert get_place_str(7) == "7th"
        assert get_place_str(8) == "8th"
        assert get_place_str(9) == "9th"
        assert get_place_str(10) == "10th"

    def test_eleventh_through_thirteenth_special_cases(self):
        """Test 11th, 12th, 13th - special cases that end in 'th' not 'st'/'nd'/'rd'."""
        assert get_place_str(11) == "11th"
        assert get_place_str(12) == "12th"
        assert get_place_str(13) == "13th"

    def test_fourteenth_through_twentieth(self):
        """Test 14th through 20th place formatting."""
        assert get_place_str(14) == "14th"
        assert get_place_str(15) == "15th"
        assert get_place_str(16) == "16th"
        assert get_place_str(17) == "17th"
        assert get_place_str(18) == "18th"
        assert get_place_str(19) == "19th"
        assert get_place_str(20) == "20th"

    def test_twenty_first_second_third(self):
        """Test 21st, 22nd, 23rd - back to regular pattern after teens."""
        assert get_place_str(21) == "21st"
        assert get_place_str(22) == "22nd"
        assert get_place_str(23) == "23rd"

    def test_larger_numbers_ending_in_1_2_3(self):
        """Test larger numbers that end in 1, 2, or 3."""
        assert get_place_str(31) == "31st"
        assert get_place_str(42) == "42nd"
        assert get_place_str(53) == "53rd"
        assert get_place_str(101) == "101st"
        assert get_place_str(1002) == "1002nd"
        assert get_place_str(10003) == "10003rd"

    def test_larger_numbers_with_teens_pattern(self):
        """Test larger numbers with teens (111th, 112th, 113th, etc.)."""
        assert get_place_str(111) == "111th"
        assert get_place_str(112) == "112th"
        assert get_place_str(113) == "113th"
        assert get_place_str(211) == "211th"
        assert get_place_str(1011) == "1011th"

    def test_larger_numbers_ending_in_4_through_0(self):
        """Test larger numbers ending in 4-9 and 0."""
        assert get_place_str(24) == "24th"
        assert get_place_str(35) == "35th"
        assert get_place_str(46) == "46th"
        assert get_place_str(57) == "57th"
        assert get_place_str(68) == "68th"
        assert get_place_str(79) == "79th"
        assert get_place_str(100) == "100th"
        assert get_place_str(1000) == "1000th"

    def test_edge_case_zero(self):
        """Test edge case of 0 (error case that returns 'Worst')."""
        assert get_place_str(0) == "Worst"

    @pytest.mark.parametrize("place,expected", [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
        (100, "100th"),
        (101, "101st"),
        (111, "111th"),
        (121, "121st"),
        (0, "Worst"),
    ])
    def test_place_str_parametrized(self, place, expected):
        """Parametrized test covering various place values."""
        assert get_place_str(place) == expected


@pytest.mark.unit
class TestFormatPointsStr:
    """Tests for format_points_str() function - ui/ui_util.py:418"""

    def test_integer_points(self):
        """Test points with no decimal value."""
        assert format_points_str(100.000) == "100"
        assert format_points_str(50.000) == "50"
        assert format_points_str(1.000) == "1"

    def test_decimal_points(self):
        """Test points with decimal values."""
        assert format_points_str(95.750) == "95.750"
        assert format_points_str(88.123) == "88.123"
        assert format_points_str(100.001) == "100.001"

    def test_zero_points(self):
        """Test zero points."""
        assert format_points_str(0.000) == "0"

    def test_small_decimal_points(self):
        """Test small decimal values."""
        assert format_points_str(0.500) == "0.500"
        assert format_points_str(0.123) == "0.123"

    def test_large_points(self):
        """Test large point values."""
        assert format_points_str(9999.999) == "9999.999"
        assert format_points_str(10000.000) == "10000"

    @pytest.mark.parametrize("points,expected", [
        (100.000, "100"),
        (95.750, "95.750"),
        (0.000, "0"),
        (0.123, "0.123"),
        (1.000, "1"),
        (99.990, "99.990"),
    ])
    def test_format_points_parametrized(self, points, expected):
        """Parametrized test for various point values."""
        assert format_points_str(points) == expected


@pytest.mark.unit
class TestBuildResponseMessageList:
    """Tests for build_response_message_list() function - ui/ui_util.py:224"""

    # Discord's character limit used in the function
    CHAR_LIMIT = 2000 - 10  # 1990

    def test_none_input(self):
        """Test that None input returns a list with empty string."""
        result = build_response_message_list(None)
        assert result == [""]

    def test_empty_string(self):
        """Test that empty string returns a list with empty string."""
        result = build_response_message_list("")
        assert result == [""]

    def test_under_character_limit(self):
        """Test message under the character limit returns single-item list."""
        message = "This is a short message."
        result = build_response_message_list(message)
        assert len(result) == 1
        assert result[0] == message

    def test_exactly_at_limit(self):
        """Test message exactly at the character limit."""
        message = "A" * self.CHAR_LIMIT
        result = build_response_message_list(message)
        assert len(result) == 1
        assert result[0] == message

    def test_simple_split_over_limit(self):
        """Test message just over limit gets split into two messages."""
        # Create a message with two lines, where combined they exceed the limit
        line1 = "A" * 1000 + "\n"
        line2 = "B" * 1000 + "\n"
        message = line1 + line2
        result = build_response_message_list(message)
        
        assert len(result) == 2
        assert result[0] == line1
        assert result[1] == line2

    def test_multiple_line_split(self):
        """Test message that requires splitting into multiple messages."""
        # Create 5 lines, each 500 chars - should split into 3 messages
        # Message 1: lines 1-3 (1500 chars), Message 2: lines 4-5 (1000 chars)
        lines = [f"Line {i}: " + "X" * 490 + "\n" for i in range(1, 6)]
        message = "".join(lines)
        result = build_response_message_list(message)
        
        # Should be split into at least 2 messages
        assert len(result) >= 2
        # Each result should be under the limit
        for msg in result:
            assert len(msg) <= self.CHAR_LIMIT

    def test_very_long_single_line_with_sentences(self):
        """Test a single line over the limit that needs sentence splitting."""
        # Create a long line with multiple sentences
        sentence = "This is a sentence. "
        # Make enough sentences to exceed the limit
        num_sentences = (self.CHAR_LIMIT // len(sentence)) + 10
        long_line = sentence * num_sentences
        
        result = build_response_message_list(long_line)
        
        # Should be split into multiple messages
        assert len(result) >= 2
        # Each result should be under the limit
        for msg in result:
            assert len(msg) <= self.CHAR_LIMIT

    def test_message_with_newlines_preserved(self):
        """Test that newlines are preserved in the split messages."""
        line1 = "First line\n"
        line2 = "Second line\n"
        line3 = "Third line\n"
        message = line1 + line2 + line3
        
        result = build_response_message_list(message)
        
        assert len(result) == 1
        assert result[0] == message
        # Verify newlines are preserved
        assert result[0].count("\n") == 3

    def test_lines_near_limit_boundary(self):
        """Test splitting behavior when lines are close to the limit."""
        # Create lines where adding one more would exceed the limit
        line = "X" * 900 + "\n"
        # Two lines fit (1800 + 2 newlines = 1802), three don't (2700)
        message = line * 3
        
        result = build_response_message_list(message)
        
        assert len(result) == 2
        assert len(result[0]) <= self.CHAR_LIMIT
        assert len(result[1]) <= self.CHAR_LIMIT

    def test_single_line_no_newline(self):
        """Test message with no newlines under the limit."""
        message = "This is a single line message with no newlines at all."
        result = build_response_message_list(message)
        
        assert len(result) == 1
        assert result[0] == message

    def test_many_short_lines(self):
        """Test message with many short lines that fit in one message."""
        lines = [f"Line {i}\n" for i in range(50)]  # 50 short lines
        message = "".join(lines)
        
        # Should fit in one message since total is under limit
        result = build_response_message_list(message)
        
        assert len(result) == 1
        assert result[0] == message

    def test_mixed_line_lengths(self):
        """Test message with varying line lengths."""
        short_line = "Short\n"
        medium_line = "Medium length line here\n"
        long_line = "X" * 500 + "\n"
        
        message = short_line + medium_line + long_line * 3
        result = build_response_message_list(message)
        
        # Should split appropriately
        assert len(result) >= 1
        # All results should be under limit
        for msg in result:
            assert len(msg) <= self.CHAR_LIMIT

    def test_message_with_multiple_newlines(self):
        """Test message with consecutive newlines (blank lines)."""
        message = "Line 1\n\n\nLine 2 after blank lines\n"
        result = build_response_message_list(message)
        
        assert len(result) == 1
        # Blank lines should be preserved
        assert result[0] == message


@pytest.mark.unit
class TestGetUserNameStr:
    """Tests for get_user_name_str() function - ui/ui_util.py:537"""

    def test_user_with_global_name(self):
        """Test user with global_name returns global_name."""
        user_id = 123456789
        user = create_mock_user(user_id=user_id, global_name="GlobalName", display_name="DisplayName")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "GlobalName"

    def test_user_with_global_name_none_string(self):
        """Test user with global_name as string 'None' falls back to display_name."""
        user_id = 123456789
        user = create_mock_user(user_id=user_id, global_name="None", display_name="DisplayName")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "DisplayName"

    def test_user_with_only_display_name(self):
        """Test user without global_name returns display_name."""
        user_id = 123456789
        user = create_mock_user(user_id=user_id, global_name=None, display_name="DisplayName")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "DisplayName"

    def test_none_user_returns_user_id(self):
        """Test None user returns user_id as string."""
        user_id = 987654321
        
        result = get_user_name_str(user_id, None)
        
        assert result == "987654321"
        assert result == str(user_id)

    def test_user_with_empty_global_name(self):
        """Test user with empty string global_name falls back to display_name."""
        user_id = 123456789
        user = create_mock_user(user_id=user_id, global_name="", display_name="DisplayName")
        
        result = get_user_name_str(user_id, user)
        
        # Empty string is falsy, but function checks for None specifically
        # So empty string should be returned if it's not None
        assert result == ""

    def test_preference_order(self):
        """Test that global_name is preferred over display_name."""
        user_id = 111222333
        
        # User with both names
        user = create_mock_user(
            user_id=user_id,
            global_name="PreferredGlobalName",
            display_name="FallbackDisplayName"
        )
        
        result = get_user_name_str(user_id, user)
        
        # Should prefer global_name
        assert result == "PreferredGlobalName"
        assert result != "FallbackDisplayName"

    @pytest.mark.parametrize("user_id,global_name,display_name,expected", [
        (123, "Global", "Display", "Global"),           # Normal case with global_name
        (456, None, "Display", "Display"),               # No global_name
        (789, "None", "Display", "Display"),             # global_name is string "None"
        (111, "", "Display", ""),                        # Empty global_name
        (222, "ValidGlobal", "Display", "ValidGlobal"),  # Both present, prefer global
    ])
    def test_user_name_parametrized(self, user_id, global_name, display_name, expected):
        """Parametrized test for various user name scenarios."""
        user = create_mock_user(user_id=user_id, global_name=global_name, display_name=display_name)
        result = get_user_name_str(user_id, user)
        assert result == expected

    def test_none_user_with_different_user_ids(self):
        """Test None user returns correct user_id string for different IDs."""
        test_ids = [1, 42, 123456789, 999999999999]
        
        for user_id in test_ids:
            result = get_user_name_str(user_id, None)
            assert result == str(user_id)
            # Verify it's actually a string
            assert isinstance(result, str)

    def test_user_with_emoji_in_global_name(self):
        """Test user with emoji in global_name handles Unicode correctly."""
        user_id = 123456789
        global_name_with_emoji = "CoolUser 😎🎮"
        user = create_mock_user(user_id=user_id, global_name=global_name_with_emoji, display_name="PlainName")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "CoolUser 😎🎮"
        assert "😎" in result
        assert "🎮" in result

    def test_user_with_emoji_in_display_name(self):
        """Test user with emoji in display_name when no global_name."""
        user_id = 987654321
        display_name_with_emoji = "RacerBoi 🏎️💨"
        user = create_mock_user(user_id=user_id, global_name=None, display_name=display_name_with_emoji)
        
        result = get_user_name_str(user_id, user)
        
        assert result == "RacerBoi 🏎️💨"
        assert "🏎️" in result
        assert "💨" in result

    def test_user_with_japanese_characters(self):
        """Test user with Japanese characters in name."""
        user_id = 111222333
        japanese_name = "さくら桜子"
        user = create_mock_user(user_id=user_id, global_name=japanese_name, display_name="Sakura")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "さくら桜子"
        assert "桜" in result

    def test_user_with_cyrillic_characters(self):
        """Test user with Cyrillic (Russian) characters in name."""
        user_id = 444555666
        cyrillic_name = "Александр"
        user = create_mock_user(user_id=user_id, global_name=cyrillic_name, display_name="Alexander")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "Александр"

    def test_user_with_arabic_characters(self):
        """Test user with Arabic characters in name."""
        user_id = 777888999
        arabic_name = "محمد"
        user = create_mock_user(user_id=user_id, global_name=arabic_name, display_name="Mohammed")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "محمد"

    def test_user_with_special_unicode_symbols(self):
        """Test user with various special Unicode symbols."""
        user_id = 123123123
        name_with_symbols = "★彡[ᴜsᴇʀ]彡★"
        user = create_mock_user(user_id=user_id, global_name=name_with_symbols, display_name="User")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "★彡[ᴜsᴇʀ]彡★"
        assert "★" in result

    def test_user_with_mixed_emoji_and_text(self):
        """Test user with mixed emoji, text, and special characters."""
        user_id = 999888777
        complex_name = "🔥 xX_Pro_Gamer_Xx 🔥"
        user = create_mock_user(user_id=user_id, global_name=complex_name, display_name="ProGamer")
        
        result = get_user_name_str(user_id, user)
        
        assert result == "🔥 xX_Pro_Gamer_Xx 🔥"
        assert len(result) > 0
        # Ensure emoji are preserved
        assert result.startswith("🔥")
        assert result.endswith("🔥")

    @pytest.mark.parametrize("user_id,name,description", [
        (101, "用户名", "Chinese characters"),
        (102, "사용자", "Korean characters"),
        (103, "ผู้ใช้", "Thai characters"),
        (104, "🎭🎪🎨", "Multiple emojis only"),
        (105, "Ñoño", "Spanish special characters"),
        (106, "Müller", "German umlaut"),
        (107, "Søren", "Scandinavian characters"),
        (108, "Αλέξανδρος", "Greek characters"),
        (109, "🏆 チャンピオン 👑", "Mixed emoji and Japanese"),
        (110, "♠️♥️♣️♦️", "Card suit symbols"),
    ])
    def test_unicode_characters_parametrized(self, user_id, name, description):
        """Parametrized test for various Unicode character sets."""
        user = create_mock_user(user_id=user_id, global_name=name, display_name="Fallback")
        result = get_user_name_str(user_id, user)
        assert result == name
        # Verify the string isn't mangled
        assert len(result) > 0


@pytest.mark.unit
class TestGetRaceEmbedFieldValue:
    """Tests for get_race_embed_field_value() function - ui/ui_util.py:344"""

    @patch('ui.ui_util.get_num_submissions')
    def test_without_user_id_shows_description(self, mock_get_num_submissions):
        """Test that when no user_id is provided, the race description is shown."""
        # Setup
        mock_get_num_submissions.return_value = 5
        category = create_mock_category(name="Test Category")
        race = create_mock_race(race_id=1, category_id=category, description="Epic Race Description")
        
        # Execute
        result = get_race_embed_field_value(race, user_id=None)
        
        # Verify
        assert "**Category:**" in result
        assert "Test Category" in result
        assert "**Submissions:** 5" in result
        assert "**Description:**" in result
        assert "Epic Race Description" in result
        # Should NOT contain place info
        assert "**Place:**" not in result
        
        # Verify the mock was called correctly
        mock_get_num_submissions.assert_called_once_with(1)

    @patch('ui.ui_util.get_user_place')
    @patch('ui.ui_util.get_num_submissions')
    def test_with_user_id_shows_place(self, mock_get_num_submissions, mock_get_user_place):
        """Test that when user_id is provided, the user's place is shown."""
        # Setup
        mock_get_num_submissions.return_value = 10
        mock_get_user_place.return_value = 3  # User is in 3rd place
        category = create_mock_category(name="Speedrun Category")
        race = create_mock_race(race_id=2, category_id=category, description="Should not appear")
        user_id = 123456789
        
        # Execute
        result = get_race_embed_field_value(race, user_id=user_id)
        
        # Verify
        assert "**Category:**" in result
        assert "Speedrun Category" in result
        assert "**Submissions:** 10" in result
        assert "**Place:** 3rd" in result  # Should show ordinal place
        # Should NOT contain description
        assert "**Description:**" not in result
        assert "Should not appear" not in result
        
        # Verify the mocks were called correctly
        mock_get_num_submissions.assert_called_once_with(2)
        mock_get_user_place.assert_called_once_with(2, user_id)

    @patch('ui.ui_util.get_user_place')
    @patch('ui.ui_util.get_num_submissions')
    def test_with_user_id_but_no_place(self, mock_get_num_submissions, mock_get_user_place):
        """Test when user_id is provided but user has no place (no submission yet)."""
        # Setup
        mock_get_num_submissions.return_value = 5
        mock_get_user_place.return_value = None  # User hasn't submitted
        category = create_mock_category(name="Test Category")
        race = create_mock_race(race_id=3, category_id=category)
        user_id = 999888777
        
        # Execute
        result = get_race_embed_field_value(race, user_id=user_id)
        
        # Verify
        assert "**Category:**" in result
        assert "**Submissions:** 5" in result
        # Should NOT show place if user hasn't submitted
        assert "**Place:**" not in result

    @patch('ui.ui_util.get_num_submissions')
    def test_with_zero_submissions(self, mock_get_num_submissions):
        """Test field value when race has no submissions yet."""
        # Setup
        mock_get_num_submissions.return_value = 0
        category = create_mock_category(name="New Category")
        race = create_mock_race(race_id=4, category_id=category, description="Brand new race")
        
        # Execute
        result = get_race_embed_field_value(race, user_id=None)
        
        # Verify
        assert "**Submissions:** 0" in result
        assert "New Category" in result
        assert "Brand new race" in result

    @patch('ui.ui_util.get_user_place')
    @patch('ui.ui_util.get_num_submissions')
    def test_first_place_user(self, mock_get_num_submissions, mock_get_user_place):
        """Test displaying 1st place for a user."""
        # Setup
        mock_get_num_submissions.return_value = 20
        mock_get_user_place.return_value = 1
        category = create_mock_category(name="Competitive Category")
        race = create_mock_race(race_id=5, category_id=category)
        
        # Execute
        result = get_race_embed_field_value(race, user_id=123)
        
        # Verify
        assert "**Place:** 1st" in result
        assert "**Submissions:** 20" in result

    @patch('ui.ui_util.get_user_place')
    @patch('ui.ui_util.get_num_submissions')
    def test_various_user_places(self, mock_get_num_submissions, mock_get_user_place):
        """Test that place ordinals are formatted correctly for various positions."""
        mock_get_num_submissions.return_value = 100
        category = create_mock_category(name="Big Race")
        race = create_mock_race(race_id=6, category_id=category)
        
        # Test various places
        test_cases = [
            (1, "1st"),
            (2, "2nd"),
            (3, "3rd"),
            (11, "11th"),
            (21, "21st"),
            (42, "42nd"),
        ]
        
        for place, expected_str in test_cases:
            mock_get_user_place.return_value = place
            result = get_race_embed_field_value(race, user_id=999)
            assert f"**Place:** {expected_str}" in result

    @patch('ui.ui_util.get_num_submissions')
    def test_multiline_description_preserved(self, mock_get_num_submissions):
        """Test that multiline descriptions are preserved in the output."""
        # Setup
        mock_get_num_submissions.return_value = 3
        category = create_mock_category(name="Test Category")
        multiline_desc = "Line 1 of description\nLine 2 of description\nLine 3 of description"
        race = create_mock_race(race_id=7, category_id=category, description=multiline_desc)
        
        # Execute
        result = get_race_embed_field_value(race, user_id=None)
        
        # Verify
        assert "Line 1 of description" in result
        assert "Line 2 of description" in result
        assert "Line 3 of description" in result
        # Newlines should be preserved
        assert "\n" in result

    @patch('ui.ui_util.get_num_submissions')
    def test_category_name_with_emoji(self, mock_get_num_submissions):
        """Test that emoji in category names are handled correctly."""
        # Setup
        mock_get_num_submissions.return_value = 8
        category = create_mock_category(name="🏆 Championship 🏆")
        race = create_mock_race(race_id=8, category_id=category, description="Test race")
        
        # Execute
        result = get_race_embed_field_value(race, user_id=None)
        
        # Verify
        assert "🏆 Championship 🏆" in result
        assert "**Category:**" in result

    @patch('ui.ui_util.get_num_submissions')
    def test_large_submission_count(self, mock_get_num_submissions):
        """Test handling of large submission counts."""
        # Setup
        mock_get_num_submissions.return_value = 9999
        category = create_mock_category(name="Popular Category")
        race = create_mock_race(race_id=9, category_id=category)
        
        # Execute
        result = get_race_embed_field_value(race, user_id=None)
        
        # Verify
        assert "**Submissions:** 9999" in result

    @patch('ui.ui_util.get_user_place')
    @patch('ui.ui_util.get_num_submissions')
    def test_format_structure(self, mock_get_num_submissions, mock_get_user_place):
        """Test the overall format structure of the field value."""
        # Test without user_id
        mock_get_num_submissions.return_value = 5
        category = create_mock_category(name="Test Cat")
        race = create_mock_race(race_id=10, category_id=category, description="Test Desc")
        
        result = get_race_embed_field_value(race, user_id=None)
        
        # Verify structure order
        category_pos = result.find("**Category:**")
        submissions_pos = result.find("**Submissions:**")
        description_pos = result.find("**Description:**")
        
        assert category_pos < submissions_pos < description_pos

