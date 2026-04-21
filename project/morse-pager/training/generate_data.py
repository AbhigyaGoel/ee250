"""
Synthetic Morse code training data generator.

Generates tap/gap duration samples by simulating realistic Morse code sessions.
Instead of shuffling events randomly (which creates a training/inference mismatch
in the running session mean), this generates events in natural Morse sequence
order: tap, intra-gap, tap, intra-gap, ..., inter-letter-gap, ..., word-gap.

This ensures the running mean evolves during training the same way it does
during real-time inference.

Classes:
    0 = dot, 1 = dash, 2 = intra-letter gap, 3 = inter-letter gap, 4 = word gap
"""

import csv
import os
import random

import numpy as np

LABEL_NAMES = ["dot", "dash", "intra_letter_gap", "inter_letter_gap", "word_gap"]

TIMING_RATIOS = {
    "dot": 1.0,
    "dash": 3.0,
    "intra_letter_gap": 1.0,
    "inter_letter_gap": 3.0,
    "word_gap": 7.0,
}

IS_TAP = {
    "dot": True,
    "dash": True,
    "intra_letter_gap": False,
    "inter_letter_gap": False,
    "word_gap": False,
}

# Morse encoding for common words used to generate realistic sequences
MORSE_TABLE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..",
    "9": "----.",
}

# Words to generate sessions from (covers a wide range of Morse patterns)
VOCABULARY = [
    "THE", "BE", "TO", "OF", "AND", "A", "IN", "THAT", "HAVE", "I",
    "IT", "FOR", "NOT", "ON", "WITH", "HE", "AS", "YOU", "DO", "AT",
    "THIS", "BUT", "HIS", "BY", "FROM", "THEY", "WE", "SAY", "HER", "SHE",
    "OR", "AN", "WILL", "MY", "ONE", "ALL", "WOULD", "THERE", "THEIR", "WHAT",
    "SO", "UP", "OUT", "IF", "ABOUT", "WHO", "GET", "WHICH", "GO", "ME",
    "SOS", "HELP", "HELLO", "WORLD", "MORSE", "CODE", "TEST", "QUICK", "FOX",
    "JUMP", "OVER", "LAZY", "DOG", "ZERO", "FIVE", "NINE",
]

WPM_SPEEDS = [10, 15, 20, 25]
NOISE_STD_FRACTION = 0.15
TARGET_SAMPLES = 50000
SESSIONS_PER_SPEED = 150  # Number of simulated sessions per WPM


def wpm_to_dit_ms(wpm: int) -> float:
    """Convert words-per-minute to dit duration in milliseconds.

    Standard: PARIS = 50 dit units, so dit_ms = 1200 / WPM.
    """
    return 1200.0 / wpm


def generate_morse_session(words: list, wpm: int, rng: np.random.Generator) -> list:
    """Generate a sequence of (duration_ms, is_tap, label_idx) for a Morse session.

    Simulates typing the given words with natural Morse timing + noise.
    Returns events in the order they'd naturally occur.
    """
    dit_ms = wpm_to_dit_ms(wpm)
    events = []

    def noisy_duration(label_name: str) -> float:
        ideal = TIMING_RATIOS[label_name] * dit_ms
        noise_std = ideal * NOISE_STD_FRACTION
        dur = rng.normal(ideal, noise_std)
        return max(dur, ideal * 0.3)

    for word_idx, word in enumerate(words):
        for char_idx, char in enumerate(word):
            morse = MORSE_TABLE.get(char)
            if not morse:
                continue

            for symbol_idx, symbol in enumerate(morse):
                # Tap: dot or dash
                if symbol == ".":
                    events.append((noisy_duration("dot"), 1, 0))
                else:
                    events.append((noisy_duration("dash"), 1, 1))

                # Intra-letter gap after each symbol except the last in the letter
                if symbol_idx < len(morse) - 1:
                    events.append((noisy_duration("intra_letter_gap"), 0, 2))

            # Inter-letter gap after each letter except the last in the word
            if char_idx < len(word) - 1:
                events.append((noisy_duration("inter_letter_gap"), 0, 3))

        # Word gap after each word except the last
        if word_idx < len(words) - 1:
            events.append((noisy_duration("word_gap"), 0, 4))

    return events


def compute_features_sequential(events: list) -> list:
    """Compute session-normalized features for a sequence of events.

    Processes events in order, maintaining running state — exactly matching
    how SessionState works during real-time inference.
    """
    rows = []
    running_sum = 0.0
    running_count = 0
    prev_duration = None

    for dur, is_tap, label in events:
        running_count += 1
        running_sum += dur

        running_mean = running_sum / running_count
        norm_by_mean = dur / running_mean if running_mean > 0 else 1.0
        rel_ratio = dur / prev_duration if prev_duration and prev_duration > 0 else 1.0

        rows.append({
            "raw_duration_ms": round(dur, 3),
            "norm_by_session_mean": round(norm_by_mean, 4),
            "relative_ratio": round(rel_ratio, 4),
            "is_tap": is_tap,
            "label": label,
        })

        prev_duration = dur

    return rows


def generate_samples(wpm: int, n_per_class: int, rng: np.random.Generator) -> list:
    """Generate synthetic samples for a given WPM speed.

    Kept for backward compatibility with tests. Returns raw (dur, is_tap, label, wpm) tuples.
    """
    dit_ms = wpm_to_dit_ms(wpm)
    samples = []

    for label_idx, label_name in enumerate(LABEL_NAMES):
        ideal_duration = TIMING_RATIOS[label_name] * dit_ms
        noise_std = ideal_duration * NOISE_STD_FRACTION
        is_tap = 1 if IS_TAP[label_name] else 0

        durations = rng.normal(ideal_duration, noise_std, size=n_per_class)
        durations = np.clip(durations, ideal_duration * 0.3, ideal_duration * 2.5)

        for dur in durations:
            samples.append((dur, is_tap, label_idx, wpm))

    return samples


def compute_features(samples: list, rng: np.random.Generator) -> list:
    """Compute features using sequential Morse sessions.

    Instead of shuffling all events, generates realistic Morse sessions and
    processes them in natural order so the running mean matches inference.
    Kept for backward compatibility — delegates to session-based generation.
    """
    # For backward compat with tests that call this directly,
    # process each WPM group sequentially (not shuffled)
    rows = []
    by_wpm = {}
    for dur, is_tap, label, wpm in samples:
        by_wpm.setdefault(wpm, []).append((dur, is_tap, label))

    for wpm, group in by_wpm.items():
        # Process in order (not shuffled) — events from generate_samples
        # are already grouped by class, so interleave them to simulate sessions
        # Split into mini-sessions of ~50 events
        session_size = 50
        for start in range(0, len(group), session_size):
            chunk = group[start:start + session_size]
            rows.extend(compute_features_sequential(chunk))

    return rows


def main():
    rng = np.random.default_rng(seed=42)
    all_rows = []

    for wpm in WPM_SPEEDS:
        for session_idx in range(SESSIONS_PER_SPEED):
            # Pick 3-8 random words per session
            n_words = rng.integers(3, 9)
            words = [VOCABULARY[rng.integers(0, len(VOCABULARY))] for _ in range(n_words)]

            events = generate_morse_session(words, wpm, rng)
            rows = compute_features_sequential(events)
            all_rows.extend(rows)

    print(f"Generated {len(all_rows)} samples from realistic Morse sessions")

    # Print class distribution
    from collections import Counter
    dist = Counter(r["label"] for r in all_rows)
    for label_idx, name in enumerate(LABEL_NAMES):
        print(f"  {name}: {dist.get(label_idx, 0)}")

    random.seed(42)
    random.shuffle(all_rows)

    output_path = os.path.join(os.path.dirname(__file__), "training_data.csv")
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["raw_duration_ms", "norm_by_session_mean", "relative_ratio", "is_tap", "label"],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
