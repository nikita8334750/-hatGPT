#pragma once

#include <Preferences.h>
#include "types.h"

class StorageManager {
public:
  void begin();
  void load(SceneSettings &settings);
  void save(const SceneSettings &settings);

private:
  Preferences prefs_;
};
