#include "DualTB9051FTGMotorShield.h"
#include <ServoTimer2.h>

DualTB9051FTGMotorShield md;

const int MOTOR_SPEED = 250;
const int STALL_THRESHOLD = 3000;

int currentM1 = 0;
int currentM2 = 0;

ServoTimer2 myservo;
const int SERVO_PIN = 3;

int servoPos = 1500;
int servoDirection = 0;
const int SERVO_STEP_DELAY = 20;
unsigned long lastServoUpdate = 0;

String inputBuffer = "";

void stopIfFault() {
  if (md.getM1Fault()) {
    Serial.println("M1 fault");
    md.disableDrivers();
    while (1) { delay(10); }
  }
  if (md.getM2Fault()) {
    Serial.println("M2 fault");
    md.disableDrivers();
    while (1) { delay(10); }
  }
}

void setBothMotors(int m1, int m2) {
  currentM1 = m1;
  currentM2 = m2;
  md.setM1Speed(m1);
  md.setM2Speed(m2);
  stopIfFault();
}

void checkStall() {
  if (currentM1 == 0 && currentM2 == 0) return;
  int m1Current = md.getM1CurrentMilliamps();
  int m2Current = md.getM2CurrentMilliamps();
  if (m1Current > STALL_THRESHOLD || m2Current > STALL_THRESHOLD) {
    currentM1 = 0;
    currentM2 = 0;
    md.setM1Speed(0);
    md.setM2Speed(0);
    Serial.println("Motors: Stall detected, auto stopped");
    Serial.print("M1: "); Serial.print(m1Current);
    Serial.print("mA | M2: "); Serial.print(m2Current); Serial.println("mA");
  }
}

void parseAndDrive(String msg) {
  msg.trim();
  if (!msg.startsWith("<") || !msg.endsWith(">")) return;
  msg = msg.substring(1, msg.length() - 1);

  String parts[14];
  for (int i = 0; i < 14; i++) {
    int comma = msg.indexOf(',');
    if (comma == -1) { parts[i] = msg; break; }
    parts[i] = msg.substring(0, comma);
    msg = msg.substring(comma + 1);
  }

  float rx = parts[8].toFloat();  // dpx
  float ry = parts[9].toFloat();  // dpy
  int a    = parts[4].toInt();
  int b    = parts[5].toInt();

  // forward/back
  if (ry > 0.2) {
    setBothMotors(-MOTOR_SPEED, -MOTOR_SPEED);
  } else if (ry < -0.2) {
    setBothMotors(MOTOR_SPEED, MOTOR_SPEED);
  } else if (rx > 0.2) {
    setBothMotors(MOTOR_SPEED, -MOTOR_SPEED);   // turn right
  } else if (rx < -0.2) {
    setBothMotors(-MOTOR_SPEED, MOTOR_SPEED);   // turn left
  } else {
    setBothMotors(0, 0);
  }

  // claw
  if (a)      servoDirection =  1;
  else if (b) servoDirection = -1;
  else        servoDirection =  0;
}

void setup() {
  Serial.begin(115200);
  Serial.println("TB9051FTG + Servo Control");

  md.init();
  md.enableDrivers();
  delay(2);
  md.flipM2(true);
  setBothMotors(0, 0);

  myservo.attach(SERVO_PIN);
  myservo.write(servoPos);
}

void loop() {
  stopIfFault();
  checkStall();

  if (servoDirection != 0 && millis() - lastServoUpdate >= SERVO_STEP_DELAY) {
    lastServoUpdate = millis();
    servoPos += servoDirection * 10;
    servoPos = constrain(servoPos, 750, 2250);
    myservo.write(servoPos);
  }

  while (Serial.available()) {
    char c = Serial.read();
    inputBuffer += c;
    if (c == '\n') {
      parseAndDrive(inputBuffer);
      inputBuffer = "";
    }
  }
}