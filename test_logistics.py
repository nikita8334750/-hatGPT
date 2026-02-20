import unittest

from logistics import LogisticsService, RouteSegment, SAMPLE_SEGMENTS


class LogisticsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LogisticsService(SAMPLE_SEGMENTS)

    def test_find_route_sequence(self):
        routes = self.service.find_route_sequence("Алматы", "Астана", "08:00")
        self.assertEqual([r.route_id for r in routes], ["R1", "R2"])

    def test_find_route_sequence_not_found(self):
        routes = self.service.find_route_sequence("Астана", "Алматы", "08:00")
        self.assertEqual(routes, [])

    def test_book_seats(self):
        booking = self.service.book_seats("R1", "Алия", 3)
        self.assertEqual(booking.booking_id, 1)
        self.assertEqual(self.service.segments["R1"].available_seats, 17)

    def test_cancel_booking(self):
        booking = self.service.book_seats("R1", "Алия", 3)
        self.service.cancel_booking(booking.booking_id)
        self.assertEqual(self.service.segments["R1"].available_seats, 20)

    def test_book_seats_over_capacity(self):
        with self.assertRaises(ValueError):
            self.service.book_seats("R1", "Алия", 30)

    def test_register_parcel(self):
        parcel = self.service.register_parcel("R3", "Бек", "Руслан", "Документы")
        self.assertEqual(parcel.parcel_id, 1)
        self.assertEqual(parcel.description, "Документы")

    def test_cancel_parcel(self):
        parcel = self.service.register_parcel("R3", "Бек", "Руслан", "Документы")
        self.service.cancel_parcel(parcel.parcel_id)
        self.assertEqual(self.service.parcels, {})

    def test_upsert_route_and_delete_route(self):
        self.service.upsert_route(RouteSegment("R100", "Астана", "Павлодар", "10:00", "13:00", 25, "Тест Водитель"))
        self.assertIn("R100", self.service.segments)
        self.service.delete_route("R100")
        self.assertNotIn("R100", self.service.segments)

    def test_schedule_for_driver_case_insensitive(self):
        schedule = self.service.schedule_for_driver("иван петров")
        self.assertEqual([s.route_id for s in schedule], ["R1", "R2"])

    def test_schedule_for_passenger_case_insensitive(self):
        schedule = self.service.schedule_for_passenger("астана")
        self.assertEqual([s.route_id for s in schedule], ["R2", "R5"])

    def test_custom_best_route(self):
        custom = LogisticsService(
            [
                RouteSegment("A", "X", "Y", "08:00", "10:00", 5, "D1"),
                RouteSegment("B", "Y", "Z", "10:30", "12:30", 5, "D2"),
                RouteSegment("C", "X", "Z", "09:00", "15:00", 5, "D3"),
            ]
        )
        routes = custom.find_route_sequence("X", "Z", "07:00")
        self.assertEqual([r.route_id for r in routes], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
