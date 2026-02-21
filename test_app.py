import unittest

import app


class AppRenderingTests(unittest.TestCase):
    def test_render_page_contains_advanced_navigation_ui(self):
        page = app.render_page()
        self.assertIn("Центральная навигация", page)
        self.assertIn("tab-guide", page)
        self.assertIn("departures-refresh", page)
        self.assertIn("recent-searches", page)
        self.assertIn("heal-now", page)
        self.assertIn("Enterprise-уровень", page)
        self.assertIn("contact-form", page)
        self.assertIn("cancel-booking-form", page)
        self.assertIn("route-admin-form", page)
        self.assertIn("photo-gallery", page)
        self.assertIn("unsplash.com", page)

    def test_manifest_data_is_pwa_ready(self):
        self.assertEqual(app.MANIFEST_JSON["display"], "standalone")
        self.assertEqual(app.MANIFEST_JSON["start_url"], "/")
        self.assertIn("Логистика", app.MANIFEST_JSON["short_name"])

    def test_segment_to_dict(self):
        seg = app.service_manager.service.segments["R1"]
        payload = app.segment_to_dict(seg)
        self.assertEqual(payload["route_id"], "R1")
        self.assertIn("available_seats", payload)

    def test_build_navigation_guide(self):
        route = [app.service_manager.service.segments["R1"], app.service_manager.service.segments["R2"]]
        guide = app.build_navigation_guide(route)
        self.assertEqual(guide["transfers_count"], 1)
        self.assertEqual(guide["total_duration_minutes"], 450)
        self.assertEqual(guide["segments"][0]["wait_minutes"], 60)

    def test_get_departures_filtered(self):
        dep = app.get_departures("Алматы", 5)
        self.assertEqual([d["route_id"] for d in dep], ["R1", "R3"])

    def test_self_healing_manager_manual_heal(self):
        manager = app.SelfHealingLogistics(app.SAMPLE_SEGMENTS)
        booking = manager.run(lambda svc: svc.book_seats("R1", "Тест", 2), "book")
        manager.record_booking(booking)
        manager.heal("manual")
        self.assertEqual(manager.heal_count, 1)
        self.assertEqual(manager.service.segments["R1"].available_seats, 18)

    def test_contact_request_validation(self):
        self.assertTrue("/api/contact" in app.__dict__["render_page"]())
        self.assertTrue("/api/route/upsert" in app.__dict__["LogisticsHandler"].do_POST.__code__.co_consts)
        self.assertTrue("/api/docs" in app.__dict__["LogisticsHandler"].do_GET.__code__.co_consts)

    def test_self_healing_validation_error_does_not_trigger_heal(self):
        manager = app.SelfHealingLogistics(app.SAMPLE_SEGMENTS)
        with self.assertRaises(ValueError):
            manager.run(lambda svc: svc.book_seats("R1", "Тест", 9999), "book_invalid")
        self.assertEqual(manager.heal_count, 0)


if __name__ == "__main__":
    unittest.main()
