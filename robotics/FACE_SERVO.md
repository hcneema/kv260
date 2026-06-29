# Face Detection Servo Project

## What does it do?

This project uses a camera to detect faces in real time. When it sees a face, it automatically moves a servo motor. You can watch the live camera feed and control everything from your phone — no app needed, just open a browser.

Here's the basic idea:

```
Camera → KV260 board sees a face → tells Arduino → servo moves
                    ↕
             your iPhone browser
             http://192.168.68.200:5000
             [Start] [Stop] + live video
```

---

## The hardware — and why we picked each piece

### AMD Kria KV260
This is a small but powerful computer board made by AMD. Think of it as a smarter, faster Raspberry Pi designed specifically for AI tasks. It runs Linux just like a regular computer, so we can write normal Python code on it.

It handles the hard part: looking at the camera 15-20 times per second and figuring out if there's a face in the image. It also runs the website that you open on your phone.

### Arduino Mega 2560 (Elegoo)
Here's the thing — the KV260 is great at AI and running software, but it cannot directly control a servo motor. Servo motors need a very precise electrical signal that has to arrive at exactly the right time, every few milliseconds. The KV260 runs Linux, which is busy doing many things at once and can't guarantee that kind of timing.

So we needed a helper board — the Arduino. The Arduino does nothing except wait for the KV260 to say "move to this angle" and then it moves the servo perfectly. It's simple, dedicated, and great at timing. That's why we had to use it.

The two boards talk to each other over a USB cable.

### SG90 Servo Motor
A small hobby servo that can rotate to any angle between 0° and 180°. When a face is detected, it sweeps from one side to the other and back.

### USB Webcam (Logitech)
Plugged into the KV260. This is what sees the faces.

### Realtek USB WiFi Adapter
The KV260 doesn't have built-in WiFi, so we plugged in a small USB WiFi dongle. This lets the board connect to the home network so you can control it from your phone.

---

## The software

**On the KV260 — `kria_app.py`**
A Python program that does three things at once:
- Reads frames from the webcam and scans for faces using OpenCV (a popular computer vision library)
- Streams the live video to your phone's browser
- Sends a "move!" command to the Arduino whenever a face is detected

**On the Arduino — `servo_test.ino`**
A tiny program (called a "sketch") uploaded to the Arduino. It just listens for angle numbers coming from the KV260 and moves the servo to that angle. That's it.

The Arduino sketch only needs to be uploaded once. After that it lives on the Arduino and you never touch it again.

---

## How to run it

### First time only — set up the Arduino
Open `servo_test.ino` in the Arduino IDE and upload it to the Elegoo Mega. You only need to do this once.

### Every time — start the app

SSH into the KV260 and run:
```bash
ssh ubuntu@192.168.68.200
# password: amdkria

cd ~/robotics
nohup /home/ubuntu/vitis-env/bin/python3 -u kria_app.py > /tmp/kria_app.log 2>&1 &
```

Then open your phone browser and go to:
```
http://192.168.68.200:5000
```

Tap **Start** and the camera turns on. Stand about 1-2 meters away and you'll see a green box appear around your face. Every 10 seconds that a face is visible, the servo will sweep back and forth.

Tap **Stop** to turn everything off.

---

## Things to watch out for

- **Stand 1-2 meters from the camera** — too close and it can't see your whole face
- **The Arduino takes a moment to wake up** — the app automatically waits 4 seconds after connecting before sending any commands, so don't worry if the servo doesn't move immediately
- **Only one program can control the servo at a time** — make sure no other scripts are running before starting the app
