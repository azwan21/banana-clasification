# 🍌 AIoT Smart Banana Ripeness Sorting System

Welcome to the **Smart Banana Ripeness Sorting System** project, built for the **AIoT Challenge 2026**. 

This system integrates a trained Deep Learning CNN classifier with physical actuators (relays) to automatically sort bananas based on their ripeness states: **Unripe**, **Ripe**, **Overripe**, and **Rotten**.

---

## 📸 System Overview

```
                        +---------------------------------------+
                        |          Webcam Video Stream          |
                        +---------------------------------------+
                                            |
                                            v (Frame Capture)
                        +---------------------------------------+
                        |      MobileNetV2 CNN Inference        |
                        +---------------------------------------+
                                            |
                                            v (Confidence Threshold > 60%)
                        +---------------------------------------+
                        |    State Change & Debounce Filter     |
                        +---------------------------------------+
                                            |
                         +------------------+------------------+
                         | (Serial/USB)                        | (Firebase/WiFi)
                         v                                     v
               +-------------------+                 +-------------------+
               |  pyserial Bridge  |                 | Firebase Admin SDK|
               +-------------------+                 +-------------------+
                         |                                     |
                         v                                     v
               +-------------------+                 +-------------------+
               |    NodeMCU USB    |                 |   Firebase Cloud  |
               +-------------------+                 +-------------------+
                         |                                     |
                         v (GPIO Controls)                     v (WiFi RTDB Stream)
               +---------------------------------------------------------+
               |                    NodeMCU ESP8266                      |
               +---------------------------------------------------------+
                                            | (High/Low Pin Logic)
                                            v
               +---------------------------------------------------------+
               |                4-Channel Relay Actuators                |
               +---------------------------------------------------------+
                                            |
         +---------------+---------------+---------------+---------------+
         | (Relay 1 ON)  | (Relay 2 ON)  | (Relay 3 ON)  | (Relay 4 ON)  |
         v               v               v               v               v
    +----------+    +----------+    +----------+    +----------+    +----------+
    |  Unripe  |    |   Ripe   |    | Overripe |    |  Rotten  |    |  System  |
    | LED/Gate |    | LED/Gate |    | LED/Gate |    | LED/Alarm|    |  Standby |
    +----------+    +----------+    +----------+    +----------+    +----------+
```

---

## 🛠️ Hardware Wiring & Pin Mapping

> [!WARNING]
> **Safety First:** For demonstration and safety purposes, the relays operate on a low-voltage DC circuit (5V–12V DC). Connecting to 220V AC household mains is strictly prohibited.

Standard multi-channel relay modules are **Active-Low** (supplying `LOW` to the input pin activates the relay coil).

### Pin Mapping Table

| Component | NodeMCU Pin | GPIO Number | Function / sorting Gate | Color Code (Wiring) |
| :--- | :---: | :---: | :--- | :---: |
| **Relay 1** | `D5` | `GPIO 14` | Unripe Banana (Chamber Fan / Yellow LED) | Pink |
| **Relay 2** | `D6` | `GPIO 12` | Ripe Banana (Packaging Line / Green LED) | Cyan |
| **Relay 3** | `D7` | `GPIO 13` | Overripe Banana (Processing Line / Orange LED) | Orange |
| **Relay 4** | `D8` | `GPIO 15` | Rotten Banana (Waste Rejection Bin / Red LED) | Green |
| **VCC** | `3V3` / `5V` | — | Power supply to Relay Board | Red |
| **GND** | `GND` | — | Common ground | White / Black |
| **Status LED** | `D4` | `GPIO 2` | Built-in LED showing connection status | Built-in |

---

## 🚀 Key Software Features

### 1. State Change Detection & Debounce Logic
To prevent serial buffer overflows and Firebase API rate-limiting, the controller implements a consensus-based debounce queue:
- **Confidence Filter:** Predictions are ignored if the prediction confidence is below `60%` (`0.60`).
- **Frame Buffering:** The system stores the last $N$ predictions in a moving queue (default: `5` frames).
- **Consensus Voting:** A state change command is dispatched only when a single class holds the majority in the frame history.
- **Standby Auto-timeout:** When the object is removed (or confidence falls), the system automatically defaults back to the `"idle"` state, turning OFF all relays.

### 2. Live Web Dashboard (Gold Level)
Serving a modern, responsive HTML5 UI on `http://localhost:5000`:
- **Real-Time Video HUD:** Features the live webcam stream overlaid with classification boxes, confidence bars, and processing telemetry.
- **Live Diagnostics:** Shows current FPS, inference time (ms), and connection health (Serial, WiFi, or Firebase).
- **Manual Override Controls:** Allows students to switch to manual mode and toggle each relay on/off directly from the dashboard to test physical wiring.
- **Dynamic Log Timeline:** Generates a real-time event log with timestamps.
- **Telegram Bot Notifications:** Configures a bot token and chat ID inside the dashboard to receive automated telegram push alerts with rich Markdown formatting when sorting states change.

### 3. Voice Alerts & Text-to-Speech (Platinum Level)
- Uses the native HTML5 **Web Speech API** inside the browser.
- Reads out alerts such as: *"Ripe banana detected. Activating packaging conveyor."* or *"Banana removed. System standby."*
- Zero additional python library dependencies, ensuring 100% platform-independent audio compatibility.

---

## 📦 Project File Structure

```
databanana_submission/
├── exports/
│   ├── best_datatrash_model.keras    <- Trained Keras CNN model
│   └── class_names.json              <- ['overripe', 'ripe', 'rotten', 'unripe']
├── arduino/
│   ├── banana_sorter_serial/
│   │   └── banana_sorter_serial.ino  <- Direct Serial firmware
│   └── banana_sorter_firebase/
│       └── banana_sorter_firebase.ino <- Firebase WiFi firmware
├── aiot_controller.py                 <- Main Python script (Flask + Inference + Bridge)
├── generate_diagram.py                <- Python script to render wiring schematic
├── diagram_skematik.png               <- Generated hardware schematic image
└── README.md                          <- This document
```

---

## 🏁 Step-by-Step Run Guide

### Step 1: Install Python Dependencies
Install the required packages in your local Python environment:
```bash
pip install flask opencv-python numpy pyserial firebase-admin pillow
```

### Step 2: Generate the Wiring Schematic
Run the program to generate the `diagram_skematik.png` file for submission:
```bash
python generate_diagram.py
```

### Step 3: Flash the NodeMCU
Open the Arduino IDE and select your board (ESP8266 or ESP32).

#### Option A: Direct Serial Control (Recommended for initial tests)
1. Open [arduino/banana_sorter_serial/banana_sorter_serial.ino](file:///c:/Users/ASUS/Downloads/databanana_submission/arduino/banana_sorter_serial/banana_sorter_serial.ino).
2. Upload the code to your NodeMCU via USB.
3. Open the Serial Monitor at `115200` baud. Type `1`, `2`, `3`, `4`, or `0` to test the relay switching.

#### Option B: Firebase Cloud Control
1. In the Arduino IDE, go to **Sketch -> Include Library -> Manage Libraries** and search/install **Firebase ESP Client** by Mobizt.
2. Open [arduino/banana_sorter_firebase/banana_sorter_firebase.ino](file:///c:/Users/ASUS/Downloads/databanana_submission/arduino/banana_sorter_firebase/banana_sorter_firebase.ino).
3. Edit the following constants with your parameters:
   ```cpp
   #define WIFI_SSID "YOUR_WIFI_SSID"
   #define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
   #define DATABASE_URL "YOUR_FIREBASE_DATABASE_URL"
   #define DATABASE_SECRET "YOUR_FIREBASE_DATABASE_SECRET"
   ```
4. Upload the code to your NodeMCU.

### Step 4: Run the Python Controller
Run the main controller:
```bash
python aiot_controller.py
```
Open a browser and navigate to **`http://localhost:5000`**.

1. Choose your **System Protocol** in the top right (Simulation, Serial, or Firebase).
2. Connect your COM port or Firebase database if utilizing hardware mode.
3. Place a banana in front of the camera and watch the hardware actuate!
