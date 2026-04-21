"""
Pi Serial Bridge — reads from Arduino Node A over USB serial (plain text format),
publishes raw tap/gap events to the MQTT broker, and relays decoded messages
and RGB commands back to Arduino Node B over serial.

Node A sends plain text: TAP,<duration_us> or GAP,<duration_us>
Node B receives plain text: CHAR,<c> or RGB,<r>,<g>,<b> or MSG,<text>

Usage:
    python serial_bridge.py [--port-a /dev/ttyUSB0] [--port-b /dev/ttyUSB1]
                            [--broker localhost] [--baud 115200]
"""

import argparse
import json
import threading
import time

import paho.mqtt.client as mqtt
import serial

TOPIC_RAW = "pager/morse/raw/{node_id}"
TOPIC_STATUS = "pager/status/{node_id}"
TOPIC_DECODED = "pager/morse/decoded/#"
TOPIC_ALERT = "pager/alert/#"


def parse_args():
    parser = argparse.ArgumentParser(description="Pi Serial Bridge")
    parser.add_argument("--port-a", default="/dev/ttyUSB0", help="Serial port for Node A")
    parser.add_argument("--port-b", default="/dev/ttyUSB1", help="Serial port for Node B")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    return parser.parse_args()


def create_mqtt_client(broker: str) -> mqtt.Client:
    client = mqtt.Client(client_id="serial_bridge", protocol=mqtt.MQTTv311)
    client.will_set("pager/status/bridge", json.dumps({"state": "offline"}), retain=True)
    client.connect(broker, 1883, keepalive=60)
    return client


def parse_serial_line(line: str) -> dict | None:
    """Parse plain text serial line from Node A.

    Expected formats:
        TAP,<duration_us>
        GAP,<duration_us>

    Returns dict with node, type, duration_us or None if invalid.
    """
    line = line.strip()
    if not line:
        return None

    parts = line.split(",")
    if len(parts) != 2:
        return None

    event_type = parts[0].strip().lower()
    if event_type not in ("tap", "gap"):
        return None

    try:
        duration_us = int(parts[1].strip())
    except ValueError:
        return None

    return {
        "node": "A",
        "type": event_type,
        "duration_us": duration_us,
    }


def serial_reader_a(port_path: str, baud: int, mqtt_client: mqtt.Client):
    """Read lines from Node A serial and publish to MQTT."""
    while True:
        try:
            ser = serial.Serial(port_path, baud, timeout=1)
            print(f"[A] Connected to {port_path}")

            mqtt_client.publish(
                TOPIC_STATUS.format(node_id="A"),
                json.dumps({"node": "A", "state": "online", "port": port_path}),
                retain=True,
            )

            while True:
                raw_line = ser.readline()
                if not raw_line:
                    continue

                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                event = parse_serial_line(line)
                if event is None:
                    print(f"[A] Ignored: {line}")
                    continue

                topic = TOPIC_RAW.format(node_id="A")
                mqtt_client.publish(topic, json.dumps(event))

        except serial.SerialException as e:
            print(f"[A] Serial error on {port_path}: {e}")
            mqtt_client.publish(
                TOPIC_STATUS.format(node_id="A"),
                json.dumps({"node": "A", "state": "offline", "error": str(e)}),
                retain=True,
            )
            time.sleep(2)

        except Exception as e:
            print(f"[A] Unexpected error: {e}")
            time.sleep(2)


def setup_node_b_relay(mqtt_client: mqtt.Client, port_b_path: str, baud: int):
    """Set up MQTT subscriptions that relay messages to Node B over serial.

    Subscribes to decoded characters and RGB alert commands, translates them
    to plain text serial commands for Node B.
    """
    ser_b = {"port": None}

    def connect_b():
        """Try to open Node B serial port."""
        if ser_b["port"] is not None:
            return True
        try:
            ser_b["port"] = serial.Serial(port_b_path, baud, timeout=1)
            print(f"[B] Connected to {port_b_path}")
            mqtt_client.publish(
                TOPIC_STATUS.format(node_id="B"),
                json.dumps({"node": "B", "state": "online", "port": port_b_path}),
                retain=True,
            )
            return True
        except serial.SerialException as e:
            print(f"[B] Cannot open {port_b_path}: {e}")
            return False

    def write_to_b(text: str):
        """Write a line to Node B serial, reconnecting if needed."""
        if ser_b["port"] is None:
            if not connect_b():
                return
        try:
            ser_b["port"].write(f"{text}\n".encode())
        except serial.SerialException as e:
            print(f"[B] Write error: {e}")
            ser_b["port"] = None
            mqtt_client.publish(
                TOPIC_STATUS.format(node_id="B"),
                json.dumps({"node": "B", "state": "offline", "error": str(e)}),
                retain=True,
            )

    def on_message(_client, _userdata, msg):
        topic = msg.topic

        try:
            data = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        if "decoded" in topic:
            # Decoded character from ml_decoder → send to Node B LCD
            char = data.get("char", "")
            if char:
                write_to_b(f"CHAR,{char}")
            # Also send full message for display
            msg_so_far = data.get("message_so_far", "")
            if msg_so_far:
                write_to_b(f"MSG,{msg_so_far}")

        elif "alert" in topic:
            # RGB command from ml_decoder → send to Node B RGB LED
            r = data.get("r", 0)
            g = data.get("g", 0)
            b = data.get("b", 0)
            write_to_b(f"RGB,{r},{g},{b}")

    mqtt_client.on_message = on_message
    mqtt_client.subscribe(TOPIC_DECODED)
    mqtt_client.subscribe(TOPIC_ALERT)

    # Try initial connection to Node B
    connect_b()


def main():
    args = parse_args()

    mqtt_client = create_mqtt_client(args.broker)

    # Set up relay to Node B (subscribes to decoded + alert topics)
    setup_node_b_relay(mqtt_client, args.port_b, args.baud)

    mqtt_client.loop_start()

    mqtt_client.publish(
        "pager/status/bridge",
        json.dumps({"state": "online"}),
        retain=True,
    )

    # Start reader thread for Node A
    thread_a = threading.Thread(
        target=serial_reader_a,
        args=(args.port_a, args.baud, mqtt_client),
        daemon=True,
    )
    thread_a.start()

    print("Serial bridge running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        mqtt_client.publish(
            "pager/status/bridge",
            json.dumps({"state": "offline"}),
            retain=True,
        )
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
