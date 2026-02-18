import unittest

import app


class AppRenderingTests(unittest.TestCase):
    def test_render_page_contains_modern_ui_sections(self):
        page = app.render_page()
        self.assertIn("Премиум-диспетчерская перевозок", page)
        self.assertIn("routes-body", page)
        self.assertIn("fetch('/api/state')", page)
        self.assertIn("service-worker.js", page)

    def test_manifest_data_is_pwa_ready(self):
        self.assertEqual(app.MANIFEST_JSON["display"], "standalone")
        self.assertEqual(app.MANIFEST_JSON["start_url"], "/")
        self.assertIn("Логистика", app.MANIFEST_JSON["short_name"])

    def test_segment_to_dict(self):
        seg = app.service.segments["R1"]
        payload = app.segment_to_dict(seg)
        self.assertEqual(payload["route_id"], "R1")
        self.assertIn("available_seats", payload)


if __name__ == "__main__":
    unittest.main()
