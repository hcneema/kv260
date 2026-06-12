# KV260 Face Detection Robot — Developer Onboarding

## What This Project Does

A live face detection system running on an AMD Kria KV260 board.
When a face is detected via USB webcam, a servo motor sweeps automatically.
Everything is controlled from an iPhone or any browser on the same WiFi network.

```
USB Webcam → KV260 (face detection) → Elegoo Mega 2560 → SG90 Servo
                    ↕
            iPhone/Browser
            http://kria.local:5000
            [Start] [Stop] + live video feed
```

---

## Hardware

| Component | Details |
|---|---|
| AMD Kria KV260 | Main compute board, IP: 192.168.68.60, hostname: kria |
| Elegoo Mega 2560 | Arduino Mega compatible, motor/servo controller |
| SG90 Servo | Wired to Mega Pin 9 (Brown=GND, Red=5V, Orange=Pin 9) |
| USB Webcam | Logitech UVC, plugged into KV260 USB port |
| USB A→B cable | Connects KV260 to Elegoo Mega |

---

## Software Stack

| Component | Details |
|---|---|
| OS | Ubuntu 24.04 LTS on KV260 |
| Python env | `/home/ubuntu/vitis-env/` (Python 3.12) |
| Key libraries | opencv-python-headless, pyserial, flask, onnxruntime, numpy |
| Face detection | OpenCV Haar Cascade (haarcascade_frontalface_default.xml) |
| Web server | Flask MJPEG stream on port 5000 |
| Serial | pyserial → /dev/ttyACM0 at 9600 baud |

---

## Key Files

| File | Purpose |
|---|---|
| `kria_app.py` | ⭐ MAIN APP — Start/Stop UI + live stream + face detection + servo |
| `face_stream.py` | Always-on version (no Start/Stop button) |
| `face_servo.py` | Face detection + servo only (no web stream) |
| `webcam_infer.py` | MobileNetV2 object detection on live webcam feed |
| `servo_test.ino` | Upload to Elegoo Mega — listens for angle commands on serial |
| `servo_control.py` | Simple servo sweep test script |
| `snapshot.py` | Grabs a single webcam frame |

All scripts live on KV260 at: `/home/ubuntu/cnn-demo/`
Backup copies on Windows at: `C:\Users\hemn\kv260\robotics\`

---

## SSH Access

```bash
# From Windows PowerShell
ssh ubuntu@192.168.68.60
# password: amdkria

# Or use hostname
ssh ubuntu@kria.local
```

**Fix for Windows PowerShell** (if ssh not found):
```powershell
& "C:\Windows\Sysnative\OpenSSH\ssh.exe" ubuntu@192.168.68.60
```

---

## How to Start the App (after every reboot)

```bash
# SSH into KV260 then run:
sudo chmod 666 /dev/ttyACM0 /dev/video0 /dev/video1
cd /home/ubuntu/cnn-demo
/home/ubuntu/vitis-env/bin/python3 -u kria_app.py &
```

Then open on any device:
- **iPhone**: http://kria.local:5000
- **Windows**: http://kria:5000
- **Any device**: http://192.168.68.60:5000

Tap **Start** → live video appears with green bounding box around detected faces.
Servo sweeps 0°→90°→180°→90°→0° every 10 seconds while face is visible.
Tap **Stop** → everything turns off.

---

## How kria_app.py Works

```
Flask server (port 5000)
│
├── GET  /        → shows Start button (if stopped) or live video (if running)
├── POST /start   → opens camera + serial, starts detection thread
├── POST /stop    → closes camera + serial, stops detection thread
└── GET  /stream  → MJPEG stream (multipart/x-mixed-replace)

Detection thread:
  loop:
    grab frame from /dev/video0
    convert to grayscale
    run Haar Cascade face detection
    draw green bounding box around faces
    if face found AND 10 seconds since last sweep:
      send angles [0, 90, 180, 90, 0] to Mega via /dev/ttyACM0
    encode frame as JPEG → serve via /stream
```

---

## Arduino Sketch (servo_test.ino)

Must be uploaded to Elegoo Mega before running kria_app.py.
Listens for integer angle values (0-180) on Serial at 9600 baud.

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

## Important Gotchas

1. **Mega resets on serial connect** — always wait 4 seconds after opening serial port before sending commands
2. **Sweep timing** — use 1.2s between angle commands (0.9s is too fast, servo misses steps)
3. **Camera permissions** — run `sudo chmod 666 /dev/video0 /dev/video1` on every reboot
4. **Serial permissions** — run `sudo chmod 666 /dev/ttyACM0` on every reboot
5. **One serial user at a time** — kill any other scripts before starting kria_app.py
6. **Stand 1-2 meters from webcam** — too close and face is cut off, detection fails
7. **vitis-env only** — always use `/home/ubuntu/vitis-env/bin/python3`, not system python3

---

## Network Setup

| Item | Value |
|---|---|
| KV260 IP | 192.168.68.60 |
| KV260 hostname | kria |
| mDNS | avahi-daemon running → kria.local works on iPhone |
| Windows hosts | 192.168.68.60 kria (added to C:\Windows\System32\drivers\etc\hosts) |

---

## Vision Algorithms Used

### 1. Haar Cascade (current — used in kria_app.py)

| Metric | Value |
|---|---|
| Type | Classical computer vision (invented 2001) |
| Detects | Faces only |
| Speed | Fast — no heavy computation |
| FPS | ~15-20fps on KV260 CPU |
| CPU load | ~30-40% |
| Accuracy | OK in good lighting, 1-2m distance, front-on face |
| Weaknesses | Misses faces at angles, many false positives, faces only |
| Script | `kria_app.py`, `face_servo.py`, `face_stream.py` |
| How it works | Hand-crafted rules: dark eye regions + lighter forehead = face |

### 2. MobileNetV2 (object detection — used in webcam_infer.py)

| Metric | Value |
|---|---|
| Type | Deep neural network (trained on ImageNet, 1000 classes) |
| Detects | People, cars, animals, furniture, 997 more classes |
| Speed | Slower — full neural network inference |
| FPS | ~12fps on KV260 CPU |
| Latency | ~83ms/frame |
| CPU load | ~100% |
| Accuracy | Much better than Haar, works at angles, various lighting |
| Script | `webcam_infer.py` |
| How it works | Learned features from millions of images via deep learning |

### Why we use both
- **Haar** → drives the servo in the main app (fast, face-specific, good enough for demo)
- **MobileNet** → used as the CPU baseline for the DPU benchmark (same model can run on DPU)

### Important: MobileNet vs MobileNet-SSD
- **MobileNet** (what we have) — classifier only, prints top-3 labels to terminal, no bounding boxes, no live stream
- **MobileNet-SSD** (future) — object detector, draws bounding boxes on live stream, like Haar but for all objects

### Benchmark Phases
| Phase | Model | Bounding Boxes | Stream | Goal |
|---|---|---|---|---|
| 1 (now) | MobileNet CPU vs DPU | No — terminal output | No | Get raw fps/latency numbers |
| 2 (after) | MobileNet-SSD CPU vs DPU | Yes — green boxes | Yes, browser | Visual demo / show-off |

Do Phase 1 first — clean numbers. Then Phase 2 as the polished showcase.

---

## CPU vs DPU Benchmark

### Goal
Fair apples-to-apples comparison: same model, same webcam, same resolution — only execution hardware changes (CPU vs FPGA DPU).

### Why NOT Haar Cascade vs YOLO
That would be algorithm vs algorithm, not CPU vs DPU. The speed difference would be mostly due to the model, not the hardware. Must use the same model on both sides.

### Chosen Model: MobileNet
Already running on CPU via ONNX (`webcam_infer.py`). AMD also provides MobileNet compiled for DPU in the Vitis AI model zoo — perfect for a clean comparison.

### CPU Baseline (measured, Ubuntu 24.04)

| Metric | Value |
|---|---|
| Model | MobileNetV2 (ONNX via onnxruntime) |
| Resolution | 640x480, USB webcam (Logitech UVC) |
| Latency | ~83ms/frame |
| FPS | ~12fps |
| CPU load | ~100% |
| Script | `webcam_infer.py` |

### DPU Target (Ubuntu 22.04, to be measured after flash)

| Metric | Value |
|---|---|
| Model | MobileNet compiled for DPU (Vitis AI model zoo) |
| Resolution | 640x480, same USB webcam |
| Latency | TBD (expected ~33ms) |
| FPS | TBD (expected ~30fps) |
| CPU load | TBD (expected ~10-20%) |

---

## Current Limitations (and future plans)

| Limitation | Fix |
|---|---|
| Ubuntu 24.04 — no DPU support | Flash Ubuntu 22.04 on new microSD |
| Haar Cascade — basic face detection only | Upgrade to YOLO on DPU (30fps) |
| Servo only — no motor control yet | L298P shield + DC motors arriving soon |
| Wired power (no battery) | 12V USB-C PD power bank (future) |
| No chassis yet | Robot chassis kit ordered on Amazon |

---

## Parts Coming (ordered)

| Item | Source | Purpose |
|---|---|---|
| Robot chassis + motors + encoders | Amazon | Robot locomotion |
| Arduino Motor Shield REV3 | Amazon | Drive DC motors from Mega |
| MicroSD 32GB+ | Microcenter | Flash Ubuntu 22.04 for DPU |
| Short USB A-B cable | Microcenter | Clean KV260↔Mega connection on chassis |
| AA batteries | Microcenter | Power motors via shield |
