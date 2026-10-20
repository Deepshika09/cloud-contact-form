"""Static checks that the existing UI is wired for submit + validation.

Does not rewrite frontend files. Fails if the form becomes display-only.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class FrontendWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (FRONTEND / "index.html").read_text(encoding="utf-8")
        cls.app = (FRONTEND / "app.js").read_text(encoding="utf-8")
        cls.config = (FRONTEND / "config.js").read_text(encoding="utf-8")

    def test_required_frontend_files_exist(self):
        for name in ("index.html", "styles.css", "app.js", "config.js", "config.example.js"):
            self.assertTrue((FRONTEND / name).is_file(), msg=f"missing frontend/{name}")

    def test_form_fields_present(self):
        for field_id in ("form", "name", "email", "message", "submit", "banner"):
            self.assertIn(f'id="{field_id}"', self.html)

    def test_scripts_loaded(self):
        self.assertIn('src="config.js"', self.html)
        self.assertIn('src="app.js"', self.html)

    def test_client_validation_implemented(self):
        self.assertIn("function validateClient", self.app)
        self.assertIn("NAME_RE", self.app)
        self.assertIn("EMAIL_RE", self.app)
        self.assertIn("Please fix the highlighted fields.", self.app)

    def test_submission_posts_json_to_api(self):
        self.assertIn("fetch(url", self.app)
        self.assertIn('method: "POST"', self.app)
        self.assertIn("application/json", self.app)
        self.assertIn("JSON.stringify(result.payload)", self.app)

    def test_loading_success_and_failure_states(self):
        self.assertIn("setLoading(true)", self.app)
        self.assertIn('setBanner("success"', self.app)
        self.assertIn("AbortError", self.app)
        self.assertIn("Could not reach the API", self.app)

    def test_local_api_endpoint_configured(self):
        match = re.search(r'apiUrl:\s*"([^"]+)"', self.config)
        self.assertIsNotNone(match)
        url = match.group(1)
        self.assertNotIn("REPLACE_WITH", url)
        self.assertTrue(url.endswith("/contact"), msg=url)
        self.assertTrue(url.startswith("http"), msg=url)


if __name__ == "__main__":
    unittest.main()
