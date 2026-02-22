#include <Servo.h>

Servo myServo;
String input;

void setup() {
  Serial.begin(9600);   // For debugging to PC
  Serial1.begin(9600);  // Communication with MKR WAN 1310
  myServo.attach(10);   // Servo control pin
  myServo.write(0);
  Serial.println("Ready to receive SPIN commands...");
}

void loop() {
  if (Serial1.available()) {
    input = Serial1.readStringUntil('\n');
    input.trim();

    if (input == "SPIN") {
      Serial.println("Running sweep...");
      runSweep();
    }
  }
}

void runSweep() {
  for (int pos = 0; pos <= 180; pos++) {
    myServo.write(pos);
    delay(15);
  }
  for (int pos = 180; pos >= 0; pos--) {
    myServo.write(pos);
    delay(15);
  }
}










