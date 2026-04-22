"""
Pi ML Decoder — subscribes to raw tap/gap events, runs Random Forest inference,
decodes Morse characters, and publishes decoded results.

Maintains per-node session state for feature computation (running mean,
previous duration). Accumulates dot/dash into letter buffers and emits
decoded characters on inter-letter and word gaps.

Usage:
    python ml_decoder.py [--broker localhost] [--model model/rf_forest.json]
"""

import argparse
import json
import os
import time
from collections import deque

import numpy as np
import paho.mqtt.client as mqtt

from morse_lookup import decode_morse_sequence
from rf_lite import RFLite

LABEL_NAMES = ["dot", "dash", "intra_letter_gap", "inter_letter_gap", "word_gap"]

TOPIC_RAW = "pager/morse/raw/#"
TOPIC_DECODED = "pager/morse/decoded/{node_id}"
TOPIC_ALERT = "pager/alert/{node_id}"

MAX_MORSE_LEN = 6   # Longest valid Morse sequence
GAP_WINDOW = 20      # Rolling window of recent gap durations for adaptive threshold
WORD_GAP_MULT = 3.0  # Gap > this * median_gap → word gap


class SessionState:
    """Per-node session state for feature computation and Morse decoding."""

    def __init__(self):
        self.running_sum = 0.0
        self.running_count = 0
        self.prev_duration = None
        self.letter_buffer = []
        self.message = ""
        self.tap_sum = 0.0
        self.tap_count = 0
        # Rolling window of recent gap durations for adaptive gap thresholds
        self.recent_gaps = deque(maxlen=GAP_WINDOW)

    def compute_features(self, duration_ms, is_tap):
        """Compute the 4-feature vector for a single event."""
        self.running_count += 1
        self.running_sum += duration_ms

        if is_tap:
            self.tap_count += 1
            self.tap_sum += duration_ms
        else:
            self.recent_gaps.append(duration_ms)

        running_mean = self.running_sum / self.running_count
        norm_by_mean = duration_ms / running_mean if running_mean > 0 else 1.0
        rel_ratio = (
            duration_ms / self.prev_duration
            if self.prev_duration and self.prev_duration > 0
            else 1.0
        )

        self.prev_duration = duration_ms

        return np.array([[duration_ms, norm_by_mean, rel_ratio, is_tap]])

    @property
    def mean_tap_duration(self):
        if self.tap_count == 0:
            return 0.0
        return self.tap_sum / self.tap_count

    @property
    def median_gap(self):
        """Median of recent gap durations, or 0 if not enough data."""
        if len(self.recent_gaps) < 3:
            return 0.0
        return float(sorted(self.recent_gaps)[len(self.recent_gaps) // 2])

    def classify_gap(self, duration_ms):
        """Classify a gap using adaptive thresholds based on recent gap history.

        Compares this gap to the median of recent gaps:
        - Below median → intra-letter (short pause within a letter)
        - Above median → inter-letter (boundary between letters)
        - Above WORD_GAP_MULT * median → word gap

        Falls back to mean tap duration comparison if not enough gap history.
        """
        median = self.median_gap

        if median > 0:
            if duration_ms >= median * WORD_GAP_MULT:
                return "word_gap", 4
            elif duration_ms >= median:
                return "inter_letter_gap", 3
            else:
                return "intra_letter_gap", 2

        # Fallback: compare to mean tap duration
        mean_tap = self.mean_tap_duration
        if mean_tap > 0:
            if duration_ms >= mean_tap * 4.0:
                return "word_gap", 4
            elif duration_ms >= mean_tap * 1.5:
                return "inter_letter_gap", 3

        return "intra_letter_gap", 2


def parse_args():
    parser = argparse.ArgumentParser(description="Pi ML Decoder")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument(
        "--model",
        default=os.path.join(os.path.dirname(__file__), "model", "rf_forest.json"),
        help="Path to exported model JSON",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Loading model from {args.model}...")
    clf = RFLite(args.model)
    print("Model loaded.")

    sessions = {}

    def get_session(node_id):
        if node_id not in sessions:
            sessions[node_id] = SessionState()
        return sessions[node_id]

    def on_connect(client, _userdata, _flags, rc):
        if rc == 0:
            print(f"Connected to broker. Subscribing to {TOPIC_RAW}")
            client.subscribe(TOPIC_RAW)
        else:
            print(f"Connection failed with code {rc}")

    def on_message(_client, _userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            return

        node_id = data.get("node", "unknown")
        event_type = data.get("type", "")
        duration_us = data.get("duration_us", 0)

        if event_type not in ("tap", "gap"):
            return

        duration_ms = duration_us / 1000.0
        is_tap = 1 if event_type == "tap" else 0

        session = get_session(node_id)
        features = session.compute_features(duration_ms, is_tap)

        if is_tap:
            # ML model for taps: dot vs dash
            label_idx = clf.predict(features)[0]
            proba = clf.predict_proba(features)[0]
            confidence = float(proba[label_idx])
            label_name = LABEL_NAMES[label_idx]
        else:
            # Adaptive thresholds for gaps: compare gap to other gaps
            label_name, label_idx = session.classify_gap(duration_ms)
            confidence = 1.0

        # Debug: show raw classification
        print(f"  [{node_id}] {event_type} {duration_ms:.0f}ms -> {label_name} (buf={''.join(session.letter_buffer)})")

        # Decode logic
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
            decoded_char = " "

        # Buffer overflow protection
        if len(session.letter_buffer) > MAX_MORSE_LEN:
            morse_seq = "".join(session.letter_buffer)
            decoded_char = decode_morse_sequence(morse_seq)
            session.message += decoded_char
            session.letter_buffer = []

        # Publish RGB alert to Node B
        if label_name in ("dot", "dash"):
            is_sos = session.message.rstrip().endswith("SOS")
            rgb_cmd = {"r": 1, "g": 0, "b": 0} if is_sos else {"r": 0, "g": 1, "b": 0}
            mqtt_client.publish(
                TOPIC_ALERT.format(node_id="B"),
                json.dumps(rgb_cmd),
            )

        # Publish classified event
        event_result = {
            "node": node_id,
            "type": event_type,
            "duration_ms": round(duration_ms, 2),
            "label": label_name,
            "confidence": round(confidence, 4),
            "ts": data.get("ts", 0),
        }
        mqtt_client.publish(
            f"pager/morse/raw/{node_id}/classified",
            json.dumps(event_result),
        )

        # Publish decoded character
        if decoded_char is not None:
            decoded_result = {
                "node": node_id,
                "char": decoded_char,
                "confidence": round(confidence, 4),
                "message_so_far": session.message,
                "ts": data.get("ts", 0),
            }
            mqtt_client.publish(
                TOPIC_DECODED.format(node_id=node_id),
                json.dumps(decoded_result),
            )
            print(f"[{node_id}] >>> Decoded: '{decoded_char}' | msg: {session.message}")

    # MQTT setup
    mqtt_client = mqtt.Client(client_id="ml_decoder", protocol=mqtt.MQTTv311)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    print(f"Connecting to broker at {args.broker}...")
    mqtt_client.connect(args.broker, 1883, keepalive=60)

    print("ML Decoder running. Press Ctrl+C to stop.")

    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
