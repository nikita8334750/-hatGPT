#include "input_manager.h"

#include "config.h"

void InputManager::begin() {
  pinMode(cfg::BUTTON_GPIO, INPUT_PULLUP);
  lastState_ = digitalRead(cfg::BUTTON_GPIO);
}

void InputManager::update(uint32_t nowMs) {
  bool state = digitalRead(cfg::BUTTON_GPIO);
  if (!state && lastState_) {
    pressStartMs_ = nowMs;
    holdMode_ = false;
  }

  if (!state && !holdMode_ && (nowMs - pressStartMs_ > 450)) {
    holdMode_ = true;
  }

  if (!state && holdMode_ && ((nowMs - pressStartMs_) % 180 < 20)) {
    pending_ = ButtonEvent::HOLD_STEP;
  }

  if (state && !lastState_) {
    uint32_t pressDuration = nowMs - pressStartMs_;
    if (pressDuration < 450) {
      if ((nowMs - lastReleaseMs_) < 320) {
        pending_ = ButtonEvent::DOUBLE_PRESS;
      } else {
        pending_ = ButtonEvent::SHORT_PRESS;
      }
      lastReleaseMs_ = nowMs;
    }
    holdMode_ = false;
  }

  lastState_ = state;
}

ButtonEvent InputManager::popEvent() {
  ButtonEvent ev = pending_;
  pending_ = ButtonEvent::NONE;
  return ev;
}
