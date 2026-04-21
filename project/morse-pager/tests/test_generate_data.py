"""Tests for generate_data.py — synthetic data generation."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "training"))

import numpy as np
from generate_data import (
    wpm_to_dit_ms,
    generate_samples,
    compute_features,
    LABEL_NAMES,
    TIMING_RATIOS,
    IS_TAP,
)


class TestWpmToDitMs:
    def test_standard_speeds(self):
        # PARIS standard: dit_ms = 1200 / WPM
        assert wpm_to_dit_ms(10) == 120.0
        assert wpm_to_dit_ms(15) == 80.0
        assert wpm_to_dit_ms(20) == 60.0
        assert wpm_to_dit_ms(25) == 48.0

    def test_proportional(self):
        # Faster WPM = shorter dit
        assert wpm_to_dit_ms(20) < wpm_to_dit_ms(10)
        assert wpm_to_dit_ms(25) < wpm_to_dit_ms(15)


class TestGenerateSamples:
    def setup_method(self):
        self.rng = np.random.default_rng(seed=99)

    def test_sample_count(self):
        samples = generate_samples(15, 100, self.rng)
        # 5 classes * 100 per class = 500
        assert len(samples) == 500

    def test_sample_structure(self):
        samples = generate_samples(20, 10, self.rng)
        for dur, is_tap, label_idx, wpm in samples:
            assert isinstance(dur, (float, np.floating))
            assert is_tap in (0, 1)
            assert 0 <= label_idx <= 4
            assert wpm == 20

    def test_durations_positive(self):
        samples = generate_samples(10, 500, self.rng)
        for dur, _, _, _ in samples:
            assert dur > 0

    def test_dot_shorter_than_dash(self):
        samples = generate_samples(15, 1000, self.rng)
        dots = [dur for dur, _, label, _ in samples if label == 0]
        dashes = [dur for dur, _, label, _ in samples if label == 1]
        assert np.mean(dots) < np.mean(dashes)

    def test_is_tap_matches_label(self):
        samples = generate_samples(20, 100, self.rng)
        for _, is_tap, label_idx, _ in samples:
            label_name = LABEL_NAMES[label_idx]
            expected = 1 if IS_TAP[label_name] else 0
            assert is_tap == expected

    def test_timing_ratios_approximate(self):
        """Mean durations should roughly match timing ratios."""
        samples = generate_samples(15, 2000, self.rng)
        dit_ms = wpm_to_dit_ms(15)

        by_label = {}
        for dur, _, label_idx, _ in samples:
            by_label.setdefault(label_idx, []).append(dur)

        for label_idx, name in enumerate(LABEL_NAMES):
            expected = TIMING_RATIOS[name] * dit_ms
            actual_mean = np.mean(by_label[label_idx])
            # Within 10% of ideal
            assert abs(actual_mean - expected) / expected < 0.10, (
                f"{name}: expected ~{expected:.1f}, got {actual_mean:.1f}"
            )


class TestComputeFeatures:
    def setup_method(self):
        self.rng = np.random.default_rng(seed=42)

    def test_feature_count(self):
        samples = generate_samples(15, 50, self.rng)
        rows = compute_features(samples, self.rng)
        assert len(rows) == len(samples)

    def test_feature_keys(self):
        samples = generate_samples(20, 10, self.rng)
        rows = compute_features(samples, self.rng)
        expected_keys = {"raw_duration_ms", "norm_by_session_mean", "relative_ratio", "is_tap", "label"}
        for row in rows:
            assert set(row.keys()) == expected_keys

    def test_raw_duration_positive(self):
        samples = generate_samples(10, 100, self.rng)
        rows = compute_features(samples, self.rng)
        for row in rows:
            assert row["raw_duration_ms"] > 0

    def test_is_tap_binary(self):
        samples = generate_samples(15, 100, self.rng)
        rows = compute_features(samples, self.rng)
        for row in rows:
            assert row["is_tap"] in (0, 1)

    def test_label_range(self):
        samples = generate_samples(20, 100, self.rng)
        rows = compute_features(samples, self.rng)
        for row in rows:
            assert 0 <= row["label"] <= 4

    def test_norm_by_mean_first_sample_is_one(self):
        """First sample in a session should have norm_by_mean = 1.0
        (duration / mean = duration / duration = 1.0)."""
        # Generate for single WPM so there's one session group
        samples = generate_samples(15, 5, self.rng)
        rows = compute_features(samples, np.random.default_rng(seed=0))
        assert rows[0]["norm_by_session_mean"] == 1.0

    def test_relative_ratio_first_sample_is_one(self):
        """First sample has no previous, so relative ratio defaults to 1.0."""
        samples = generate_samples(15, 5, self.rng)
        rows = compute_features(samples, np.random.default_rng(seed=0))
        assert rows[0]["relative_ratio"] == 1.0
