import cv2
import serial
import time
import threading
from flask import Flask, Response, render_template_string, request, jsonify

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

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# ── Serial ─────────────────────────────────────────────────────────
def init_serial():
    global ser
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
        time.sleep(4)
        ser.reset_input_buffer()
        send_command('90')
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
            send_command('S')
            time.sleep(0.5)
            ser.close()
        except:
            pass
        ser = None

def send_command(cmd):
    if ser:
        try:
            ser.reset_input_buffer()
            ser.write((str(cmd) + '\n').encode())
        except Exception as e:
            print('Serial send error:', e, flush=True)

# ── Servo sweep ────────────────────────────────────────────────────
def sweep_servo():
    print('Sweeping servo...', flush=True)
    for angle in [0, 90, 180, 90, 0]:
        send_command(angle)
        time.sleep(1.2)
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
        cv2.putText(frame, 'KV260 Robot Car', (10, 465), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 1)

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
    <title>KV260 Robot Car</title>
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
    </style>
</head>
<body>
    <h1>&#128663; KV260 Robot Car</h1>
    <p>AMD Kria — Face Detection + Motor Control</p>
    <form method="post" action="/start">
        <button class="btn" type="submit">&#9654; Start</button>
    </form>
</body>
</html>
'''

HTML_RUNNING = '''
<!DOCTYPE html>
<html>
<head>
    <title>KV260 Robot Car</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#1e1e2e; color:white; font-family:sans-serif; text-align:center; }
        h1 { color:#ed1c24; font-size:1.2em; padding:10px; }
        img { width:100%; max-width:640px; border:3px solid #ed1c24; border-radius:8px; }
        .status { color:#00c853; font-size:0.85em; padding:5px; }

        /* D-pad */
        .dpad { display:grid; grid-template-columns: repeat(3, 70px);
                grid-template-rows: repeat(3, 70px); gap:6px;
                margin:16px auto; width:fit-content; }
        .dpad-btn { background:#2a2a3e; border:2px solid #ed1c24; border-radius:10px;
                    color:white; font-size:1.6em; cursor:pointer;
                    display:flex; align-items:center; justify-content:center; }
        .dpad-btn:active { background:#ed1c24; transform:scale(0.95); }
        .dpad-empty { visibility:hidden; }
        .stop-btn { background:#333; border:2px solid #ed1c24; }

        .bottom-bar { display:flex; justify-content:center; gap:15px; padding:10px; }
        .ctrl-btn { background:#333; color:white; border:2px solid #555;
                    border-radius:10px; font-size:1em; padding:10px 25px; cursor:pointer; }
        .ctrl-btn:active { transform:scale(0.97); }
    </style>
</head>
<body>
    <h1>&#128663; KV260 Robot Car</h1>
    <img src="/stream" />
    <div class="status">&#9679; Live — face detection active</div>

    <!-- D-pad motor control -->
    <div class="dpad">
        <div class="dpad-empty"></div>
        <button class="dpad-btn" onmousedown="motor('F')" onmouseup="motor('S')"
                ontouchstart="motor('F')" ontouchend="motor('S')">&#8593;</button>
        <div class="dpad-empty"></div>

        <button class="dpad-btn" onmousedown="motor('L')" onmouseup="motor('S')"
                ontouchstart="motor('L')" ontouchend="motor('S')">&#8592;</button>
        <button class="dpad-btn stop-btn" onclick="motor('S')">&#9632;</button>
        <button class="dpad-btn" onmousedown="motor('R')" onmouseup="motor('S')"
                ontouchstart="motor('R')" ontouchend="motor('S')">&#8594;</button>

        <div class="dpad-empty"></div>
        <button class="dpad-btn" onmousedown="motor('B')" onmouseup="motor('S')"
                ontouchstart="motor('B')" ontouchend="motor('S')">&#8595;</button>
        <div class="dpad-empty"></div>
    </div>

    <div class="bottom-bar">
        <form method="post" action="/stop">
            <button class="ctrl-btn" type="submit">&#9632; Stop Detection</button>
        </form>
    </div>

    <script>
        function motor(cmd) {
            fetch('/motor', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({cmd: cmd})
            });
        }
    </script>
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

@app.route('/motor', methods=['POST'])
def motor():
    cmd = request.json.get('cmd', 'S')
    if cmd in ('F', 'B', 'L', 'R', 'S'):
        send_command(cmd)
    return jsonify({'ok': True})

@app.route('/stream')
def stream():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ── Main ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('KV260 Robot Car ready!', flush=True)
    print('Open http://192.168.68.200:5000 on iPhone', flush=True)
    app.run(host='0.0.0.0', port=5000, threaded=True)
