#include "core_controller.h"

#include <time.h>

#include "config.h"
#include "logging.h"

namespace {
SceneId nextScene(SceneId s) {
  int idx = static_cast<int>(s);
  idx++;
  if (idx > static_cast<int>(SceneId::RAINBOW_SLOW)) idx = static_cast<int>(SceneId::WARM_SOLID);
  return static_cast<SceneId>(idx);
}
} // namespace

void CoreController::begin() {
  storage_.begin();
  storage_.load(active_);
  manual_ = active_;
  automationScene_ = active_;

  led_.begin();
  input_.begin();
  automation_.begin();
  network_.begin(this);

  configTzTime(cfg::kTimezone, cfg::kNtpServer);
  led_.setState(active_, true);
  state_ = active_.power ? ControllerState::ON : ControllerState::OFF;
  LOGI("Controller started");
}

SceneSettings CoreController::makeCircadianAdjusted(SceneSettings in) const {
  struct tm ti;
  if (!getLocalTime(&ti, 5)) return in;
  int h = ti.tm_hour;
  if (h >= 9 && h < 17) {
    in.scene = SceneId::COOL_SOLID;
    in.color = 0xC8E6FF;
  } else if (h >= 17 && h < 23) {
    in.scene = SceneId::WARM_SOLID;
    in.color = 0xFFA062;
  }
  return in;
}

SceneSettings CoreController::applyNightCaps(const SceneSettings &base) const {
  SceneSettings out = base;
  RuntimeFlags flags = automation_.getFlags();
  if (flags.nightMode) {
    uint8_t cap = static_cast<uint8_t>(255 * cfg::NIGHT_BRIGHTNESS_PERCENT_CAP / 100);
    if (out.brightness > cap) out.brightness = cap;
  }
  return out;
}

void CoreController::applyCommand(const SceneSettings &settings, SourcePriority priority) {
  if (priority < activePriority_ && !led_.isAlertActive()) {
    return;
  }
  activePriority_ = priority;

  SceneSettings adjusted = applyNightCaps(makeCircadianAdjusted(settings));
  active_ = adjusted;

  if (!active_.power) {
    state_ = ControllerState::OFF;
    active_.scene = SceneId::OFF;
  } else if (active_.scene == SceneId::FIRE || active_.scene == SceneId::RAINBOW_SLOW || active_.scene == SceneId::GRADIENT) {
    state_ = ControllerState::EFFECT;
  } else {
    state_ = ControllerState::TRANSITION;
  }

  led_.setState(active_, false);
  if (priority == SourcePriority::MANUAL) {
    manual_ = settings;
    savePending_ = true;
    lastSaveRequestMs_ = millis();
  }
  network_.publishState(active_, automation_.getFlags(), state_, true);
}

void CoreController::triggerAlert(AlertType alertType) {
  if (alertType == AlertType::NONE) return;
  led_.setAlert(alertType);
  state_ = ControllerState::ALERT;
  activePriority_ = SourcePriority::ALERT;
  network_.publishState(active_, automation_.getFlags(), state_, true);
}

void CoreController::handleButton(ButtonEvent ev) {
  if (ev == ButtonEvent::SHORT_PRESS) {
    SceneSettings s = manual_;
    s.power = !s.power;
    if (s.power && s.scene == SceneId::OFF) s.scene = SceneId::WARM_SOLID;
    applyCommand(s, SourcePriority::MANUAL);
  } else if (ev == ButtonEvent::DOUBLE_PRESS) {
    SceneSettings s = manual_;
    s.power = true;
    s.scene = nextScene(s.scene);
    applyCommand(s, SourcePriority::MANUAL);
  } else if (ev == ButtonEvent::HOLD_STEP) {
    SceneSettings s = manual_;
    int step = dimPingPongUp_ ? 4 : -4;
    int b = s.brightness + step;
    if (b >= 255) {
      b = 255;
      dimPingPongUp_ = false;
    }
    if (b <= 5) {
      b = 5;
      dimPingPongUp_ = true;
    }
    s.brightness = b;
    applyCommand(s, SourcePriority::MANUAL);
  }
}

void CoreController::update() {
  uint32_t nowMs = millis();

  input_.update(nowMs);
  handleButton(input_.popEvent());

  automation_.update(nowMs);
  RuntimeFlags flags = automation_.getFlags();

  if (automation_.hasMotionSceneRequest()) {
    applyCommand(automation_.motionSceneRequest(), SourcePriority::AUTOMATION);
    automation_.clearMotionSceneRequest();
  } else if (activePriority_ == SourcePriority::AUTOMATION && !flags.motionActive) {
    applyCommand(manual_, SourcePriority::MANUAL);
  }

  if (!led_.isAlertActive() && activePriority_ == SourcePriority::ALERT) {
    activePriority_ = SourcePriority::MANUAL;
    applyCommand(manual_, SourcePriority::MANUAL);
  }

  if (state_ != ControllerState::ALERT) {
    if (!active_.power) state_ = ControllerState::OFF;
    else if (flags.nightMode) state_ = ControllerState::SLEEP;
    else state_ = ControllerState::ON;
  }

  led_.update(nowMs, flags);
  network_.update(nowMs);
  network_.publishState(active_, flags, state_);

  if (savePending_ && (nowMs - lastSaveRequestMs_ > cfg::STORAGE_SAVE_DEBOUNCE_MS)) {
    storage_.save(manual_);
    savePending_ = false;
  }
}

SceneSettings CoreController::currentSettings() const { return active_; }
RuntimeFlags CoreController::currentFlags() const { return automation_.getFlags(); }
ControllerState CoreController::currentState() const { return state_; }
