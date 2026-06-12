import cv2
import serial
import time
import threading
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# ── Serial setup ──────────────────────────────────────────────────
ser = None
def init_serial():
    global ser
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
        time.sleep(4)  # wait for Mega to fully boot after serial connect
        ser.reset_input_buffer()
        # Center servo at start
        ser.write(b'90')
        time.sleep(1)
        ser.reset_input_buffer()
        print('Serial OK — servo centered')
    except Exception as e:
        print('Serial error:', e)

# ── Face detection setup ──────────────────────────────────────────
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ── Shared state ──────────────────────────────────────────────────
latest_frame = None
frame_lock = threading.Lock()
status_text = 'Scanning...'
face_count = 0
last_sweep = 0

# ── Servo sweep ───────────────────────────────────────────────────
def sweep_servo():
    if ser is None:
        return
    print('Sweeping servo...', flush=True)
    for angle in [0, 90, 180, 90, 0]:
        ser.reset_input_buffer()
        ser.write(str(angle).encode())
        time.sleep(1.2)  # give Mega enough time to move
    ser.reset_input_buffer()
    print('Sweep done.', flush=True)

# ── Detection loop (runs in background thread) ────────────────────
def detection_loop():
    global latest_frame, status_text, face_count, last_sweep
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))

        now = time.time()
        face_count = len(faces)

        # Draw bounding boxes
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(frame, 'Face', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Status overlay
        if face_count > 0:
            status_text = 'Face detected! (' + str(face_count) + ')'
            color = (0, 255, 0)
            if now - last_sweep >= 10:
                threading.Thread(target=sweep_servo, daemon=True).start()
                last_sweep = now
        else:
            status_text = 'Scanning...'
            color = (0, 200, 255)

        cv2.putText(frame, status_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        cv2.putText(frame, 'KV260 | Face Detection', (10, 465), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        # Store frame
        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with frame_lock:
            latest_frame = jpeg.tobytes()

        time.sleep(0.05)

# ── MJPEG stream generator ────────────────────────────────────────
def generate():
    while True:
        with frame_lock:
            frame = latest_frame
        if frame is None:
            time.sleep(0.05)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.05)

# ── HTML page ─────────────────────────────────────────────────────
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>KV260 Face Detection</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="60">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #1e1e2e; color: white; font-family: sans-serif; text-align: center; }
        h1 { padding: 15px; color: #ed1c24; font-size: 1.4em; }
        img { width: 100%; max-width: 640px; border: 3px solid #ed1c24; border-radius: 8px; }
        p { padding: 10px; color: #aaa; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>&#128247; KV260 Face Detection</h1>
    <img src="/stream" />
    <p>AMD Kria KV260 &middot; OpenCV Haar Cascade &middot; Live Stream</p>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/stream')
def stream():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ── Main ──────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_serial()
    t = threading.Thread(target=detection_loop, daemon=True)
    t.start()
    print('Server starting at http://192.168.68.60:5000')
    print('Open this on your iPhone or any browser!')
    app.run(host='0.0.0.0', port=5000, threaded=True)
