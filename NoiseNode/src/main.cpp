#include <Arduino.h>

// DFRobot Gravity analog sound level meter (SEN0232):
// A/signal -> senseBox IO2 (GPIO2), + -> 3.3V, - -> GND.
// Change this pin if the signal is connected to another analogue input.
constexpr uint8_t SOUND_PIN = A2;
constexpr unsigned long READING_INTERVAL_MS = 250;

void setup() {
    Serial.begin(115200);

    // Enable power to the senseBox digital/analogue connectors.
    pinMode(IO_ENABLE, OUTPUT);
    digitalWrite(IO_ENABLE, HIGH);
    pinMode(SOUND_PIN, INPUT);
    analogReadResolution(12);
    analogSetPinAttenuation(SOUND_PIN, ADC_11db);

    // Allow USB serial and the sensor to start without waiting indefinitely.
    delay(1000);
    Serial.println("Sound level meter ready (signal: GPIO2, 115200 baud)");
}

void loop() {
    // Use the ESP32 voltage conversion rather than assuming a linear 3.3V ADC.
    const uint32_t millivolts = analogReadMilliVolts(SOUND_PIN);
    const float voltage = millivolts / 1000.0f;

    // The sensor already measures A-weighted sound level; no FFT/RMS needed.
    // Manufacturer's conversion: 0.6-2.6V corresponds to 30-130 dBA.
    const float decibels = voltage * 50.0f;

    Serial.print(decibels, 1);
    Serial.print(" dBA | ");
    Serial.print(voltage, 3);
    Serial.print(" V");
    if (millivolts < 600 || millivolts > 2600) {
        Serial.print(" | outside sensor range (check wiring/power)");
    }
    Serial.println();
    delay(READING_INTERVAL_MS);