"""EE 250L Lab 04 Chain Code - Continue Terminal
This script continues the ping-pong cycle by responding to ping messages.

Team: Abhigya Goel (solo)
GitHub: https://github.com/AbhigyaGoel/ee250
"""

import paho.mqtt.client as mqtt
import time

def on_connect(client, userdata, flags, rc):
    print("Connected to server (i.e., broker) with result code "+str(rc))
    client.subscribe("abhigyag/ping")
    client.message_callback_add("abhigyag/ping", on_message_from_ping)

def on_message(client, userdata, msg):
    print("Default callback - topic: " + msg.topic + "   msg: " + str(msg.payload, "utf-8"))

def on_message_from_ping(client, userdata, message):
    received_number = int(message.payload.decode())
    new_number = received_number + 1
    print(f"Ping Callback - Received: {received_number}, Publishing pong: {new_number}")
    time.sleep(1)
    client.publish("abhigyag/pong", str(new_number))

if __name__ == '__main__':
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = on_connect

    client.connect(host="172.20.10.4", port=1883, keepalive=60)

    client.loop_start()
    time.sleep(1)

    print("Waiting for ping messages to continue the chain...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        client.loop_stop()