#include "storage_manager.h"

void StorageManager::begin() { prefs_.begin("smartled", false); }

void StorageManager::load(SceneSettings &settings) {
  settings.power = prefs_.getBool("power", true);
  settings.scene = static_cast<SceneId>(prefs_.getUChar("scene", static_cast<uint8_t>(SceneId::WARM_SOLID)));
  settings.brightness = prefs_.getUChar("bright", settings.brightness);
  settings.speed = prefs_.getUChar("speed", settings.speed);
  settings.color = prefs_.getUInt("color", settings.color);
  settings.transitionMs = prefs_.getUShort("trans", settings.transitionMs);
}

void StorageManager::save(const SceneSettings &settings) {
  prefs_.putBool("power", settings.power);
  prefs_.putUChar("scene", static_cast<uint8_t>(settings.scene));
  prefs_.putUChar("bright", settings.brightness);
  prefs_.putUChar("speed", settings.speed);
  prefs_.putUInt("color", settings.color);
  prefs_.putUShort("trans", settings.transitionMs);
}
