#include <Servo.h>
#include <SoftwareSerial.h>

Servo esc1;  // old flipsky (pin 10)
Servo esc2;  // dual flipsky (pin 9)

const int escPin1 = 10;
const int escPin2 = 9;

const int min1 = 1160;
const int neutral1 = 1500;
const int max1 = 1840;

const int max2 = 1079;
const int neutral2 = 1280;
const int min2 = 1535;

int currentPWM1 = neutral1;
int currentPWM2 = neutral2;

#define rxPin1 16
#define txPin1 17
#define rxPin2 14
#define txPin2 15

#define SPEED 2000
#define STOP_SPEED 0

SoftwareSerial smc1(rxPin1, txPin1);
SoftwareSerial smc2(rxPin2, txPin2);

String inputBuffer = "";

void exitSafeStart(SoftwareSerial &smc) {
  smc.write(0x83);
}

void setMotorSpeed(SoftwareSerial &smc, int speed) {
  if (speed < 0) {
    smc.write(0x86);
    speed = -speed;
  } else {
    smc.write(0x85);
  }
  smc.write(speed & 0x1F);
  smc.write((speed >> 5) & 0x7F);
}

void setup() {
  Serial.begin(115200);

  esc1.attach(escPin1);
  esc2.attach(escPin2, min2, max2);
  esc1.writeMicroseconds(neutral1);
  esc2.writeMicroseconds(neutral2);
  delay(2000);
  esc1.writeMicroseconds(neutral1);
  esc2.writeMicroseconds(neutral2);
  delay(3000);

  smc1.begin(19200);
  smc2.begin(19200);
  delay(5);
  smc1.write(0xAA);
  smc2.write(0xAA);
  exitSafeStart(smc1);
  exitSafeStart(smc2);
}

int mapAxis(float val, int minPWM, int neutralPWM, int maxPWM) {
  if (val >= 0.0) return (int)(neutralPWM + val * (maxPWM - neutralPWM));
  else            return (int)(neutralPWM + val * (neutralPWM - minPWM));
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

  float lx = parts[0].toFloat();
  float ly = parts[1].toFloat();
  int lb   = parts[10].toInt();  // actuator 1 retract
  int lt   = parts[12].toInt();  // actuator 1 extend
  int rb   = parts[11].toInt();  // actuator 2 retract
  int rt   = parts[13].toInt();  // actuator 2 extend

  // drive
  float left  = constrain(ly + lx, -1.0, 1.0);
  float right = constrain(ly - lx, -1.0, 1.0);
  currentPWM1 = mapAxis(left,  min1, neutral1, max1);
  currentPWM2 = mapAxis(right, min2, neutral2, max2);

  // actuator 1: lt = extend, lb = retract
  if (lt)      setMotorSpeed(smc1,  SPEED);
  else if (lb) setMotorSpeed(smc1, -SPEED);
  else         setMotorSpeed(smc1,  STOP_SPEED);

  // actuator 2: rt = extend, rb = retract
  if (rt)      setMotorSpeed(smc2,  -SPEED);
  else if (rb) setMotorSpeed(smc2, SPEED);
  else         setMotorSpeed(smc2,  STOP_SPEED);
}

void loop() {
  esc1.writeMicroseconds(currentPWM1);
  esc2.writeMicroseconds(currentPWM2);

  while (Serial.available()) {
    char c = Serial.read();
    inputBuffer += c;
    if (c == '\n') {
      parseAndDrive(inputBuffer);
      inputBuffer = "";
    }
  }
}