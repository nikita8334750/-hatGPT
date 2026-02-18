#include "automation_engine.h"

#include <time.h>
#include <Arduino.h>

#include "config.h"

void AutomationEngine::begin() {
  pinMode(cfg::PIR_GPIO, INPUT);
  pinMode(cfg::LDR_GPIO, INPUT);
}

bool AutomationEngine::isNightWindow(int hour) const { return hour >= 23 || hour < 7; }

void AutomationEngine::update(uint32_t nowMs) {
  struct tm ti;
  bool timeOk = getLocalTime(&ti, 5);
  int hour = timeOk ? ti.tm_hour : 0;
  flags_.nightMode = isNightWindow(hour);
  flags_.doNotDisturb = flags_.nightMode;

  int ldrValue = analogRead(cfg::LDR_GPIO);
  flags_.dark = ldrValue < cfg::LDR_DARK_THRESHOLD;

  bool motion = digitalRead(cfg::PIR_GPIO) == HIGH;
  if (motion) {
    lastMotionMs_ = nowMs;
  }
  flags_.motionActive = motion || ((nowMs - lastMotionMs_) < cfg::MOTION_HOLD_MS);

  if (flags_.nightMode && flags_.dark && motion) {
    motionRequestReady_ = true;
  }
}

RuntimeFlags AutomationEngine::getFlags() const { return flags_; }

bool AutomationEngine::hasMotionSceneRequest() const { return motionRequestReady_; }

SceneSettings AutomationEngine::motionSceneRequest() const {
  SceneSettings req;
  req.power = true;
  req.scene = SceneId::NIGHT_LOW;
  req.brightness = 35;
  req.color = 0xFF8A40;
  req.transitionMs = 300;
  return req;
}

void AutomationEngine::clearMotionSceneRequest() { motionRequestReady_ = false; }
