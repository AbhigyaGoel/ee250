"""EE 250L Lab 04 Chain Code - Start Terminal
This script initiates the ping-pong cycle by publishing the first message.

Team: Abhigya Goel (solo)
GitHub: https://github.com/AbhigyaGoel/ee250
"""

import paho.mqtt.client as mqtt
import time

def on_connect(client, userdata, flags, rc):
    print("Connected to server (i.e., broker) with result code "+str(rc))
    client.subscribe("abhigyag/pong")
    client.message_callback_add("abhigyag/pong", on_message_from_pong)

def on_message(client, userdata, msg):
    print("Default callback - topic: " + msg.topic + "   msg: " + str(msg.payload, "utf-8"))

def on_message_from_pong(client, userdata, message):
    received_number = int(message.payload.decode())
    new_number = received_number + 1
    print(f"Pong Callback - Received: {received_number}, Publishing ping: {new_number}")
    time.sleep(1)
    client.publish("abhigyag/ping", str(new_number))

if __name__ == '__main__':
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = on_connect

    client.connect(host="172.20.10.4", port=1883, keepalive=60)

    client.loop_start()
    time.sleep(1)

    initial_number = 0
    print(f"Starting chain - Publishing initial ping: {initial_number}")
    client.publish("abhigyag/ping", str(initial_number))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        client.loop_stop()