import cv2
import serial
import time
import threading
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# ── State ─────────────────────────────────────────────────────────
running = False
latest_frame = None
frame_lock = threading.Lock()
status_text = 'Scanning...'
last_sweep = 0
ser = None
cap = None
detection_thread = None

# ── Face detector ──────────────────────────────────────────────────
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# ── Serial ─────────────────────────────────────────────────────────
def init_serial():
    global ser
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
        time.sleep(4)
        ser.reset_input_buffer()
        ser.write(b'90')
        time.sleep(1)
        ser.reset_input_buffer()
        print('Serial OK', flush=True)
    except Exception as e:
        print('Serial error:', e, flush=True)
        ser = None

def close_serial():
    global ser
    if ser:
        try:
            ser.close()
        except:
            pass
        ser = None

# ── Servo sweep ────────────────────────────────────────────────────
def sweep_servo():
    if ser is None:
        return
    print('Sweeping servo...', flush=True)
    for angle in [0, 90, 180, 90, 0]:
        ser.reset_input_buffer()
        ser.write(str(angle).encode())
        time.sleep(1.2)
    ser.reset_input_buffer()
    print('Sweep done.', flush=True)

# ── Detection loop ─────────────────────────────────────────────────
def detection_loop():
    global latest_frame, status_text, last_sweep, running, cap
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))

        now = time.time()

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(frame, 'Face', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if len(faces) > 0:
            status_text = 'Face detected! (' + str(len(faces)) + ')'
            color = (0, 255, 0)
            if now - last_sweep >= 10:
                threading.Thread(target=sweep_servo, daemon=True).start()
                last_sweep = now
        else:
            status_text = 'Scanning...'
            color = (0, 200, 255)

        cv2.putText(frame, status_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        cv2.putText(frame, 'KV260 | kria.local:5000', (10, 465), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 1)

        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with frame_lock:
            latest_frame = jpeg.tobytes()

        time.sleep(0.05)

    cap.release()
    cap = None
    with frame_lock:
        latest_frame = None
    print('Detection stopped.', flush=True)

# ── MJPEG stream ───────────────────────────────────────────────────
def generate():
    while True:
        with frame_lock:
            frame = latest_frame
        if frame is None:
            time.sleep(0.1)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.05)

# ── HTML ───────────────────────────────────────────────────────────
HTML_STOPPED = '''
<!DOCTYPE html>
<html>
<head>
    <title>KV260 Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#1e1e2e; color:white; font-family:sans-serif;
               display:flex; flex-direction:column; align-items:center;
               justify-content:center; height:100vh; }
        h1 { color:#ed1c24; font-size:1.6em; margin-bottom:10px; }
        p  { color:#888; font-size:0.9em; margin-bottom:40px; }
        .btn { background:#ed1c24; color:white; border:none; border-radius:12px;
               font-size:1.4em; padding:20px 50px; cursor:pointer;
               box-shadow:0 4px 20px rgba(237,28,36,0.4); }
        .btn:active { transform:scale(0.97); }
        .status { margin-top:30px; color:#555; font-size:0.85em; }
    </style>
</head>
<body>
    <h1>&#128247; KV260</h1>
    <p>AMD Kria Face Detection + Servo</p>
    <form method="post" action="/start">
        <button class="btn" type="submit">&#9654; Start</button>
    </form>
    <div class="status">Status: Off</div>
</body>
</html>
'''

HTML_RUNNING = '''
<!DOCTYPE html>
<html>
<head>
    <title>KV260 Live</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#1e1e2e; color:white; font-family:sans-serif; text-align:center; }
        h1 { color:#ed1c24; font-size:1.2em; padding:12px; }
        img { width:100%; max-width:640px; border:3px solid #ed1c24; border-radius:8px; }
        .btn { background:#333; color:white; border:2px solid #ed1c24; border-radius:10px;
               font-size:1.1em; padding:12px 35px; cursor:pointer; margin:15px; }
        .btn:active { transform:scale(0.97); }
        .status { color:#00c853; font-size:0.85em; padding:5px; }
    </style>
</head>
<body>
    <h1>&#128247; KV260 Face Detection</h1>
    <img src="/stream" />
    <div class="status">&#9679; Live — kria.local:5000</div>
    <form method="post" action="/stop">
        <button class="btn" type="submit">&#9632; Stop</button>
    </form>
</body>
</html>
'''

# ── Routes ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    if running:
        return render_template_string(HTML_RUNNING)
    return render_template_string(HTML_STOPPED)

@app.route('/start', methods=['POST'])
def start():
    global running, detection_thread, last_sweep
    if not running:
        running = True
        last_sweep = 0
        init_serial()
        detection_thread = threading.Thread(target=detection_loop, daemon=True)
        detection_thread.start()
        print('App started.', flush=True)
    return index()

@app.route('/stop', methods=['POST'])
def stop():
    global running
    running = False
    close_serial()
    time.sleep(1)
    print('App stopped.', flush=True)
    return index()

@app.route('/stream')
def stream():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ── Main ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('KV260 App ready!', flush=True)
    print('Open http://kria.local:5000 on iPhone', flush=True)
    print('Open http://kria:5000 on Windows', flush=True)
    app.run(host='0.0.0.0', port=5000, threaded=True)
