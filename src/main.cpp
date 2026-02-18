#include <Arduino.h>

#include "core_controller.h"

CoreController gCore;

void setup() {
  Serial.begin(115200);
  delay(200);
  gCore.begin();
}

void loop() { gCore.update(); }
