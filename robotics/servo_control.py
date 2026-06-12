import serial, time

# Connect to Elegoo Mega on KV260
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
time.sleep(2)  # wait for Mega to initialize

def move_servo(angle):
    ser.write(str(angle).encode())
    time.sleep(0.5)
    response = ser.read_all().decode()
    print(f'Sent {angle} -> {response.strip()}')

# Sweep demo
for angle in [0, 90, 180, 90]:
    move_servo(angle)
    time.sleep(1)

ser.close()
