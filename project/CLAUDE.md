# Morse Code IoT Pager — Project Brief

## What This Is
A Morse code pager across four physical nodes. Arduino Node A lets a user tap Morse code messages using a touch sensor. The Raspberry Pi decodes the tap stream in real time using a trained ML model and relays decoded messages to Arduino Node B, which displays them on an LCD and blinks LEDs. A laptop runs a Flask dashboard that visualizes the decoding process live.

## Nodes
- **Node A**: Arduino Uno R3 (Sender). Has a capacitive touch sensor and a buzzer. User taps Morse code on the touch sensor. Arduino computes tap/gap durations and streams them over USB serial to the Pi.
- **Node B**: Arduino Uno R3 (Receiver). Has a 16x2 LCD shield (stacked on top), an RGB LED, and two extra LEDs. Displays decoded messages on the LCD and blinks LEDs to indicate incoming Morse. No buttons, no buzzer.
- **Node C**: Raspberry Pi. Runs the Mosquitto MQTT broker, a serial bridge process that reads from both Arduinos over USB and publishes raw tap events to the broker, and an ML inference process that decodes the tap stream in real time.
- **Node D**: Laptop. Runs a Flask-SocketIO dashboard that subscribes to the broker over LAN and visualizes everything live. Also has a manual message inject panel.

## Communication
Arduinos have no WiFi. They connect to the Pi via USB serial only. The Pi serial bridge is the translation layer between hardware and MQTT. The laptop connects to the Pi's broker over the local network.

## Data Collection
Raw data is tap durations and gap durations — the time between press/release events on the touch sensor. Arduino A computes these using `micros()` and sends them over serial in the format `TAP,<duration_us>\n` and `GAP,<duration_us>\n`. The Pi bridge publishes them as-is; no processing happens at the Arduino level.

## Signal Processing — This Is the Core
The Pi runs a trained Random Forest classifier to decode the tap stream. This is the non-trivial processing the project is built around.

**Why ML instead of fixed thresholds:** Every person taps at a different speed. A fixed dot/dash threshold breaks across users. The classifier uses session-normalized features so it's speed-invariant.

**Features per tap/gap event:**
- Raw duration
- Duration divided by the running session mean (normalization)
- Duration divided by the previous duration (relative ratio)
- Binary flag: is this a tap or a gap

**Classes:** dot, dash, intra-letter gap, inter-letter gap, word gap

**Training data:** Synthetically generated from realistic Morse sessions. Simulates actual word sequences (from a vocabulary of common English words) at multiple WPM speeds (10, 15, 20, 25) with Gaussian noise (15% of ideal duration). Events are processed in natural sequential order so the running session mean evolves during training exactly as it does during real-time inference. Generates ~55k samples.

**Model:** RandomForestClassifier from sklearn (100 estimators, max_depth=12, class_weight="balanced"). Trained on laptop, exported to a lightweight JSON format via `training/export_model.py`. The Pi loads this JSON using `pi/rf_lite.py` — a pure-numpy inference engine that traverses the decision trees without needing sklearn or joblib installed. This keeps Pi dependencies minimal (`paho-mqtt`, `pyserial`, `numpy` only).

**Decoding pipeline on Pi:**
1. Tap event arrives from serial bridge via MQTT
2. Compute features using running session state
3. model.predict() → label
4. Accumulate dot/dash into letter buffer
5. On inter-letter gap: lookup table → character
6. On word gap: append space
7. Publish decoded character + confidence score (from predict_proba) to broker
8. Publish RGB color command to pager/alert/B (green = decoding active, red = SOS detected)
9. Publish decoded text to pager/morse/decoded/A for Node B to display on LCD

## Flask Dashboard (Laptop)
Single-page Flask-SocketIO app. Three live panels:
1. **Tap waveform**: Chart.js bar/timeline of raw durations, color-coded by predicted label (dot/dash/gap type). Updates in real time as taps arrive.
2. **Confidence plot**: Rolling chart of per-character confidence scores. Low-confidence characters flagged visually.
3. **Message log**: Decoded messages with sender node, timestamp, and flagged characters. Backed by SQLite.

Also includes a **manual inject panel**: user types text on the laptop, it encodes to Morse and publishes directly to the broker. This demonstrates bidirectional control from the dashboard node.

## MQTT Topic Structure
- `pager/morse/raw/<node_id>` — raw tap/gap events from serial bridge
- `pager/morse/decoded/<node_id>` — decoded character + confidence from ML decoder
- `pager/status/<node_id>` — node online/offline state
- `pager/alert/<node_id>` — RGB color commands sent to Node B

## Wiring

### Node A — Arduino Uno R3 (Sender)
No shield. All pins free.

| Component | Pin | Notes |
|-----------|-----|-------|
| Touch sensor VCC | 5V | |
| Touch sensor GND | GND | |
| Touch sensor SIG | D2 | Digital input |
| Buzzer positive | D3 | Digital output |
| Buzzer negative | GND | |

### Node B — Arduino Uno R3 (Receiver)
16x2 LCD shield stacked on top. Shield occupies D4, D5, D6, D7, D8, D9, D10, A0. Remaining free pins: D2, D3, D11, D12, D13.

| Component | Pin | Resistor | Notes |
|-----------|-----|----------|-------|
| LCD shield | stacked | — | Uses D4–D10 internally |
| RGB LED R leg | D11 | 220Ω (red-yellow-brown) | Common cathode RGB |
| RGB LED G leg | D12 | 220Ω (red-yellow-brown) | |
| RGB LED B leg | D13 | 220Ω (red-yellow-brown) | |
| RGB LED cathode | GND | — | |
| Extra LED 1 | D2 | 1.5kΩ (brown-green-red) | Blink pattern |
| Extra LED 2 | D3 | 1.5kΩ (brown-green-red) | Blink pattern |

### Node C — Raspberry Pi
- Arduino A → USB port on Pi
- Arduino B → USB port on Pi
- No additional wiring

### Node D — Laptop
- WiFi/LAN only, connects to Pi broker at `pi.local:1883`

## File Structure
```
morse-pager/
├── arduino/
│   ├── node_a/node_a.ino
│   └── node_b/node_b.ino
├── pi/
│   ├── serial_bridge.py
│   ├── ml_decoder.py
│   ├── rf_lite.py
│   ├── morse_lookup.py
│   └── model/
│       ├── rf_forest.json
│       └── rf_classifier.joblib
├── training/
│   ├── generate_data.py
│   ├── train_model.py
│   └── export_model.py
├── dashboard/
│   ├── app.py
│   ├── templates/index.html
│   └── morse.db
├── tests/
│   ├── test_morse_lookup.py
│   ├── test_generate_data.py
│   ├── test_ml_decoder.py
│   ├── test_serial_bridge.py
│   └── test_dashboard.py
└── README.txt
```

## Build Priority Order
1. Training pipeline — synthetic data generation and model training. Everything else depends on this working.
2. Arduino Node A firmware — touch sensor to serial output (TAP/GAP durations via `micros()`).
3. Pi serial bridge — read serial from both Arduinos, publish raw events to broker.
4. Pi ML decoder — full inference pipeline, subscribe to raw, publish decoded + RGB commands.
5. Arduino Node B firmware — subscribe to decoded messages via Pi relay, display on LCD, blink LEDs, drive RGB.
6. Flask dashboard — subscribe to broker, live Chart.js panels, manual inject.
7. Integration — full loop test.

## Serial Protocol
Node A sends plain text over USB serial at 115200 baud:
- `TAP,<duration_us>\n` — touch press duration in microseconds
- `GAP,<duration_us>\n` — gap between releases and presses in microseconds

Node B receives plain text commands from the Pi:
- `CHAR,<c>\n` — single decoded character to append to LCD
- `MSG,<text>\n` — full message to display on LCD line 2
- `RGB,<r>,<g>,<b>\n` — set RGB LED (0 or 1 per channel, digital only)

## Pi Dependencies
Pi does NOT need scikit-learn or joblib. The model is exported to JSON and loaded by `rf_lite.py` using only numpy.
```
pip install paho-mqtt pyserial numpy
```

## Laptop Dependencies
Training (one-time): `numpy pandas scikit-learn joblib`
Dashboard: `flask flask-socketio paho-mqtt`

## Constraints
- Arduinos have no WiFi. All network communication goes through the Pi via USB serial.
- Pi is CPU only, no GPU. Model must run fast on CPU — Random Forest is the right call.
- Pi runs the lightweight `rf_lite.py` inference engine. No sklearn on Pi.
- Dashboard runs on laptop, connects to Pi broker at `pi.local:1883` over LAN.
- Keep the dashboard frontend simple — Flask-SocketIO + Chart.js + plain HTML. No frontend frameworks.
- Arduino code must be lean. No heavy libraries. Timing precision matters — use `micros()` not `millis()` for tap duration measurement.
- Node B LCD shield uses D4–D10. Do not assign any other components to those pins on Node B.
- Node A has no LCD shield. Do not reference LCD libraries in node_a.ino.
- Node B has no buzzer and no buttons. Do not include buzzer or button logic in node_b.ino.
- Node B RGB LED is on D11/D12/D13 — D12 and D13 are NOT PWM on Uno, so use digitalWrite (on/off) not analogWrite.

## What Makes This Strong for the Demo
The live tap waveform + confidence plot means the TA can watch the ML inference happening in real time. When asked "describe your signal processing," point at the confidence plot on screen and explain the session-normalized feature approach and why it beats fixed thresholds. That's the answer.
