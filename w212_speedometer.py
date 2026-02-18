#!/usr/bin/env python3
"""Программа спидометра Mercedes W212 (эмулятор/стенд).

Возможности:
- Расчёт скорости из оборотов колёс и радиуса шины.
- Сглаживание показаний.
- Подсчёт дистанции, времени после старта, текущего и среднего расхода.
- Режимы:
  1) simulator — генератор поездки.
  2) csv — чтение телеметрии из CSV.

CSV формат:
    timestamp,wheel_rpm,fuel_lph,gear,outside_temp_c
    0.0,0,0.8,P,6.0
    0.1,15,1.2,D,6.0
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import time
from dataclasses import dataclass
from typing import Iterable, Iterator


@dataclass(slots=True)
class VehicleConfig:
    """Параметры автомобиля для расчётов."""

    tire_radius_m: float = 0.318
    smoothing_alpha: float = 0.22

    @property
    def wheel_circumference_m(self) -> float:
        return 2 * math.pi * self.tire_radius_m


@dataclass(slots=True)
class SensorPacket:
    timestamp_s: float
    wheel_rpm: float
    fuel_lph: float
    gear: str
    outside_temp_c: float


@dataclass(slots=True)
class DashboardState:
    speed_kmh: float = 0.0
    trip_km: float = 0.0
    elapsed_s: float = 0.0
    avg_fuel_l_100: float = 0.0
    inst_fuel_l_100: float = 0.0
    gear: str = "P"
    outside_temp_c: float = 0.0


class SpeedEstimator:
    def __init__(self, config: VehicleConfig) -> None:
        self.config = config
        self._speed_kmh = 0.0

    def update(self, wheel_rpm: float) -> float:
        wheel_rps = max(wheel_rpm, 0.0) / 60.0
        raw_speed_mps = wheel_rps * self.config.wheel_circumference_m
        raw_speed_kmh = raw_speed_mps * 3.6

        alpha = self.config.smoothing_alpha
        self._speed_kmh = alpha * raw_speed_kmh + (1 - alpha) * self._speed_kmh
        return self._speed_kmh


class TripComputer:
    def __init__(self) -> None:
        self._trip_km = 0.0
        self._elapsed_s = 0.0
        self._fuel_l = 0.0

    def update(self, dt_s: float, speed_kmh: float, fuel_lph: float) -> None:
        self._elapsed_s += max(dt_s, 0.0)
        self._trip_km += max(speed_kmh, 0.0) * max(dt_s, 0.0) / 3600.0
        self._fuel_l += max(fuel_lph, 0.0) * max(dt_s, 0.0) / 3600.0

    @property
    def trip_km(self) -> float:
        return self._trip_km

    @property
    def elapsed_s(self) -> float:
        return self._elapsed_s

    @property
    def avg_fuel_l_100(self) -> float:
        if self._trip_km < 0.01:
            return 0.0
        return self._fuel_l / self._trip_km * 100.0


def instant_fuel_per_100km(fuel_lph: float, speed_kmh: float) -> float:
    if speed_kmh < 1.0:
        return 0.0
    return fuel_lph / speed_kmh * 100.0


class W212SpeedometerProgram:
    def __init__(self, config: VehicleConfig | None = None) -> None:
        self.config = config or VehicleConfig()
        self.speed_estimator = SpeedEstimator(self.config)
        self.trip = TripComputer()
        self.state = DashboardState()
        self._prev_ts: float | None = None

    def process(self, packet: SensorPacket) -> DashboardState:
        speed_kmh = self.speed_estimator.update(packet.wheel_rpm)

        if self._prev_ts is None:
            dt = 0.0
        else:
            dt = packet.timestamp_s - self._prev_ts
        self._prev_ts = packet.timestamp_s

        self.trip.update(dt_s=dt, speed_kmh=speed_kmh, fuel_lph=packet.fuel_lph)

        self.state.speed_kmh = speed_kmh
        self.state.trip_km = self.trip.trip_km
        self.state.elapsed_s = self.trip.elapsed_s
        self.state.avg_fuel_l_100 = self.trip.avg_fuel_l_100
        self.state.inst_fuel_l_100 = instant_fuel_per_100km(packet.fuel_lph, speed_kmh)
        self.state.gear = packet.gear
        self.state.outside_temp_c = packet.outside_temp_c
        return self.state


def format_elapsed(elapsed_s: float) -> str:
    h = int(elapsed_s // 3600)
    m = int((elapsed_s % 3600) // 60)
    return f"{h}:{m:02d} ч"


def render_dashboard(state: DashboardState) -> str:
    return (
        "\n"
        "================ W212 SPEEDOMETER ================\n"
        "После старта\n"
        f"{state.trip_km:6.1f} км              {format_elapsed(state.elapsed_s):>8}\n"
        f"{state.avg_fuel_l_100:6.1f} л/100км        {state.speed_kmh:6.1f} км/ч\n"
        "-----------------------------------------------\n"
        f"{state.outside_temp_c:4.1f} °C              PRND: {state.gear}\n"
        f"Текущий расход: {state.inst_fuel_l_100:4.1f} л/100км\n"
    )


def simulator_stream(duration_s: float, hz: float, outside_temp_c: float = 6.0) -> Iterator[SensorPacket]:
    dt = 1.0 / hz
    steps = int(duration_s * hz)
    for i in range(steps):
        t = i * dt

        if t < 8:
            speed_target = (t / 8) * 70
        elif t < 20:
            speed_target = 70 + math.sin(t) * 4
        elif t < 28:
            speed_target = max(0.0, 70 - (t - 20) * 8.7)
        else:
            speed_target = 0.0

        wheel_rpm = (speed_target / 3.6) / (2 * math.pi * 0.318) * 60
        wheel_rpm += random.uniform(-2.0, 2.0)

        if speed_target < 1.0:
            fuel_lph = 0.9
            gear = "P"
        else:
            fuel_lph = 3.2 + speed_target * 0.08
            gear = "D"

        yield SensorPacket(
            timestamp_s=t,
            wheel_rpm=max(wheel_rpm, 0.0),
            fuel_lph=fuel_lph,
            gear=gear,
            outside_temp_c=outside_temp_c,
        )


def csv_stream(path: str) -> Iterable[SensorPacket]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"timestamp", "wheel_rpm", "fuel_lph", "gear", "outside_temp_c"}
        if not required.issubset(reader.fieldnames or set()):
            missing = required - set(reader.fieldnames or [])
            raise ValueError(f"В CSV не хватает колонок: {', '.join(sorted(missing))}")

        for row in reader:
            yield SensorPacket(
                timestamp_s=float(row["timestamp"]),
                wheel_rpm=float(row["wheel_rpm"]),
                fuel_lph=float(row["fuel_lph"]),
                gear=row["gear"],
                outside_temp_c=float(row["outside_temp_c"]),
            )


def run_program(source: Iterable[SensorPacket], realtime: bool = False, hz: float = 10.0) -> None:
    app = W212SpeedometerProgram()
    sleep_dt = 1.0 / hz
    for packet in source:
        state = app.process(packet)
        print(render_dashboard(state), flush=True)
        if realtime:
            time.sleep(sleep_dt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Эмулятор спидометра W212")
    parser.add_argument("--mode", choices=["simulator", "csv"], default="simulator")
    parser.add_argument("--csv-path", help="Путь к CSV с телеметрией")
    parser.add_argument("--duration", type=float, default=30.0, help="Длительность симуляции в секундах")
    parser.add_argument("--hz", type=float, default=5.0, help="Частота обновления")
    parser.add_argument("--realtime", action="store_true", help="Вывод с реальными паузами")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "simulator":
        source = simulator_stream(duration_s=args.duration, hz=args.hz)
    else:
        if not args.csv_path:
            raise SystemExit("Для режима csv нужно указать --csv-path")
        source = csv_stream(args.csv_path)
    run_program(source, realtime=args.realtime, hz=args.hz)


if __name__ == "__main__":
    main()
