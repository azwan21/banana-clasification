#!/usr/bin/env python3
"""
AIoT CHALLENGE 2026 - Smart Banana Ripeness Sorting System
Schematic Diagram Generator using Python PIL.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

def create_schematic():
    # 1. Create canvas
    width, height = 1200, 800
    img = Image.new('RGB', (width, height), color='#0f172a') # Slate-900 background
    draw = ImageDraw.Draw(img)

    # 2. Draw engineering grid lines
    grid_spacing = 40
    for x in range(0, width, grid_spacing):
        draw.line([(x, 0), (x, height)], fill='#1e293b', width=1)
    for y in range(0, height, grid_spacing):
        draw.line([(0, y), (width, y)], fill='#1e293b', width=1)

    # Try loading default font or local standard font
    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_header = ImageFont.truetype("arial.ttf", 18)
        font_body = ImageFont.truetype("arial.ttf", 14)
        font_bold = ImageFont.truetype("arialbd.ttf", 14)
        font_pin = ImageFont.truetype("cour.ttf", 12)
    except IOError:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_pin = ImageFont.load_default()

    # 3. Draw Header Title Block
    draw.rectangle([(40, 30), (width - 40, 100)], fill='#1e293b', outline='#3b82f6', width=2)
    draw.text((60, 45), "AIoT BANANA RIPENESS SORTING SYSTEM", fill='#f8fafc', font=font_title)
    draw.text((60, 75), "System Architecture & Hardware Wiring Schematic (Active-Low Relays)", fill='#94a3b8', font=font_body)

    # 4. Define Component Positions
    # NodeMCU Board
    esp_x, esp_y, esp_w, esp_h = 100, 200, 240, 480
    # Relay Module
    rly_x, rly_y, rly_w, rly_h = 580, 200, 260, 480
    # Output Load / Indicators
    load_x, load_y, load_w, load_h = 1000, 200, 140, 480

    # Draw NodeMCU Module
    draw.rectangle([(esp_x, esp_y), (esp_x + esp_w, esp_y + esp_h)], fill='#1e3a8a', outline='#3b82f6', width=3)
    draw.rectangle([(esp_x + 30, esp_y - 20), (esp_x + esp_w - 30, esp_y)], fill='#475569', outline='#64748b', width=1) # Antenna
    draw.text((esp_x + 40, esp_y + 20), "NodeMCU ESP8266", fill='#f8fafc', font=font_header)
    draw.text((esp_x + 50, esp_y + 45), "(ESP-12E Module)", fill='#94a3b8', font=font_body)

    # NodeMCU Pin Lists
    left_pins = ["A0", "RSV", "RSV", "SD3", "SD2", "SD1", "CMD", "SD0", "CLK", "GND", "3V3", "EN", "RST", "GND", "VIN"]
    right_pins = ["D0", "D1", "D2", "D3", "D4", "3V3", "GND", "D5", "D6", "D7", "D8", "RX", "TX", "GND", "3V3"]

    pin_step = 26
    start_pin_y = esp_y + 80

    # Draw NodeMCU Pins (Left & Right)
    for i, pin in enumerate(left_pins):
        py = start_pin_y + i * pin_step
        # Pin indicator dot
        draw.ellipse([(esp_x - 5, py - 5), (esp_x + 5, py + 5)], fill='#94a3b8')
        draw.text((esp_x + 10, py - 6), pin, fill='#38bdf8', font=font_pin)

    # Highlighted Pins for routing
    target_pins = {
        "D5": '#ec4899', # Pink - Relay 1
        "D6": '#06b6d4', # Cyan - Relay 2
        "D7": '#f59e0b', # Amber - Relay 3
        "D8": '#10b981', # Emerald - Relay 4
        "GND": '#ef4444', # Black representation (using red/gray for routing visual)
        "3V3": '#3b82f6'  # VCC 3.3V
    }

    for i, pin in enumerate(right_pins):
        py = start_pin_y + i * pin_step
        draw.ellipse([(esp_x + esp_w - 5, py - 5), (esp_x + esp_w + 5, py + 5)], fill='#94a3b8')
        
        # Color specific signal pins
        color = '#38bdf8'
        if pin in target_pins:
            color = target_pins[pin]
            if pin in ["D5", "D6", "D7", "D8"]:
                draw.ellipse([(esp_x + esp_w - 5, py - 5), (esp_x + esp_w + 5, py + 5)], fill=color)
        
        draw.text((esp_x + esp_w - 45, py - 6), pin, fill=color, font=font_pin)

    # Draw 4-Channel Relay Module
    draw.rectangle([(rly_x, rly_y), (rly_x + rly_w, rly_y + rly_h)], fill='#064e3b', outline='#10b981', width=3)
    draw.text((rly_x + 40, rly_y + 20), "4-CHANNEL RELAY", fill='#f8fafc', font=font_header)
    draw.text((rly_x + 50, rly_y + 45), "(5V Active-Low Module)", fill='#94a3b8', font=font_body)

    # Relay control interface (Input pins on the left)
    rly_inputs = ["VCC", "GND", "IN1", "IN2", "IN3", "IN4"]
    rly_in_step = 40
    start_rly_in_y = rly_y + 120

    for i, inp in enumerate(rly_inputs):
        iy = start_rly_in_y + i * rly_in_step
        draw.ellipse([(rly_x - 5, iy - 5), (rly_x + 5, iy + 5)], fill='#fbbf24')
        draw.text((rly_x + 12, iy - 7), inp, fill='#fbbf24', font=font_pin)

    # Relay output blocks (NO, COM, NC terminals on the right)
    channels = [
        {"name": "CH 1: Unripe (D5)", "y_offset": 0},
        {"name": "CH 2: Ripe (D6)", "y_offset": 100},
        {"name": "CH 3: Overripe (D7)", "y_offset": 200},
        {"name": "CH 4: Rotten (D8)", "y_offset": 300}
    ]
    start_rly_out_y = rly_y + 130

    for ch in channels:
        cy = start_rly_out_y + ch["y_offset"]
        
        # Channel boundary
        draw.rectangle([(rly_x + 40, cy - 15), (rly_x + rly_w - 20, cy + 50)], fill='#042f2e', outline='#14b8a6', width=1)
        draw.text((rly_x + 45, cy - 10), ch["name"], fill='#f2f4f7', font=font_bold)
        
        # Terminals
        draw.ellipse([(rly_x + rly_w - 5, cy + 10), (rly_x + rly_w + 5, cy + 15)], fill='#f59e0b')
        draw.text((rly_x + rly_w - 40, cy + 5), "NO", fill='#94a3b8', font=font_pin)
        
        draw.ellipse([(rly_x + rly_w - 5, cy + 25), (rly_x + rly_w + 5, cy + 30)], fill='#f59e0b')
        draw.text((rly_x + rly_w - 40, cy + 20), "COM", fill='#94a3b8', font=font_pin)

        draw.ellipse([(rly_x + rly_w - 5, cy + 40), (rly_x + rly_w + 5, cy + 45)], fill='#f59e0b')
        draw.text((rly_x + rly_w - 40, cy + 35), "NC", fill='#94a3b8', font=font_pin)

    # Draw Indicators/Loads (LEDs representation on the right)
    loads = [
        {"name": "LED 1: Yellow (Unripe)", "color": '#fbbf24', "y": 330},
        {"name": "LED 2: Green (Ripe)", "color": '#10b981', "y": 430},
        {"name": "LED 3: Orange (Overripe)", "color": '#f97316', "y": 530},
        {"name": "LED 4: Red (Rotten / Buzzer)", "color": '#ef4444', "y": 630}
    ]

    for ld in loads:
        # LED circles
        draw.ellipse([(load_x + 20, ld["y"] - 15), (load_x + 60, ld["y"] + 25)], fill=ld["color"], outline='#ffffff', width=1)
        # LED Symbol inside
        draw.line([(load_x + 30, ld["y"] - 5), (load_x + 50, ld["y"] + 15)], fill='#000000', width=2)
        draw.line([(load_x + 50, ld["y"] - 5), (load_x + 30, ld["y"] + 15)], fill='#000000', width=2)
        
        # Load Name
        draw.text((load_x + 10, ld["y"] + 30), ld["name"], fill=ld["color"], font=font_pin)

    # Draw Power Supply Block
    pwr_x, pwr_y, pwr_w, pwr_h = 390, 600, 140, 120
    draw.rectangle([(pwr_x, pwr_y), (pwr_x + pwr_w, pwr_y + pwr_h)], fill='#78350f', outline='#f59e0b', width=2)
    draw.text((pwr_x + 15, pwr_y + 15), "5V DC POWER", fill='#f8fafc', font=font_header)
    draw.text((pwr_x + 15, pwr_y + 40), "SUPPLY (USB)", fill='#f8fafc', font=font_header)
    
    # Power Pins
    draw.ellipse([(pwr_x + 20, pwr_y + 90), (pwr_x + 30, pwr_y + 100)], fill='#ef4444')
    draw.text((pwr_x + 35, pwr_y + 88), "VCC (+)", fill='#ef4444', font=font_pin)
    
    draw.ellipse([(pwr_x + 110, pwr_y + 90), (pwr_x + 120, pwr_y + 100)], fill='#000000')
    draw.text((pwr_x + 75, pwr_y + 88), "GND (-)", fill='#ffffff', font=font_pin)

    # 5. Draw Color-Coded Signal Wires (Routing)
    # Signal D5 -> IN1 (Magenta wire)
    d5_y = start_pin_y + 7 * pin_step # D5 position
    in1_y = start_rly_in_y + 2 * rly_in_step # IN1
    draw.line([(esp_x + esp_w, d5_y), (480, d5_y), (480, in1_y), (rly_x, in1_y)], fill='#ec4899', width=2)

    # Signal D6 -> IN2 (Cyan wire)
    d6_y = start_pin_y + 8 * pin_step # D6
    in2_y = start_rly_in_y + 3 * rly_in_step # IN2
    draw.line([(esp_x + esp_w, d6_y), (490, d6_y), (490, in2_y), (rly_x, in2_y)], fill='#06b6d4', width=2)

    # Signal D7 -> IN3 (Orange/Yellow wire)
    d7_y = start_pin_y + 9 * pin_step # D7
    in3_y = start_rly_in_y + 4 * rly_in_step # IN3
    draw.line([(esp_x + esp_w, d7_y), (500, d7_y), (500, in3_y), (rly_x, in3_y)], fill='#f59e0b', width=2)

    # Signal D8 -> IN4 (Green wire)
    d8_y = start_pin_y + 10 * pin_step # D8
    in4_y = start_rly_in_y + 5 * rly_in_step # IN4
    draw.line([(esp_x + esp_w, d8_y), (510, d8_y), (510, in4_y), (rly_x, in4_y)], fill='#10b981', width=2)

    # VCC / GND sharing lines
    # NodeMCU GND -> Relay GND
    gnd_esp_y = start_pin_y + 6 * pin_step
    gnd_rly_y = start_rly_in_y + 1 * rly_in_step
    draw.line([(esp_x + esp_w, gnd_esp_y), (450, gnd_esp_y), (450, gnd_rly_y), (rly_x, gnd_rly_y)], fill='#ffffff', width=2)

    # Power supply connections
    # VCC (+) -> Relay VCC
    vcc_rly_y = start_rly_in_y + 0 * rly_in_step
    draw.line([(pwr_x + 25, pwr_y + 90), (25, pwr_y + 90), (25, vcc_rly_y), (rly_x, vcc_rly_y)], fill='#ef4444', width=2)
    # Also power NodeMCU VIN (for standalone power backup)
    vin_esp_y = start_pin_y + 14 * pin_step
    draw.line([(25, vin_esp_y), (esp_x, vin_esp_y)], fill='#ef4444', width=2)

    # External GND (-) -> NodeMCU GND & Relay GND loop
    draw.line([(pwr_x + 115, pwr_y + 90), (450, pwr_y + 90), (450, gnd_rly_y)], fill='#64748b', width=2)

    # NO Relay outputs connecting to respective LEDs
    # NO 1 (CH 1) -> LED 1
    draw.line([(rly_x + rly_w, start_rly_out_y + 10), (950, start_rly_out_y + 10), (950, 330), (load_x + 20, 330)], fill='#fbbf24', width=2)
    # NO 2 (CH 2) -> LED 2
    draw.line([(rly_x + rly_w, start_rly_out_y + 110), (940, start_rly_out_y + 110), (940, 430), (load_x + 20, 430)], fill='#10b981', width=2)
    # NO 3 (CH 3) -> LED 3
    draw.line([(rly_x + rly_w, start_rly_out_y + 210), (930, start_rly_out_y + 210), (930, 530), (load_x + 20, 530)], fill='#f97316', width=2)
    # NO 4 (CH 4) -> LED 4
    draw.line([(rly_x + rly_w, start_rly_out_y + 310), (920, start_rly_out_y + 310), (920, 630), (load_x + 20, 630)], fill='#ef4444', width=2)

    # COM terminals daisy chained to Power Supply VCC (+)
    com_chain_x = rly_x + rly_w + 30
    for ch in channels:
        cy = start_rly_out_y + ch["y_offset"] + 27 # COM dot
        draw.line([(rly_x + rly_w, cy), (com_chain_x, cy)], fill='#ef4444', width=2)
        
    # Connect COM chain to VCC
    draw.line([(com_chain_x, start_rly_out_y + 27), (com_chain_x, start_rly_out_y + 327)], fill='#ef4444', width=2)
    draw.line([(com_chain_x, start_rly_out_y + 177), (35, start_rly_out_y + 177), (35, vcc_rly_y)], fill='#ef4444', width=2)

    # LED Cathodes (negative leads) daisy-chained to Power Supply GND (-)
    gnd_chain_x = load_x + 80
    for ld in loads:
        draw.line([(load_x + 60, ld["y"] + 5), (gnd_chain_x, ld["y"] + 5)], fill='#64748b', width=2)
    # Resistor on the GND line
    draw.line([(gnd_chain_x, 335), (gnd_chain_x, 635)], fill='#64748b', width=2)
    # Connect resistor block to power GND
    draw.line([(gnd_chain_x, 635), (gnd_chain_x, 750), (450, 750), (450, pwr_y + 90)], fill='#64748b', width=2)

    # Add text label for Resistor in the chain
    draw.rectangle([(gnd_chain_x - 10, 470), (gnd_chain_x + 10, 500)], fill='#7c2d12', outline='#ffffff')
    draw.text((gnd_chain_x + 18, 475), "220 Ohm", fill='#ffffff', font=font_pin)

    # Draw Legend box
    draw.rectangle([(50, 690), (320, 780)], fill='#1e293b', outline='#475569')
    draw.text((60, 695), "LEGEND & CONNECTIONS", fill='#ffffff', font=font_bold)
    draw.text((60, 715), "- Pink: D5 -> Relay IN1 (Unripe)", fill='#ec4899', font=font_pin)
    draw.text((60, 730), "- Cyan: D6 -> Relay IN2 (Ripe)", fill='#06b6d4', font=font_pin)
    draw.text((60, 745), "- Yellow: D7 -> Relay IN3 (Overripe)", fill='#f59e0b', font=font_pin)
    draw.text((60, 760), "- Green: D8 -> Relay IN4 (Rotten)", fill='#10b981', font=font_pin)

    # Save outputs
    # 1. Save locally in workspace
    workspace_path = "diagram_skematik.png"
    img.save(workspace_path)
    print(f"Generated schematic diagram: {workspace_path}")

    # 2. Save inside artifacts directory for walkthrough markdown
    artifact_dir = "C:\\Users\\ASUS\\.gemini\\antigravity-ide\\brain\\f281b5f7-9886-4287-877e-8d164174efaf"
    if os.path.exists(artifact_dir):
        artifact_path = os.path.join(artifact_dir, "diagram_skematik.png")
        img.save(artifact_path)
        print(f"Copied schematic diagram to artifact folder: {artifact_path}")

if __name__ == "__main__":
    create_schematic()
