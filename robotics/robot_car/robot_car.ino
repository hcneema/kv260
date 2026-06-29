#include <Servo.h>

Servo myServo;

// Servo on Pin 6 (Pin 9 is used by Motor Shield REV3 for Motor A brake)
const int SERVO_PIN = 6;

// Motor Shield REV3 pins - Motor A (left wheel)
const int MOTOR_A_DIR   = 12;
const int MOTOR_A_PWM   = 3;
const int MOTOR_A_BRAKE = 9;

// Motor Shield REV3 pins - Motor B (right wheel)
const int MOTOR_B_DIR   = 13;
const int MOTOR_B_PWM   = 11;
const int MOTOR_B_BRAKE = 8;

const int MOTOR_SPEED = 200; // 0-255

void stopMotors() {
  digitalWrite(MOTOR_A_BRAKE, HIGH);
  digitalWrite(MOTOR_B_BRAKE, HIGH);
  analogWrite(MOTOR_A_PWM, 0);
  analogWrite(MOTOR_B_PWM, 0);
}

void forward() {
  digitalWrite(MOTOR_A_BRAKE, LOW);
  digitalWrite(MOTOR_B_BRAKE, LOW);
  digitalWrite(MOTOR_A_DIR, HIGH);
  digitalWrite(MOTOR_B_DIR, HIGH);
  analogWrite(MOTOR_A_PWM, MOTOR_SPEED);
  analogWrite(MOTOR_B_PWM, MOTOR_SPEED);
}

void backward() {
  digitalWrite(MOTOR_A_BRAKE, LOW);
  digitalWrite(MOTOR_B_BRAKE, LOW);
  digitalWrite(MOTOR_A_DIR, LOW);
  digitalWrite(MOTOR_B_DIR, LOW);
  analogWrite(MOTOR_A_PWM, MOTOR_SPEED);
  analogWrite(MOTOR_B_PWM, MOTOR_SPEED);
}

void turnLeft() {
  digitalWrite(MOTOR_A_BRAKE, LOW);
  digitalWrite(MOTOR_B_BRAKE, LOW);
  digitalWrite(MOTOR_A_DIR, LOW);
  digitalWrite(MOTOR_B_DIR, HIGH);
  analogWrite(MOTOR_A_PWM, MOTOR_SPEED);
  analogWrite(MOTOR_B_PWM, MOTOR_SPEED);
}

void turnRight() {
  digitalWrite(MOTOR_A_BRAKE, LOW);
  digitalWrite(MOTOR_B_BRAKE, LOW);
  digitalWrite(MOTOR_A_DIR, HIGH);
  digitalWrite(MOTOR_B_DIR, LOW);
  analogWrite(MOTOR_A_PWM, MOTOR_SPEED);
  analogWrite(MOTOR_B_PWM, MOTOR_SPEED);
}

void setup() {
  Serial.begin(9600);

  myServo.attach(SERVO_PIN);
  myServo.write(90);

  pinMode(MOTOR_A_DIR,   OUTPUT);
  pinMode(MOTOR_A_PWM,   OUTPUT);
  pinMode(MOTOR_A_BRAKE, OUTPUT);
  pinMode(MOTOR_B_DIR,   OUTPUT);
  pinMode(MOTOR_B_PWM,   OUTPUT);
  pinMode(MOTOR_B_BRAKE, OUTPUT);

  stopMotors();
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if      (cmd == "F") forward();
    else if (cmd == "B") backward();
    else if (cmd == "L") turnLeft();
    else if (cmd == "R") turnRight();
    else if (cmd == "S") stopMotors();
    else {
      int angle = cmd.toInt();
      if (angle >= 0 && angle <= 180) myServo.write(angle);
    }
  }
}
