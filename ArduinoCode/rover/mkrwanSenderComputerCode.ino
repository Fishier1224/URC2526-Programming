// sender.ino
// Reads controller packet from PC over USB Serial, sends over LoRa P2P

#include <SPI.h>
#include <LoRa.h>

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println("LoRa Sender Ready");

  if (!LoRa.begin(915E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

  LoRa.setSpreadingFactor(7);       // SF7 = fastest, lowest latency
  LoRa.setSignalBandwidth(125E3);
  LoRa.setTxPower(17);

  Serial.println("Waiting for packets from PC...");
}

String inputBuf = "";

void loop() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '<') {
      inputBuf = "<";
    } else if (inputBuf.length() > 0) {
      inputBuf += c;

      // Transmit once we have a complete packet
      if (c == '\n') {
        inputBuf.trim();
        if (inputBuf.startsWith("<") && inputBuf.length() <= 60) {
          LoRa.beginPacket();
          LoRa.print(inputBuf);
          LoRa.endPacket();
        }
        inputBuf = "";
      }

      // Safety: discard if too long
      if (inputBuf.length() > 80) {
        inputBuf = "";
      }
    }
  }
}