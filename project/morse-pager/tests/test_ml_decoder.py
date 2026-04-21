"""Tests for ml_decoder.py — SessionState and decode pipeline."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi"))

import numpy as np

from ml_decoder import SessionState, LABEL_NAMES, TOPIC_ALERT
from rf_lite import RFLite


class TestSessionState:
    def test_initial_state(self):
        s = SessionState()
        assert s.running_sum == 0.0
        assert s.running_count == 0
        assert s.prev_duration is None
        assert s.letter_buffer == []
        assert s.message == ""

    def test_compute_features_shape(self):
        s = SessionState()
        features = s.compute_features(100.0, 1)
        assert features.shape == (1, 4)

    def test_compute_features_first_event(self):
        s = SessionState()
        features = s.compute_features(120.0, 1)
        raw, norm, ratio, is_tap = features[0]
        assert raw == 120.0
        assert norm == 1.0  # first event: dur / dur = 1.0
        assert ratio == 1.0  # no previous: default 1.0
        assert is_tap == 1

    def test_compute_features_updates_running_state(self):
        s = SessionState()
        s.compute_features(100.0, 1)
        assert s.running_count == 1
        assert s.running_sum == 100.0
        assert s.prev_duration == 100.0

        s.compute_features(200.0, 0)
        assert s.running_count == 2
        assert s.running_sum == 300.0
        assert s.prev_duration == 200.0

    def test_compute_features_normalization(self):
        s = SessionState()
        s.compute_features(100.0, 1)  # mean=100, norm=1.0

        features = s.compute_features(200.0, 0)
        raw, norm, ratio, is_tap = features[0]
        assert raw == 200.0
        # mean = (100+200)/2 = 150, norm = 200/150 = 1.333...
        assert abs(norm - 200.0 / 150.0) < 0.001
        # ratio = 200/100 = 2.0
        assert abs(ratio - 2.0) < 0.001
        assert is_tap == 0

    def test_compute_features_is_tap_flag(self):
        s = SessionState()
        f1 = s.compute_features(100.0, 1)
        assert f1[0, 3] == 1
        f2 = s.compute_features(100.0, 0)
        assert f2[0, 3] == 0

    def test_letter_buffer_accumulation(self):
        s = SessionState()
        s.letter_buffer.append(".")
        s.letter_buffer.append(".")
        s.letter_buffer.append(".")
        assert "".join(s.letter_buffer) == "..."

    def test_letter_buffer_clear_on_decode(self):
        s = SessionState()
        s.letter_buffer = [".", "-"]
        morse_seq = "".join(s.letter_buffer)
        s.letter_buffer = []
        assert morse_seq == ".-"
        assert s.letter_buffer == []

    def test_message_accumulation(self):
        s = SessionState()
        s.message += "H"
        s.message += "I"
        s.message += " "
        assert s.message == "HI "


class TestDecodeLogic:
    """Test the decode logic from ml_decoder without MQTT."""

    def _simulate_decode(self, label_sequence):
        """Simulate the decode logic from on_message.

        label_sequence: list of label names (e.g. ["dot", "intra_letter_gap", "dash", ...])
        Returns the session state after processing.
        """
        from morse_lookup import decode_morse_sequence

        session = SessionState()

        for label_name in label_sequence:
            decoded_char = None

            if label_name == "dot":
                session.letter_buffer.append(".")
            elif label_name == "dash":
                session.letter_buffer.append("-")
            elif label_name == "inter_letter_gap":
                if session.letter_buffer:
                    morse_seq = "".join(session.letter_buffer)
                    decoded_char = decode_morse_sequence(morse_seq)
                    session.message += decoded_char
                    session.letter_buffer = []
            elif label_name == "word_gap":
                if session.letter_buffer:
                    morse_seq = "".join(session.letter_buffer)
                    decoded_char = decode_morse_sequence(morse_seq)
                    session.message += decoded_char
                    session.letter_buffer = []
                session.message += " "

        return session

    def test_decode_sos(self):
        # S = ..., O = ---
        labels = [
            "dot", "intra_letter_gap", "dot", "intra_letter_gap", "dot",
            "inter_letter_gap",
            "dash", "intra_letter_gap", "dash", "intra_letter_gap", "dash",
            "inter_letter_gap",
            "dot", "intra_letter_gap", "dot", "intra_letter_gap", "dot",
            "inter_letter_gap",
        ]
        session = self._simulate_decode(labels)
        assert session.message == "SOS"

    def test_decode_hi(self):
        # H = ...., I = ..
        labels = [
            "dot", "intra_letter_gap", "dot", "intra_letter_gap",
            "dot", "intra_letter_gap", "dot",
            "inter_letter_gap",
            "dot", "intra_letter_gap", "dot",
            "inter_letter_gap",
        ]
        session = self._simulate_decode(labels)
        assert session.message == "HI"

    def test_decode_with_word_gap(self):
        # H I <space> E
        labels = [
            "dot", "intra_letter_gap", "dot", "intra_letter_gap",
            "dot", "intra_letter_gap", "dot",
            "inter_letter_gap",
            "dot", "intra_letter_gap", "dot",
            "word_gap",
            "dot",
            "inter_letter_gap",
        ]
        session = self._simulate_decode(labels)
        assert session.message == "HI E"

    def test_decode_single_letter_e(self):
        labels = ["dot", "inter_letter_gap"]
        session = self._simulate_decode(labels)
        assert session.message == "E"

    def test_decode_single_letter_t(self):
        labels = ["dash", "inter_letter_gap"]
        session = self._simulate_decode(labels)
        assert session.message == "T"

    def test_decode_unknown_sequence(self):
        # 8 dots is not valid Morse
        labels = ["dot"] * 8 + ["inter_letter_gap"]
        session = self._simulate_decode(labels)
        assert session.message == "?"

    def test_word_gap_with_empty_buffer(self):
        """Word gap when buffer is empty should just add space."""
        labels = ["dot", "inter_letter_gap", "word_gap"]
        session = self._simulate_decode(labels)
        assert session.message == "E "

    def test_word_gap_flushes_buffer(self):
        """Word gap should flush any pending buffer before adding space."""
        labels = ["dot", "word_gap"]
        session = self._simulate_decode(labels)
        assert session.message == "E "

    def test_consecutive_inter_letter_gaps_no_crash(self):
        """Two inter-letter gaps with empty buffer shouldn't break."""
        labels = ["dot", "inter_letter_gap", "inter_letter_gap"]
        session = self._simulate_decode(labels)
        assert session.message == "E"

    def test_intra_letter_gap_does_not_decode(self):
        """Intra-letter gap should not trigger any decode."""
        labels = ["dot", "intra_letter_gap"]
        session = self._simulate_decode(labels)
        assert session.message == ""
        assert session.letter_buffer == ["."]


class TestModelIntegration:
    """Test the trained model produces sensible predictions."""

    @classmethod
    def setup_class(cls):
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "pi", "model", "rf_forest.json"
        )
        if not os.path.exists(model_path):
            import pytest
            pytest.skip("Model not exported yet")
        cls.clf = RFLite(model_path)

    def test_model_classes(self):
        assert list(self.clf.classes_) == [0, 1, 2, 3, 4]

    def test_predict_dot(self):
        """A short tap (~120ms at 10 WPM) with norm ~0.5 should be classified as dot."""
        # At 10 WPM, dit = 120ms. Norm by mean depends on session.
        # Use features that clearly look like a dot: short duration, is_tap=1
        features = np.array([[60.0, 0.5, 1.0, 1]])  # short tap
        pred = self.clf.predict(features)[0]
        assert pred == 0, f"Expected dot (0), got {LABEL_NAMES[pred]}"

    def test_predict_dash(self):
        """A long tap (~360ms at 10 WPM) should be classified as dash."""
        features = np.array([[360.0, 2.5, 3.0, 1]])  # long tap
        pred = self.clf.predict(features)[0]
        assert pred == 1, f"Expected dash (1), got {LABEL_NAMES[pred]}"

    def test_predict_word_gap(self):
        """A very long gap (~840ms at 10 WPM) should be word gap."""
        features = np.array([[840.0, 5.0, 7.0, 0]])  # very long gap
        pred = self.clf.predict(features)[0]
        assert pred == 4, f"Expected word_gap (4), got {LABEL_NAMES[pred]}"

    def test_predict_proba_sums_to_one(self):
        features = np.array([[120.0, 1.0, 1.0, 1]])
        proba = self.clf.predict_proba(features)[0]
        assert abs(sum(proba) - 1.0) < 0.001

    def test_predict_batch(self):
        """Model should handle batch predictions."""
        features = np.array([
            [60.0, 0.5, 1.0, 1],
            [360.0, 2.5, 3.0, 1],
            [60.0, 0.5, 1.0, 0],
            [360.0, 2.5, 3.0, 0],
            [840.0, 5.0, 7.0, 0],
        ])
        preds = self.clf.predict(features)
        assert len(preds) == 5

    def test_end_to_end_sos_decode(self):
        """Simulate tapping SOS at 15 WPM and check the model decodes it."""
        from morse_lookup import decode_morse_sequence

        dit_ms = 80.0  # 15 WPM

        # SOS = ... --- ...
        # Events: dot gap dot gap dot LETTER_GAP dash gap dash gap dash LETTER_GAP dot gap dot gap dot
        events = [
            (dit_ms * 1.0, 1),   # dot
            (dit_ms * 1.0, 0),   # intra gap
            (dit_ms * 1.0, 1),   # dot
            (dit_ms * 1.0, 0),   # intra gap
            (dit_ms * 1.0, 1),   # dot
            (dit_ms * 3.0, 0),   # inter-letter gap
            (dit_ms * 3.0, 1),   # dash
            (dit_ms * 1.0, 0),   # intra gap
            (dit_ms * 3.0, 1),   # dash
            (dit_ms * 1.0, 0),   # intra gap
            (dit_ms * 3.0, 1),   # dash
            (dit_ms * 3.0, 0),   # inter-letter gap
            (dit_ms * 1.0, 1),   # dot
            (dit_ms * 1.0, 0),   # intra gap
            (dit_ms * 1.0, 1),   # dot
            (dit_ms * 1.0, 0),   # intra gap
            (dit_ms * 1.0, 1),   # dot
            (dit_ms * 3.0, 0),   # inter-letter gap (flush last S)
        ]

        session = SessionState()
        message = ""
        letter_buffer = []

        for duration_ms, is_tap in events:
            features = session.compute_features(duration_ms, is_tap)
            label_idx = self.clf.predict(features)[0]
            label_name = LABEL_NAMES[label_idx]

            if label_name == "dot":
                letter_buffer.append(".")
            elif label_name == "dash":
                letter_buffer.append("-")
            elif label_name == "inter_letter_gap":
                if letter_buffer:
                    morse_seq = "".join(letter_buffer)
                    message += decode_morse_sequence(morse_seq)
                    letter_buffer = []
            elif label_name == "word_gap":
                if letter_buffer:
                    morse_seq = "".join(letter_buffer)
                    message += decode_morse_sequence(morse_seq)
                    letter_buffer = []
                message += " "

        assert message == "SOS", f"Expected 'SOS', got '{message}'"
