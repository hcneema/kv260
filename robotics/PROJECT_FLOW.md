# KV260 Vision Robot — Full Project Flow

## Overview
Building a vision-enabled autonomous robot using AMD Kria KV260 as the AI brain
and Elegoo Mega 2560 as the motor controller.

---

## Hardware Stack

```
┌─────────────────────────────────────────┐
│           AMD Kria KV260                │
│   Ubuntu 24.04 → 22.04 (future)        │
│   ARM Cortex-A53 + FPGA DPU            │
│   IP: 192.168.68.60                     │
└──────────────┬──────────────────────────┘
               │ USB Serial (/dev/ttyACM0)
┌──────────────▼──────────────────────────┐
│          Elegoo Mega 2560               │
│   Arduino Mega 2560 compatible          │
│   Runs motor control sketch             │
└──────────────┬──────────────────────────┘
               │ Pins (plugs on top)
┌──────────────▼──────────────────────────┐
│        L298P Motor Drive Shield         │
│   4-channel, 2A per channel             │
│   Screw terminals for motor wires       │
└────────┬─────────────────┬──────────────┘
         │ 2 wires         │ 2 wires
┌────────▼────────┐ ┌──────▼────────────┐
│   Left Motor    │ │   Right Motor     │
│   TT Gear Motor │ │   TT Gear Motor   │
└────────┬────────┘ └──────┬────────────┘
         │                 │
┌────────▼────────┐ ┌──────▼────────────┐
│   Left Wheel    │ │   Right Wheel     │
└─────────────────┘ └───────────────────┘

Additional sensors (from Elegoo kit):
- SG90 Servo       → Pin 9  (camera pan/tilt)
- HC-SR04 Ultrasonic → Pins 12/13 (obstacle avoidance)
- IR Receiver      → Pin 11 (remote control)
- GY-521 IMU       → I2C   (orientation)

Vision:
- USB Webcam       → /dev/video0 (current, CPU inference)
- RPi Camera v2    → MIPI CSI-2  (future, DPU inference)
```

---

## Power Strategy

```
Wall Adapter (12V) ──→ KV260          (brain power)
AA Batteries (6V)  ──→ L298P Shield   (motor power)
─────────────────────────────────────
Future:
12V USB-C PD Power Bank ──→ KV260    (untethered)
```

---

## Communication Flow

```
KV260 Python Script
       │
       │ pyserial → /dev/ttyACM0 (9600 baud)
       │
Elegoo Mega (servo_test.ino)
       │
       │ PWM signal
       │
Motor / Servo
```

---

## Development Phases

| Phase | Feature | Hardware Needed | OS | Status |
|-------|---------|----------------|-----|--------|
| 0 | SSH + Serial link proven | KV260 + Mega | 24.04 | ✅ DONE |
| 0 | Servo control from KV260 | + SG90 Servo | 24.04 | ✅ DONE |
| 0 | USB webcam detection | + USB Webcam | 24.04 | ✅ DONE |
| 0 | Live object detection (MobileNet) | same | 24.04 | ✅ DONE |
| 0 | Face detection + servo sweep | same | 24.04 | ✅ DONE |
| 1 | Motor control from KV260 | + L298P Shield + TT Motors | 24.04 | 🛒 Pending parts |
| 2 | IR remote control | + IR receiver (in kit) | 24.04 | 🔜 |
| 3 | Ultrasonic obstacle avoidance | + HC-SR04 (in kit) | 24.04 | 🔜 |
| 4 | Live webcam + object detection on robot | same | 24.04 | 🔜 |
| 5 | Real-time AI vision at 30fps (YOLO) | + RPi Camera | 22.04 | 🔜 |

---

## Shopping List

### Microcenter Santa Clara (5201 Stevens Creek Blvd)
| Item | Price | Link |
|------|-------|------|
| L298P 4-Channel Motor Drive Shield | ~$30 | https://www.microcenter.com/product/639730 |
| MicroSD 32GB+ | ~$10 | In store |

### Amazon
| Item | Price | Link |
|------|-------|------|
| DIYmall 2x TT Motor + 2 Wheels | ~$10 | https://www.amazon.com/dp/B0861Q2LH9 |
| XiaoR Geek Aluminum Chassis (future) | ~$40 | https://www.amazon.com/dp/B078HQ5T5H |

### Future Purchases
- 12V USB-C PD Power Bank (~$40) — for untethered operation
- Raspberry Pi Camera v2 (~$25) — for DPU vision

---

## Key Files

| File | Location | Purpose |
|------|----------|---------|
| `servo_test.ino` | `robotics/` | Upload to Mega — servo control sketch |
| `servo_control.py` | `robotics/` | Simple servo sweep test from KV260 |
| `face_servo.py` | `robotics/` | Face detection → servo sweep (WORKING) |
| `webcam_infer.py` | `robotics/` | Live MobileNet object detection |
| `snapshot.py` | `robotics/` | Grab single webcam frame |
| `mobilenet.onnx` | `cnn-demo/` | MobileNetV2 model (on KV260) |
| `face_servo.py` | `cnn-demo/` | Running copy on KV260 |

---

## KV260 Quick Reference

| Item | Value |
|------|-------|
| IP Address | 192.168.68.60 |
| Username | ubuntu |
| Password | amdkria |
| SSH (PowerShell) | `ssh ubuntu@192.168.68.60` |
| Python (venv) | `/home/ubuntu/vitis-env/bin/python3` |
| Serial port | `/dev/ttyACM0` |
| Webcam | `/dev/video0` |
| Scripts location | `/home/ubuntu/cnn-demo/` |

---

## Wiring Reference

### Servo (SG90)
| Servo Wire | Mega Pin |
|-----------|---------|
| Brown | GND |
| Red | 5V |
| Orange | Pin 9 |

### Motors (future — via L298P Shield)
| Connection | Detail |
|-----------|--------|
| Left motor | M1 screw terminals |
| Right motor | M2 screw terminals |
| Battery | Shield power input |

---

## Ultimate Goal

```
USB Webcam / RPi Camera
         │
         ▼
   KV260 + YOLO DPU
   (detects: person, obstacle, object)
         │
         ▼ serial command
   Elegoo Mega + L298P Shield
         │
         ▼ PWM
   2x DC Motors → Robot moves!

Result: Autonomous vision robot that
- follows a person
- avoids obstacles  
- reacts to what it sees in real time
```
