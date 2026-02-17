from logistics import LogisticsService, SAMPLE_SEGMENTS


def print_routes(routes):
    if not routes:
        print("Маршруты не найдены")
        return
    for segment in routes:
        print(
            f"[{segment.route_id}] {segment.departure_city} {segment.departure_time} -> "
            f"{segment.arrival_city} {segment.arrival_time} | водитель: {segment.driver_name} | "
            f"свободно мест: {segment.available_seats}"
        )


def main() -> None:
    service = LogisticsService(SAMPLE_SEGMENTS)

    menu = """
Логистическая программа пассажирских перевозок
1. Найти последовательность маршрута
2. Показать расписание водителя
3. Показать расписание для города (пассажир)
4. Забронировать места
5. Оформить передачку
0. Выход
"""

    while True:
        print(menu)
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            dep = input("Город отправления: ").strip()
            arr = input("Город назначения: ").strip()
            earliest = input("Время не раньше (HH:MM, Enter если не важно): ").strip() or None
            routes = service.find_route_sequence(dep, arr, earliest)
            print_routes(routes)
        elif choice == "2":
            driver = input("Имя водителя: ").strip()
            print_routes(service.schedule_for_driver(driver))
        elif choice == "3":
            city = input("Город: ").strip()
            print_routes(service.schedule_for_passenger(city))
        elif choice == "4":
            route_id = input("ID маршрута: ").strip()
            passenger = input("ФИО пассажира: ").strip()
            seats = int(input("Количество мест: ").strip())
            try:
                booking = service.book_seats(route_id, passenger, seats)
                print(f"Бронь создана: #{booking.booking_id}")
            except ValueError as exc:
                print(f"Ошибка: {exc}")
        elif choice == "5":
            route_id = input("ID маршрута: ").strip()
            sender = input("Отправитель: ").strip()
            recipient = input("Получатель: ").strip()
            description = input("Описание передачи: ").strip()
            try:
                parcel = service.register_parcel(route_id, sender, recipient, description)
                print(f"Передачка оформлена: #{parcel.parcel_id}")
            except ValueError as exc:
                print(f"Ошибка: {exc}")
        elif choice == "0":
            print("Выход из программы")
            break
        else:
            print("Неизвестная команда")


if __name__ == "__main__":
    main()
