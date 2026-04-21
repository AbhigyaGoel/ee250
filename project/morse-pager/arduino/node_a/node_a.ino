/*
 * Node A — Morse Code Sender Terminal
 *
 * Hardware: Arduino Uno R3 + capacitive touch sensor + buzzer
 * No LCD shield on this node.
 *
 * Captures tap/release timestamps from a capacitive touch sensor,
 * computes durations using micros(), and streams them over USB serial
 * as plain text lines.
 *
 * Serial output format (plain text, one per line):
 *   TAP,<duration_us>
 *   GAP,<duration_us>
 */

// --- Pin Configuration ---
const int TOUCH_PIN = 2;     // Capacitive touch sensor SIG
const int BUZZER_PIN = 3;    // Buzzer positive lead
const int BUZZER_FREQ = 800; // Hz

// --- State ---
bool lastTouchState = false;
unsigned long pressTime = 0;
unsigned long releaseTime = 0;
bool isPressed = false;

// Debounce
const unsigned long DEBOUNCE_US = 5000; // 5ms
unsigned long lastChangeTime = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; }

    pinMode(TOUCH_PIN, INPUT);
    pinMode(BUZZER_PIN, OUTPUT);
}

void loop() {
    bool touchState = digitalRead(TOUCH_PIN);
    unsigned long now = micros();

    // Debounce
    if (touchState != lastTouchState) {
        if (now - lastChangeTime < DEBOUNCE_US) {
            return;
        }
        lastChangeTime = now;
        lastTouchState = touchState;
    } else {
        return;
    }

    if (touchState && !isPressed) {
        // --- PRESS ---
        isPressed = true;
        pressTime = now;

        // Emit gap duration since last release
        if (releaseTime > 0) {
            unsigned long gapDuration = pressTime - releaseTime;
            Serial.print("GAP,");
            Serial.println(gapDuration);
        }

        // Buzzer on
        tone(BUZZER_PIN, BUZZER_FREQ);

    } else if (!touchState && isPressed) {
        // --- RELEASE ---
        isPressed = false;
        releaseTime = now;

        unsigned long tapDuration = releaseTime - pressTime;
        Serial.print("TAP,");
        Serial.println(tapDuration);

        // Buzzer off
        noTone(BUZZER_PIN);
    }
}
