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
 *   RGB LED R:   D11 (with 220 ohm resistor)
 *   RGB LED G:   D12 (with 220 ohm resistor)
 *   RGB LED B:   D13 (with 220 ohm resistor)
 *   RGB cathode: GND (common cathode) — if common anode, set COMMON_ANODE true
 *   Extra LED 1: D2 (with resistor)
 *   Extra LED 2: D3 (with resistor)
 */

#include <LiquidCrystal.h>

// LCD shield pin configuration (standard DFRobot/SainSmart 16x2 shield)
LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

// --- Configuration ---
// Set to true if your RGB LED is common ANODE (most kit RGB LEDs are)
const bool COMMON_ANODE = true;

// --- Pin Configuration ---
const int RGB_R_PIN = 11;
const int RGB_G_PIN = 12;
const int RGB_B_PIN = 13;
const int LED1_PIN = 2;
const int LED2_PIN = 3;

// --- Display state ---
char displayLine[17] = "";
int displayPos = 0;

// --- Serial input buffer ---
char serialBuf[128];
int serialBufPos = 0;

// --- LED blink state ---
unsigned long lastBlinkTime = 0;
bool blinkState = false;
bool blinkActive = false;
const unsigned long BLINK_DURATION = 150;
int blinksRemaining = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; }

    lcd.begin(16, 2);
    lcd.clear();

    pinMode(RGB_R_PIN, OUTPUT);
    pinMode(RGB_G_PIN, OUTPUT);
    pinMode(RGB_B_PIN, OUTPUT);
    pinMode(LED1_PIN, OUTPUT);
    pinMode(LED2_PIN, OUTPUT);

    // Startup test: cycle through all LEDs so you can verify hardware
    lcd.setCursor(0, 0);
    lcd.print("LED Test...");

    setRGB(1, 0, 0); delay(300);  // Red
    setRGB(0, 1, 0); delay(300);  // Green
    setRGB(0, 0, 1); delay(300);  // Blue
    setRGB(1, 1, 1); delay(300);  // White
    setRGB(0, 0, 0);              // Off

    digitalWrite(LED1_PIN, HIGH); delay(200);
    digitalWrite(LED1_PIN, LOW);
    digitalWrite(LED2_PIN, HIGH); delay(200);
    digitalWrite(LED2_PIN, LOW);

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Morse Pager [B]");
    lcd.setCursor(0, 1);
    lcd.print("Waiting...");

    setRGB(0, 1, 0);  // Green = ready
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
        char ch = cmd[5];
        appendChar(ch);
        triggerBlink(2);

    } else if (strncmp(cmd, "RGB,", 4) == 0) {
        int r = 0, g = 0, b = 0;
        sscanf(cmd + 4, "%d,%d,%d", &r, &g, &b);
        setRGB(r, g, b);

    } else if (strncmp(cmd, "MSG,", 4) == 0) {
        const char* text = cmd + 4;
        lcd.setCursor(0, 1);
        lcd.print("                ");
        lcd.setCursor(0, 1);

        int len = strlen(text);
        if (len > 16) {
            lcd.print(text + len - 16);
        } else {
            lcd.print(text);
        }

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
        for (int i = 0; i < 15; i++) {
            displayLine[i] = displayLine[i + 1];
        }
        displayPos = 15;
    }
    displayLine[displayPos] = ch;
    displayPos++;
    displayLine[displayPos] = '\0';

    lcd.setCursor(0, 1);
    lcd.print("                ");
    lcd.setCursor(0, 1);
    lcd.print(displayLine);
}

void triggerBlink(int count) {
    blinksRemaining = count * 2;
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
    if (COMMON_ANODE) {
        // Common anode: HIGH = off, LOW = on
        digitalWrite(RGB_R_PIN, r ? LOW : HIGH);
        digitalWrite(RGB_G_PIN, g ? LOW : HIGH);
        digitalWrite(RGB_B_PIN, b ? LOW : HIGH);
    } else {
        // Common cathode: HIGH = on, LOW = off
        digitalWrite(RGB_R_PIN, r ? HIGH : LOW);
        digitalWrite(RGB_G_PIN, g ? HIGH : LOW);
        digitalWrite(RGB_B_PIN, b ? HIGH : LOW);
    }
}
