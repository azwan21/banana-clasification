/**
 * AIoT CHALLENGE 2026 - Smart Banana Ripeness Sorting System
 * Protocol: Direct Serial Communication (Option A)
 * 
 * Hardware Layout (NodeMCU ESP8266):
 * - Relay 1 (Unripe)   -> Pin D5 (GPIO 14)
 * - Relay 2 (Ripe)     -> Pin D6 (GPIO 12)
 * - Relay 3 (Overripe) -> Pin D7 (GPIO 13)
 * - Relay 4 (Rotten)   -> Pin D8 (GPIO 15)
 * - Indicator LED      -> Pin D4 (Built-in LED, GPIO 2, Active-LOW)
 * 
 * Communication Baud Rate: 115200 bps
 */

// Define relay pins
const int RELAY_1_PIN = 14; // D5
const int RELAY_2_PIN = 27; // D6
const int RELAY_3_PIN = 26; // D7
const int RELAY_4_PIN = 25; // D8
const int LED_INDICATOR = 2; // D4 (Built-in LED, active-LOW on ESP8266)

// Relay Logic Configuration
// Most standard multi-channel relay modules are ACTIVE-LOW (LOW turns relay ON).
// If your relay module is ACTIVE-HIGH, swap these values.
const int RELAY_ON = LOW;
const int RELAY_OFF = HIGH;

// Timing configuration for status indicator LED
unsigned long lastBlinkTime = 0;
int blinkInterval = 1000; // Default slow blink (Idle state)
bool ledState = HIGH;      // LED off (since active-LOW)

void setup() {
  // Initialize Serial communication at 115200 baud
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for serial port to connect (needed for native USB port only)
  }

  // Configure Relay Pins as outputs
  pinMode(RELAY_1_PIN, OUTPUT);
  pinMode(RELAY_2_PIN, OUTPUT);
  pinMode(RELAY_3_PIN, OUTPUT);
  pinMode(RELAY_4_PIN, OUTPUT);
  pinMode(LED_INDICATOR, OUTPUT);

  // Set initial state: All relays OFF
  turnAllRelaysOff();
  digitalWrite(LED_INDICATOR, HIGH); // LED off initially

  Serial.println("System Initialized. Awaiting Serial Commands...");
  Serial.println("Command Cheat Sheet:");
  Serial.println("  '0' : Turn off all relays (Idle / No Banana)");
  Serial.println("  '1' : Unripe Banana -> Relay 1 ON");
  Serial.println("  '2' : Ripe Banana   -> Relay 2 ON");
  Serial.println("  '3' : Overripe Banana -> Relay 3 ON");
  Serial.println("  '4' : Rotten Banana -> Relay 4 ON");
}

void loop() {
  // 1. Process Incoming Serial Commands
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    // Ignore newline and carriage return characters
    if (command != '\n' && command != '\r') {
      executeCommand(command);
    }
  }

  // 2. Non-blocking status LED indicator
  unsigned long currentMillis = millis();
  if (currentMillis - lastBlinkTime >= blinkInterval) {
    lastBlinkTime = currentMillis;
    ledState = !ledState;
    digitalWrite(LED_INDICATOR, ledState);
  }
}

/**
 * Parses and executes sorting actions based on incoming serial command
 */
void executeCommand(char command) {
  Serial.print("Received Command: '");
  Serial.print(command);
  Serial.println("'");

  switch (command) {
    case '0':
      turnAllRelaysOff();
      blinkInterval = 1000; // Slow blink (system idle)
      Serial.println("Action: All Relays OFF [System Idle]");
      break;

    case '1':
      // Unripe Banana
      digitalWrite(RELAY_1_PIN, RELAY_ON);
      digitalWrite(RELAY_2_PIN, RELAY_OFF);
      digitalWrite(RELAY_3_PIN, RELAY_OFF);
      digitalWrite(RELAY_4_PIN, RELAY_OFF);
      blinkInterval = 300; // Faster blink (Unripe active)
      Serial.println("Action: Relay 1 ON [Unripe Sorting Activated]");
      break;

    case '2':
      // Ripe Banana
      digitalWrite(RELAY_1_PIN, RELAY_OFF);
      digitalWrite(RELAY_2_PIN, RELAY_ON);
      digitalWrite(RELAY_3_PIN, RELAY_OFF);
      digitalWrite(RELAY_4_PIN, RELAY_OFF);
      blinkInterval = 150; // Rapid blink (Ripe active)
      Serial.println("Action: Relay 2 ON [Ripe Sorting Activated]");
      break;

    case '3':
      // Overripe Banana
      digitalWrite(RELAY_1_PIN, RELAY_OFF);
      digitalWrite(RELAY_2_PIN, RELAY_OFF);
      digitalWrite(RELAY_3_PIN, RELAY_ON);
      digitalWrite(RELAY_4_PIN, RELAY_OFF);
      blinkInterval = 300; // Medium-fast blink (Overripe active)
      Serial.println("Action: Relay 3 ON [Overripe Sorting Activated]");
      break;

    case '4':
      // Rotten Banana
      digitalWrite(RELAY_1_PIN, RELAY_OFF);
      digitalWrite(RELAY_2_PIN, RELAY_OFF);
      digitalWrite(RELAY_3_PIN, RELAY_OFF);
      digitalWrite(RELAY_4_PIN, RELAY_ON);
      blinkInterval = 75; // Ultra-fast blink (Rotten alarm)
      Serial.println("Action: Relay 4 ON [Rotten Sorting Activated]");
      break;

    default:
      Serial.print("Warning: Unknown command '");
      Serial.print(command);
      Serial.println("'. Ignoring.");
      break;
  }
}

/**
 * Turns off all relays safety first
 */
void turnAllRelaysOff() {
  digitalWrite(RELAY_1_PIN, RELAY_OFF);
  digitalWrite(RELAY_2_PIN, RELAY_OFF);
  digitalWrite(RELAY_3_PIN, RELAY_OFF);
  digitalWrite(RELAY_4_PIN, RELAY_OFF);
}
