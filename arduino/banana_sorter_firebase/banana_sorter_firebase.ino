/**
 * AIoT CHALLENGE 2026 - Smart Banana Ripeness Sorting System
 * Protocol: Cloud Control via Firebase Realtime Database (Option B)
 * 
 * Dependencies:
 * - Arduino IDE -> Library Manager -> Install "Firebase ESP Client" by Mobizt
 * - If using ESP8266, install "ESP8266 Board Package"
 * - If using ESP32, install "ESP32 Board Package"
 * 
 * Hardware Layout:
 * - Relay 1 (Unripe)   -> Pin D5 (GPIO 14)
 * - Relay 2 (Ripe)     -> Pin D6 (GPIO 12)
 * - Relay 3 (Overripe) -> Pin D7 (GPIO 13)
 * - Relay 4 (Rotten)   -> Pin D8 (GPIO 15)
 * - Indicator LED      -> Pin D4 (Built-in LED, GPIO 2, Active-LOW)
 */

#if defined(ESP8266)
#include <ESP8266WiFi.h>
#elif defined(ESP32)
#include <WiFi.h>
#endif

#include <Firebase_ESP_Client.h>

// Provide the RTDB payload printing info helper (for debugging)
#include <addons/RTDBHelper.h>

// 1. WiFi Credentials Configuration
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// 2. Firebase Project Credentials Configuration
// Firebase RTDB URL (e.g. "https://project-id-default-rtdb.firebaseio.com/")
#define DATABASE_URL "YOUR_FIREBASE_DATABASE_URL"
// Database Secret / API Key
#define DATABASE_SECRET "YOUR_FIREBASE_DATABASE_SECRET"

// Define relay pins
const int RELAY_1_PIN = 14; // D5
const int RELAY_2_PIN = 12; // D6
const int RELAY_3_PIN = 13; // D7
const int RELAY_4_PIN = 15; // D8
const int LED_INDICATOR = 2; // D4 (Built-in LED)

// Relay Logic Configuration (ACTIVE-LOW)
const int RELAY_ON = LOW;
const int RELAY_OFF = HIGH;

// Firebase Data Objects
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// Status LED variables
unsigned long lastBlinkTime = 0;
int blinkInterval = 1000; // Slow blink (connecting/idle)
bool ledState = HIGH;      // LED off (active-LOW)

void setup() {
  Serial.begin(115200);

  // Configure Relay and LED Pins
  pinMode(RELAY_1_PIN, OUTPUT);
  pinMode(RELAY_2_PIN, OUTPUT);
  pinMode(RELAY_3_PIN, OUTPUT);
  pinMode(RELAY_4_PIN, OUTPUT);
  pinMode(LED_INDICATOR, OUTPUT);

  // All Relays OFF initially
  turnAllRelaysOff();
  digitalWrite(LED_INDICATOR, HIGH); // LED off

  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    digitalWrite(LED_INDICATOR, LOW);
    delay(100);
    digitalWrite(LED_INDICATOR, HIGH);
    delay(100);
  }
  Serial.println();
  Serial.print("Connected with IP: ");
  Serial.println(WiFi.localIP());

  // Configure Firebase connection details
  config.database_url = DATABASE_URL;
  config.signer.tokens.legacy_token = DATABASE_SECRET; // Using database secret (RTDB legacy token)

  // Initialize Firebase Client
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  // Set database stream for real-time monitoring on path: /deteksi
  if (!Firebase.RTDB.beginStream(&fbdo, "/deteksi")) {
    Serial.printf("Firebase Stream begin error: %s\n", fbdo.errorReason().c_str());
  } else {
    Serial.println("Firebase RTDB Stream started on path '/deteksi'. Listening...");
  }
}

void loop() {
  // 1. Process Real-Time Firebase Stream updates
  if (Firebase.ready()) {
    if (!Firebase.RTDB.readStream(&fbdo)) {
      Serial.printf("Firebase Stream read error: %s\n", fbdo.errorReason().c_str());
    }

    if (fbdo.streamTimeout()) {
      Serial.println("Firebase Stream timeout, resuming...");
    }

    if (fbdo.streamAvailable()) {
      // Check if the change is at "/status" or a key inside /deteksi
      if (fbdo.dataPath() == "/status" || fbdo.dataPath() == "/") {
        String statusVal = "";
        
        if (fbdo.dataPath() == "/status") {
          statusVal = fbdo.stringData();
        } else if (fbdo.dataPath() == "/") {
          // If the root node /deteksi was updated, parse JSON to find status
          if (fbdo.dataType() == "json") {
            FirebaseJson &json = fbdo.jsonObject();
            FirebaseJsonData jsonData;
            json.get(jsonData, "status");
            if (jsonData.success) {
              statusVal = jsonData.stringValue;
            }
          }
        }

        if (statusVal != "") {
          statusVal.trim();
          statusVal.toLowerCase();
          executeSortAction(statusVal);
        }
      }
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
 * Maps banana status string to relay controls
 */
void executeSortAction(String status) {
  Serial.print("Firebase Status Updated: \"");
  Serial.print(status);
  Serial.println("\"");

  if (status == "unripe") {
    digitalWrite(RELAY_1_PIN, RELAY_ON);
    digitalWrite(RELAY_2_PIN, RELAY_OFF);
    digitalWrite(RELAY_3_PIN, RELAY_OFF);
    digitalWrite(RELAY_4_PIN, RELAY_OFF);
    blinkInterval = 300; // Medium blink
    Serial.println("Action: Relay 1 ON [Unripe Sorting Activated]");
  } 
  else if (status == "ripe") {
    digitalWrite(RELAY_1_PIN, RELAY_OFF);
    digitalWrite(RELAY_2_PIN, RELAY_ON);
    digitalWrite(RELAY_3_PIN, RELAY_OFF);
    digitalWrite(RELAY_4_PIN, RELAY_OFF);
    blinkInterval = 150; // Fast blink
    Serial.println("Action: Relay 2 ON [Ripe Sorting Activated]");
  } 
  else if (status == "overripe") {
    digitalWrite(RELAY_1_PIN, RELAY_OFF);
    digitalWrite(RELAY_2_PIN, RELAY_OFF);
    digitalWrite(RELAY_3_PIN, RELAY_ON);
    digitalWrite(RELAY_4_PIN, RELAY_OFF);
    blinkInterval = 300; // Medium blink
    Serial.println("Action: Relay 3 ON [Overripe Sorting Activated]");
  } 
  else if (status == "rotten") {
    digitalWrite(RELAY_1_PIN, RELAY_OFF);
    digitalWrite(RELAY_2_PIN, RELAY_OFF);
    digitalWrite(RELAY_3_PIN, RELAY_OFF);
    digitalWrite(RELAY_4_PIN, RELAY_ON);
    blinkInterval = 75; // Ultra-fast blink (Alarm)
    Serial.println("Action: Relay 4 ON [Rotten Sorting Activated]");
  } 
  else {
    // Idle state
    turnAllRelaysOff();
    blinkInterval = 1000; // Slow blink (Standby)
    Serial.println("Action: All Relays OFF [System Standby]");
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
