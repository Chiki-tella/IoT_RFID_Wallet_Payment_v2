# main.py - RFID Card Top-Up Edge Controller (ESP8266 + MicroPython)
# Assignment compliant: only MQTT, unique team_id namespace, no HTTP/WebSocket
# Author: M (your team)

import network
import time
import json
from umqtt.simple import MQTTClient
from mfrc522 import MFRC522

# ===================== CONFIG - CHANGE THESE =====================
TEAM_ID         = "its_ace"              # MUST BE UNIQUE (your choice, e.g. m_kigali, team_m_rw, grp_m_2026)
WIFI_SSID       = "RCA"          # Replace with real SSID (2.4 GHz only!)
WIFI_PASSWORD   = "@RcaNyabihu2023"      # Replace

MQTT_BROKER     = "157.173.101.159"        # From assignment diagram
MQTT_PORT       = 1883
MQTT_CLIENT_ID  = "esp8266_" + TEAM_ID    # Unique client ID

# MQTT Topics - MUST use your team_id prefix
BASE_TOPIC      = f"rfid/{TEAM_ID}/"
STATUS_TOPIC    = BASE_TOPIC + "card/status"      # ESP → Broker
TOPUP_TOPIC     = BASE_TOPIC + "card/topup"       # Broker → ESP
BALANCE_TOPIC   = BASE_TOPIC + "card/balance"     # ESP → Broker
PAY_TOPIC       = BASE_TOPIC + "card/pay"          # ← ADDED for Payment

# RFID pins - YOUR exact wiring
SCK_PIN   = 14   # D5 GPIO14
MOSI_PIN  = 13   # D7 GPIO13
MISO_PIN  = 12   # D6 GPIO12
RST_PIN   = 0    # D3 GPIO0
CS_PIN    = 2    # D4 GPIO2 (SDA/CS)

# Balance storage on card
BLOCK_NUMBER = 8
DEFAULT_KEY  = [0xFF] * 6

# ===================== INIT =====================
reader = MFRC522(SCK_PIN, MOSI_PIN, MISO_PIN, RST_PIN, CS_PIN)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
    print("\nWiFi:", wlan.ifconfig() if wlan.isconnected() else "FAILED")

def mqtt_connect(client):
    while True:
        try:
            print("Connecting to MQTT...")
            client.connect()
            print("MQTT connected!")
            client.subscribe(TOPUP_TOPIC)
            client.subscribe(PAY_TOPIC)
            print(f"Subscribed: {TOPUP_TOPIC}, {PAY_TOPIC}")
            return True
        except OSError as e:
            print("MQTT failed:", e)
            time.sleep(5)

def on_mqtt_message(topic, msg):
    try:
        data = json.loads(msg)
        target_uid = data.get("uid")
        amount = data.get("amount", 0)

        if amount <= 0:
            print("Invalid amount")
            return

        topic_str = topic.decode()
        is_deduct = topic_str == PAY_TOPIC
        op = "Payment" if is_deduct else "Top-up"

        print(f"{op} command → UID: {target_uid}, Amount: {amount}")

        # Wait for card to be present
        for _ in range(30):  # wait up to ~3 seconds
            (status, uid) = reader.anticoll()
            if status == reader.OK:
                break
            time.sleep(0.1)
        else:
            print("No card present after wait")
            return

        current_uid = ''.join('{:02X}'.format(x) for x in uid)
        if current_uid != target_uid:
            print(f"UID mismatch: card {current_uid} ≠ requested {target_uid}")
            return

        # Authenticate
        reader.select_tag(uid)
        if reader.auth(reader.AUTHENT1A, BLOCK_NUMBER, DEFAULT_KEY, uid) != reader.OK:
            print("Auth failed")
            reader.stop_crypto1()
            return

        # Read current
        block_data = reader.read(BLOCK_NUMBER)
        if block_data is None:
            print("Read failed")
            reader.stop_crypto1()
            return

        current_balance = int.from_bytes(bytes(block_data[:4]), 'big')
        print(f"Card balance: {current_balance}")

        if is_deduct and current_balance < amount:
            print("Insufficient balance")
            reader.stop_crypto1()
            return

        new_balance = current_balance - amount if is_deduct else current_balance + amount

        # Prepare data
        new_data = new_balance.to_bytes(4, 'big') + block_data[4:]

        print(f"Writing: {current_balance} → {new_balance}")

        time.sleep(0.1)  # stability delay
        write_ok = reader.write(BLOCK_NUMBER, new_data) == reader.OK

        time.sleep(0.2)  # important delay before verify
        verify_data = reader.read(BLOCK_NUMBER)
        verified = int.from_bytes(bytes(verify_data[:4]), 'big') if verify_data else -1

        reader.stop_crypto1()

        if write_ok and verified == new_balance:
            print(f"✓ {op} SUCCESS - Verified {new_balance} on card")
            client.publish(BALANCE_TOPIC, json.dumps({
                "uid": current_uid,
                "balance": new_balance
            }))
        else:
            print(f"✗ {op} FAILED - Write: {write_ok}, Verified: {verified} (expected {new_balance})")

    except Exception as e:
        print("MQTT message error:", e)

# ===================== MAIN =====================
connect_wifi()
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT)
client.set_callback(on_mqtt_message)
mqtt_connect(client)

print("Ready. Scanning cards...")

while True:
    try:
        client.check_msg()

        (status, uid) = reader.request(reader.REQIDL)
        if status == reader.OK:
            (status, uid) = reader.anticoll()
            if status == reader.OK:
                uid_str = ''.join('{:02X}'.format(x) for x in uid)
                print(f"Card detected: {uid_str}")

                reader.select_tag(uid)
                if reader.auth(reader.AUTHENT1A, BLOCK_NUMBER, DEFAULT_KEY, uid) == reader.OK:
                    block_data = reader.read(BLOCK_NUMBER)
                    if block_data:
                        balance = int.from_bytes(bytes(block_data[:4]), 'big')
                        print(f"Balance read: {balance}")
                        client.publish(STATUS_TOPIC, json.dumps({
                            "uid": uid_str,
                            "balance": balance
                        }))
                reader.stop_crypto1()

        time.sleep(0.5)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(2)
