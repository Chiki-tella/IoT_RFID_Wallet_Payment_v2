# RFID Wallet Transaction System

**Team ID:** its_ace  

**Keywords:** RFID Systems, IoT Architecture, MQTT Messaging, Publish–Subscribe Model, Wallet Systems, Transaction Integrity, Edge Controllers, Cloud Backend Services, Real-Time Web Communication, Distributed Systems

## Live Dashboard URL

**http://157.173.101.159:9111**

(The dashboard is hosted directly on the instructor-provided VPS at port 9111. It receives real-time balance updates via WebSocket and sends top-up/payment requests via HTTP POST /topup and /pay.)

## Objective

Design and implement a complete RFID Wallet Transaction System using:

- ESP8266 (Edge Controller) to read RFID cards and communicate via MQTT  
- Cloud Backend (VPS) to handle business logic, database operations, and message translation  
- Web Dashboard with separate Admin (Top-Up) and Cashier (Payment) interfaces  

The system supports:

- Top-Up (Credit) operations to increase a card’s stored balance  
- Payment (Debit) operations to deduct balance when purchasing a product or service  
- Real-time balance updates reflected instantly on the dashboard using WebSocket  
- Safe wallet updates, ensuring that the balance change and transaction record are saved together (all-or-nothing principle)  

The solution demonstrates proper separation between MQTT, HTTP, and WebSocket communication layers.

All teams operate on the same MQTT broker; therefore, strict topic isolation using `rfid/its_ace/...` is mandatory to prevent interference between teams.

## System Architecture

The implementation strictly follows the required architecture:

- **ESP8266 (Edge Controller)**  
  - Reads RFID card UID via SPI  
  - Publishes card UID and balance via MQTT  
  - Subscribes to top-up and payment commands  
  - **Must NOT** use HTTP or WebSocket  

- **Cloud Backend (VPS)**  
  - Receives top-up/payment commands via HTTP POST  
  - Communicates with ESP8266 via MQTT  
  - Pushes real-time balance updates to dashboard via WebSocket  
  - Maintains persistent wallet balance and transaction ledger in SQLite  

- **Web Dashboard (Browser)**  
  - Separate Admin (Top-Up) and Cashier (Payment) interfaces  
  - Sends requests via HTTP  
  - Receives real-time updates via WebSocket  
  - **Does NOT** communicate directly with MQTT  

**MQTT Broker:** 157.173.101.159:1883 (shared instructor broker)

**Topic Isolation Rule:** All topics are prefixed with `rfid/its_ace/` to avoid conflicts with other teams.

### Required MQTT Topics

- **Card status** (ESP8266 → Broker)  
  `rfid/its_ace/card/status`  
  Example payload:
  ```json
  {"uid": "E264B20135", "balance": 2000}