#pragma once

#include "types.h"

class AutomationEngine {
public:
  void begin();
  void update(uint32_t nowMs);

  RuntimeFlags getFlags() const;
  bool hasMotionSceneRequest() const;
  SceneSettings motionSceneRequest() const;
  void clearMotionSceneRequest();

private:
  bool isNightWindow(int hour) const;
  uint32_t lastMotionMs_ = 0;
  bool motionRequestReady_ = false;
  RuntimeFlags flags_{};
};
