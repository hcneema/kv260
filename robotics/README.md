# KV260 Robotics Setup

## Hardware
- AMD Kria KV260 (192.168.68.60) — brain/vision
- Elegoo Mega 2560 — motor controller
- SG90 Servo motor — wired to Mega pin 9
- L298P Motor Drive Shield (to buy) — for DC motors
- Robot chassis + DC motors (to buy)

## Wiring — Servo to Mega
| Servo Wire | Mega Pin |
|---|---|
| Brown | GND |
| Red | 5V |
| Orange | Pin 9 |

## Files
- `servo_test.ino` — upload to Elegoo Mega via Arduino IDE
- `servo_control.py` — run on KV260 to control servo from Python

## Running servo_control.py on KV260
```bash
ssh ubuntu@192.168.68.60
python3 ~/servo_control.py
```

## Next Steps
1. Buy L298P Motor Shield + chassis + microSD at Microcenter Santa Clara
   - 5201 Stevens Creek Blvd, Santa Clara, CA
2. Flash Ubuntu 22.04 on new microSD for DPU support
3. Wire up DC motors with L298P shield
4. Install ROS 2 for proper robot control
5. Add Raspberry Pi Camera v2 for vision

## Proven Working
- KV260 <-> Elegoo Mega serial communication over /dev/ttyACM0
- KV260 remotely controlling servo via Python serial
