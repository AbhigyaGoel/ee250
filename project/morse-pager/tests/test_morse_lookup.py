"""Tests for morse_lookup.py — lookup table, encode, decode."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi"))

from morse_lookup import (
    MORSE_TO_CHAR,
    CHAR_TO_MORSE,
    decode_morse_sequence,
    encode_char,
    encode_text,
)


# --- decode_morse_sequence ---

class TestDecodeMorseSequence:
    def test_all_letters(self):
        for morse, expected in MORSE_TO_CHAR.items():
            assert decode_morse_sequence(morse) == expected

    def test_unknown_sequence_returns_question_mark(self):
        assert decode_morse_sequence("........") == "?"
        assert decode_morse_sequence("") == "?"

    def test_common_letters(self):
        assert decode_morse_sequence(".-") == "A"
        assert decode_morse_sequence("...") == "S"
        assert decode_morse_sequence("---") == "O"
        assert decode_morse_sequence(".") == "E"
        assert decode_morse_sequence("-") == "T"


# --- encode_char ---

class TestEncodeChar:
    def test_all_chars_roundtrip(self):
        for char, morse in CHAR_TO_MORSE.items():
            assert encode_char(char) == morse

    def test_case_insensitive(self):
        assert encode_char("a") == ".-"
        assert encode_char("A") == ".-"
        assert encode_char("s") == "..."
        assert encode_char("S") == "..."

    def test_unknown_char_returns_empty(self):
        assert encode_char("~") == ""
        assert encode_char(" ") == ""
        assert encode_char("\n") == ""

    def test_digits(self):
        assert encode_char("0") == "-----"
        assert encode_char("1") == ".----"
        assert encode_char("9") == "----."


# --- encode_text ---

class TestEncodeText:
    def test_single_word(self):
        result = encode_text("SOS")
        assert result == "... --- ..."

    def test_two_words(self):
        result = encode_text("HI THERE")
        assert " / " in result
        assert result == ".... .. / - .... . .-. ."

    def test_case_insensitive(self):
        assert encode_text("sos") == encode_text("SOS")

    def test_empty_string(self):
        assert encode_text("") == ""

    def test_single_letter(self):
        assert encode_text("E") == "."
        assert encode_text("T") == "-"

    def test_unknown_chars_skipped(self):
        # Characters not in lookup should be silently dropped
        result = encode_text("A~B")
        assert result == ".- -..."

    def test_roundtrip_letters(self):
        """Encode then decode each letter should get original back."""
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            morse = encode_char(char)
            decoded = decode_morse_sequence(morse)
            assert decoded == char, f"Roundtrip failed for {char}: {morse} -> {decoded}"


# --- Table consistency ---

class TestTableConsistency:
    def test_reverse_map_matches(self):
        """CHAR_TO_MORSE should be exact inverse of MORSE_TO_CHAR."""
        assert len(CHAR_TO_MORSE) == len(MORSE_TO_CHAR)
        for morse, char in MORSE_TO_CHAR.items():
            assert CHAR_TO_MORSE[char] == morse

    def test_no_duplicate_morse_codes(self):
        codes = list(MORSE_TO_CHAR.keys())
        assert len(codes) == len(set(codes))

    def test_no_duplicate_characters(self):
        chars = list(MORSE_TO_CHAR.values())
        assert len(chars) == len(set(chars))
