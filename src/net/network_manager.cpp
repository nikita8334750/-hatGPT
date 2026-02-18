#include "network_manager.h"

#include <ArduinoOTA.h>
#include <secrets.h>

#include "config.h"
#include "core_controller.h"
#include "logging.h"

namespace {
String topicSet() { return String(cfg::MQTT_BASE_TOPIC) + "/set"; }
String topicState() { return String(cfg::MQTT_BASE_TOPIC) + "/state"; }
String topicAvailability() { return String(cfg::MQTT_BASE_TOPIC) + "/availability"; }

const char *stateName(ControllerState s) {
  switch (s) {
  case ControllerState::OFF: return "OFF";
  case ControllerState::ON: return "ON";
  case ControllerState::TRANSITION: return "TRANSITION";
  case ControllerState::EFFECT: return "EFFECT";
  case ControllerState::ALERT: return "ALERT";
  case ControllerState::SLEEP: return "SLEEP";
  }
  return "UNKNOWN";
}
} // namespace

void NetworkManager::begin(CoreController *core) {
  core_ = core;
  WiFi.mode(WIFI_STA);
  mqtt_.setServer(cfg::MQTT_BROKER, cfg::MQTT_PORT);
  mqtt_.setCallback([this](char *topic, uint8_t *payload, unsigned int length) { mqttCallback(topic, payload, length); });

  ArduinoOTA.setHostname(cfg::kDeviceName);
  ArduinoOTA.begin();
  setupHttpRoutes();
  server_.begin();
}

void NetworkManager::ensureWiFi(uint32_t nowMs) {
  if (WiFi.status() == WL_CONNECTED) return;
  if (nowMs - lastWifiAttempt_ < cfg::WIFI_RECONNECT_MS) return;
  lastWifiAttempt_ = nowMs;
  LOGI("Connecting WiFi to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void NetworkManager::ensureMqtt(uint32_t nowMs) {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt_.connected()) return;
  if (nowMs - lastMqttAttempt_ < cfg::MQTT_RECONNECT_MS) return;
  lastMqttAttempt_ = nowMs;

  String clientId = String(cfg::kDeviceName) + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  if (mqtt_.connect(clientId.c_str(), topicAvailability().c_str(), 0, true, "offline")) {
    mqtt_.publish(topicAvailability().c_str(), "online", true);
    mqtt_.subscribe(topicSet().c_str());
    LOGI("MQTT connected");
  } else {
    LOGW("MQTT connect failed rc=%d", mqtt_.state());
  }
}

bool NetworkManager::parseSetPayload(const JsonDocument &doc, SceneSettings &out, AlertType &alert) {
  out = core_->currentSettings();
  alert = AlertType::NONE;

  if (doc["power"].is<bool>()) out.power = doc["power"].as<bool>();
  if (doc["brightness"].is<int>()) out.brightness = constrain(doc["brightness"].as<int>(), 0, 255);
  if (doc["speed"].is<int>()) out.speed = constrain(doc["speed"].as<int>(), 1, 255);
  if (doc["transition_ms"].is<int>()) out.transitionMs = constrain(doc["transition_ms"].as<int>(), 0, 10000);
  if (doc["scene"].is<int>()) out.scene = static_cast<SceneId>(constrain(doc["scene"].as<int>(), 0, 6));
  if (doc["color"].is<const char *>()) {
    const char *hex = doc["color"].as<const char *>();
    out.color = strtoul(hex[0] == '#' ? hex + 1 : hex, nullptr, 16);
  }
  if (doc["alert"].is<const char *>()) {
    String a = doc["alert"].as<const char *>();
    if (a == "doorbell") alert = AlertType::DOORBELL;
    if (a == "timer") alert = AlertType::TIMER;
    if (a == "call") alert = AlertType::CALL;
  }
  return true;
}

void NetworkManager::mqttCallback(char *topic, uint8_t *payload, unsigned int length) {
  if (String(topic) != topicSet()) return;
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    LOGW("Bad MQTT JSON: %s", err.c_str());
    return;
  }
  SceneSettings settings;
  AlertType alert;
  parseSetPayload(doc, settings, alert);
  core_->applyCommand(settings, SourcePriority::MANUAL);
  if (alert != AlertType::NONE) {
    core_->triggerAlert(alert);
  }
}

void NetworkManager::setupHttpRoutes() {
  server_.on("/state", HTTP_GET, [this]() {
    JsonDocument doc;
    SceneSettings s = core_->currentSettings();
    RuntimeFlags f = core_->currentFlags();
    doc["power"] = s.power;
    doc["scene"] = static_cast<int>(s.scene);
    doc["brightness"] = s.brightness;
    doc["speed"] = s.speed;
    doc["color"] = s.color;
    doc["transition_ms"] = s.transitionMs;
    doc["night_mode"] = f.nightMode;
    doc["state"] = stateName(core_->currentState());
    String out;
    serializeJson(doc, out);
    server_.send(200, "application/json", out);
  });

  server_.on("/state", HTTP_POST, [this]() {
    if (!server_.hasArg("plain")) {
      server_.send(400, "application/json", "{\"error\":\"missing body\"}");
      return;
    }
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, server_.arg("plain"));
    if (err) {
      server_.send(400, "application/json", "{\"error\":\"bad json\"}");
      return;
    }
    SceneSettings settings;
    AlertType alert;
    parseSetPayload(doc, settings, alert);
    core_->applyCommand(settings, SourcePriority::MANUAL);
    if (alert != AlertType::NONE) core_->triggerAlert(alert);
    server_.send(200, "application/json", "{\"ok\":true}");
  });

  server_.on("/alert", HTTP_POST, [this]() {
    if (!server_.hasArg("plain")) {
      server_.send(400, "application/json", "{\"error\":\"missing body\"}");
      return;
    }
    JsonDocument doc;
    if (deserializeJson(doc, server_.arg("plain"))) {
      server_.send(400, "application/json", "{\"error\":\"bad json\"}");
      return;
    }
    const char *a = doc["alert"] | "";
    AlertType t = AlertType::NONE;
    if (String(a) == "doorbell") t = AlertType::DOORBELL;
    if (String(a) == "timer") t = AlertType::TIMER;
    if (String(a) == "call") t = AlertType::CALL;
    core_->triggerAlert(t);
    server_.send(200, "application/json", "{\"ok\":true}");
  });
}

void NetworkManager::update(uint32_t nowMs) {
  ensureWiFi(nowMs);
  ensureMqtt(nowMs);
  if (mqtt_.connected()) mqtt_.loop();
  server_.handleClient();
  ArduinoOTA.handle();
}

void NetworkManager::publishState(const SceneSettings &settings, const RuntimeFlags &flags, ControllerState controllerState, bool force) {
  uint32_t nowMs = millis();
  if (!mqtt_.connected()) return;
  if (!force && nowMs - lastStatePublish_ < cfg::STATE_PUBLISH_MS) return;

  JsonDocument doc;
  doc["power"] = settings.power;
  doc["scene"] = static_cast<int>(settings.scene);
  doc["brightness"] = settings.brightness;
  doc["speed"] = settings.speed;
  doc["color"] = settings.color;
  doc["transition_ms"] = settings.transitionMs;
  doc["night_mode"] = flags.nightMode;
  doc["dark"] = flags.dark;
  doc["motion"] = flags.motionActive;
  doc["state"] = stateName(controllerState);

  String out;
  serializeJson(doc, out);
  mqtt_.publish(topicState().c_str(), out.c_str(), true);
  lastStatePublish_ = nowMs;
}
