import cv2
import serial
import time

# Serial connection to Elegoo Mega
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
time.sleep(3)  # wait longer for Mega to fully boot after serial connect
ser.reset_input_buffer()

# Load Haar Cascade face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Open webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('ERROR: Cannot open webcam')
    exit()

print('Face detection started...', flush=True)
print('Face found -> servo sweeps every 10 seconds', flush=True)
print('No face   -> servo stays still', flush=True)
print(flush=True)

def send_angle(angle):
    ser.write(str(angle).encode())
    time.sleep(1.0)  # give Mega time to move servo
    ser.reset_input_buffer()

def sweep_servo():
    print('Face detected! Sweeping servo...', flush=True)
    for angle in [0, 90, 180, 90, 0]:
        send_angle(angle)
    print('Sweep done.', flush=True)

last_sweep = 0

# Center servo at start
send_angle(90)
print('Servo centered at 90', flush=True)

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print('Failed to grab frame', flush=True)
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(30, 30)
        )

        now = time.time()

        if len(faces) > 0:
            print('Face detected! (' + str(len(faces)) + ' face(s) )', flush=True)
            if now - last_sweep >= 10:
                sweep_servo()
                last_sweep = now
        else:
            print('No face - scanning...', flush=True)

        time.sleep(0.5)

except KeyboardInterrupt:
    print('Stopped.')

cap.release()
ser.close()
