#pragma once

#include <FastLED.h>
#include "types.h"

class LedEngine {
public:
  void begin();
  void setState(const SceneSettings &target, bool immediate = false);
  void setAlert(AlertType type);
  bool isAlertActive() const;
  void update(uint32_t nowMs, const RuntimeFlags &flags);

private:
  void renderScene(SceneId scene, uint32_t nowMs, const RuntimeFlags &flags, const SceneSettings &settings);
  void renderSolid(const CRGB &color, uint8_t brightness);
  void renderGradient(uint32_t nowMs, uint8_t brightness);
  void renderFire(uint32_t nowMs, uint8_t brightness);
  void renderRainbow(uint32_t nowMs, uint8_t brightness);
  CRGB colorFromPacked(uint32_t packed) const;
  uint8_t applyGamma(uint8_t v) const;

  CRGB leds_[150];
  SceneSettings current_{};
  SceneSettings target_{};
  SceneSettings start_{};
  uint32_t transitionStartMs_ = 0;
  bool inTransition_ = false;
  AlertType alertType_ = AlertType::NONE;
  uint32_t alertStartMs_ = 0;
};
