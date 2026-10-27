#include <Arduino.h>

void setup() {
    Serial.begin(115200);
    delay(2000);

    Serial.println("QuietCity - Sensor Initialised!");
}

void loop() {
    Serial.println("senseBox running...");
    delay(1000);
}