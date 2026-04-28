Morse Code IoT Pager: EE250 Final Project

TEAM MEMBERS
Abhigya Goel
Lucas Kim


OVERVIEW
A four-node Morse code pager. A user taps Morse code on a pushbutton connected
to Arduino Node A. The Raspberry Pi decodes the tap stream in real time using
a trained Random Forest classifier and relays the decoded message to Arduino
Node B, which displays it on an LCD and plays it back audibly through a buzzer.
A laptop runs a Flask dashboard that visualizes the ML inference live.


INSTRUCTIONS TO COMPILE/EXECUTE

1. Training (laptop, one-time):
   cd training
   pip install numpy pandas scikit-learn joblib
   python generate_data.py
   python train_model.py

2. Arduino (upload via Arduino IDE on laptop):
   Upload arduino/node_a/node_a.ino to Node A Arduino
   Upload arduino/node_b/node_b.ino to Node B Arduino
   Connect both to Pi via USB

3. Raspberry Pi:
   sudo apt install mosquitto mosquitto-clients
   pip install paho-mqtt pyserial numpy
   cd project/morse-pager/pi
   ls /dev/ttyACM*
   python3 serial_bridge.py --port-a /dev/ttyACM<A> --port-b /dev/ttyACM<B>
   python3 ml_decoder.py    (in a second terminal)

4. Dashboard (laptop):
   cd dashboard
   pip install flask flask-socketio paho-mqtt
   python app.py --broker <pi_ip_address>
   Open http://localhost:5000


EXTERNAL LIBRARIES
Pi:         paho-mqtt, pyserial, numpy
Laptop:     flask, flask-socketio, paho-mqtt
Training:   numpy, pandas, scikit-learn, joblib
Frontend:   Chart.js (CDN), Socket.IO client (CDN)
Arduino:    LiquidCrystal (built-in)


NODES

Node A - Arduino Uno R3 (Sender)
  Pushbutton on D2 (INPUT_PULLUP). Button only.
  Computes tap/gap durations using micros() and streams them over USB serial
  as plain text: TAP,<duration_us> and GAP,<duration_us>.

Node B - Arduino Uno R3 (Receiver)
  16x2 LCD shield (stacked, D4-D10), buzzer on D13, LED1 on D2, LED2 on D3.
  Displays decoded characters on LCD. Plays back decoded Morse patterns
  through the buzzer (dots = short beep, dashes = long beep). LED1 blinks for
  dots, LED2 blinks for dashes. SOS triggers a warbling alarm tone.

Node C - Raspberry Pi
  Runs Mosquitto MQTT broker, serial bridge (reads Node A, writes Node B),
  and ML decoder (Random Forest inference). Uses a lightweight JSON model
  loaded by rf_lite.py (pure numpy, no sklearn needed on Pi).

Node D - Laptop
  Runs Flask-SocketIO dashboard with live Chart.js visualizations.
  Manual inject panel lets you type text to encode as Morse and send to
  Node B (LCD + buzzer). Reset button clears session state.


SERIAL PROTOCOL

Node A -> Pi (plain text, 115200 baud):
  TAP,<duration_us>
  GAP,<duration_us>

Pi -> Node B (plain text, 115200 baud):
  CHAR,<character>          - append character to LCD
  TONE,<morse_pattern>      - play Morse on buzzer (e.g. "...", "---")
  SOS                       - play warbling alarm tone
  RESET                     - clear LCD back to "Waiting..."


MQTT TOPICS
  pager/morse/raw/A              - raw tap/gap events (JSON, from bridge)
  pager/morse/raw/A/classified   - events with ML label + confidence (from decoder)
  pager/morse/decoded/<node>     - decoded character + confidence (from decoder)
  pager/alert/<node>             - tone/SOS commands for Node B (from decoder)
  pager/status/<node>            - node online/offline state
  pager/control/reset            - session reset command (from dashboard)


ML APPROACH
Random Forest classifier (100 trees, max_depth=12, class_weight="balanced").

Training: Synthetic data generated from realistic Morse sessions. Simulates
actual English words at 10/15/20/25 WPM with 15% Gaussian noise. Events
processed in natural sequential order so the running session mean matches
real-time inference. ~55k samples. Trained on laptop with sklearn, exported
to JSON for Pi deployment (no sklearn needed on Pi).

Features per event (4 features):
  1. Raw duration (ms)
  2. Duration / running session mean (speed normalization)
  3. Duration / previous duration (relative ratio)
  4. Is-tap flag (1 = tap, 0 = gap)

Classes: dot, dash, intra-letter gap, inter-letter gap, word gap

Inference: ML model classifies all events. During a warmup period (first 6
events), fixed thresholds (400ms inter-letter, 1200ms word gap) are used as
fallback while the session mean stabilizes. After warmup, the model handles
gap classification using its session-normalized features.

Buffer overflow protection: if the letter buffer exceeds 6 symbols (max
valid Morse length), it flushes immediately.


FILE STRUCTURE
morse-pager/
  arduino/
    node_a/node_a.ino            - sender: button only, streams TAP/GAP
    node_b/node_b.ino            - receiver: LCD + buzzer + LEDs, plays Morse
  pi/
    serial_bridge.py             - USB serial to MQTT bridge
    ml_decoder.py                - real-time ML inference + Morse decoding
    rf_lite.py                   - lightweight RF inference (no sklearn)
    morse_lookup.py              - Morse code encode/decode lookup table
    model/
      rf_forest.json             - exported model for Pi
      rf_classifier.joblib       - sklearn model (laptop use)
  training/
    generate_data.py             - synthetic training data from Morse sessions
    train_model.py               - trains RF + exports JSON in one step
    export_model.py              - standalone JSON export (optional)
    training_data.csv            - generated training data (~55k rows)
  dashboard/
    app.py                       - Flask-SocketIO server + MQTT bridge
    templates/index.html         - live dashboard UI
    morse.db                     - SQLite message log (auto-created)
  tests/
    test_morse_lookup.py
    test_generate_data.py
    test_ml_decoder.py
    test_serial_bridge.py
    test_dashboard.py
  README.txt


LLM ACKNOWLEDGMENT
Claude Code (Anthropic) was used to assist with code development, debugging,
and iterative refinement throughout this project. All design decisions were
reviewed and understood by the team.
