#pragma once

#include <Arduino.h>

enum class ButtonEvent : uint8_t {
  NONE = 0,
  SHORT_PRESS,
  DOUBLE_PRESS,
  HOLD_STEP
};

class InputManager {
public:
  void begin();
  void update(uint32_t nowMs);
  ButtonEvent popEvent();

private:
  bool lastState_ = true;
  uint32_t pressStartMs_ = 0;
  uint32_t lastReleaseMs_ = 0;
  bool holdMode_ = false;
  bool dimUp_ = true;
  ButtonEvent pending_ = ButtonEvent::NONE;
};
