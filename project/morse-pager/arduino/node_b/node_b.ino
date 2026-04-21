/*
 * Node B — Morse Code Receiver Terminal
 *
 * Hardware: Arduino Uno R3 + 16x2 LCD shield (stacked) + RGB LED + 2 extra LEDs
 * No buttons, no buzzer on this node. Receive-only.
 *
 * LCD shield occupies D4–D10 and A0.
 * Remaining free digital pins: D2, D3, D11, D12, D13.
 *
 * Receives commands from the Pi over USB serial:
 *   CHAR,<character>        — display decoded character on LCD
 *   RGB,<r>,<g>,<b>         — set RGB LED color (0 or 1 per channel, digital)
 *   MSG,<text>              — display full message on LCD line 2
 *
 * Wiring:
 *   LCD shield:  stacked (D4–D10)
 *   RGB LED R:   D11 (with 220Ω resistor)
 *   RGB LED G:   D12 (with 220Ω resistor)
 *   RGB LED B:   D13 (with 220Ω resistor)
 *   RGB cathode: GND
 *   Extra LED 1: D2 (with 1.5kΩ resistor) — blink on incoming Morse
 *   Extra LED 2: D3 (with 1.5kΩ resistor) — blink on incoming Morse
 */

#include <LiquidCrystal.h>

// LCD shield pin configuration (standard DFRobot/SainSmart 16x2 shield)
LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

// --- Pin Configuration ---
const int RGB_R_PIN = 11;
const int RGB_G_PIN = 12;
const int RGB_B_PIN = 13;
const int LED1_PIN = 2;
const int LED2_PIN = 3;

// --- Display state ---
char displayLine[17] = "";  // 16 chars + null for LCD line 2
int displayPos = 0;

// --- Serial input buffer ---
char serialBuf[128];
int serialBufPos = 0;

// --- LED blink state ---
unsigned long lastBlinkTime = 0;
bool blinkState = false;
bool blinkActive = false;
const unsigned long BLINK_DURATION = 200; // ms per blink
int blinksRemaining = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; }

    lcd.begin(16, 2);
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Morse Pager [B]");
    lcd.setCursor(0, 1);
    lcd.print("Waiting...");

    // RGB LED pins — digital output only (D12, D13 not PWM on Uno)
    pinMode(RGB_R_PIN, OUTPUT);
    pinMode(RGB_G_PIN, OUTPUT);
    pinMode(RGB_B_PIN, OUTPUT);

    // Extra LEDs
    pinMode(LED1_PIN, OUTPUT);
    pinMode(LED2_PIN, OUTPUT);

    // Start with RGB green = ready
    setRGB(0, 1, 0);
    digitalWrite(LED1_PIN, LOW);
    digitalWrite(LED2_PIN, LOW);
}

void loop() {
    handleSerialInput();
    handleBlink();
}

void handleSerialInput() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n') {
            serialBuf[serialBufPos] = '\0';
            processCommand(serialBuf);
            serialBufPos = 0;
        } else if (c != '\r' && serialBufPos < 126) {
            serialBuf[serialBufPos++] = c;
        }
    }
}

void processCommand(const char* cmd) {
    if (strncmp(cmd, "CHAR,", 5) == 0) {
        // Single decoded character
        char ch = cmd[5];
        appendChar(ch);
        triggerBlink(3);

    } else if (strncmp(cmd, "RGB,", 4) == 0) {
        // RGB command: RGB,r,g,b (each 0 or 1)
        int r = 0, g = 0, b = 0;
        sscanf(cmd + 4, "%d,%d,%d", &r, &g, &b);
        setRGB(r, g, b);

    } else if (strncmp(cmd, "MSG,", 4) == 0) {
        // Full message — replace LCD line 2
        const char* text = cmd + 4;
        lcd.setCursor(0, 1);
        lcd.print("                "); // clear line
        lcd.setCursor(0, 1);

        // Show last 16 chars if message is longer
        int len = strlen(text);
        if (len > 16) {
            lcd.print(text + len - 16);
        } else {
            lcd.print(text);
        }

        // Reset display buffer to match
        displayPos = 0;
        int start = (len > 16) ? len - 16 : 0;
        for (int i = start; i < len && displayPos < 16; i++) {
            displayLine[displayPos++] = text[i];
        }
        displayLine[displayPos] = '\0';
    }
}

void appendChar(char ch) {
    if (displayPos >= 16) {
        // Scroll left
        for (int i = 0; i < 15; i++) {
            displayLine[i] = displayLine[i + 1];
        }
        displayPos = 15;
    }
    displayLine[displayPos] = ch;
    displayPos++;
    displayLine[displayPos] = '\0';

    lcd.setCursor(0, 1);
    lcd.print("                "); // clear line
    lcd.setCursor(0, 1);
    lcd.print(displayLine);
}

void triggerBlink(int count) {
    blinksRemaining = count * 2; // each blink = on + off
    blinkActive = true;
    blinkState = true;
    lastBlinkTime = millis();
    digitalWrite(LED1_PIN, HIGH);
    digitalWrite(LED2_PIN, HIGH);
}

void handleBlink() {
    if (!blinkActive) return;

    unsigned long now = millis();
    if (now - lastBlinkTime >= BLINK_DURATION) {
        lastBlinkTime = now;
        blinkState = !blinkState;
        digitalWrite(LED1_PIN, blinkState ? HIGH : LOW);
        digitalWrite(LED2_PIN, blinkState ? HIGH : LOW);

        blinksRemaining--;
        if (blinksRemaining <= 0) {
            blinkActive = false;
            digitalWrite(LED1_PIN, LOW);
            digitalWrite(LED2_PIN, LOW);
        }
    }
}

void setRGB(int r, int g, int b) {
    // Digital only — D12 and D13 are not PWM on Uno
    digitalWrite(RGB_R_PIN, r ? HIGH : LOW);
    digitalWrite(RGB_G_PIN, g ? HIGH : LOW);
    digitalWrite(RGB_B_PIN, b ? HIGH : LOW);
}
