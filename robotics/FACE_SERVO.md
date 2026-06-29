# Face Detection Servo — Project Overview

A real-time face detection system that physically responds to people. When a face appears in the webcam, a servo motor sweeps automatically. Live video with face detection overlays streams to any iPhone or browser on the same WiFi network — no app install required.

```
Webcam → KV260 (detects face) → Arduino Mega → Servo sweeps
                  ↕ WiFi
         iPhone / Browser
         http://192.168.68.200:5000
         [Start] [Stop] + live video
```

---

## Why Two Boards?

### AMD Kria KV260 — the brain
The KV260 is an edge AI board built around a Xilinx Zynq UltraScale+ SoC — a chip that combines an ARM Cortex-A53 CPU with programmable FPGA logic. It runs full Ubuntu Linux, which means it can run Python, OpenCV, Flask, and any standard library without modification.

It handles everything compute-heavy:
- Reading frames from the USB webcam
- Running face detection (OpenCV Haar Cascade) at 15-20 FPS
- Serving the live video stream and web UI over WiFi
- Sending servo commands over USB serial to the Arduino

A Raspberry Pi could do a similar job, but the KV260 is designed for AI workloads and has a built-in DPU (Deep Learning Processing Unit) on the FPGA — meaning the same board can later run YOLO or MobileNet at 30+ FPS with a fraction of the CPU load.

### Elegoo Mega 2560 — the muscle
The Arduino Mega handles servo control. This separation is intentional:

- **Servo control needs precise timing** — PWM signals at exact microsecond intervals. Linux on the KV260 is not a real-time OS and cannot guarantee that timing reliably.
- **The Arduino is purpose-built for this** — it has dedicated hardware PWM timers, runs bare-metal (no OS), and responds to serial commands in microseconds.
- **Clean separation of concerns** — the KV260 decides *when* and *where* to move; the Mega executes *how* to move it reliably.

The Mega listens on USB serial (9600 baud) for angle values (0–180) and moves the servo immediately.

---

## Hardware

| Component | Role |
|---|---|
| AMD Kria KV260 | Vision, web server, WiFi, face detection |
| Realtek 88x2bu USB WiFi adapter | Wireless connectivity |
| USB Webcam (Logitech UVC) | Video input → `/dev/video0` |
| Elegoo Mega 2560 | Servo controller |
| SG90 Servo Motor | Physical output — sweeps on face detection |
| USB A→B cable | KV260 ↔ Mega serial link → `/dev/ttyACM0` |

### Servo Wiring (Mega)

| Servo Wire | Mega Pin |
|---|---|
| Brown | GND |
| Red | 5V |
| Orange (signal) | Pin 9 |

---

## Software

### On the KV260 (`kria_app.py`)

| Component | Details |
|---|---|
| OS | Ubuntu 24.04 LTS |
| Python | 3.12 via `/home/ubuntu/vitis-env/` |
| Face detection | OpenCV Haar Cascade — fast, no GPU needed, ~15-20 FPS |
| Web server | Flask — serves UI and MJPEG video stream on port 5000 |
| Serial | pyserial — sends angle commands to Mega at 9600 baud |

### On the Arduino (`servo_test.ino`)

Listens on Serial for integer angle values (0–180) and moves the servo immediately via hardware PWM on Pin 9.

```cpp
#include <Servo.h>
Servo myServo;
void setup() { Serial.begin(9600); myServo.attach(9); myServo.write(90); }
void loop() {
  if (Serial.available() > 0) {
    int angle = Serial.parseInt();
    if (angle >= 0 && angle <= 180) myServo.write(angle);
  }
}
```

---

## How It Works

1. User opens `http://192.168.68.200:5000` and taps **Start**
2. Flask opens the webcam (`/dev/video0`) and serial port (`/dev/ttyACM0`)
3. Detection thread runs continuously:
   - Grabs frame → converts to grayscale → runs Haar Cascade
   - Draws green bounding box around any detected face
   - Encodes frame as JPEG → streams to browser via MJPEG
4. When a face is detected and 10 seconds have passed since the last sweep:
   - Sends angles `[0, 90, 180, 90, 0]` to Mega (1.2s between each)
   - Mega moves servo in real time
5. User taps **Stop** → camera and serial close, stream ends

---

## Deploy & Run

### One-time setup — Flash Arduino
Upload `servo_test.ino` to the Elegoo Mega via Arduino IDE. This only needs to be done once — the sketch is stored permanently on the Arduino.

### Every time — Start the app

**SSH one-liner:**
```bash
ssh ubuntu@192.168.68.200 "cd ~/robotics && nohup /home/ubuntu/vitis-env/bin/python3 -u kria_app.py > /tmp/kria_app.log 2>&1 &"
```

**Or SSH in manually:**
```bash
ssh ubuntu@192.168.68.200
# password: amdkria
cd ~/robotics
nohup /home/ubuntu/vitis-env/bin/python3 -u kria_app.py > /tmp/kria_app.log 2>&1 &
```

**Then open on any device:**
```
http://192.168.68.200:5000
```
Tap **Start** → face detection begins → servo sweeps when face appears.

### Check logs
```bash
ssh ubuntu@192.168.68.200 "tail -f /tmp/kria_app.log"
```

---

## Key Numbers

| Metric | Value |
|---|---|
| Face detection | 15-20 FPS (Haar Cascade on KV260 CPU) |
| Servo sweep | 0°→90°→180°→90°→0°, triggered every 10s |
| Serial speed | 9600 baud, 1.2s between angle commands |
| Arduino reset delay | 4 seconds after serial open before first command |
| Video resolution | 640×480 |
| Stream quality | JPEG at 70% quality |

---

## Gotchas

1. **Arduino resets when serial opens** — the app waits 4 seconds before sending the first command
2. **1.2s between servo angles** — faster and the servo misses steps
3. **Stand 1-2 meters from the webcam** — too close and the face is partially cut off
4. **Only one script can own `/dev/ttyACM0`** — kill any other running scripts first
5. **Always use vitis-env Python** — system python3 causes silent hangs on this board
