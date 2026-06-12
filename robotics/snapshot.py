import cv2

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    cv2.imwrite('/home/ubuntu/cnn-demo/snapshot.jpg', frame)
    print('Snapshot saved! Size:', frame.shape)
else:
    print('Failed to capture frame')
cap.release()
