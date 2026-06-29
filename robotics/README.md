# KV260 Face Detection Robot

A real-time face detection system running on an AMD Kria KV260 edge AI board. When a face is detected via USB webcam, a servo motor sweeps automatically. The system is fully wireless — controlled from any browser or iPhone on the same WiFi network.

```
USB Webcam → KV260 (OpenCV face detection)
                    ↓ USB serial
             Elegoo Mega 2560 → SG90 Servo
                    ↕ WiFi
             iPhone / Browser
             http://192.168.68.200:5000
             [Start] [Stop] + live video stream
```

---

## Hardware

| Component | Details |
|---|---|
| AMD Kria KV260 | Main compute board — runs face detection + web server |
| Realtek 88x2bu USB WiFi adapter | Wireless connectivity (driver installed via DKMS) |
| USB Webcam (Logitech UVC) | Plugged into KV260 USB port → `/dev/video0` |
| Elegoo Mega 2560 | Arduino-compatible — receives servo angle commands |
| SG90 Servo Motor | Wired to Mega Pin 9 |
| USB A→B cable | Connects KV260 to Elegoo Mega → `/dev/ttyACM0` |

### Servo Wiring

| Servo Wire | Mega Pin |
|---|---|
| Brown | GND |
| Red | 5V |
| Orange | Pin 9 |

---

## Software

| Component | Details |
|---|---|
| OS | Ubuntu 24.04 LTS |
| Python | 3.12 via `/home/ubuntu/vitis-env/` (virtualenv) |
| Face detection | OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`) |
| Web server | Flask, MJPEG stream on port 5000 |
| Serial comms | pyserial → `/dev/ttyACM0` at 9600 baud |
| Key packages | `flask`, `opencv-python-headless`, `pyserial`, `numpy`, `onnxruntime` |

---

## Files

| File | Purpose |
|---|---|
| `kria_app.py` | **Main app** — Flask web UI + face detection + servo control |
| `servo_test.ino` | Arduino sketch — upload once to Elegoo Mega via Arduino IDE |
| `face_stream.py` | Always-on face detection + stream (no Start/Stop button) |
| `face_servo.py` | Face detection + servo only (no web UI) |
| `webcam_infer.py` | MobileNetV2 object detection (CPU benchmark baseline) |
| `servo_control.py` | Simple servo sweep test |
| `snapshot.py` | Grabs a single webcam frame |

Only `kria_app.py` is needed for the main demo. `servo_test.ino` must be flashed to the Arduino once — after that it lives on the Arduino permanently.

---

## Network

| Item | Value |
|---|---|
| WiFi IP | `192.168.68.200` (static) |
| Wired IP | `192.168.68.56` (static) |
| Web UI | `http://192.168.68.200:5000` |
| SSH | `ssh ubuntu@192.168.68.200` |
| Username | `ubuntu` |
| Password | `amdkria` |

---

## Deploy & Run

### Prerequisites
- Elegoo Mega flashed with `servo_test.ino` via Arduino IDE
- Board powered on, connected to `hem-saanvi-deco` WiFi

### Start the app

**Via SSH:**
```bash
ssh ubuntu@192.168.68.200
cd ~/robotics
nohup /home/ubuntu/vitis-env/bin/python3 -u kria_app.py > /tmp/kria_app.log 2>&1 &
```

**One-liner from your machine:**
```bash
ssh ubuntu@192.168.68.200 "cd ~/robotics && nohup /home/ubuntu/vitis-env/bin/python3 -u kria_app.py > /tmp/kria_app.log 2>&1 &"
```

### Use the app
1. Open `http://192.168.68.200:5000` on your iPhone or browser
2. Tap **Start** — live video appears with green boxes around detected faces
3. Servo sweeps 0°→90°→180°→90°→0° every 10 seconds while a face is visible
4. Tap **Stop** to shut down detection

### Check logs
```bash
ssh ubuntu@192.168.68.200 "tail -f /tmp/kria_app.log"
```

---

## How It Works

```
Flask (port 5000)
├── GET  /        → Start button or live video page
├── POST /start   → opens /dev/video0 + /dev/ttyACM0, starts detection thread
├── POST /stop    → stops detection, closes camera + serial
└── GET  /stream  → MJPEG video stream

Detection thread:
  loop:
    grab frame from webcam
    convert to grayscale → run Haar Cascade
    draw green bounding box around faces
    if face found AND 10s since last sweep:
      send angles [0, 90, 180, 90, 0] to Mega over serial
    encode frame as JPEG → serve via /stream
```

---

## Gotchas

1. **Mega resets on serial connect** — kria_app.py waits 4 seconds before sending commands
2. **Sweep timing** — 1.2s between angle commands (0.9s is too fast, servo misses steps)
3. **Stand 1-2 meters from webcam** — too close and face is cut off, detection fails
4. **One serial user at a time** — only one script can own `/dev/ttyACM0`
5. **Always use vitis-env Python** — system python3 causes silent hangs

---

## SD Cards

Two SD cards are in use:

| Card | OS | Purpose |
|---|---|---|
| Card A (current) | Ubuntu 24.04 | This robotics app |
| Card B | Ubuntu 22.04 | DPU benchmarking (`~/dpu_benchmark/`) |

After swapping to a new SD card, reinstall the WiFi driver:
```bash
sudo bash ~/install-wifi-driver.sh
```
