# Morse Code IoT Pager — Project Brief

## What This Is
A Morse code pager across four physical nodes. Arduino Node A lets a user tap Morse code messages using a pushbutton. The Raspberry Pi decodes the tap stream in real time using a trained ML model and relays decoded messages to Arduino Node B, which displays them on an LCD, plays them back through a buzzer, and blinks LEDs. A laptop runs a Flask dashboard that visualizes the decoding process live.

## Nodes
- **Node A**: Arduino Uno R3 (Sender). Pushbutton on D2 (INPUT_PULLUP), buzzer on D4. Computes tap/gap durations using `micros()` and streams them as `TAP,<us>` / `GAP,<us>` over USB serial.
- **Node B**: Arduino Uno R3 (Receiver). 16x2 LCD shield (stacked, D4-D10), buzzer on D13, LED1 on D2, LED2 on D3. Displays decoded text on LCD, plays decoded Morse patterns through buzzer, blinks LEDs (LED1=dot, LED2=dash). SOS triggers warbling alarm. No buttons.
- **Node C**: Raspberry Pi. Runs Mosquitto MQTT broker, serial bridge, and ML decoder. Python 3.7 — all Pi code must avoid 3.8+ syntax.
- **Node D**: Laptop. Runs Flask-SocketIO dashboard with live Chart.js panels, manual inject, and reset button.

## Communication
Arduinos connect to Pi via USB serial only (no WiFi). Pi serial bridge translates between hardware and MQTT. Laptop connects to Pi's broker over LAN.

## Serial Protocol
Node A -> Pi (plain text, 115200 baud):
- `TAP,<duration_us>\n`
- `GAP,<duration_us>\n`

Pi -> Node B (plain text, 115200 baud):
- `CHAR,<c>\n` — append character to LCD
- `MSG,<text>\n` — replace LCD line 2
- `TONE,<pattern>\n` — play Morse on buzzer (e.g. "...", "---")
- `SOS\n` — play warbling alarm

## Signal Processing — ML Core
Random Forest classifier (100 trees, max_depth=12, class_weight="balanced").

**Features per event (4):**
- Raw duration (ms)
- Duration / running session mean (speed normalization)
- Duration / previous duration (relative ratio)
- Is-tap flag (1=tap, 0=gap)

**Classes:** dot, dash, intra-letter gap, inter-letter gap, word gap

**Training:** Synthetic data from realistic Morse sessions (~55k samples, 10/15/20/25 WPM, 15% noise). Events in natural sequential order so session mean matches inference.

**Model deployment:** Trained with sklearn on laptop, exported to JSON via `train_model.py`. Pi loads JSON with `rf_lite.py` — pure numpy tree traversal, no sklearn needed. Pi deps: `paho-mqtt pyserial numpy` only.

**Inference pipeline:**
1. ML model classifies all events (taps AND gaps)
2. During warmup (first 6 events), fixed thresholds (400ms/1200ms) used as fallback
3. After warmup, model handles gap classification via session-normalized features
4. Buffer overflow at 7 symbols flushes immediately
5. Decoded characters published to MQTT + Morse pattern sent to Node B buzzer
6. SOS detection triggers warbling alarm on Node B

## Critical Bug History (do not reintroduce)
- **MQTT feedback loop**: Decoder subscribed to `pager/morse/raw/#` which matched its own `raw/A/classified` output → infinite 0ms ghost events. Fix: subscribe to `pager/morse/raw/+` (single-level wildcard).
- **Python 3.7 compat**: Pi runs old Python. No `dict | None`, no walrus `:=`, no `dict[str, X]`.
- **Arduino firmware**: Must be uploaded via Arduino IDE from laptop. `git pull` on Pi does NOT flash Arduinos. Arduino serial ports change on replug — always `ls /dev/ttyACM*` first.
- **0ms durations**: If all durations show 0ms, the Arduino has old firmware. Re-upload .ino.

## MQTT Topic Structure
- `pager/morse/raw/<node_id>` — raw tap/gap events from serial bridge
- `pager/morse/raw/<node_id>/classified` — events with ML label (decoder publishes, nobody subscribes)
- `pager/morse/decoded/<node_id>` — decoded character + confidence
- `pager/alert/<node_id>` — tone/SOS commands for Node B
- `pager/status/<node_id>` — node online/offline state
- `pager/control/reset` — session reset command

## Wiring

### Node A — Arduino Uno R3 (Sender)
No shield. All pins free.
| Component | Pin |
|-----------|-----|
| Pushbutton (one leg to D2, other to GND) | D2 (INPUT_PULLUP) |
| Buzzer + | D4 |
| Buzzer - | GND |

### Node B — Arduino Uno R3 (Receiver)
LCD shield stacked (D4-D10, A0).
| Component | Pin |
|-----------|-----|
| LCD shield | stacked (D4-D10) |
| Buzzer + | D13 |
| Buzzer - | GND |
| LED 1 (dot indicator) | D2 (with resistor) |
| LED 2 (dash indicator) | D3 (with resistor) |

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
├── tests/ (89 tests, all passing)
└── README.txt
```

## Pi Dependencies
```
pip install paho-mqtt pyserial numpy
```

## Laptop Dependencies
Training: `numpy pandas scikit-learn joblib`
Dashboard: `flask flask-socketio paho-mqtt`

## Startup Sequence
1. `sudo systemctl start mosquitto` (Pi)
2. `python3 serial_bridge.py --port-a /dev/ttyACM<A> --port-b /dev/ttyACM<B>` (Pi terminal 1)
3. `python3 ml_decoder.py` (Pi terminal 2)
4. `python app.py --broker <pi_ip>` (Laptop)

## Constraints
- Pi code must be Python 3.7 compatible. No walrus operator, no `dict | None`, no `dict[str, X]`.
- Pi runs `rf_lite.py` for inference. No sklearn on Pi.
- Arduino serial ports shift on replug. Always check `ls /dev/ttyACM*`.
- Node B LCD shield uses D4-D10. Do not use those pins.
- Node A has no LCD. Node B has no buttons.
- D13 on Uno has the built-in LED — buzzer on D13 is fine but external LED on D13 is dim.
