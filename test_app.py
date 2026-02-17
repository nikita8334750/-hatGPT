import json
import unittest

import app


class AppRenderingTests(unittest.TestCase):
    def test_render_page_contains_mobile_and_pwa_tags(self):
        page = app.render_page()
        self.assertIn("manifest.webmanifest", page)
        self.assertIn("apple-mobile-web-app-capable", page)
        self.assertIn("mobile-nav", page)
        self.assertIn("service-worker.js", page)

    def test_manifest_is_valid_json(self):
        manifest = json.loads(app.MANIFEST_JSON)
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["start_url"], "/")


if __name__ == "__main__":
    unittest.main()
