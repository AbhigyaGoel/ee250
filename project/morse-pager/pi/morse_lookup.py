# AI-assisted development (Claude Code, Anthropic)
"""
Morse code lookup table.

Maps dot/dash sequences to characters and vice versa.
"""

# Morse code: dot = '.', dash = '-'
MORSE_TO_CHAR = {
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
    "-----": "0",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9",
    ".-.-.-": ".",
    "--..--": ",",
    "..--..": "?",
    ".----.": "'",
    "-.-.--": "!",
    "-..-.": "/",
    "-.--.": "(",
    "-.--.-": ")",
    ".-...": "&",
    "---...": ":",
    "-.-.-.": ";",
    "-...-": "=",
    ".-.-.": "+",
    "-....-": "-",
    "..--.-": "_",
    ".-..-.": '"',
    "...-..-": "$",
    ".--.-.": "@",
}

CHAR_TO_MORSE = {v: k for k, v in MORSE_TO_CHAR.items()}


def decode_morse_sequence(sequence: str) -> str:
    """Look up a dot/dash sequence and return the character, or '?' if unknown."""
    return MORSE_TO_CHAR.get(sequence, "?")


def encode_char(char: str) -> str:
    """Encode a single character to its Morse dot/dash sequence."""
    return CHAR_TO_MORSE.get(char.upper(), "")


def encode_text(text: str) -> str:
    """Encode text to Morse code string.

    Letters separated by ' ', words separated by ' / '.
    """
    words = text.upper().split()
    encoded_words = []
    for word in words:
        letters = [encode_char(c) for c in word if encode_char(c)]
        encoded_words.append(" ".join(letters))
    return " / ".join(encoded_words)
