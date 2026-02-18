import tempfile
import unittest

from w212_speedometer import (
    SensorPacket,
    VehicleConfig,
    W212SpeedometerProgram,
    csv_stream,
    instant_fuel_per_100km,
)


class SpeedometerTests(unittest.TestCase):
    def test_instant_fuel_zero_at_low_speed(self):
        self.assertEqual(instant_fuel_per_100km(3.0, 0.5), 0.0)

    def test_trip_and_speed_increase(self):
        app = W212SpeedometerProgram(VehicleConfig(tire_radius_m=0.318, smoothing_alpha=1.0))
        p1 = SensorPacket(timestamp_s=0.0, wheel_rpm=100.0, fuel_lph=4.0, gear="D", outside_temp_c=5.0)
        p2 = SensorPacket(timestamp_s=1.0, wheel_rpm=100.0, fuel_lph=4.0, gear="D", outside_temp_c=5.0)
        s1 = app.process(p1)
        s2 = app.process(p2)

        self.assertGreater(s1.speed_kmh, 0.0)
        self.assertGreater(s2.trip_km, 0.0)

    def test_csv_stream_parse(self):
        content = "timestamp,wheel_rpm,fuel_lph,gear,outside_temp_c\n0,0,1.0,P,6.0\n1,100,4.1,D,6.0\n"
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write(content)
            tmp.flush()
            packets = list(csv_stream(tmp.name))

        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[1].gear, "D")


if __name__ == "__main__":
    unittest.main()
