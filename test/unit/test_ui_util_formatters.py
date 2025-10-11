# -*- coding: utf-8 -*-
"""
Unit tests for UI utility formatting functions.
Tests pure functions from ui/ui_util.py with no external dependencies.
"""
import pytest
from ui.ui_util import get_place_str, format_points_str


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

