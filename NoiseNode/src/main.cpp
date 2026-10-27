#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

#define LED_PIN 1
#define NUM_LEDS 1

Adafruit_NeoPixel led(
    NUM_LEDS,
    LED_PIN,
    NEO_GRB + NEO_KHZ800
);

void setup() {
    Serial.begin(115200);

    led.begin();
    led.setBrightness(30);
    led.clear();
    led.show();
}

void loop() {
    // Red
    led.setPixelColor(0, led.Color(255, 0, 0));
    led.show();
    delay(1000);

    // Green
    led.setPixelColor(0, led.Color(0, 255, 0));
    led.show();
    delay(1000);

    // Blue
    led.setPixelColor(0, led.Color(0, 0, 255));
    led.show();
    delay(1000);

    // Purple
    led.setPixelColor(0, led.Color(128, 0, 255));
    led.show();
    delay(1000);
}