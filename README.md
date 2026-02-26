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
