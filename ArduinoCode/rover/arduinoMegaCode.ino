#include <SoftwareSerial.h>

// --- Pin Definitions ---
#define rxPin1 16   // SMC1 TX -> Mega pin 16 (base actuator)
#define txPin1 17   // SMC1 RX -> Mega pin 17
#define rxPin2 18   // SMC2 TX -> Mega pin 18 (shoulder actuator)
#define txPin2 19   // SMC2 RX -> Mega pin 19

#define SPEED      2000
#define STOP_SPEED 0

SoftwareSerial smc1(rxPin1, txPin1);
SoftwareSerial smc2(rxPin2, txPin2);

// --- SMC Helpers ---
void exitSafeStart(SoftwareSerial &smc) {
  smc.write(0x83);
}

void setMotorSpeed(SoftwareSerial &smc, int speed) {
  if (speed < 0) {
    smc.write(0x86);  // reverse
    speed = -speed;
  } else {
    smc.write(0x85);  // forward (also used for stop at speed=0)
  }
  smc.write(speed & 0x1F);
  smc.write((speed >> 5) & 0x7F);
}

// --- Packet Parsing ---
// Packet format: <lx,ly,rx,ry,a,b,x,y,dpx,dpy,lb,rb,lt,rt>\n
// Index:           0  1  2  3  4 5 6 7  8   9  10  11 12  13

struct ControllerState {
  float lx, ly, rx, ry;
  int   a, b, x, y;
  int   dpx, dpy;
  int   lb, rb, lt, rt;
};

String packetBuf = "";
bool   inPacket  = false;

bool parsePacket(const String &raw, ControllerState &state) {
  // raw is the content between < and >, e.g. "-0.01,0.95,..."
  float vals[4];
  int   ivals[10];
  
  int idx = 0;
  int last = 0;
  String fields[14];
  int fieldCount = 0;

  for (int i = 0; i <= (int)raw.length(); i++) {
    if (i == (int)raw.length() || raw[i] == ',') {
      if (fieldCount >= 14) return false;
      fields[fieldCount++] = raw.substring(last, i);
      last = i + 1;
    }
  }

  if (fieldCount != 14) return false;

  state.lx  = fields[0].toFloat();
  state.ly  = fields[1].toFloat();
  state.rx  = fields[2].toFloat();
  state.ry  = fields[3].toFloat();
  state.a   = fields[4].toInt();
  state.b   = fields[5].toInt();
  state.x   = fields[6].toInt();
  state.y   = fields[7].toInt();
  state.dpx = fields[8].toInt();
  state.dpy = fields[9].toInt();
  state.lb  = fields[10].toInt();
  state.rb  = fields[11].toInt();
  state.lt  = fields[12].toInt();
  state.rt  = fields[13].toInt();

  return true;
}

// --- Control Logic ---
void applyControl(const ControllerState &s) {
  // --- Actuator 1: BASE (LB = extend, LT = retract) ---
  if (s.lb && !s.lt) {
    setMotorSpeed(smc1, SPEED);
    Serial.println("ACT1: Extending");
  } else if (s.lt && !s.lb) {
    setMotorSpeed(smc1, -SPEED);
    Serial.println("ACT1: Retracting");
  } else {
    setMotorSpeed(smc1, STOP_SPEED);
  }

  // --- Actuator 2: SHOULDER (RB = extend, RT = retract) ---
  if (s.rb && !s.rt) {
    setMotorSpeed(smc2, SPEED);
    Serial.println("ACT2: Extending");
  } else if (s.rt && !s.rb) {
    setMotorSpeed(smc2, -SPEED);
    Serial.println("ACT2: Retracting");
  } else {
    setMotorSpeed(smc2, STOP_SPEED);
  }

  // TODO: drive motors  -> use lx, ly, rx, ry, dpx, dpy
  // TODO: claw          -> use a (close), b (open)
  // TODO: other         -> use x, y
}

// --- Setup ---
void setup() {
  smc1.begin(19200);
  smc2.begin(19200);
  Serial.begin(115200);  // Match Jetson bridge baud rate

  delay(10);

  // Init both SMCs
  smc1.write(0xAA);
  smc2.write(0xAA);
  exitSafeStart(smc1);
  exitSafeStart(smc2);

  Serial.println("Rover Mega Ready. Waiting for controller packets...");
}

// --- Loop ---
void loop() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '<') {
      packetBuf = "";
      inPacket  = true;
    } else if (c == '>' && inPacket) {
      inPacket = false;
      ControllerState state;
      if (parsePacket(packetBuf, state)) {
        applyControl(state);
      } else {
        Serial.print("Bad packet: ");
        Serial.println(packetBuf);
      }
      packetBuf = "";
    } else if (inPacket) {
      if (packetBuf.length() < 80) {  // guard against runaway buffer
        packetBuf += c;
      } else {
        // Overflow — discard
        inPacket  = false;
        packetBuf = "";
      }
    }
  }
}