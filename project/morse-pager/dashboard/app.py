"""
Flask-SocketIO Dashboard — subscribes to the MQTT broker and visualizes
the Morse decoding process live. Three panels: tap waveform, confidence plot,
and message log. Includes a manual inject panel for sending text from the laptop.

Usage:
    python app.py [--broker pi.local] [--port 5000]
"""

import argparse
import json
import sqlite3
import os
import time
from datetime import datetime

from flask import Flask, render_template, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

# Add parent dir to path for morse_lookup
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi"))
from morse_lookup import encode_text

app = Flask(__name__)
app.config["SECRET_KEY"] = "morse-pager-dashboard"
socketio = SocketIO(app, cors_allowed_origins="*")

# Global MQTT client reference
mqtt_client = None
DB_PATH = os.path.join(os.path.dirname(__file__), "morse.db")


def init_db():
    """Initialize SQLite database for message log."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node TEXT NOT NULL,
            character TEXT NOT NULL,
            confidence REAL NOT NULL,
            message_so_far TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_message(node: str, char: str, confidence: float, message_so_far: str):
    """Save a decoded character to the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (node, character, confidence, message_so_far, timestamp) VALUES (?, ?, ?, ?, ?)",
        (node, char, confidence, message_so_far, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_recent_messages(limit: int = 50) -> list:
    """Get recent messages from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def setup_mqtt(broker: str):
    """Set up MQTT client that forwards events to SocketIO."""
    global mqtt_client

    client = mqtt.Client(client_id="dashboard", protocol=mqtt.MQTTv311)

    def on_connect(_client, _userdata, _flags, rc):
        if rc == 0:
            print(f"Dashboard connected to MQTT broker at {broker}")
            _client.subscribe("pager/morse/raw/+/classified")
            _client.subscribe("pager/morse/decoded/#")
            _client.subscribe("pager/status/#")

    def on_message(_client, _userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            return

        if "classified" in msg.topic:
            # Raw event with classification — send to waveform + confidence panels
            socketio.emit("tap_event", data)

        elif "decoded" in msg.topic:
            # Decoded character — send to message log
            socketio.emit("decoded_char", data)
            save_message(
                data.get("node", "?"),
                data.get("char", "?"),
                data.get("confidence", 0.0),
                data.get("message_so_far", ""),
            )

        elif "status" in msg.topic:
            socketio.emit("node_status", data)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker, 1883, keepalive=60)
    client.loop_start()
    mqtt_client = client


@app.route("/")
def index():
    messages = get_recent_messages()
    return render_template("index.html", messages=messages)


@app.route("/api/messages")
def api_messages():
    messages = get_recent_messages(100)
    return json.dumps(messages)


@socketio.on("connect")
def handle_connect():
    print("Dashboard client connected")


@socketio.on("reset_session")
def handle_reset():
    """Reset decoder session and clear dashboard state."""
    if mqtt_client is not None:
        mqtt_client.publish("pager/control/reset", json.dumps({"action": "reset"}))
    socketio.emit("session_reset")
    print("[reset] Session reset requested")


@socketio.on("inject_message")
def handle_inject(data):
    """Manual message inject — encode text to Morse, send each character
    to the broker as decoded + tone events so Node B displays and buzzes."""
    text = data.get("text", "").strip()
    if not text or mqtt_client is None:
        return

    from morse_lookup import encode_char
    morse = encode_text(text)
    node_id = data.get("node", "dashboard")
    ts = int(time.time() * 1000)
    message_so_far = ""

    for ch in text.upper():
        if ch == " ":
            message_so_far += " "
            continue
        pattern = encode_char(ch)
        if not pattern:
            continue
        message_so_far += ch

        # Publish decoded character — bridge relays CHAR + MSG to Node B LCD
        mqtt_client.publish(
            f"pager/morse/decoded/{node_id}",
            json.dumps({"node": node_id, "char": ch, "confidence": 1.0,
                         "message_so_far": message_so_far, "ts": ts}),
        )
        # Publish tone command — bridge relays TONE to Node B buzzer
        mqtt_client.publish(
            f"pager/alert/{node_id}",
            json.dumps({"cmd": "tone", "pattern": pattern, "char": ch}),
        )

    # Check for SOS
    if "SOS" in text.upper():
        mqtt_client.publish(
            f"pager/alert/{node_id}",
            json.dumps({"cmd": "sos"}),
        )

    socketio.emit("inject_sent", {"node": node_id, "text": text, "morse": morse, "ts": ts})
    print(f"[inject] Sent: {text} -> {morse}")


def main():
    parser = argparse.ArgumentParser(description="Morse Pager Dashboard")
    parser.add_argument("--broker", default="pi.local", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=5000, help="Flask port")
    args = parser.parse_args()

    init_db()
    setup_mqtt(args.broker)

    print(f"Dashboard starting on http://localhost:{args.port}")
    socketio.run(app, host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
