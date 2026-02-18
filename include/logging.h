#pragma once

#include <Arduino.h>

#define LOGI(fmt, ...) Serial.printf("[INFO] " fmt "\n", ##__VA_ARGS__)
#define LOGW(fmt, ...) Serial.printf("[WARN] " fmt "\n", ##__VA_ARGS__)
#define LOGE(fmt, ...) Serial.printf("[ERROR] " fmt "\n", ##__VA_ARGS__)
