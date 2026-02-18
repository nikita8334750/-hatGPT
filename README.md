# ESP32 Smart LED Firmware (PlatformIO)

Прошивка для ESP32 + адресной ленты (WS2812B/SK6812/APA102 архитектурно, текущая сборка настроена под WS2812B) с:
- сценами, эффектами, ALERT-режимами,
- автоматизациями (night mode, motion+LDR, circadian, DND),
- управлением по MQTT и HTTP,
- OTA, сохранением состояния и ограничением тока.

## Технологический стек
- Framework: Arduino (ESP32)
- Build: PlatformIO
- LED: FastLED
- JSON: ArduinoJson
- MQTT: PubSubClient
- HTTP: встроенный WebServer ESP32
- OTA: ArduinoOTA

> Выбор MQTT библиотеки: `PubSubClient` как самый распространенный и стабильный вариант для ESP32.

## Структура проекта
- `platformio.ini`
- `src/main.cpp`
- `src/core/*`
- `src/led/*`
- `src/net/*`
- `src/automation/*`
- `src/storage/*`
- `include/*`
- `secrets.example.h`

## Конфигурация
1. Скопируйте `secrets.example.h` в `secrets.h`:
   ```bash
   cp secrets.example.h secrets.h
   ```
2. Заполните Wi-Fi доступы в `secrets.h`.
3. При необходимости отредактируйте параметры в `include/config.h`:
   - LED pin/count/type (в коде драйвер FastLED сейчас WS2812B),
   - MQTT broker/base topic,
   - GPIO кнопки/PIR/LDR,
   - лимит тока (`MAX_CURRENT_MA`),
   - timezone/NTP.

## Сборка и прошивка
```bash
pio run
```

Прошивка на устройство:
```bash
pio run -t upload
```

Монитор порта:
```bash
pio device monitor
```

## State machine и приоритеты
Состояния: `OFF / ON / TRANSITION / EFFECT / ALERT / SLEEP`.

Приоритет источников:
`ALERT > Manual > Automation > Default`

## Сцены
1. Off
2. Warm solid (2700K emulation)
3. Cool solid
4. Gradient
5. Fire
6. Rainbow slow
+ `NIGHT_LOW` служебная сцена автоматизации.

## ALERT режимы
- `doorbell` — 3 белых вспышки
- `timer` — оранжевая пульсация 10 сек
- `call` — breathing blue

## MQTT API
Base topic: `led/room1`

### Subscribe/Publish
- `led/room1/set` (input JSON)
- `led/room1/state` (retained JSON)
- `led/room1/availability` (`online/offline`, retained LWT)

### Пример команды
```bash
mosquitto_pub -h 192.168.1.10 -p 1883 -t led/room1/set -m '{"power":true,"scene":5,"brightness":120,"transition_ms":1200}'
```

Alert через MQTT:
```bash
mosquitto_pub -h 192.168.1.10 -p 1883 -t led/room1/set -m '{"alert":"doorbell"}'
```

## HTTP API
- `GET /state`
- `POST /state`
- `POST /alert`

Примеры:
```bash
curl http://<device-ip>/state
curl -X POST http://<device-ip>/state -H 'Content-Type: application/json' -d '{"power":true,"scene":3,"brightness":90}'
curl -X POST http://<device-ip>/alert -H 'Content-Type: application/json' -d '{"alert":"timer"}'
```

## Автоматизации (дефолт)
- Night mode: `23:00-07:00`, ограничение яркости до 20%.
- Motion ночью: если темно + движение => warm low-light на 60 сек.
- Circadian: днем холоднее, вечером теплее.
- DND: ночью блокируются «агрессивные» эффекты (fire -> soft fallback).

## Кнопка
- Short press: toggle on/off
- Double press: next scene
- Long hold: dim up/down (ping-pong)

## Нюансы и как изменить
- Сейчас драйвер FastLED в `LedEngine::begin()` сконфигурирован как `WS2812B`. Для `SK6812` или `APA102` замените шаблон `FastLED.addLeds<...>` (и укажите clock pin для APA102).
- Порог темноты LDR (`LDR_DARK_THRESHOLD`) зависит от делителя — откалибруйте под свою схему.
