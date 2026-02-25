const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const mqtt = require('mqtt');
const sqlite3 = require('sqlite3').verbose();   // ← added (one line)

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// === YOUR CONFIG (unchanged) ===
const TEAM_ID = 'its_ace';
const MQTT_BROKER = '157.173.101.159';
const MQTT_PORT = 1883;

const STATUS_TOPIC  = `rfid/${TEAM_ID}/card/status`;
const BALANCE_TOPIC = `rfid/${TEAM_ID}/card/balance`;
const TOPUP_TOPIC   = `rfid/${TEAM_ID}/card/topup`;
const PAY_TOPIC     = `rfid/${TEAM_ID}/card/pay`;   // ← added

// ================ BALANCE STORE (unchanged) ================
const balances = {};

// ================ SQLITE DB + SAFE WALLET (added) ================
const db = new sqlite3.Database('./wallet.db');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS cards (uid TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)`);
  db.run(`CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT,
    type TEXT,
    amount INTEGER,
    product TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
});

// Load existing balances on startup (fixes "updates then reverts")
db.all("SELECT uid, balance FROM cards", [], (err, rows) => {
  if (!err) {
    rows.forEach(row => balances[row.uid] = row.balance);
  }
  console.log(`Loaded ${rows ? rows.length : 0} cards from wallet.db`);
});

// ================ MQTT CLIENT (tiny update for safety) ================
const mqttClient = mqtt.connect(`mqtt://${MQTT_BROKER}:${MQTT_PORT}`, {
  clientId: `backend_${TEAM_ID}_${Math.random().toString(16).slice(3)}`
});

mqttClient.on('connect', () => {
  console.log('MQTT connected to broker');
  mqttClient.subscribe([STATUS_TOPIC, BALANCE_TOPIC], (err) => {
    if (!err) console.log(`Subscribed to ${STATUS_TOPIC} and ${BALANCE_TOPIC}`);
  });
});

mqttClient.on('message', (topic, message) => {
  try {
    const payload = JSON.parse(message.toString());
    console.log(`[MQTT] Message on ${topic}:`, payload);

    if (topic === BALANCE_TOPIC) {
      const uid = payload.uid;
      const balance = payload.balance;
      if (balance !== undefined) {
        balances[uid] = balance;
        db.run('INSERT OR REPLACE INTO cards (uid, balance) VALUES (?, ?)', [uid, balance]);
        broadcast(BALANCE_TOPIC, { uid, balance });
      }
      return;
    }

    if (topic === STATUS_TOPIC) {
      const uid = payload.uid;
      const balance = payload.balance || (balances[uid] || 0);
      balances[uid] = balance;
      db.run('INSERT OR REPLACE INTO cards (uid, balance) VALUES (?, ?)', [uid, balance]);
      broadcast(topic, payload);
      return;
    }

    broadcast(topic, payload);

  } catch (e) {
    console.error('Invalid MQTT message:', e);
  }
});

mqttClient.on('error', (err) => console.error('MQTT error:', err));

// ================ EXPRESS MIDDLEWARE (unchanged) ================
app.use(express.json());

// ================ SAFE TOP-UP (your beautiful code, adapted to WebSocket) ================
app.post('/topup', (req, res) => {
  const { uid, amount } = req.body;

  if (!uid || typeof amount !== 'number' || amount <= 0) {
    return res.status(400).json({ error: 'Invalid uid or amount (>0)' });
  }

  db.serialize(() => {
    db.run('BEGIN TRANSACTION');

    db.get('SELECT balance FROM cards WHERE uid = ?', [uid], (err, row) => {
      const oldBalance = row ? row.balance : 0;
      const newBalance = oldBalance + amount;

      db.run('INSERT OR REPLACE INTO cards (uid, balance) VALUES (?, ?)', [uid, newBalance]);

      db.run('INSERT INTO transactions (uid, type, amount) VALUES (?, "TOPUP", ?)', [uid, amount]);

      db.run('COMMIT', () => {
        balances[uid] = newBalance;
        const payload = { uid, balance: newBalance };

        mqttClient.publish(TOPUP_TOPIC, JSON.stringify({ uid, amount }));
        broadcast(BALANCE_TOPIC, payload);

        console.log(`[TOPUP] UID: ${uid}, Amount: ${amount}, New balance: ${newBalance}`);
        res.json({ success: true, message: 'Top-up completed', balance: newBalance });
      });
    });
  });
});

// ================ SAFE PAY (your beautiful code, adapted to WebSocket) ================
app.post('/pay', (req, res) => {
  const { uid, amount, product = 'Service' } = req.body;

  if (!uid || typeof amount !== 'number' || amount <= 0) {
    return res.status(400).json({ error: 'Invalid uid or amount (>0)' });
  }

  db.serialize(() => {
    db.run('BEGIN TRANSACTION');

    db.get('SELECT balance FROM cards WHERE uid = ?', [uid], (err, row) => {
      if (!row || row.balance < amount) {
        db.run('ROLLBACK');
        return res.json({ success: false, message: row ? 'Insufficient balance' : 'Card not found' });
      }

      const newBalance = row.balance - amount;

      db.run('UPDATE cards SET balance = ? WHERE uid = ?', [newBalance, uid]);

      db.run('INSERT INTO transactions (uid, type, amount, product) VALUES (?, "PAYMENT", ?, ?)', [uid, amount, product]);

      db.run('COMMIT', () => {
        balances[uid] = newBalance;
        const payload = { uid, balance: newBalance };

        mqttClient.publish(PAY_TOPIC, JSON.stringify({ uid, amount }));
        broadcast(BALANCE_TOPIC, payload);

        console.log(`[PAY] UID: ${uid}, Amount: ${amount}, New balance: ${newBalance}`);
        res.json({ success: true, message: 'Payment completed', balance: newBalance });
      });
    });
  });
});

// ================ WEBSOCKET UTILITY (unchanged) ================
function broadcast(topic, data) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({ topic, data }));
      console.log(`[WS] Sent to client:`, { topic, data });
    }
  });
}

// ================ WEBSOCKET CONNECTION (small improvement) ================
wss.on('connection', (ws) => {
  console.log('Dashboard connected via WebSocket');

  ws.send(JSON.stringify({ message: 'Connected to real-time updates' }));

  Object.entries(balances).forEach(([uid, balance]) => {
    ws.send(JSON.stringify({ topic: BALANCE_TOPIC, data: { uid, balance } }));
  });

  ws.on('close', () => console.log('Dashboard disconnected'));
});

// ================ STATIC FILES + START SERVER (unchanged) ================
app.use(express.static(__dirname));

const PORT = process.env.PORT || 9111;
server.listen(PORT, () => {
  console.log(`Backend running on port ${PORT}`);
});