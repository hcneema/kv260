import cv2, serial, time, sys

print('imports ok', flush=True)
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
print('serial ok', flush=True)
time.sleep(2)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
print('cascade ok', flush=True)

cap = cv2.VideoCapture(0)
print('camera ok, opened:', cap.isOpened(), flush=True)

ret, frame = cap.read()
print('frame grabbed:', ret, flush=True)

gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60,60))
print('faces detected:', len(faces), flush=True)

cap.release()
ser.close()
print('all done!', flush=True)
