// receiver.ino
// Receives LoRa packets and forwards them over USB Serial to Jetson Nano

#include <SPI.h>
#include <LoRa.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println("LoRa Receiver Ready");

  if (!LoRa.begin(915E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    String packet = "";
    while (LoRa.available()) {
      packet += (char)LoRa.read();
    }
    // Forward to Jetson as-is
    Serial.println(packet);
  }
}