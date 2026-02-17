from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import heapq

TIME_FMT = "%H:%M"


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FMT)


@dataclass
class RouteSegment:
    route_id: str
    departure_city: str
    arrival_city: str
    departure_time: str
    arrival_time: str
    capacity: int
    driver_name: str
    available_seats: int = field(init=False)

    def __post_init__(self) -> None:
        self.available_seats = self.capacity


@dataclass
class Booking:
    booking_id: int
    route_id: str
    passenger_name: str
    seats: int


@dataclass
class ParcelOrder:
    parcel_id: int
    route_id: str
    sender_name: str
    recipient_name: str
    description: str


class LogisticsService:
    """Сервис перевозок: маршруты, расписание, бронирование, передачки."""

    def __init__(self, segments: List[RouteSegment]) -> None:
        self.segments: Dict[str, RouteSegment] = {segment.route_id: segment for segment in segments}
        self.bookings: Dict[int, Booking] = {}
        self.parcels: Dict[int, ParcelOrder] = {}
        self._booking_counter = 1
        self._parcel_counter = 1

    def find_route_sequence(
        self,
        departure_city: str,
        arrival_city: str,
        earliest_departure: Optional[str] = None,
    ) -> List[RouteSegment]:
        """Находит последовательность сегментов с минимальным временем прибытия."""
        start_time = parse_time(earliest_departure) if earliest_departure else parse_time("00:00")
        graph: Dict[str, List[RouteSegment]] = {}
        for segment in self.segments.values():
            graph.setdefault(segment.departure_city, []).append(segment)

        pq: List[Tuple[datetime, str, List[str]]] = [(start_time, departure_city, [])]
        visited: Dict[Tuple[str, str], datetime] = {}

        while pq:
            current_time, city, path_ids = heapq.heappop(pq)
            key = (city, ",".join(path_ids))
            if key in visited and visited[key] <= current_time:
                continue
            visited[key] = current_time

            if city == arrival_city:
                return [self.segments[route_id] for route_id in path_ids]

            for segment in graph.get(city, []):
                dep_time = parse_time(segment.departure_time)
                arr_time = parse_time(segment.arrival_time)
                if dep_time >= current_time:
                    heapq.heappush(pq, (arr_time, segment.arrival_city, path_ids + [segment.route_id]))

        return []

    def book_seats(self, route_id: str, passenger_name: str, seats: int) -> Booking:
        if seats <= 0:
            raise ValueError("Количество мест должно быть положительным")

        segment = self.segments.get(route_id)
        if not segment:
            raise ValueError("Маршрут не найден")
        if segment.available_seats < seats:
            raise ValueError("Недостаточно свободных мест")

        segment.available_seats -= seats
        booking = Booking(
            booking_id=self._booking_counter,
            route_id=route_id,
            passenger_name=passenger_name,
            seats=seats,
        )
        self.bookings[self._booking_counter] = booking
        self._booking_counter += 1
        return booking

    def register_parcel(
        self,
        route_id: str,
        sender_name: str,
        recipient_name: str,
        description: str,
    ) -> ParcelOrder:
        if route_id not in self.segments:
            raise ValueError("Маршрут не найден")

        parcel = ParcelOrder(
            parcel_id=self._parcel_counter,
            route_id=route_id,
            sender_name=sender_name,
            recipient_name=recipient_name,
            description=description,
        )
        self.parcels[self._parcel_counter] = parcel
        self._parcel_counter += 1
        return parcel

    def schedule_for_driver(self, driver_name: str) -> List[RouteSegment]:
        return sorted(
            [segment for segment in self.segments.values() if segment.driver_name == driver_name],
            key=lambda x: parse_time(x.departure_time),
        )

    def schedule_for_passenger(self, city: str) -> List[RouteSegment]:
        return sorted(
            [segment for segment in self.segments.values() if segment.departure_city == city or segment.arrival_city == city],
            key=lambda x: parse_time(x.departure_time),
        )


SAMPLE_SEGMENTS = [
    RouteSegment("R1", "Алматы", "Караганда", "08:00", "12:00", 20, "Иван Петров"),
    RouteSegment("R2", "Караганда", "Астана", "13:00", "15:30", 18, "Иван Петров"),
    RouteSegment("R3", "Алматы", "Тараз", "09:00", "11:30", 16, "Сергей Омаров"),
    RouteSegment("R4", "Тараз", "Шымкент", "12:30", "14:00", 16, "Сергей Омаров"),
    RouteSegment("R5", "Шымкент", "Астана", "15:00", "21:00", 12, "Нурлан Абиев"),
]
