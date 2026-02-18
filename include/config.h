#pragma once

#include <Arduino.h>

namespace cfg {

constexpr const char *kDeviceName = "esp32-smart-led";
constexpr const char *kTimezone = "America/New_York";
constexpr const char *kNtpServer = "pool.ntp.org";

constexpr uint8_t LED_PIN = 5;
constexpr uint8_t LED_CLK_PIN = 255; // unused for WS2812B
constexpr uint16_t LED_COUNT = 150;
constexpr bool GAMMA_CORRECTION = true;

constexpr uint8_t DEFAULT_BRIGHTNESS = 96;
constexpr uint16_t MAX_CURRENT_MA = 3000;
constexpr uint8_t DEFAULT_SPEED = 80;

constexpr uint8_t BUTTON_GPIO = 0;
constexpr uint8_t PIR_GPIO = 27;
constexpr uint8_t LDR_GPIO = 34;
constexpr int LDR_DARK_THRESHOLD = 1400;

constexpr const char *MQTT_BROKER = "192.168.1.10";
constexpr uint16_t MQTT_PORT = 1883;
constexpr const char *MQTT_BASE_TOPIC = "led/room1";

constexpr uint32_t WIFI_RECONNECT_MS = 10000;
constexpr uint32_t MQTT_RECONNECT_MS = 5000;
constexpr uint32_t STATE_PUBLISH_MS = 15000;
constexpr uint32_t STORAGE_SAVE_DEBOUNCE_MS = 2000;
constexpr uint32_t MOTION_HOLD_MS = 60000;

constexpr uint8_t NIGHT_BRIGHTNESS_PERCENT_CAP = 20;

} // namespace cfg
