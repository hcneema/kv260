import cv2
import numpy as np
import onnxruntime as ort
import json
import time

with open('/home/ubuntu/cnn-demo/labels.json') as f:
    labels = json.load(f)

session = ort.InferenceSession('/home/ubuntu/cnn-demo/mobilenet.onnx', providers=['CPUExecutionProvider'])
input_name = session.get_inputs()[0].name

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('ERROR: Cannot open webcam')
    exit()

print('Webcam opened! Running inference...')
print()

mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

for i in range(10):
    ret, frame = cap.read()
    if not ret:
        print('Failed to grab frame')
        break

    img = cv2.resize(frame, (224, 224))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.0
    img = (img - mean) / std
    img = img.transpose(2, 0, 1)
    img = np.expand_dims(img, 0)

    start = time.time()
    outputs = session.run(None, {input_name: img})
    elapsed = time.time() - start

    scores = outputs[0][0]
    top3 = np.argsort(scores)[::-1][:3]

    print("Frame", i+1, "(", round(elapsed*1000), "ms ):")
    for idx in top3:
        print(" ", labels[idx], round(float(scores[idx]), 3))
    print()

cap.release()
print("Done!")
