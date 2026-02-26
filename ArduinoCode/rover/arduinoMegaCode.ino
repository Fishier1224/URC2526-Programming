#include <Servo.h>

Servo esc1;  // old flipsky (pin 10)
Servo esc2;  // dual flipsky (pin 9)

const int escPin1 = 10;
const int escPin2 = 9;

const int min1 = 1160; // 1160
const int neutral1 = 1500; // 1500
const int max1 = 1840; // 1840

const int max2 = 1079; // 1079
const int neutral2 = 1280; // 1280
const int min2 = 1535; // 1535

int currentPWM1 = neutral1;
int currentPWM2 = neutral2;

String inputBuffer = "";

void setup() {
  Serial.begin(115200);

  esc1.attach(escPin1);
  esc2.attach(escPin2, min2, max2);

  //Serial.println("Arming ESCs...");
  esc1.writeMicroseconds(neutral1);
  esc2.writeMicroseconds(neutral2);
  delay(2000);

  esc1.writeMicroseconds(neutral1);
  esc2.writeMicroseconds(neutral2);
  delay(3000);

  //Serial.println("ESCs armed! Awaiting joystick input.");
}

// Map float -1.0 to 1.0 → PWM range, with neutral at 0
int mapAxis(float val, int minPWM, int neutralPWM, int maxPWM) {
  if (val >= 0.0) {
    return (int)(neutralPWM + val * (maxPWM - neutralPWM));
  } else {
    return (int)(neutralPWM + val * (neutralPWM - minPWM));
  }
}

void parseAndDrive(String msg) {
  msg.trim();
  if (msg.startsWith("<") && msg.endsWith(">")) {
    msg = msg.substring(1, msg.length() - 1);

    // parse all 14 fields: lx,ly,rx,ry,a,b,x,y,dpx,dpy,lb,rb,lt,rt
    float fields[4];
    String tmp = msg;
    for (int i = 0; i < 4; i++) {
      int comma = tmp.indexOf(',');
      if (comma == -1) return;
      fields[i] = tmp.substring(0, comma).toFloat();
      tmp = tmp.substring(comma + 1);
    }
    // skip the remaining 10 integer fields for now
    float lx = fields[0];
    float ly = fields[1];

    float left  = constrain(ly + lx, -1.0, 1.0);
    float right = constrain(ly - lx, -1.0, 1.0);

    currentPWM1 = mapAxis(left,  min1, neutral1, max1);
    currentPWM2 = mapAxis(right, min2, neutral2, max2);
  }
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