#include "led_engine.h"

#include "config.h"

namespace {
CRGB lerpColor(const CRGB &a, const CRGB &b, float t) {
  return CRGB(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t);
}
} // namespace

void LedEngine::begin() {
  FastLED.addLeds<WS2812B, cfg::LED_PIN, GRB>(leds_, cfg::LED_COUNT);
  FastLED.setMaxPowerInVoltsAndMilliamps(5, cfg::MAX_CURRENT_MA);
  FastLED.clear(true);
  current_.brightness = cfg::DEFAULT_BRIGHTNESS;
  target_ = current_;
  start_ = current_;
}

void LedEngine::setState(const SceneSettings &target, bool immediate) {
  target_ = target;
  if (immediate || target.transitionMs == 0) {
    current_ = target_;
    inTransition_ = false;
    return;
  }
  start_ = current_;
  transitionStartMs_ = millis();
  inTransition_ = true;
}

void LedEngine::setAlert(AlertType type) {
  alertType_ = type;
  alertStartMs_ = millis();
}

bool LedEngine::isAlertActive() const { return alertType_ != AlertType::NONE; }

uint8_t LedEngine::applyGamma(uint8_t v) const {
  if (!cfg::GAMMA_CORRECTION) {
    return v;
  }
  float f = static_cast<float>(v) / 255.0f;
  return static_cast<uint8_t>(powf(f, 2.2f) * 255.0f);
}

CRGB LedEngine::colorFromPacked(uint32_t packed) const {
  return CRGB((packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF);
}

void LedEngine::renderSolid(const CRGB &color, uint8_t brightness) {
  FastLED.setBrightness(applyGamma(brightness));
  fill_solid(leds_, cfg::LED_COUNT, color);
}

void LedEngine::renderGradient(uint32_t nowMs, uint8_t brightness) {
  FastLED.setBrightness(applyGamma(brightness));
  uint8_t phase = (nowMs / 20) % 255;
  for (uint16_t i = 0; i < cfg::LED_COUNT; ++i) {
    leds_[i] = CHSV((phase + i * 2) & 0xFF, 200, 255);
  }
}

void LedEngine::renderFire(uint32_t nowMs, uint8_t brightness) {
  FastLED.setBrightness(applyGamma(brightness));
  for (uint16_t i = 0; i < cfg::LED_COUNT; ++i) {
    uint8_t flicker = random8(120, 255);
    uint8_t wave = sin8((i * 12 + nowMs / 6) & 0xFF);
    leds_[i] = CRGB(flicker, wave / 3, 0);
  }
}

void LedEngine::renderRainbow(uint32_t nowMs, uint8_t brightness) {
  FastLED.setBrightness(applyGamma(brightness));
  fill_rainbow(leds_, cfg::LED_COUNT, (nowMs / 40) & 0xFF, 3);
}

void LedEngine::renderScene(SceneId scene, uint32_t nowMs, const RuntimeFlags &flags, const SceneSettings &settings) {
  switch (scene) {
  case SceneId::OFF:
    renderSolid(CRGB::Black, 0);
    break;
  case SceneId::WARM_SOLID:
    renderSolid(CRGB(255, 147, 41), settings.brightness);
    break;
  case SceneId::COOL_SOLID:
    renderSolid(CRGB(200, 230, 255), settings.brightness);
    break;
  case SceneId::GRADIENT:
    renderGradient(nowMs, settings.brightness);
    break;
  case SceneId::FIRE:
    if (flags.doNotDisturb) {
      renderSolid(CRGB(255, 130, 35), settings.brightness / 2);
    } else {
      renderFire(nowMs, settings.brightness);
    }
    break;
  case SceneId::RAINBOW_SLOW:
    renderRainbow(nowMs, settings.brightness);
    break;
  case SceneId::NIGHT_LOW:
    renderSolid(CRGB(255, 120, 40), settings.brightness);
    break;
  }
}

void LedEngine::update(uint32_t nowMs, const RuntimeFlags &flags) {
  if (alertType_ != AlertType::NONE) {
    uint32_t elapsed = nowMs - alertStartMs_;
    if (alertType_ == AlertType::DOORBELL) {
      bool on = ((elapsed / 180) % 2 == 0) && (elapsed < 1080);
      renderSolid(on ? CRGB::White : CRGB::Black, on ? 255 : 0);
      if (elapsed > 1200) alertType_ = AlertType::NONE;
    } else if (alertType_ == AlertType::TIMER) {
      if (elapsed > 10000) {
        alertType_ = AlertType::NONE;
      } else {
        uint8_t breath = beatsin8(24, 40, 220, 0, elapsed & 0xFF);
        renderSolid(CRGB(255, 120, 0), breath);
      }
    } else if (alertType_ == AlertType::CALL) {
      if (elapsed > 30000) {
        alertType_ = AlertType::NONE;
      }
      uint8_t breath = beatsin8(16, 30, 200, 0, elapsed & 0xFF);
      renderSolid(CRGB(20, 100, 255), breath);
    }
    FastLED.show();
    return;
  }

  if (inTransition_) {
    float t = static_cast<float>(nowMs - transitionStartMs_) / static_cast<float>(target_.transitionMs);
    if (t >= 1.0f) {
      t = 1.0f;
      inTransition_ = false;
      current_ = target_;
    }
    SceneSettings blended = target_;
    blended.brightness = static_cast<uint8_t>(start_.brightness + (target_.brightness - start_.brightness) * t);
    CRGB from = colorFromPacked(start_.color);
    CRGB to = colorFromPacked(target_.color);
    CRGB mixed = lerpColor(from, to, t);
    blended.color = (static_cast<uint32_t>(mixed.r) << 16) | (static_cast<uint32_t>(mixed.g) << 8) | mixed.b;
    renderScene(t < 0.5f ? start_.scene : target_.scene, nowMs, flags, blended);
  } else {
    current_ = target_;
    renderScene(current_.power ? current_.scene : SceneId::OFF, nowMs, flags, current_);
  }
  FastLED.show();
}
