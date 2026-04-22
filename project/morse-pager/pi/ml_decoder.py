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

import numpy as np
import paho.mqtt.client as mqtt

from morse_lookup import decode_morse_sequence
from rf_lite import RFLite

LABEL_NAMES = ["dot", "dash", "intra_letter_gap", "inter_letter_gap", "word_gap"]

TOPIC_RAW = "pager/morse/raw/#"
TOPIC_DECODED = "pager/morse/decoded/{node_id}"
TOPIC_ALERT = "pager/alert/{node_id}"


MAX_MORSE_LEN = 6  # Longest valid Morse sequence (e.g. "...-.." for $)

# Adaptive gap thresholds relative to mean tap duration.
# Standard Morse ratios are 1:3:7 (dot:dash/inter-gap:word-gap).
# We use generous thresholds to handle noisy human tapping.
GAP_INTER_LETTER = 1.5   # gap > this * mean_tap → inter-letter
GAP_WORD = 4.0            # gap > this * mean_tap → word gap


class SessionState:
    """Per-node session state for feature computation and Morse decoding."""

    def __init__(self):
        self.running_sum = 0.0
        self.running_count = 0
        self.prev_duration = None
        self.letter_buffer = []  # List of '.' and '-'
        self.message = ""
        # Track tap durations separately for gap classification fallback
        self.tap_sum = 0.0
        self.tap_count = 0

    def compute_features(self, duration_ms, is_tap):
        """Compute the 4-feature vector for a single event."""
        self.running_count += 1
        self.running_sum += duration_ms

        if is_tap:
            self.tap_count += 1
            self.tap_sum += duration_ms

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

    # Load lightweight model (no sklearn needed)
    print(f"Loading model from {args.model}...")
    clf = RFLite(args.model)
    print("Model loaded.")

    # Per-node session states
    sessions = {}

    def get_session(node_id: str) -> SessionState:
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

        # Classification: use ML model for taps (dot vs dash),
        # adaptive thresholds for gaps (intra vs inter vs word).
        # The model struggles with gap classification on real human input
        # because timing ratios are much noisier than synthetic training data.
        label_idx = clf.predict(features)[0]
        proba = clf.predict_proba(features)[0]
        confidence = float(proba[label_idx])
        label_name = LABEL_NAMES[label_idx]

        if not is_tap:
            # Override model gap classification with adaptive thresholds
            mean_tap = session.mean_tap_duration
            if mean_tap > 0:
                if duration_ms >= mean_tap * GAP_WORD:
                    label_name = "word_gap"
                    label_idx = 4
                elif duration_ms >= mean_tap * GAP_INTER_LETTER:
                    label_name = "inter_letter_gap"
                    label_idx = 3
                else:
                    label_name = "intra_letter_gap"
                    label_idx = 2
                confidence = 1.0  # threshold-based, deterministic

        # Decode logic
        decoded_char = None

        if label_name == "dot":
            session.letter_buffer.append(".")
        elif label_name == "dash":
            session.letter_buffer.append("-")
        elif label_name == "inter_letter_gap":
            # End of letter — decode buffer
            if session.letter_buffer:
                morse_seq = "".join(session.letter_buffer)
                decoded_char = decode_morse_sequence(morse_seq)
                session.message += decoded_char
                session.letter_buffer = []
        elif label_name == "word_gap":
            # End of word — decode buffer + add space
            if session.letter_buffer:
                morse_seq = "".join(session.letter_buffer)
                decoded_char = decode_morse_sequence(morse_seq)
                session.message += decoded_char
                session.letter_buffer = []
            session.message += " "
            decoded_char = " "
        # intra_letter_gap: do nothing, just separates dots/dashes within a letter

        # Buffer overflow protection: if buffer exceeds max valid Morse length,
        # flush what we have so far. This prevents runaway accumulation when
        # gap classification fails.
        if len(session.letter_buffer) > MAX_MORSE_LEN:
            morse_seq = "".join(session.letter_buffer)
            decoded_char = decode_morse_sequence(morse_seq)
            session.message += decoded_char
            session.letter_buffer = []

        # Publish RGB alert to Node B
        # Green = decoding active, Red = SOS detected
        if label_name in ("dot", "dash"):
            # Check for SOS: message ends with "SOS"
            is_sos = session.message.rstrip().endswith("SOS")
            rgb_cmd = {"r": 1, "g": 0, "b": 0} if is_sos else {"r": 0, "g": 1, "b": 0}
            mqtt_client.publish(
                TOPIC_ALERT.format(node_id="B"),
                json.dumps(rgb_cmd),
            )

        # Publish raw event with prediction
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

        # Publish decoded character if we have one
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
            print(f"[{node_id}] Decoded: '{decoded_char}' (conf={confidence:.3f}) | msg: {session.message}")

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
