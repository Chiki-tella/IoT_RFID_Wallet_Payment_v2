# RFID Wallet Transaction System

**Team ID:** its_ace  

**Keywords:** RFID Systems, IoT Architecture, MQTT Messaging, Publish–Subscribe Model, Wallet Systems, Transaction Integrity, Edge Controllers, Cloud Backend Services, Real-Time Web Communication, Distributed Systems

## Live Dashboard URL

**http://157.173.101.159:9111**

(The dashboard is hosted directly on the instructor-provided VPS at port 9111. It receives real-time balance updates via WebSocket and sends top-up/payment requests via HTTP POST /topup and /pay.)

## Objective

Design and implement a complete RFID Wallet Transaction System using:

- ESP8266 (Edge Controller) to read/write RFID cards and communicate via MQTT  
- Cloud Backend (VPS) to handle business logic, database operations, and message translation  
- Web Dashboard with separate **Admin (Top-Up)** and **Cashier (Payment)** interfaces  

The system supports:

- Top-Up (Credit) operations to increase a card’s stored balance  
- Payment (Debit) operations to deduct balance when purchasing a product or service  
- Real-time balance updates reflected instantly on the dashboard using WebSocket  
- Safe wallet updates, ensuring that the balance change and transaction record are saved together (all-or-nothing principle)  

The solution demonstrates strict separation between MQTT, HTTP, and WebSocket communication layers.

All teams operate on the same MQTT broker; therefore, strict topic isolation using `rfid/its_ace/...` is mandatory to prevent interference between teams.

## System Architecture

The implementation strictly follows the required architecture:

```text
ESP8266 (RFID Reader) ──► MQTT Broker (157.173.101.159:1883)
                               │
                               ▼
                    VPS Backend (Node.js + Express + SQLite)
                   /         │          \
             HTTP       MQTT         WebSocket
             (POST)    (commands)     (real-time)
              │                       │
              ▼                       ▼
      Admin Dashboard           Cashier Dashboard

      MQTT Broker: 157.173.101.159:1883 (shared instructor broker)
Topic Isolation Rule: All topics prefixed with rfid/its_ace/ to avoid conflicts.
Required MQTT Topics



































TopicDirectionPurposeExample Payloadrfid/its_ace/card/statusESP → BrokerCard detection & current balance{"uid": "A96E950456", "balance": 5000}rfid/its_ace/card/balanceESP → BrokerConfirmed new balance after write{"uid": "A96E950456", "balance": 6000}rfid/its_ace/card/topupBackend → ESPTop-up command{"uid": "A96E950456", "amount": 1000}rfid/its_ace/card/payBackend → ESPPayment command{"uid": "A96E950456", "amount": 500}
Features
Core Functionality

Instant RFID card detection via MQTT
Persistent balance storage in SQLite (wallet.db)
Safe atomic updates (balance + transaction log or rollback)
Separate Admin (credit) and Cashier (debit) interfaces
Real-time balance & transaction updates via WebSocket

Technical Highlights

Strict protocol separation (MQTT / HTTP / WebSocket)
Topic isolation (rfid/its_ace/...) for multi-team compatibility
Transaction ledger for full audit trail
Modern dark-themed glass-morphism UI with Tailwind CSS
Auto-fill UID on scan for both panels
Safe handling of unreliable ESP balance reporting

Quick Start (Local Development)
Bash# 1. Clone repo
git clone https://github.com/YOUR_USERNAME/rfid-wallet-its-ace.git
cd rfid-wallet-its-ace

# 2. Install dependencies
npm install

# 3. Start backend
node server.js
Open: http://localhost:3000
Hardware Setup
ESP8266 + MFRC522 Wiring





















































RC522 PinESP8266 PinNodeMCU LabelFunction3.3V3V33V3Power (+3.3V)RSTGPIO0D3ResetGNDGNDGNDGroundMISOGPIO12D6SPI MISOMOSIGPIO13D7SPI MOSISCKGPIO14D5SPI ClockSDA (SS)GPIO2D4SPI Slave Select
Firmware

Flash main.py using Thonny or ampy
Ensure MicroPython firmware is installed on ESP8266
Libraries needed: umqtt.simple, mfrc522

Configuration
Backend (server.js)

Port: 9111 (as assigned)
MQTT Broker: 157.173.101.159:1883
Static files: serves index.html from same directory

Frontend (index.html)

Auto-detects environment (localhost vs VPS)
WebSocket URL: ws://157.173.101.159:9111

Database

SQLite file: wallet.db (auto-created)
Tables: cards (UID + balance), transactions (full ledger)

Deployment (Instructor VPS)

Upload files to ~/IoT_Card_v2/ (or your folder)
SSH into VPS
Install dependencies:

Bashcd ~/IoT_Card_v2
npm install

Start permanently (nohup example):

Bashnohup node server.js > server.log 2>&1 &

Verify:

Bashtail -f server.log
Look for: Backend running on port 9111 and MQTT connected
Troubleshooting
Common Issues & Fixes



































IssueLikely CauseFixBalance jumps (4501 → 4001 → 4501)Write to card fails → old value readCheck ESP logs for "Write FAILED" → fix hardware/write logicNo UID/balance on dashboardWrong WS URLSet WS_URL = 'ws://157.173.101.159:9111'"Web Access blocked" pageRCA network filter on port 9111Test via SSH tunnel: ssh -L 9111:localhost:9111 user@157.173.101.159Server won't start (EADDRINUSE)Old process on port 9111pkill -f "node server.js" then restartMQTT not connectingWrong broker IP/portVerify 157.173.101.159:1883
Team Information
Team ID: its_ace
VPS Server: 157.173.101.159
Backend Port: 9111
MQTT Broker: 157.173.101.159:1883
Built with ❤️ for RCA IoT Assignment – 2026
Team its_ace