#include <Servo.h>

Servo esc;

const int escPin = 9;  
const int minThrottle = 1000;   // full reverse
const int neutral = 1500;       // stop
const int maxThrottle = 2000;   // full forward

void setup() {
  Serial.begin(9600);
  esc.attach(escPin, minThrottle, maxThrottle);

  // Arm ESC
  Serial.println("Arming ESC...");
  esc.writeMicroseconds(neutral);
  delay(5000);
  Serial.println("ESC armed!");
  Serial.println("Commands: f <0-100>, b <0-100>, 0 0 = stop");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() < 3) return;

    char dir = input.charAt(0);
    int speed = input.substring(2).toInt();
    speed = constrain(speed, 0, 100);

    int pwm = neutral;  // default stop
    if (dir == 'f') {
      pwm = map(speed, 0, 100, neutral, maxThrottle);
    } else if (dir == 'b') {
      pwm = map(speed, 0, 100, neutral, minThrottle);
    } else if (dir == '0') {
      pwm = neutral;  // stop
    } else {
      Serial.println("Invalid command");
      return;
    }

    esc.writeMicroseconds(pwm);
    Serial.print("Dir: "); Serial.print(dir);
    Serial.print(" | Speed: "); Serial.println(speed);
  }
}
