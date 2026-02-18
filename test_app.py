import unittest

import app


class AppRenderingTests(unittest.TestCase):
    def test_render_page_contains_advanced_navigation_ui(self):
        page = app.render_page()
        self.assertIn("Центральная навигация", page)
        self.assertIn("tab-guide", page)
        self.assertIn("departures-refresh", page)
        self.assertIn("recent-searches", page)

    def test_manifest_data_is_pwa_ready(self):
        self.assertEqual(app.MANIFEST_JSON["display"], "standalone")
        self.assertEqual(app.MANIFEST_JSON["start_url"], "/")
        self.assertIn("Логистика", app.MANIFEST_JSON["short_name"])

    def test_segment_to_dict(self):
        seg = app.service.segments["R1"]
        payload = app.segment_to_dict(seg)
        self.assertEqual(payload["route_id"], "R1")
        self.assertIn("available_seats", payload)

    def test_build_navigation_guide(self):
        route = [app.service.segments["R1"], app.service.segments["R2"]]
        guide = app.build_navigation_guide(route)
        self.assertEqual(guide["transfers_count"], 1)
        self.assertEqual(guide["total_duration_minutes"], 450)
        self.assertEqual(guide["segments"][0]["wait_minutes"], 60)

    def test_get_departures_filtered(self):
        dep = app.get_departures("Алматы", 5)
        self.assertEqual([d["route_id"] for d in dep], ["R1", "R3"])


if __name__ == "__main__":
    unittest.main()
