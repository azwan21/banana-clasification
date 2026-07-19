#!/usr/bin/env python3
"""
AIoT CHALLENGE 2026 - Smart Banana Ripeness Sorting System
Main Controller: AI Inference Engine, Web Dashboard, and Hardware Bridge.
"""

import os
import sys
import time
import json
import threading
from datetime import datetime

# Web and API dependencies 
from flask import Flask, Response, jsonify, request

# AI and OpenCV dependencies
import cv2
import numpy as np

# Try importing TensorFlow/Keras
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("Warning: TensorFlow not installed. Running in Simulation/TFLite-only mode.")

# Try importing PySerial
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not installed. Serial communication will be disabled.")

# Try importing Firebase
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Warning: firebase-admin not installed. Firebase cloud communication will be disabled.")

# ==========================================
# SYSTEM CONFIGURATION & INITIALIZATION
# ==========================================

class AIoTSystemState:
    def __init__(self):
        # Hardware Connection States
        self.com_port = "COM3"
        self.baud_rate = 115200
        self.serial_conn = None
        self.serial_status = "Disconnected"
        
        # Firebase Credentials & State
        self.firebase_initialized = False
        self.firebase_db_url = ""
        self.firebase_status = "Not Configured"
        
        # AI Config
        self.model_path = os.path.join("exports", "best_datatrash_model.h5")
        self.class_names = ["overripe", "ripe", "rotten", "unripe"]
        self.confidence_threshold = 0.60
        self.debounce_frames = 5
        
        # Inference & Camera States
        self.camera_source = 0
        self.is_camera_running = False
        self.cap = None
        self.current_frame = None
        self.fps = 0.0
        self.processing_time_ms = 0.0
        
        # Debounce/Filter Logic
        self.frame_history = []
        self.last_sent_class = "idle"
        self.stable_class = "idle"
        self.current_prediction = "idle"
        self.current_confidence = 0.0
        
        # Actuator State
        # Relays: 0 = OFF, 1 = ON
        self.relays = {
            "relay_1": 0,  # Unripe -> D5
            "relay_2": 0,  # Ripe -> D6
            "relay_3": 0,  # Overripe -> D7
            "relay_4": 0   # Rotten -> D8
        }
        self.manual_mode = False
        
        # Detection History (Limit to 50 entries)
        self.detection_history = []
        
        # Active Mode: "serial", "firebase", "simulation"
        self.active_mode = "simulation"
        
        # Telegram Bot Config
        self.telegram_enabled = False
        self.telegram_token = ""
        self.telegram_chat_id = ""
        
        # SSE Event Queue for frontend real-time updates
        self.listeners = []
        
        # Lock for thread safety
        self.lock = threading.Lock()

state = AIoTSystemState()
app = Flask(__name__, static_folder=None) # We will serve pages dynamically

# Render HTML dashboard directly to keep it single-file and simple
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍌 AIoT Banana Ripeness Sorting System</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            font-family: 'Outfit', sans-serif;
            background-color: #080c14;
            color: #f3f4f6;
        }
        .glass-card {
            background: rgba(17, 24, 39, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }
        .glow-unripe { box-shadow: 0 0 20px rgba(234, 179, 8, 0.3); border-color: rgba(234, 179, 8, 0.5); }
        .glow-ripe { box-shadow: 0 0 20px rgba(34, 197, 94, 0.3); border-color: rgba(34, 197, 94, 0.5); }
        .glow-overripe { box-shadow: 0 0 20px rgba(249, 115, 22, 0.3); border-color: rgba(249, 115, 22, 0.5); }
        .glow-rotten { box-shadow: 0 0 20px rgba(239, 68, 68, 0.3); border-color: rgba(239, 68, 68, 0.5); }
        .glow-idle { box-shadow: 0 0 20px rgba(59, 130, 246, 0.2); border-color: rgba(59, 130, 246, 0.4); }
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        
        <!-- Header -->
        <header class="flex justify-between items-center p-6 glass-card rounded-2xl glow-idle" id="main-header">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-yellow-400 via-green-400 to-red-500 bg-clip-text text-transparent">
                    🍌 BANANA RIPENESS SORTING SYSTEM
                </h1>
                <p class="text-gray-400 text-sm mt-1">AIoT Challenge 2026 - From Digital Screen to Physical Actuation</p>
            </div>
            <div class="flex items-center space-x-4">
                <div class="flex flex-col items-end">
                    <span class="text-xs text-gray-500 font-semibold uppercase">System Protocol</span>
                    <select id="protocol-select" class="bg-gray-800 border border-gray-700 text-yellow-400 rounded-lg px-3 py-1.5 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-yellow-400" onchange="changeProtocol()">
                        <option value="simulation">Simulation Mode</option>
                        <option value="serial">USB Serial Mode</option>
                        <option value="firebase">Firebase Cloud Mode</option>
                    </select>
                </div>
                <div class="flex items-center space-x-2 bg-gray-900/80 px-4 py-2 rounded-xl border border-gray-800">
                    <span class="w-3 h-3 rounded-full bg-green-500 animate-pulse" id="cam-indicator"></span>
                    <span class="text-xs font-bold text-gray-300" id="cam-status">Webcam Running</span>
                </div>
            </div>
        </header>

        <!-- Main Content Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            <!-- Column 1: Video Live Stream -->
            <div class="lg:col-span-2 space-y-6">
                <div class="glass-card rounded-2xl overflow-hidden relative">
                    <div class="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-mono border border-white/10 flex items-center space-x-2">
                        <span class="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping"></span>
                        <span class="text-white font-bold">LIVE INFERENCE FEED</span>
                    </div>
                    <div class="absolute top-4 right-4 z-10 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-mono border border-white/10 text-emerald-400 font-bold" id="inference-fps">
                        FPS: -- | -- ms
                    </div>
                    <img src="/video_feed" class="w-full aspect-video object-cover bg-gray-950" alt="Video Stream">
                </div>

                <!-- Detection Alert Panel -->
                <div class="p-6 glass-card rounded-2xl flex items-center justify-between transition-all duration-300" id="detection-status-card">
                    <div class="flex items-center space-x-5">
                        <div class="w-16 h-16 rounded-2xl flex items-center justify-center text-4xl shadow-lg border border-white/10 bg-gray-800/80" id="detection-emoji">
                            🍌
                        </div>
                        <div>
                            <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">Detected State</span>
                            <h2 class="text-3xl font-extrabold text-blue-400" id="detected-class-label">SYSTEM IDLE</h2>
                        </div>
                    </div>
                    <div class="text-right">
                        <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">Confidence Level</span>
                        <div class="text-3xl font-extrabold text-white mt-1" id="detected-confidence">0.0%</div>
                    </div>
                </div>
            </div>

            <!-- Column 2: Controller & Diagnostic Settings -->
            <div class="space-y-6">
                
                <!-- Physical Actuator Panel -->
                <div class="p-6 glass-card rounded-2xl">
                    <div class="flex justify-between items-center mb-6">
                        <h3 class="text-lg font-extrabold tracking-wide uppercase text-gray-300">⚙️ Relay Actuators (4-Ch)</h3>
                        <label class="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" id="manual-override-switch" class="sr-only peer" onchange="toggleManualOverride()">
                            <div class="w-11 h-6 bg-gray-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-yellow-500 peer-checked:after:bg-black"></div>
                            <span class="ml-2.5 text-xs font-bold text-gray-400 uppercase tracking-wider">Override</span>
                        </label>
                    </div>

                    <div class="space-y-4">
                        <!-- Relay 1 -->
                        <div class="flex justify-between items-center p-3 rounded-xl bg-gray-900/60 border border-gray-800/80" id="card-relay-1">
                            <div>
                                <h4 class="font-bold text-gray-300">Relay 1 (D5) - Unripe</h4>
                                <p class="text-xs text-gray-500">Green Banana Sorting Gate</p>
                            </div>
                            <button id="btn-relay-1" disabled onclick="toggleRelay(1)" class="px-4 py-2 rounded-lg text-xs font-bold bg-gray-800 text-gray-500 cursor-not-allowed uppercase border border-gray-700/50">OFF</button>
                        </div>

                        <!-- Relay 2 -->
                        <div class="flex justify-between items-center p-3 rounded-xl bg-gray-900/60 border border-gray-800/80" id="card-relay-2">
                            <div>
                                <h4 class="font-bold text-gray-300">Relay 2 (D6) - Ripe</h4>
                                <p class="text-xs text-gray-500">Ripe Banana Packaging Conveyor</p>
                            </div>
                            <button id="btn-relay-2" disabled onclick="toggleRelay(2)" class="px-4 py-2 rounded-lg text-xs font-bold bg-gray-800 text-gray-500 cursor-not-allowed uppercase border border-gray-700/50">OFF</button>
                        </div>

                        <!-- Relay 3 -->
                        <div class="flex justify-between items-center p-3 rounded-xl bg-gray-900/60 border border-gray-800/80" id="card-relay-3">
                            <div>
                                <h4 class="font-bold text-gray-300">Relay 3 (D7) - Overripe</h4>
                                <p class="text-xs text-gray-500">Overripe Processing Line</p>
                            </div>
                            <button id="btn-relay-3" disabled onclick="toggleRelay(3)" class="px-4 py-2 rounded-lg text-xs font-bold bg-gray-800 text-gray-500 cursor-not-allowed uppercase border border-gray-700/50">OFF</button>
                        </div>

                        <!-- Relay 4 -->
                        <div class="flex justify-between items-center p-3 rounded-xl bg-gray-900/60 border border-gray-800/80" id="card-relay-4">
                            <div>
                                <h4 class="font-bold text-gray-300">Relay 4 (D8) - Rotten</h4>
                                <p class="text-xs text-gray-500">Rotten Rejection Bin / Alarm</p>
                            </div>
                            <button id="btn-relay-4" disabled onclick="toggleRelay(4)" class="px-4 py-2 rounded-lg text-xs font-bold bg-gray-800 text-gray-500 cursor-not-allowed uppercase border border-gray-700/50">OFF</button>
                        </div>
                    </div>
                </div>

                <!-- Hardware Connection Settings -->
                <div class="p-6 glass-card rounded-2xl">
                    <h3 class="text-lg font-extrabold tracking-wide uppercase text-gray-300 mb-4">🔌 Physical Bridge</h3>
                    
                    <!-- Serial Settings -->
                    <div id="serial-settings-panel" class="space-y-4 hidden">
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-xs text-gray-400 font-bold uppercase tracking-wider block mb-1">COM Port</label>
                                <select id="serial-port" class="bg-gray-800 border border-gray-700 text-white rounded-lg w-full px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400">
                                    <!-- Populated dynamically -->
                                </select>
                            </div>
                            <div>
                                <label class="text-xs text-gray-400 font-bold uppercase tracking-wider block mb-1">Baud Rate</label>
                                <select id="serial-baud" class="bg-gray-800 border border-gray-700 text-white rounded-lg w-full px-2 py-1.5 text-sm focus:outline-none">
                                    <option value="115200">115200</option>
                                    <option value="9600">9600</option>
                                </select>
                            </div>
                        </div>
                        <button onclick="connectSerial()" id="btn-serial-connect" class="w-full bg-blue-600 hover:bg-blue-500 font-bold py-2 rounded-xl text-sm transition-all duration-300">Connect Serial</button>
                        <p class="text-xs text-gray-400 text-center" id="serial-connection-status">Status: Disconnected</p>
                    </div>

                    <!-- Firebase Settings -->
                    <div id="firebase-settings-panel" class="space-y-4 hidden">
                        <div>
                            <label class="text-xs text-gray-400 font-bold uppercase tracking-wider block mb-1">Firebase RTDB URL</label>
                            <input type="text" id="firebase-url" placeholder="https://your-rtdb.firebaseio.com" class="bg-gray-800 border border-gray-700 text-white rounded-lg w-full px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400">
                        </div>
                        <button onclick="connectFirebase()" id="btn-firebase-connect" class="w-full bg-orange-600 hover:bg-orange-500 font-bold py-2 rounded-xl text-sm transition-all duration-300">Initialize Firebase</button>
                        <p class="text-xs text-gray-400 text-center" id="firebase-connection-status">Status: Not Configured</p>
                    </div>

                    <!-- Simulation Info -->
                    <div id="simulation-panel" class="p-4 bg-blue-950/40 border border-blue-900/60 rounded-xl">
                        <p class="text-xs text-blue-300 leading-relaxed">
                            💡 <strong>Simulation Mode Active:</strong> Relays are toggled virtually in the dashboard. No hardware connections are required. Toggle "Override" above to manually test sorting.
                        </p>
                    </div>
                </div>

                <!-- Debounce and Filter Controls -->
                <div class="p-6 glass-card rounded-2xl">
                    <h3 class="text-lg font-extrabold tracking-wide uppercase text-gray-300 mb-4">🧠 Debounce & Stability</h3>
                    <div class="space-y-5">
                        <div>
                            <div class="flex justify-between text-xs text-gray-400 font-bold uppercase tracking-wider mb-2">
                                <span>Confidence Threshold</span>
                                <span id="threshold-val">60%</span>
                            </div>
                            <input type="range" id="threshold-slider" min="50" max="95" value="60" oninput="updateSettings()" class="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-yellow-400">
                        </div>
                        <div>
                            <div class="flex justify-between text-xs text-gray-400 font-bold uppercase tracking-wider mb-2">
                                <span>Stability Filter (Frames)</span>
                                <span id="debounce-val">5 Frames</span>
                            </div>
                            <input type="range" id="debounce-slider" min="2" max="15" value="5" oninput="updateSettings()" class="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-yellow-400">
                        </div>
                        <div class="flex justify-between items-center pt-2">
                            <label class="text-xs text-gray-400 font-bold uppercase tracking-wider">Voice Alerts (TTS)</label>
                            <input type="checkbox" id="tts-switch" checked class="w-4 h-4 text-yellow-400 bg-gray-800 rounded border-gray-700 focus:ring-yellow-400 focus:ring-2">
                        </div>
                    </div>
                </div>

                <!-- Telegram Notifications Card -->
                <div class="p-6 glass-card rounded-2xl">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-extrabold tracking-wide uppercase text-gray-300">📢 Telegram Bot</h3>
                        <label class="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" id="telegram-switch" class="sr-only peer" onchange="updateTelegramSettings()">
                            <div class="w-11 h-6 bg-gray-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-yellow-500 peer-checked:after:bg-black"></div>
                        </label>
                    </div>
                    <div class="space-y-3" id="telegram-inputs">
                        <div>
                            <label class="text-xs text-gray-400 font-bold uppercase tracking-wider block mb-1">Bot Token</label>
                            <input type="text" id="telegram-token" placeholder="123456789:ABCdefGhI..." onchange="updateTelegramSettings()" class="bg-gray-800 border border-gray-700 text-white rounded-lg w-full px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-yellow-400">
                        </div>
                        <div>
                            <label class="text-xs text-gray-400 font-bold uppercase tracking-wider block mb-1">Chat ID</label>
                            <input type="text" id="telegram-chat-id" placeholder="-100123456789" onchange="updateTelegramSettings()" class="bg-gray-800 border border-gray-700 text-white rounded-lg w-full px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-yellow-400">
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Section 3: Detection Timeline log -->
        <div class="p-6 glass-card rounded-2xl">
            <h3 class="text-lg font-extrabold tracking-wide uppercase text-gray-300 mb-4">📜 Sorting History Log</h3>
            <div class="overflow-x-auto max-h-60 overflow-y-auto">
                <table class="min-w-full text-sm text-left">
                    <thead class="bg-gray-900 text-gray-400 uppercase text-xs font-bold border-b border-gray-800">
                        <tr>
                            <th class="py-3 px-4">Timestamp</th>
                            <th class="py-3 px-4">Banana Status</th>
                            <th class="py-3 px-4">Confidence</th>
                            <th class="py-3 px-4">Actuation Command</th>
                            <th class="py-3 px-4">System State</th>
                        </tr>
                    </thead>
                    <tbody id="log-table-body" class="divide-y divide-gray-800 text-gray-300">
                        <!-- Populated dynamically -->
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- Frontend Script -->
    <script>
        // Web Speech API Voice synthesis setup
        const ttsEnabled = () => document.getElementById('tts-switch').checked;
        function speak(text) {
            if (!ttsEnabled()) return;
            window.speechSynthesis.cancel(); // Cancel current audio queue
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'en-US';
            utterance.rate = 1.0;
            window.speechSynthesis.speak(utterance);
        }

        // Handle Protocol configuration UI
        function changeProtocol() {
            const proto = document.getElementById('protocol-select').value;
            fetch('/api/set_protocol', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ protocol: proto })
            });
        }

        // Toggle Manual Override
        function toggleManualOverride() {
            const override = document.getElementById('manual-override-switch').checked;
            fetch('/api/set_override', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ override: override })
            });
        }

        // Toggle Single Relay manually
        function toggleRelay(index) {
            fetch(`/api/toggle_relay/${index}`, {method: 'POST'});
        }

        // Connect Serial
        function connectSerial() {
            const port = document.getElementById('serial-port').value;
            const baud = document.getElementById('serial-baud').value;
            document.getElementById('btn-serial-connect').innerText = "Connecting...";
            fetch('/api/connect_serial', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ port: port, baud: parseInt(baud) })
            });
        }

        // Connect Firebase
        function connectFirebase() {
            const url = document.getElementById('firebase-url').value;
            document.getElementById('btn-firebase-connect').innerText = "Initializing...";
            fetch('/api/connect_firebase', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: url })
            });
        }

        // Push settings updates
        function updateSettings() {
            const threshold = document.getElementById('threshold-slider').value;
            const debounce = document.getElementById('debounce-slider').value;
            document.getElementById('threshold-val').innerText = threshold + "%";
            document.getElementById('debounce-val').innerText = debounce + " Frames";
            
            fetch('/api/update_settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    threshold: parseFloat(threshold) / 100.0,
                    debounce: parseInt(debounce)
                })
            });
        }

        // Push Telegram updates
        function updateTelegramSettings() {
            const enabled = document.getElementById('telegram-switch').checked;
            const token = document.getElementById('telegram-token').value;
            const chatId = document.getElementById('telegram-chat-id').value;
            
            fetch('/api/update_telegram', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    enabled: enabled,
                    token: token,
                    chat_id: chatId
                })
            });
        }

        // Fetch serial ports list
        function refreshPorts() {
            fetch('/api/ports')
                .then(r => r.json())
                .then(ports => {
                    const select = document.getElementById('serial-port');
                    select.innerHTML = '';
                    if (ports.length === 0) {
                        select.innerHTML = '<option value="">No COM Ports Found</option>';
                    } else {
                        ports.forEach(p => {
                            select.innerHTML += `<option value="${p}">${p}</option>`;
                        });
                    }
                });
        }

        // State Styling Maps
        const CLASS_META = {
            'idle': { emoji: '💤', name: 'SYSTEM READY', card: 'glow-idle', text: 'text-blue-400' },
            'unripe': { emoji: '🥬', name: 'UNRIPE BANANA', card: 'glow-unripe', text: 'text-yellow-400' },
            'ripe': { emoji: '🍌', name: 'RIPE BANANA', card: 'glow-ripe', text: 'text-green-500' },
            'overripe': { emoji: '🥞', name: 'OVERRIPE BANANA', card: 'glow-overripe', text: 'text-orange-400' },
            'rotten': { emoji: '🥀', name: 'ROTTEN BANANA', card: 'glow-rotten', text: 'text-red-500' }
        };

        // Subscribe to Server-Sent Events for live dashboard streaming
        const source = new EventSource('/events');
        source.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            // 1. Update Inferences details
            document.getElementById('inference-fps').innerText = `FPS: ${data.fps} | ${data.processing_time}ms`;
            
            const meta = CLASS_META[data.stable_class] || CLASS_META['idle'];
            document.getElementById('detection-emoji').innerText = meta.emoji;
            document.getElementById('detected-class-label').innerText = meta.name;
            document.getElementById('detected-class-label').className = "text-3xl font-extrabold " + meta.text;
            
            // Styling core card border based on class
            const card = document.getElementById('detection-status-card');
            card.className = "p-6 glass-card rounded-2xl flex items-center justify-between transition-all duration-300 " + meta.card;
            document.getElementById('main-header').className = "flex justify-between items-center p-6 glass-card rounded-2xl " + meta.card;
            
            document.getElementById('detected-confidence').innerText = (data.current_confidence * 100).toFixed(1) + "%";

            // 2. Update protocol selectors if updated on server
            document.getElementById('protocol-select').value = data.active_mode;
            
            // Show/Hide Panels based on current protocol
            document.getElementById('serial-settings-panel').style.display = data.active_mode === 'serial' ? 'block' : 'none';
            document.getElementById('firebase-settings-panel').style.display = data.active_mode === 'firebase' ? 'block' : 'none';
            document.getElementById('simulation-panel').style.display = data.active_mode === 'simulation' ? 'block' : 'none';
            
            // Connection diagnostics text
            document.getElementById('serial-connection-status').innerText = "Status: " + data.serial_status;
            document.getElementById('firebase-connection-status').innerText = "Status: " + data.firebase_status;

            // Sync Telegram inputs from state
            document.getElementById('telegram-switch').checked = data.telegram_enabled;
            if (document.activeElement !== document.getElementById('telegram-token')) {
                document.getElementById('telegram-token').value = data.telegram_token;
            }
            if (document.activeElement !== document.getElementById('telegram-chat-id')) {
                document.getElementById('telegram-chat-id').value = data.telegram_chat_id;
            }

            // Connect button styles
            const serialBtn = document.getElementById('btn-serial-connect');
            if (data.serial_status === 'Connected') {
                serialBtn.className = "w-full bg-red-600 hover:bg-red-500 font-bold py-2 rounded-xl text-sm transition-all duration-300";
                serialBtn.innerText = "Disconnect Serial";
            } else {
                serialBtn.className = "w-full bg-blue-600 hover:bg-blue-500 font-bold py-2 rounded-xl text-sm transition-all duration-300";
                serialBtn.innerText = "Connect Serial";
            }

            // 3. Update Relay buttons states
            document.getElementById('manual-override-switch').checked = data.manual_mode;
            const buttonsDisabled = !data.manual_mode;

            for (let i = 1; i <= 4; i++) {
                const btn = document.getElementById(`btn-relay-${i}`);
                const stateVal = data.relays[`relay_${i}`];
                btn.disabled = buttonsDisabled;
                
                if (stateVal === 1) {
                    btn.innerText = "ON";
                    btn.className = `px-4 py-2 rounded-lg text-xs font-bold bg-green-600 hover:bg-green-500 text-white cursor-pointer uppercase border border-green-500`;
                } else {
                    btn.innerText = "OFF";
                    btn.className = buttonsDisabled 
                        ? "px-4 py-2 rounded-lg text-xs font-bold bg-gray-800 text-gray-500 cursor-not-allowed uppercase border border-gray-700/50"
                        : "px-4 py-2 rounded-lg text-xs font-bold bg-gray-700 hover:bg-gray-600 text-white cursor-pointer uppercase border border-gray-600";
                }
            }

            // 4. Update timeline log
            const logBody = document.getElementById('log-table-body');
            logBody.innerHTML = '';
            data.detection_history.forEach(log => {
                const stateMeta = CLASS_META[log.class] || CLASS_META['idle'];
                logBody.innerHTML += `
                    <tr class="hover:bg-gray-900/40 transition-colors">
                        <td class="py-3.5 px-4 font-mono text-gray-400 text-xs">${log.timestamp}</td>
                        <td class="py-3.5 px-4 font-bold ${stateMeta.text}">${stateMeta.emoji} ${log.class.toUpperCase()}</td>
                        <td class="py-3.5 px-4 font-mono font-bold">${(log.confidence * 100).toFixed(1)}%</td>
                        <td class="py-3.5 px-4"><span class="bg-gray-800 text-yellow-400 border border-gray-700/50 px-2 py-0.5 rounded font-mono font-bold text-xs">${log.action}</span></td>
                        <td class="py-3.5 px-4 text-xs font-semibold text-gray-500">${log.details}</td>
                    </tr>
                `;
            });

            // 5. Text-to-Speech voice alert triggering
            if (data.tts_text) {
                speak(data.tts_text);
            }
        };

        // Initialize ports and trigger once on startup
        refreshPorts();
        setInterval(refreshPorts, 10000);
    </script>
</body>
</html>
"""

# ==========================================
# HARDWARE BRIDGING & DATA TRANSMISSION
# ==========================================

def update_relays_by_class(class_name):
    """
    Sets physical or simulation relay flags based on stable detection class
    """
    with state.lock:
        if state.manual_mode:
            return  # Ignore AI controls when manual override is ON

        # Reset all relays first
        for r in state.relays:
            state.relays[r] = 0

        # Map to specific relay
        command = '0'
        if class_name == 'unripe':
            state.relays['relay_1'] = 1
            command = '1'
        elif class_name == 'ripe':
            state.relays['relay_2'] = 1
            command = '2'
        elif class_name == 'overripe':
            state.relays['relay_3'] = 1
            command = '3'
        elif class_name == 'rotten':
            state.relays['relay_4'] = 1
            command = '4'

    # Transmit physical commands based on mode
    if state.active_mode == 'serial':
        send_serial_command(command)
    elif state.active_mode == 'firebase':
        send_firebase_status(class_name)

def send_serial_command(command_char):
    """
    Writes a byte code command to USB Serial
    """
    if not SERIAL_AVAILABLE or not state.serial_conn:
        return
    try:
        state.serial_conn.write(command_char.encode())
        print(f"[Serial TX] Sent command: '{command_char}'")
    except Exception as e:
        print(f"[Serial TX Error] Failed to write serial: {e}")
        state.serial_status = "Error/Disconnected"
        if state.serial_conn:
            try: state.serial_conn.close()
            except: pass
            state.serial_conn = None

def send_firebase_status(class_name):
    """
    Pushes status updates to Firebase Realtime Database
    """
    if not FIREBASE_AVAILABLE or not state.firebase_initialized:
        return
    try:
        ref = db.reference('/deteksi')
        ref.update({
            'status': class_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        print(f"[Firebase TX] Updated status to: '{class_name}'")
    except Exception as e:
        print(f"[Firebase TX Error] Failed to push to DB: {e}")
        state.firebase_status = "Write Error"

def send_telegram_alert(class_name, confidence):
    """
    Sends notification to Telegram Bot if enabled
    """
    if not state.telegram_enabled or not state.telegram_token or not state.telegram_chat_id:
        return
        
    import urllib.request
    import urllib.parse
    
    emoji = "💤"
    action = "System Standby"
    if class_name == 'unripe':
        emoji = "🥬"
        action = "Relay 1 ON [Ripening Line Activated]"
    elif class_name == 'ripe':
        emoji = "🍌"
        action = "Relay 2 ON [Packaging Line Activated]"
    elif class_name == 'overripe':
        emoji = "🥞"
        action = "Relay 3 ON [Processing Line Activated]"
    elif class_name == 'rotten':
        emoji = "🥀"
        action = "Relay 4 ON [Rotten Rejection Bin / Alarm Activated]"
        
    text = (
        f"🍌 *AIoT Banana Sorter Alert*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *State change detected!*\n"
        f"🏷️ *Ripeness Status:* {class_name.upper()} {emoji}\n"
        f"🎯 *Confidence:* {confidence * 100:.1f}%\n"
        f"⚙️ *Action taken:* {action}\n"
        f"⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    url = f"https://api.telegram.org/bot{state.telegram_token}/sendMessage"
    payload = {
        "chat_id": state.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    def worker():
        try:
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data)
            urllib.request.urlopen(req, timeout=5)
            print(f"[Telegram Alert] Sent notification for state: '{class_name}'")
        except Exception as e:
            print(f"[Telegram Alert Error] Failed to send message: {e}")
            
    # Send in a separate thread to prevent blocking the main inference loop
    threading.Thread(target=worker, daemon=True).start()

# ==========================================
# DIGITAL BRAIN - INFERENCE PIPELINE
# ==========================================

def run_ai_inference():
    """
    Background worker that runs camera frame polling and CNN inference
    """
    # 1. Load Deep Learning model
    model = None
    tflite_mode = False
    
    # Try loading Keras model
    if TF_AVAILABLE and os.path.exists(state.model_path):
        try:
            print(f"Loading Keras Model: {state.model_path}")
            model = load_model(state.model_path)
            print("Keras Model loaded successfully.")
        except Exception as e:
            print(f"Error loading Keras model: {e}")
            model = None

    # Fallback to TFLite if available in exports/
    tflite_path = os.path.join("exports", "best_datatrash_model.tflite")
    if not model and os.path.exists(tflite_path):
        try:
            print(f"Loading TF-Lite Model: {tflite_path}")
            try:
                import tflite_runtime.interpreter as tflite
                InterpreterClass = tflite.Interpreter
            except ImportError:
                if TF_AVAILABLE:
                    from tensorflow.lite.python.interpreter import Interpreter as InterpreterClass
                else:
                    raise ImportError("Neither tflite_runtime nor tensorflow is installed.")
                    
            model = InterpreterClass(model_path=tflite_path)
            model.allocate_tensors()
            tflite_mode = True
            print("TF-Lite Model loaded successfully.")
        except Exception as e:
            print(f"Error loading TF-Lite model: {e}")
            model = None

    if not model:
        print("CRITICAL: No trained CNN model could be loaded. System running in DEMO Simulation mode.")

    # 2. Open camera capture
    state.cap = cv2.VideoCapture(state.camera_source)
    if not state.cap.isOpened():
        print(f"Error: Camera source {state.camera_source} could not be opened.")
        state.is_camera_running = False
        return
    
    state.is_camera_running = True
    last_frame_time = time.time()
    
    # Track debounce logic timing
    consecutive_low_confidence_frames = 0

    while state.is_camera_running:
        ret, frame = state.cap.read()
        if not ret:
            time.sleep(0.01)
            continue
            
        start_time = time.time()
        
        # Keep copy of raw frame for web client view
        h, w, _ = frame.shape
        
        # Normalization parameters (MobileNetV2 inputs expect [224, 224, 3])
        target_size = (224, 224)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized_img = cv2.resize(rgb_frame, target_size)
        
        # Initialize default predictions
        pred_class = "idle"
        pred_conf = 0.0
        
        # 3. Model Inference Execution
        if model:
            try:
                # Model already has a Rescaling layer (1/127.5 - 1), so we feed raw [0, 255] pixels
                input_data = np.expand_dims(resized_img.astype(np.float32), axis=0)
                
                if tflite_mode:
                    # Run TF-Lite interpreter
                    input_details = model.get_input_details()
                    output_details = model.get_output_details()
                    model.set_tensor(input_details[0]['index'], input_data)
                    model.invoke()
                    preds = model.get_tensor(output_details[0]['index'])[0]
                else:
                    # Run Keras prediction
                    preds = model.predict(input_data, verbose=0)[0]
                    
                class_idx = np.argmax(preds)
                pred_conf = float(preds[class_idx])
                
                # Check confidence threshold (0.60 as specified)
                if pred_conf >= state.confidence_threshold:
                    pred_class = state.class_names[class_idx]
                else:
                    pred_class = "idle"
            except Exception as e:
                print(f"Inference error: {e}")
                pred_class = "idle"
                pred_conf = 0.0
        else:
            # Simulation/Demo mode (if no model file exists, mock a slow ripeness rotation)
            # Cycle through classes based on seconds
            sec = int(time.time()) % 20
            if sec < 4:
                pred_class = "ripe"
                pred_conf = 0.94
            elif sec < 8:
                pred_class = "unripe"
                pred_conf = 0.88
            elif sec < 12:
                pred_class = "overripe"
                pred_conf = 0.76
            elif sec < 16:
                pred_class = "rotten"
                pred_conf = 0.91
            else:
                pred_class = "idle"
                pred_conf = 0.0

        # Calculate inference speeds
        end_time = time.time()
        state.processing_time_ms = round((end_time - start_time) * 1000, 1)
        state.fps = round(1.0 / (start_time - last_frame_time + 0.0001), 1)
        last_frame_time = start_time

        # 4. Debounce and Filtering Logic
        # Keep track of recent N frames to prevent serial jitter
        state.frame_history.append(pred_class)
        if len(state.frame_history) > state.debounce_frames:
            state.frame_history.pop(0)
            
        # Check consensus in stability window
        # Ensure that the majority (e.g. >70% of frames) in the buffer match
        most_common_class = max(set(state.frame_history), key=state.frame_history.count)
        common_count = state.frame_history.count(most_common_class)
        
        stable_pred = "idle"
        # If class is stable and meets consensus requirement, promote to stable
        if common_count >= (state.debounce_frames * 0.6) and most_common_class != "idle":
            stable_pred = most_common_class
            consecutive_low_confidence_frames = 0
        else:
            # If low confidence or idle for a timeout, set system to idle
            consecutive_low_confidence_frames += 1
            if consecutive_low_confidence_frames > (state.debounce_frames * 2):
                stable_pred = "idle"
            else:
                stable_pred = state.stable_class # Maintain previous stable state briefly

        # Update global state values
        state.current_prediction = pred_class
        state.current_confidence = pred_conf
        
        # Trigger sorting hardware on state change!
        tts_text_to_dispatch = None
        if stable_pred != state.stable_class:
            state.stable_class = stable_pred
            
            # Format display strings & actions
            actions = {
                "idle": "All Relays OFF [Idle]",
                "unripe": "Relay 1 ON [Ripening Line]",
                "ripe": "Relay 2 ON [Packaging Line]",
                "overripe": "Relay 3 ON [Processing Line]",
                "rotten": "Relay 4 ON [Waste / Rejection]"
            }
            
            action_str = actions.get(stable_pred, "Idle")
            
            # Record historical log
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "class": stable_pred,
                "confidence": pred_conf if stable_pred != "idle" else 0.0,
                "action": action_str,
                "details": f"Debounced over {state.debounce_frames} frames (Inference: {state.processing_time_ms}ms)"
            }
            
            with state.lock:
                state.detection_history.insert(0, log_entry)
                if len(state.detection_history) > 50:
                    state.detection_history.pop()
                    
            # Set up voice synthesis prompt text for dashboard speaker
            if stable_pred == "idle":
                tts_text_to_dispatch = "Banana removed. System standby."
            else:
                tts_text_to_dispatch = f"{stable_pred.capitalize()} banana detected. Activating {action_str.split('[')[1].replace(']', '')}."

            # Update the physical actuator state based on sorting class
            update_relays_by_class(stable_pred)

            # Send Telegram Bot Alert
            send_telegram_alert(stable_pred, pred_conf)

        # 5. Overlay Graphics HUD (Heads-Up Display) for output video stream
        hud_color = (255, 120, 0) # Default Blue/Cyan for idle
        if stable_pred == "unripe":
            hud_color = (0, 220, 255) # Yellow
        elif stable_pred == "ripe":
            hud_color = (0, 200, 0) # Green
        elif stable_pred == "overripe":
            hud_color = (0, 120, 255) # Orange
        elif stable_pred == "rotten":
            hud_color = (0, 0, 255) # Red

        # Render decorative border
        cv2.rectangle(frame, (10, 10), (w-10, h-10), hud_color, 2)
        
        # Bounding indicators on center of interest
        box_w, box_h = 240, 240
        cx, cy = w // 2, h // 2
        cv2.rectangle(frame, (cx - box_w//2, cy - box_h//2), (cx + box_w//2, cy + box_h//2), hud_color, 2, cv2.LINE_AA)
        
        # Add labels overlay
        overlay_text = f"STATE: {stable_pred.upper()}"
        if stable_pred != "idle":
            overlay_text += f" ({pred_conf*100:.1f}%)"
            
        # Draw transparent label box
        cv2.rectangle(frame, (cx - box_w//2, cy - box_h//2 - 35), (cx + box_w//2, cy - box_h//2), hud_color, -1)
        cv2.putText(frame, overlay_text, (cx - box_w//2 + 10, cy - box_h//2 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        # Draw details at the bottom of the frame
        info_overlay = f"FPS: {state.fps} | Infer: {state.processing_time_ms}ms | Bridge: {state.active_mode.upper()}"
        cv2.putText(frame, info_overlay, (20, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # Compress frame as JPEG for MJPEG stream
        ret, jpeg = cv2.imencode('.jpg', frame)
        if ret:
            with state.lock:
                state.current_frame = jpeg.tobytes()
                
        # Send SSE real-time state event to browser listeners
        if len(state.listeners) > 0:
            payload = {
                "fps": state.fps,
                "processing_time": state.processing_time_ms,
                "current_prediction": state.current_prediction,
                "current_confidence": state.current_confidence,
                "stable_class": state.stable_class,
                "relays": state.relays,
                "manual_mode": state.manual_mode,
                "active_mode": state.active_mode,
                "serial_status": state.serial_status,
                "firebase_status": state.firebase_status,
                "detection_history": state.detection_history,
                "tts_text": tts_text_to_dispatch, # Triggers speech synthesis in browser client
                "telegram_enabled": state.telegram_enabled,
                "telegram_token": state.telegram_token,
                "telegram_chat_id": state.telegram_chat_id
            }
            # Dispatch event to listener queues
            for listener in state.listeners:
                listener.put(json.dumps(payload))

        # Sleep to regulate camera frames polling
        time.sleep(0.03)

    if state.cap:
        state.cap.release()

# ==========================================
# FLASK WEB SERVER API ENDPOINTS
# ==========================================

@app.route('/')
def index():
    """Serves the main application dashboard"""
    return DASHBOARD_HTML

def gen_video():
    """MJPEG Frame Streaming Generator"""
    while True:
        with state.lock:
            frame_bytes = state.current_frame
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')
        time.sleep(0.04)

@app.route('/video_feed')
def video_feed():
    """Live Video feed route"""
    return Response(gen_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/events')
def sse_events():
    """
    Server-Sent Events endpoint to stream telemetry data to browser
    """
    import queue
    q = queue.Queue()
    state.listeners.append(q)
    
    def event_stream():
        try:
            # Send initial event immediately
            initial_payload = {
                "fps": state.fps,
                "processing_time": state.processing_time_ms,
                "current_prediction": state.current_prediction,
                "current_confidence": state.current_confidence,
                "stable_class": state.stable_class,
                "relays": state.relays,
                "manual_mode": state.manual_mode,
                "active_mode": state.active_mode,
                "serial_status": state.serial_status,
                "firebase_status": state.firebase_status,
                "detection_history": state.detection_history,
                "tts_text": "System Ready. Direct connection active.",
                "telegram_enabled": state.telegram_enabled,
                "telegram_token": state.telegram_token,
                "telegram_chat_id": state.telegram_chat_id
            }
            yield f"data: {json.dumps(initial_payload)}\n\n"
            
            while True:
                # Wait for next update from camera thread
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            pass
        finally:
            state.listeners.remove(q)
            
    return Response(event_stream(), mimetype="text/event-stream")

# --- API CONTROL ROUTES ---

@app.route('/api/ports', methods=['GET'])
def get_com_ports():
    """Lists all available USB COM ports on the local machine"""
    if SERIAL_AVAILABLE:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return jsonify(ports)
    return jsonify([])

@app.route('/api/set_protocol', methods=['POST'])
def set_protocol():
    """Switches communication protocol (Simulation, Serial, Firebase)"""
    data = request.json
    proto = data.get('protocol', 'simulation')
    
    if proto in ['simulation', 'serial', 'firebase']:
        # If changing from serial, disconnect it
        if state.active_mode == 'serial' and proto != 'serial':
            if state.serial_conn:
                try: state.serial_conn.close()
                except: pass
                state.serial_conn = None
                state.serial_status = "Disconnected"
                
        state.active_mode = proto
        print(f"Protocol changed to: {proto.upper()}")
        return jsonify({"status": "success", "protocol": proto})
    return jsonify({"status": "error", "message": "Invalid protocol"}), 400

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    """Updates confidence threshold and debounce frames dynamically"""
    data = request.json
    state.confidence_threshold = float(data.get('threshold', 0.60))
    state.debounce_frames = int(data.get('debounce', 5))
    print(f"Settings Updated: Threshold={state.confidence_threshold*100:.0f}%, Debounce={state.debounce_frames} frames")
    return jsonify({"status": "success"})

@app.route('/api/update_telegram', methods=['POST'])
def update_telegram():
    """Updates Telegram notification settings dynamically"""
    data = request.json
    state.telegram_enabled = bool(data.get('enabled', False))
    state.telegram_token = data.get('token', '').strip()
    state.telegram_chat_id = data.get('chat_id', '').strip()
    print(f"Telegram Settings Updated: Enabled={state.telegram_enabled}, ChatID={state.telegram_chat_id}")
    return jsonify({"status": "success"})

@app.route('/api/set_override', methods=['POST'])
def set_override():
    """Enables/Disables Manual override mode"""
    data = request.json
    state.manual_mode = bool(data.get('override', False))
    print(f"Manual Override Mode: {state.manual_mode}")
    
    # If disabling override, trigger AI update immediately
    if not state.manual_mode:
        update_relays_by_class(state.stable_class)
        
    return jsonify({"status": "success", "override": state.manual_mode})

@app.route('/api/toggle_relay/<int:relay_num>', methods=['POST'])
def toggle_relay(relay_num):
    """Manually toggles individual relays (only if override is enabled)"""
    if not state.manual_mode:
        return jsonify({"status": "error", "message": "Enable manual override first"}), 403
        
    key = f"relay_{relay_num}"
    if key in state.relays:
        with state.lock:
            # Toggle state
            state.relays[key] = 1 - state.relays[key]
            
        print(f"[Manual Control] Toggled {key} to {state.relays[key]}")
        
        # Dispatch command character representing manual relay state configuration
        # Write exact commands to Serial or Firebase
        if state.active_mode == 'serial':
            # For manual control, we can send a custom command or map the individual state.
            # Let's map active relays to their number, or '0' if all off.
            # In a simple serial setup, we can just send the command.
            if state.relays['relay_1']: send_serial_command('1')
            elif state.relays['relay_2']: send_serial_command('2')
            elif state.relays['relay_3']: send_serial_command('3')
            elif state.relays['relay_4']: send_serial_command('4')
            else: send_serial_command('0')
        elif state.active_mode == 'firebase':
            # Push full relay node for custom manual dashboard reading
            if FIREBASE_AVAILABLE and state.firebase_initialized:
                try:
                    ref = db.reference('/deteksi/manual_relays')
                    ref.update({key: state.relays[key]})
                except Exception as e:
                    print(f"Firebase manual write error: {e}")
                    
        return jsonify({"status": "success", "relays": state.relays})
    return jsonify({"status": "error", "message": "Invalid relay number"}), 400

@app.route('/api/connect_serial', methods=['POST'])
def connect_serial():
    """Initializes or terminates USB Serial connection"""
    if not SERIAL_AVAILABLE:
        return jsonify({"status": "error", "message": "pyserial library not available"}), 500
        
    data = request.json
    port = data.get('port', 'COM3')
    baud = int(data.get('baud', 115200))
    
    if state.serial_conn:
        # Disconnect
        try:
            state.serial_conn.close()
        except:
            pass
        state.serial_conn = None
        state.serial_status = "Disconnected"
        print("Disconnected Serial Port.")
        return jsonify({"status": "success", "serial_status": state.serial_status})
    else:
        # Connect
        try:
            print(f"Connecting to Serial Port: {port} at {baud} bps...")
            state.serial_conn = serial.Serial(port, baud, timeout=1)
            state.serial_status = "Connected"
            state.com_port = port
            state.baud_rate = baud
            print("Serial Port connected successfully.")
            return jsonify({"status": "success", "serial_status": state.serial_status})
        except Exception as e:
            state.serial_status = f"Connect Error"
            print(f"Serial connection error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/connect_firebase', methods=['POST'])
def connect_firebase():
    """Initializes Firebase Admin SDK connection"""
    if not FIREBASE_AVAILABLE:
        return jsonify({"status": "error", "message": "firebase-admin library not available"}), 500
        
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({"status": "error", "message": "Firebase database URL is required"}), 400
        
    try:
        # Check if already initialized, if so, delete the app to reinitialize
        try:
            firebase_admin.delete_app(firebase_admin.get_app())
        except ValueError:
            pass # App not initialized yet
            
        # For simplicity, we initialize using the default legacy credential config.
        # Ensure the user has firebase access credentials set up or uses a service account.
        # Note: If no service account JSON is supplied, we will initialize in databaseAuthVariableOverride mode 
        # using the databaseUrl directly (ideal for public test RTDB databases).
        print(f"Initializing Firebase with DB: {url}")
        
        # Check if local credentials file exists
        cred_path = "firebase_credentials.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {'databaseURL': url})
        else:
            # Fallback to default anonymous config (works if security rules allow public read/write)
            firebase_admin.initialize_app(options={'databaseURL': url})
            
        state.firebase_initialized = True
        state.firebase_status = "Connected"
        state.firebase_db_url = url
        print("Firebase Admin SDK initialized successfully.")
        return jsonify({"status": "success", "firebase_status": state.firebase_status})
    except Exception as e:
        state.firebase_status = "Init Error"
        state.firebase_initialized = False
        print(f"Firebase init error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# ==========================================
# MAIN EXECUTION BOOTSTRAPPER
# ==========================================

if __name__ == '__main__':
    print("==================================================")
    print("  🍌 AIOT BANANA RIPENESS SORTING CONTROLLER  ")
    print("==================================================")
    
    # 1. Start AI Inference thread in background
    inference_thread = threading.Thread(target=run_ai_inference, daemon=True)
    inference_thread.start()
    
    # 2. Run Flask web dashboard server locally
    # Runs on port 5000 (accessible via http://localhost:5000)
    print("\nStarting local Web Dashboard at http://localhost:5000...")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nTerminating system...")
    finally:
        state.is_camera_running = False
        if state.serial_conn:
            try: state.serial_conn.close()
            except: pass
        print("System shutdown completed.")
