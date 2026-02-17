import unittest

from logistics import LogisticsService, SAMPLE_SEGMENTS


class LogisticsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LogisticsService(SAMPLE_SEGMENTS)

    def test_find_route_sequence(self):
        routes = self.service.find_route_sequence("Алматы", "Астана", "08:00")
        self.assertEqual([r.route_id for r in routes], ["R1", "R2"])

    def test_book_seats(self):
        booking = self.service.book_seats("R1", "Алия", 3)
        self.assertEqual(booking.booking_id, 1)
        self.assertEqual(self.service.segments["R1"].available_seats, 17)

    def test_register_parcel(self):
        parcel = self.service.register_parcel("R3", "Бек", "Руслан", "Документы")
        self.assertEqual(parcel.parcel_id, 1)
        self.assertEqual(parcel.description, "Документы")


if __name__ == "__main__":
    unittest.main()
