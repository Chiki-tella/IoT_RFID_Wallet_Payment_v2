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

# ===================== RFID READER INIT =====================
reader = MFRC522(SCK_PIN, MOSI_PIN, MISO_PIN, RST_PIN, CS_PIN)

# ===================== NETWORK FUNCTIONS =====================
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
    
    if wlan.isconnected():
        print("\nWiFi connected:", wlan.ifconfig())
    else:
        print("\nWiFi connection FAILED - check SSID/password")

# ===================== MQTT RECONNECT LOGIC =====================
def mqtt_connect(client):
    while True:
        try:
            print("Attempting MQTT connection...")
            client.connect()
            print("MQTT connected successfully!")
            client.subscribe(TOPUP_TOPIC)
            client.subscribe(PAY_TOPIC)                    # ← ADDED
            print(f"Subscribed to: {TOPUP_TOPIC} and {PAY_TOPIC}")
            return True
        except OSError as e:
            print("MQTT connect failed:", e)
            print("Retrying in 5 seconds...")
            time.sleep(5)

# ===================== MQTT MESSAGE HANDLER =====================
def on_mqtt_message(topic, msg):
    try:
        data = json.loads(msg)
        target_uid = data.get("uid")
        amount = data.get("amount", 0)
        
        if amount <= 0:
            print("Invalid amount received")
            return

        topic_str = topic.decode()

        # ==================== TOP-UP ====================
        if topic_str == TOPUP_TOPIC:
            print(f"Top-up command received → UID: {target_uid}, Amount: {amount}")
            operation = "top-up"
            is_deduct = False

        # ==================== PAYMENT ====================
        elif topic_str == PAY_TOPIC:
            print(f"Payment command received → UID: {target_uid}, Amount: {amount}")
            operation = "payment"
            is_deduct = True
        else:
            return

        # Check if card is present and UID matches
        (status, uid) = reader.anticoll()
        if status != reader.OK:
            print("No card present")
            return
        
        current_uid = ''.join('{:02X}'.format(x) for x in uid)
        if current_uid != target_uid:
            print(f"UID mismatch (card: {current_uid}, requested: {target_uid})")
            return
        
        # Authenticate
        reader.select_tag(uid)
        if reader.auth(reader.AUTHENT1A, BLOCK_NUMBER, DEFAULT_KEY, uid) != reader.OK:
            print("Authentication failed")
            reader.stop_crypto1()
            return
        
        # Read current balance
        block_data = reader.read(BLOCK_NUMBER)
        if block_data is None:
            print("Read failed")
            reader.stop_crypto1()
            return
        
        current_balance = int.from_bytes(bytes(block_data[:4]), 'big')

        if is_deduct:
            if current_balance < amount:
                print("Insufficient balance on card")
                reader.stop_crypto1()
                return
            new_balance = current_balance - amount
        else:
            new_balance = current_balance + amount

        # Write new balance
        new_data = new_balance.to_bytes(4, 'big') + block_data[4:]
        if reader.write(BLOCK_NUMBER, new_data) != reader.OK:
            print("Write failed")
        else:
            print(f"{operation.capitalize()} successful: {current_balance} → {new_balance}")
            
            # Publish updated balance
            client.publish(BALANCE_TOPIC, json.dumps({
                "uid": current_uid,
                "balance": new_balance
            }))
        
        reader.stop_crypto1()
        
    except Exception as e:
        print("Error processing MQTT message:", e)

# ===================== MAIN PROGRAM =====================
connect_wifi()

# Create MQTT client
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT)
client.set_callback(on_mqtt_message)

# Connect with retry
mqtt_connect(client)

print("System ready. Scanning for RFID cards...")

while True:
    try:
        # Check for incoming MQTT messages (top-up & payment)
        client.check_msg()
        
        # Scan for card (same as before)
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
        
        time.sleep(0.4)
        
    except Exception as e:
        print("Main loop error:", e)
        time.sleep(2)
