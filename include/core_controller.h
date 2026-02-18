#pragma once

#include "automation_engine.h"
#include "input_manager.h"
#include "led_engine.h"
#include "network_manager.h"
#include "storage_manager.h"

class CoreController {
public:
  void begin();
  void update();

  void applyCommand(const SceneSettings &settings, SourcePriority priority);
  void triggerAlert(AlertType alertType);

  SceneSettings currentSettings() const;
  RuntimeFlags currentFlags() const;
  ControllerState currentState() const;

private:
  void handleButton(ButtonEvent ev);
  SceneSettings applyNightCaps(const SceneSettings &base) const;
  SceneSettings makeCircadianAdjusted(SceneSettings in) const;

  StorageManager storage_;
  LedEngine led_;
  AutomationEngine automation_;
  InputManager input_;
  NetworkManager network_;

  SceneSettings active_{};
  SceneSettings manual_{};
  SceneSettings automationScene_{};
  SourcePriority activePriority_ = SourcePriority::DEFAULT;
  ControllerState state_ = ControllerState::OFF;

  uint32_t lastSaveRequestMs_ = 0;
  bool savePending_ = false;
  bool dimPingPongUp_ = true;
};
