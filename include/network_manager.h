#pragma once

#include <WebServer.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "types.h"

class CoreController;

class NetworkManager {
public:
  void begin(CoreController *core);
  void update(uint32_t nowMs);
  void publishState(const SceneSettings &settings, const RuntimeFlags &flags, ControllerState controllerState, bool force = false);

private:
  void ensureWiFi(uint32_t nowMs);
  void ensureMqtt(uint32_t nowMs);
  void setupHttpRoutes();
  void mqttCallback(char *topic, uint8_t *payload, unsigned int length);
  bool parseSetPayload(const JsonDocument &doc, SceneSettings &out, AlertType &alert);

  WiFiClient wifiClient_;
  PubSubClient mqtt_{wifiClient_};
  WebServer server_{80};
  CoreController *core_ = nullptr;
  uint32_t lastWifiAttempt_ = 0;
  uint32_t lastMqttAttempt_ = 0;
  uint32_t lastStatePublish_ = 0;
};
