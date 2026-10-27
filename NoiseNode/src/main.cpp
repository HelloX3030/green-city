#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "CloudUpload.h"

// DFRobot Gravity analog sound level meter (SEN0232):
// A/signal -> senseBox IO6 (GPIO6), + -> 3.3V, - -> GND.
// Change this pin if the signal is connected to another analogue input.
constexpr uint8_t SOUND_PIN = A6;
constexpr unsigned long READING_INTERVAL_MS = 250;

Adafruit_NeoPixel led(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

void updateNoiseLed(float decibels) {
    uint32_t color;
    if (decibels < 50.0f) {
        color = led.Color(0, 255, 0);     // Green
    } else if (decibels < 65.0f) {
        color = led.Color(255, 255, 0);   // Yellow
    } else if (decibels <= 80.0f) {
        color = led.Color(255, 100, 0);   // Orange
    } else {
        color = led.Color(255, 0, 0);     // Red
    }
    led.setPixelColor(0, color);
    led.show();
}

void setup() {
    Serial.begin(115200);
    led.begin();
    led.setBrightness(30);
    led.clear();
    led.show();

    // Enable power to the senseBox digital/analogue connectors.
    pinMode(IO_ENABLE, OUTPUT);
    digitalWrite(IO_ENABLE, HIGH);
    pinMode(SOUND_PIN, INPUT);
    analogReadResolution(12);
    analogSetPinAttenuation(SOUND_PIN, ADC_11db);

    // Allow USB serial and the sensor to start without waiting indefinitely.
    delay(1000);
    Serial.println("Sound level meter ready (signal: GPIO6, 115200 baud)");
    beginCloudUpload();
}

void loop() {
    static unsigned long lastReading = millis() - READING_INTERVAL_MS;
    const unsigned long now = millis();
    if (now - lastReading < READING_INTERVAL_MS) {
        delay(1); // Yield to the network worker between sensor readings.
        return;
    }
    lastReading = now;
    // Use the ESP32 voltage conversion rather than assuming a linear 3.3V ADC.
    const uint32_t millivolts = analogReadMilliVolts(SOUND_PIN);
    const float voltage = millivolts / 1000.0f;

    // The sensor already measures A-weighted sound level; no FFT/RMS needed.
    // Manufacturer's conversion: 0.6-2.6V corresponds to 30-130 dBA.
    const float decibels = voltage * 50.0f;
    updateNoiseLed(decibels);
    offerCloudMeasurement(decibels);

    Serial.print(decibels, 1);
    Serial.print(" dBA | ");
    Serial.print(voltage, 3);
    Serial.print(" V");
    if (millivolts < 600 || millivolts > 2600) {
        Serial.print(" | outside sensor range (check wiring/power)");
    }
    Serial.println();
}
