const int BUTTON_PIN = 2;    // Pushbutton wired to D2, other leg to GND
const int BUZZER_PIN = 4;
const int BUZZER_FREQ = 800;

bool lastButtonState = true;  // INPUT_PULLUP: unpressed = HIGH
unsigned long pressTime = 0;
unsigned long releaseTime = 0;
bool isPressed = false;

const unsigned long DEBOUNCE_US = 5000;
unsigned long lastChangeTime = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial) { ; }
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    pinMode(BUZZER_PIN, OUTPUT);
}

void loop() {
    bool buttonState = !digitalRead(BUTTON_PIN);  // invert: LOW = pressed
    unsigned long now = micros();

    if (buttonState != lastButtonState) {
        if (now - lastChangeTime < DEBOUNCE_US) return;
        lastChangeTime = now;
        lastButtonState = buttonState;
    } else {
        return;
    }

    if (buttonState && !isPressed) {
        isPressed = true;
        pressTime = now;
        if (releaseTime > 0) {
            Serial.print("GAP,");
            Serial.println(pressTime - releaseTime);
        }
        tone(BUZZER_PIN, BUZZER_FREQ);
    } else if (!buttonState && isPressed) {
        isPressed = false;
        releaseTime = now;
        Serial.print("TAP,");
        Serial.println(releaseTime - pressTime);
        noTone(BUZZER_PIN);
    }
}