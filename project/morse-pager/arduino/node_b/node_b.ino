/*
 * Node B — Morse Code Receiver Terminal
 *
 * Hardware: Arduino Uno R3 + 16x2 LCD shield (stacked) + buzzer + 2 LEDs
 * No buttons on this node. Receive-only.
 *
 * LCD shield occupies D4–D10 and A0.
 * Remaining free digital pins: D2, D3, D11, D12, D13.
 *
 * Receives commands from the Pi over USB serial:
 *   CHAR,<character>        — display character on LCD + blink LEDs
 *   TONE,<morse_pattern>    — play Morse pattern on buzzer (e.g. "...", "---")
 *   MSG,<text>              — display full message on LCD line 2
 *   SOS                     — play SOS alarm (distinct warbling tone)
 *
 * Wiring:
 *   LCD shield:  stacked (D4–D10)
 *   Buzzer +     D13
 *   Buzzer -     GND
 *   LED 1:       D2 (with resistor) — blinks on dot
 *   LED 2:       D3 (with resistor) — blinks on dash
 */

#include <LiquidCrystal.h>

LiquidCrystal lcd(8, 9, 4, 5, 6, 7);

const int BUZZER_PIN = 13;
const int LED_DOT_PIN = 2;
const int LED_DASH_PIN = 3;

const int TONE_FREQ = 800;
const int DOT_MS = 80;
const int DASH_MS = 240;
const int SYMBOL_GAP_MS = 80;

char displayLine[17] = "";
int displayPos = 0;

char serialBuf[128];
int serialBufPos = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; }

    lcd.begin(16, 2);
    lcd.clear();

    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_DOT_PIN, OUTPUT);
    pinMode(LED_DASH_PIN, OUTPUT);

    // Startup test
    lcd.setCursor(0, 0);
    lcd.print("LED/Buzz Test...");

    digitalWrite(LED_DOT_PIN, HIGH); delay(200);
    digitalWrite(LED_DOT_PIN, LOW);
    digitalWrite(LED_DASH_PIN, HIGH); delay(200);
    digitalWrite(LED_DASH_PIN, LOW);
    tone(BUZZER_PIN, TONE_FREQ, 150); delay(200);
    tone(BUZZER_PIN, TONE_FREQ + 200, 150); delay(200);

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Morse Pager [B]");
    lcd.setCursor(0, 1);
    lcd.print("Waiting...");
}

void loop() {
    handleSerialInput();
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

    } else if (strncmp(cmd, "TONE,", 5) == 0) {
        // Play Morse pattern: dots and dashes as audio + LEDs
        const char* pattern = cmd + 5;
        playMorsePattern(pattern);

    } else if (strcmp(cmd, "SOS") == 0) {
        playSosAlarm();

    } else if (strcmp(cmd, "RESET") == 0) {
        displayPos = 0;
        displayLine[0] = '\0';
        lcd.setCursor(0, 1);
        lcd.print("                ");
        lcd.setCursor(0, 1);
        lcd.print("Waiting...");

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

void playMorsePattern(const char* pattern) {
    for (int i = 0; pattern[i] != '\0'; i++) {
        if (pattern[i] == '.') {
            digitalWrite(LED_DOT_PIN, HIGH);
            tone(BUZZER_PIN, TONE_FREQ);
            delay(DOT_MS);
            noTone(BUZZER_PIN);
            digitalWrite(LED_DOT_PIN, LOW);
        } else if (pattern[i] == '-') {
            digitalWrite(LED_DASH_PIN, HIGH);
            tone(BUZZER_PIN, TONE_FREQ);
            delay(DASH_MS);
            noTone(BUZZER_PIN);
            digitalWrite(LED_DASH_PIN, LOW);
        }
        delay(SYMBOL_GAP_MS);
    }
}

void playSosAlarm() {
    // Warbling alarm tone for SOS detection
    for (int i = 0; i < 3; i++) {
        tone(BUZZER_PIN, 1000);
        digitalWrite(LED_DOT_PIN, HIGH);
        digitalWrite(LED_DASH_PIN, HIGH);
        delay(150);
        tone(BUZZER_PIN, 1400);
        digitalWrite(LED_DOT_PIN, LOW);
        digitalWrite(LED_DASH_PIN, LOW);
        delay(150);
    }
    noTone(BUZZER_PIN);
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
