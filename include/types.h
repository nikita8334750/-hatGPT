#pragma once

#include <Arduino.h>

enum class ControllerState : uint8_t {
  OFF,
  ON,
  TRANSITION,
  EFFECT,
  ALERT,
  SLEEP
};

enum class SourcePriority : uint8_t {
  DEFAULT = 0,
  AUTOMATION = 1,
  MANUAL = 2,
  ALERT = 3
};

enum class SceneId : uint8_t {
  OFF = 0,
  WARM_SOLID,
  COOL_SOLID,
  GRADIENT,
  FIRE,
  RAINBOW_SLOW,
  NIGHT_LOW
};

enum class AlertType : uint8_t {
  NONE = 0,
  DOORBELL,
  TIMER,
  CALL
};

struct SceneSettings {
  bool power = true;
  SceneId scene = SceneId::WARM_SOLID;
  uint8_t brightness = 96;
  uint8_t speed = 80;
  uint32_t color = 0xFFA060;
  uint16_t transitionMs = 600;
};

struct RuntimeFlags {
  bool nightMode = false;
  bool doNotDisturb = false;
  bool motionActive = false;
  bool dark = false;
};
