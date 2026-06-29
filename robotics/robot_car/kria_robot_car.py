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
current_cmd = None          # tracks last sent motor command to avoid flooding
ser = None
cap = None
detection_thread = None

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# ── Face following config ──────────────────────────────────────────
FRAME_WIDTH = 640
CENTER_X    = FRAME_WIDTH // 2
DEAD_ZONE   = 80            # px either side of center → go forward

# ── Serial ─────────────────────────────────────────────────────────
def init_serial():
    global ser
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
        time.sleep(4)
        ser.reset_input_buffer()
        send_command('S')
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
            time.sleep(0.3)
            ser.close()
        except:
            pass
        ser = None

def send_command(cmd):
    global current_cmd
    if ser and cmd != current_cmd:
        try:
            ser.reset_input_buffer()
            ser.write((str(cmd) + '\n').encode())
            current_cmd = cmd
        except Exception as e:
            print('Serial send error:', e, flush=True)

# ── Detection + face following loop ───────────────────────────────
def detection_loop():
    global latest_frame, status_text, running, cap, current_cmd
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 50))

        # Draw center line (dead zone)
        cv2.line(frame, (CENTER_X - DEAD_ZONE, 0), (CENTER_X - DEAD_ZONE, 480), (50, 50, 200), 1)
        cv2.line(frame, (CENTER_X + DEAD_ZONE, 0), (CENTER_X + DEAD_ZONE, 480), (50, 50, 200), 1)

        if len(faces) > 0:
            # Use the largest face
            (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
            face_cx = x + w // 2
            offset  = face_cx - CENTER_X

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.circle(frame, (face_cx, y + h // 2), 5, (0, 255, 0), -1)

            if offset < -DEAD_ZONE:
                cmd = 'L'
                status_text = 'Face left  → turning left'
                arrow = '<--'
            elif offset > DEAD_ZONE:
                cmd = 'R'
                status_text = 'Face right → turning right'
                arrow = '-->'
            else:
                cmd = 'F'
                status_text = 'Face centered → forward'
                arrow = ' ^ '

            send_command(cmd)
            cv2.putText(frame, arrow, (CENTER_X - 20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        else:
            send_command('S')
            status_text = 'No face — stopped'
            cv2.putText(frame, 'Searching...', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)

        cv2.putText(frame, status_text, (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 1)

        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with frame_lock:
            latest_frame = jpeg.tobytes()
        time.sleep(0.05)

    send_command('S')
    cap.release()
    cap = None
    current_cmd = None
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
        p  { color:#888; font-size:0.9em; margin-bottom:10px; }
        .desc { color:#555; font-size:0.8em; margin-bottom:40px; text-align:center; padding:0 20px; }
        .btn { background:#ed1c24; color:white; border:none; border-radius:12px;
               font-size:1.4em; padding:20px 50px; cursor:pointer;
               box-shadow:0 4px 20px rgba(237,28,36,0.4); }
        .btn:active { transform:scale(0.97); }
    </style>
</head>
<body>
    <h1>&#128663; KV260 Robot Car</h1>
    <p>Face Following Mode</p>
    <div class="desc">The car will automatically steer toward any face it detects.</div>
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
        .status { color:#00c853; font-size:0.85em; padding:6px; }
        .hint { color:#555; font-size:0.75em; padding:4px; }
        .stop-btn { background:#333; color:white; border:2px solid #ed1c24;
                    border-radius:10px; font-size:1.1em; padding:12px 35px;
                    cursor:pointer; margin:12px; }
        .stop-btn:active { transform:scale(0.97); }
    </style>
</head>
<body>
    <h1>&#128663; KV260 Robot Car — Face Following</h1>
    <img src="/stream" />
    <div class="status">&#9679; Live — auto-steering toward face</div>
    <div class="hint">Blue lines show the dead zone. Car steers when face moves outside.</div>
    <form method="post" action="/stop">
        <button class="stop-btn" type="submit">&#9632; Stop</button>
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
    global running, detection_thread
    if not running:
        running = True
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
    print('KV260 Robot Car ready!', flush=True)
    print('Open http://192.168.68.200:5000 on iPhone', flush=True)
    app.run(host='0.0.0.0', port=5000, threaded=True)
