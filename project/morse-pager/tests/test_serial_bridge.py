"""Tests for serial_bridge.py — plain text serial parsing."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi"))

from serial_bridge import parse_serial_line


class TestParseSerialLine:
    def test_tap_event(self):
        result = parse_serial_line("TAP,120000")
        assert result == {"node": "A", "type": "tap", "duration_us": 120000}

    def test_gap_event(self):
        result = parse_serial_line("GAP,80000")
        assert result == {"node": "A", "type": "gap", "duration_us": 80000}

    def test_case_insensitive(self):
        result = parse_serial_line("tap,50000")
        assert result is not None
        assert result["type"] == "tap"

    def test_with_trailing_newline(self):
        result = parse_serial_line("TAP,120000\n")
        assert result is not None
        assert result["duration_us"] == 120000

    def test_with_trailing_carriage_return(self):
        result = parse_serial_line("TAP,120000\r\n")
        assert result is not None
        assert result["duration_us"] == 120000

    def test_empty_string(self):
        assert parse_serial_line("") is None

    def test_whitespace_only(self):
        assert parse_serial_line("   ") is None

    def test_invalid_type(self):
        assert parse_serial_line("CLICK,120000") is None

    def test_missing_duration(self):
        assert parse_serial_line("TAP") is None

    def test_non_numeric_duration(self):
        assert parse_serial_line("TAP,abc") is None

    def test_extra_commas(self):
        assert parse_serial_line("TAP,120000,extra") is None

    def test_json_input_rejected(self):
        """Old JSON format should be rejected."""
        assert parse_serial_line('{"node":"A","type":"tap","duration_us":120000}') is None

    def test_zero_duration(self):
        result = parse_serial_line("TAP,0")
        assert result is not None
        assert result["duration_us"] == 0

    def test_large_duration(self):
        result = parse_serial_line("GAP,5000000")
        assert result is not None
        assert result["duration_us"] == 5000000

    def test_spaces_around_values(self):
        result = parse_serial_line(" TAP , 120000 ")
        assert result is not None
        assert result["type"] == "tap"
        assert result["duration_us"] == 120000
